from pathlib import Path
from types import SimpleNamespace
import importlib.util
import sys
import pytest
from xiaoan_eval_core import model_config as config

@pytest.fixture
def shared(monkeypatch, tmp_path):
    path = tmp_path / '.env'
    values = {'XIAOAN_OPENAI_WIRE_API':'chat_completions', 'XIAOAN_MAX_RETRIES':'0'}
    for provider in config.PROVIDERS:
        family = 'OPENAI' if provider == 'gpt' else provider.upper()
        values[f'XIAOAN_{family}_BASE_URL'] = 'https://configured.invalid/v1'
        values[f'XIAOAN_{family}_API_KEY'] = family + '-synthetic'
        for tier in ('LATEST','SECOND','JUDGE'):
            values[f'XIAOAN_{provider.upper()}_{tier}_MODEL'] = f'{provider}-{tier.lower()}'
    for role in ('JUDGE','SECONDARY_JUDGE','RECOMMENDATION','REPORT','CLAIM_EXTRACTOR','CLAIM_ASSESSOR','SAFETY','ROUTER','RESPONSE'):
        values[f'XIAOAN_{role}_MODEL'] = 'gpt-latest'
    def write(): path.write_text(''.join(f'{k}={v}\n' for k,v in values.items()))
    write(); monkeypatch.setattr(config,'ENV_PATH',path)
    monkeypatch.setenv('XIAOAN_JUDGE_MODEL','stale-process-model')
    return path,values,write

def test_file_authority_no_defaults_and_conflicting_identity(shared):
    path,values,write=shared
    assert config.model('XIAOAN_JUDGE_MODEL')=='gpt-latest'
    values['XIAOAN_JUDGE_MODEL']='gemini-latest';write()
    assert config.model('XIAOAN_JUDGE_MODEL')=='gemini-latest'
    with pytest.raises(ValueError,match='冲突'): config.model('XIAOAN_JUDGE_MODEL','gpt-latest')
    del values['XIAOAN_JUDGE_MODEL'];write()
    with pytest.raises(ValueError,match='XIAOAN_JUDGE_MODEL'): config.model('XIAOAN_JUDGE_MODEL')

@pytest.mark.parametrize('folder',['evaluation','evaluation_multimodels'])
def test_both_evaluator_clients_follow_same_file_and_family(shared,monkeypatch,folder):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('isolated_plugins',root/folder/'company_eval_plugins.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    captured={};monkeypatch.setattr(module,'OpenAI',lambda **kwargs: captured.update(kwargs))
    for model,family in [('claude-latest','CLAUDE'),('gpt-second','OPENAI'),('gemini-judge','GEMINI')]:
        module._openai_client(model)
        assert captured['api_key']==family+'-synthetic'
        assert captured['base_url']=='https://configured.invalid/v1'
    assert module._evaluation_value('XIAOAN_JUDGE_MODEL','hardcoded')=='gpt-latest'
    with pytest.raises(ValueError):module._openai_client('gpt-stale')

def test_matrix_loads_file_without_plugin_import(shared):
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('xiaoan_eval.matrix_config_probe',root/'evaluation_multimodels/xiaoan_eval/multimodel.py')
    module=importlib.util.module_from_spec(spec);sys.modules[spec.name]=module;spec.loader.exec_module(module)
    assert [x.model for x in module.default_subject_specs()]==[f'{p}-{t}' for p in config.PROVIDERS for t in ('latest','second')]
    assert [x.model for x in module.default_judge_specs()]==[f'{p}-judge' for p in config.PROVIDERS]
    with pytest.raises(ValueError):config.validate_matrix_model('gpt','old')

def test_unified_rejects_model_mismatch_before_client(shared,monkeypatch):
    import company_eval_plugins
    from xiaoan_eval.unified import configured_provider
    monkeypatch.setattr(company_eval_plugins,'_openai_client',lambda *a:pytest.fail('must not call client'))
    with pytest.raises(ValueError,match='冲突'):
        configured_provider({'task':'extract_claims','identity':{'provider':'configured','model':'old'}})

@pytest.fixture(autouse=True)
def prohibit_unmocked_network(monkeypatch):
    import httpx
    def reject(*args, **kwargs):
        pytest.fail('Unmocked synchronous HTTP transport')
    async def reject_async(*args, **kwargs):
        pytest.fail('Unmocked asynchronous HTTP transport')
    monkeypatch.setattr(httpx.HTTPTransport, 'handle_request', reject)
    monkeypatch.setattr(httpx.AsyncHTTPTransport, 'handle_async_request', reject_async)


@pytest.fixture
def wire_requests(monkeypatch):
    import httpx
    import json
    captured = []
    def handler(request):
        captured.append(request)
        body = json.loads(request.content)
        if body.get('stream'):
            data = {'choices':[{'delta':{'content':'{}'}}]}
            return httpx.Response(200, text='data: '+json.dumps(data)+'\n\ndata: [DONE]\n\n',
                                  headers={'content-type':'text/event-stream'})
        return httpx.Response(200, json={'id':'mock-response', 'choices':[{'message':{'content':'{}'}}],
                                       'usage':{'prompt_tokens':7,'completion_tokens':2}})
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs))
    return captured


def test_report_agent_model_and_protocol(shared,monkeypatch,wire_requests):
    import json
    root=Path(__file__).resolve().parents[2];monkeypatch.syspath_prepend(str(root))
    from evaluation_report_agent.agent import KaroProvider
    provider=KaroProvider()
    result, usage = provider('synthetic',{})
    assert result == '{}'
    assert usage['input_tokens'] == 7 and usage['output_tokens'] == 2
    body=json.loads(wire_requests[0].content)
    assert provider.model == body['model'] == 'gpt-latest'
    assert str(wire_requests[0].url) == 'https://configured.invalid/v1/chat/completions'
    assert wire_requests[0].headers['authorization'] == 'Bearer OPENAI-synthetic'
    with pytest.raises(ValueError,match='Unconfigured model'):KaroProvider('old')


@pytest.mark.parametrize('provider,selected,tier', [('gpt','gpt-latest','latest'),('claude','claude-judge','judge'),('gemini','gemini-second','second')])
def test_matrix_http_model_key_and_url(shared,monkeypatch,wire_requests,provider,selected,tier):
    import json
    root=Path(__file__).resolve().parents[2]
    spec=importlib.util.spec_from_file_location('http_matrix_plugins',root/'evaluation_multimodels/company_eval_plugins.py')
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    shared[1]['XIAOAN_CLAUDE_API_MODE']='openai';shared[2]()
    monkeypatch.setattr(module,'_judge_response_error',lambda *args:'')
    model=SimpleNamespace(provider=provider,model=selected,tier=tier,reasoning_effort=None)
    module.multimodel_transport(model,'synthetic')
    assert json.loads(wire_requests[0].content)['model']==selected
    assert str(wire_requests[0].url)=='https://configured.invalid/v1/chat/completions'
    family='OPENAI' if provider=='gpt' else provider.upper()
    assert wire_requests[0].headers['authorization']=='Bearer '+family+'-synthetic'
    assert json.loads(wire_requests[0].content)['stream'] is True
    model.model='old'
    with pytest.raises(ValueError):module.multimodel_transport(model,'synthetic')
    assert len(wire_requests)==1


def test_remote_service_preflight_blocks_mismatched_model(shared,monkeypatch):
    from xiaoan_eval.transport import FastAPITransport,TransportError
    transport=FastAPITransport('https://local.invalid',models={'safety':'gpt-latest','router':'gpt-latest','response':'gpt-latest'})
    calls=[]
    def request(method,path):
        calls.append((method,path))
        return {'safety':{'default':'old'}}
    monkeypatch.setattr(transport,'_request_json',request)
    with pytest.raises(TransportError,match='safety model'):transport.create_conversation()
    assert calls==[('GET','/v1/config/models')]
