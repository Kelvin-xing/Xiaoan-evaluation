from xiaoan_eval.frozen_provider import normalize_quote_offsets


def test_claude_tool_use_input_is_decoded_as_json():
    from xiaoan_eval.frozen_provider import response_text
    assert response_text({
        'content': [{'type': 'tool_use', 'name': 'submit_result',
                     'input': {'binding': 'ok', 'claims': []}}]
    }) == '{"binding": "ok", "claims": []}'


def test_claude_empty_max_token_response_is_incomplete():
    import pytest
    from xiaoan_eval.frozen_provider import response_text
    with pytest.raises(ValueError, match='incomplete'):
        response_text({'stop_reason': 'max_tokens', 'content': [{'type': 'thinking'}]})


def test_unique_literal_quote_offsets_repaired_without_changing_text():
    payload={'claims':[{'answer_span':{'start':0,'end':2,'text':'中文'}}]}
    result,repairs=normalize_quote_offsets(payload,{'answer':'前：中文。'})
    assert result['claims'][0]['answer_span']=={'start':2,'end':4,'text':'中文'}
    assert payload['claims'][0]['answer_span']['start']==0
    assert len(repairs)==1


def test_ambiguous_or_missing_quote_never_repaired():
    for text in ('中文','不存在'):
        payload={'claims':[{'answer_span':{'start':99,'end':100,'text':text}}]}
        result,repairs=normalize_quote_offsets(payload,{'answer':'中文，中文'})
        assert result==payload and repairs==[]


def test_assessment_request_names_exact_evidence_domains_and_version():
    from xiaoan_eval_core.contracts import assessment_request
    row={'answer_id':'a','answer':'answer','question':'question','history':[],
         'context_capture':'EXPOSED','context':[{'ref':'ctx:1','content':'quote','layer':'SOURCE'}],
         'reference_facts':[{'ref':'fact:1','content':'fact','layer':'SOURCE'}],
         'truth_status':'approved','truth_version':'v1','requirements':[],'observations':{}}
    inventory={'claims':[],'inventory_id':'i'}
    judge={'id':'fixture'}
    request=assessment_request(row,inventory,judge)
    assert request['validator_version']=='frozen/v3'
    assert 'context refs: ["ctx:1"]' in request['instructions']
    assert 'reference_facts refs: ["fact:1"]' in request['instructions']


def test_provider_repairs_only_deterministic_applicability_and_absence():
    from copy import deepcopy
    payload={'claims':[
        {'id':'s','faithfulness':{'verdict':'ENTAILED','evidence':[{'ref':'answer'}],'reason':'guess'},
         'correctness':{'verdict':'ENTAILED','evidence':[{'ref':'answer'}],'reason':'guess'}},
        {'id':'f','faithfulness':{'verdict':'ENTAILED','evidence':[],'reason':'guess'},
         'correctness':{'verdict':'ENTAILED','evidence':[],'reason':'guess'}}]}
    request={'inventory':{'claims':[{'id':'s','kind':'SUPPORTIVE'},{'id':'f','kind':'FACTUAL'}]},
             'context_capture':'UNAVAILABLE','reference_facts':[]}
    frozen=deepcopy(payload)
    result,repairs=normalize_quote_offsets(payload,request)
    assert payload==frozen
    assert len(repairs)==4
    assert result['claims'][0]['faithfulness']['verdict']=='NOT_APPLICABLE'
    assert result['claims'][0]['correctness']['evidence']==[]
    assert result['claims'][1]['faithfulness']['verdict']=='UNKNOWN'
    assert result['claims'][1]['correctness']['verdict']=='UNKNOWN'


def test_live_provider_binds_its_own_response_but_preserves_raw(monkeypatch,tmp_path):
    import json
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    provider=ConfiguredProvider.__new__(ConfiguredProvider)
    provider.values={};provider.artifact_dir=tmp_path
    raw={'choices':[{'message':{'content':json.dumps({'binding':'mistyped','claims':[]})}}]}
    monkeypatch.setattr(provider,'_request',lambda body:raw)
    result=provider({'task':'extract_claims','identity':{'model':'fixture'},'binding':'expected','answer':'text'})
    assert result['payload']['binding']=='expected'
    assert json.loads(raw['choices'][0]['message']['content'])['binding']=='mistyped'
    receipt=json.loads(next(tmp_path.glob('*normalization.json')).read_text())
    assert receipt['repairs'][0]['rule']=='current-provider-invocation/v1'


def test_deepseek_judge_uses_supported_json_object_format(monkeypatch):
    import json
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    provider = ConfiguredProvider.__new__(ConfiguredProvider)
    provider.values = {'XIAOAN_DEEPSEEK_LATEST_MODEL': 'deepseek-flash',
                       'XIAOAN_DEEPSEEK_WIRE_API': 'chat_completions'}
    provider.artifact_dir = None
    captured = []
    monkeypatch.setattr(provider, '_request', lambda body: captured.append(body) or
                        {'choices': [{'message': {'content': json.dumps({'binding': 'expected'})}}]})
    request = {'task': 'assess_claims', 'identity': {'model': 'deepseek-flash'},
               'response_schema': {'type': 'object'}, 'binding': 'expected'}
    assert provider(request)['payload']['binding'] == 'expected'
    assert captured[0]['response_format'] == {'type': 'json_object'}


def test_other_judges_keep_strict_schema(monkeypatch):
    import json
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    provider = ConfiguredProvider.__new__(ConfiguredProvider)
    provider.values = {'XIAOAN_GPT_LATEST_MODEL': 'gpt-test'}
    provider.artifact_dir = None
    captured = []
    monkeypatch.setattr(provider, '_request', lambda body: captured.append(body) or
                        {'choices': [{'message': {'content': json.dumps({'binding': 'expected'})}}]})
    provider({'task': 'extract_claims', 'identity': {'model': 'gpt-test'},
              'response_schema': {'type': 'object'}, 'binding': 'expected'})
    assert captured[0]['response_format']['json_schema']['strict'] is True


def test_claude_judge_tool_enforces_strict_input_schema():
    from xiaoan_eval_core.llm_adapter import adapt_body
    config = {'XIAOAN_CLAUDE_LATEST_MODEL': 'claude-sonnet-5'}
    body = {'model': 'claude-sonnet-5', 'messages': [{'role': 'user', 'content': 'test'}],
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'xiaoan_rubric', 'strict': True,
                'schema': {'type': 'object', 'properties': {'dimensions': {'type': 'array'}}}}}}
    effective = adapt_body(body, 'messages', config)
    assert effective['tools'][0]['strict'] is True
    body['response_format']['json_schema']['strict'] = False
    assert adapt_body(body, 'messages', config)['tools'][0]['strict'] is False


def test_frozen_provider_reuses_one_http_client_across_worker_threads(monkeypatch):
    from concurrent.futures import ThreadPoolExecutor
    import httpx
    from xiaoan_eval.frozen_provider import ConfiguredProvider

    original = httpx.AsyncClient
    clients = []
    def respond(request):
        return httpx.Response(200, json={'id': 'ok', 'choices': [{'message': {'content': '{}'}}]})
    def build_client(**kwargs):
        client = original(transport=httpx.MockTransport(respond), **kwargs)
        clients.append(client)
        return client
    monkeypatch.setattr(httpx, 'AsyncClient', build_client)
    provider = ConfiguredProvider()
    provider.values = {'XIAOAN_GPT_LATEST_MODEL': 'gpt-test',
                       'XIAOAN_OPENAI_WIRE_API': 'chat_completions',
                       'XIAOAN_OPENAI_BASE_URL': 'https://example.test/v1'}
    body = {'model': 'gpt-test', 'messages': [{'role': 'user', 'content': 'test'}]}
    try:
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(provider._request, [body] * 24))
        assert len(results) == 24
        assert len(clients) == 1
    finally:
        provider.close()
    assert clients[0].is_closed


def test_runtime_requirement_uses_bound_boolean_not_model_opinion():
    payload={'requirements':[{'id':'route','verdict':'VIOLATED','reason':'wrong','answer_spans':[]}]}
    request={'requirements':[{'id':'route','kind':'route'}],'observations':{'route':{'status':'AVAILABLE','value':True}}}
    value,receipts=normalize_quote_offsets(payload,request)
    assert value['requirements'][0]['verdict']=='SATISFIED'
    assert value['requirements'][0]['source']=='deterministic'
    assert receipts[0]['original']['verdict']=='VIOLATED'


def test_identical_duplicate_json_only_is_accepted():
    import pytest
    from xiaoan_eval.frozen_provider import parse_response_json
    assert parse_response_json('{"x":1}{"x":1}')=={'x':1}
    with pytest.raises(ValueError):parse_response_json('{"x":1}{"x":2}')
