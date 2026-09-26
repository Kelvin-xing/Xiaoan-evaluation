"""离线验证真实 SDK 的 HTTP 请求和纯请求体转换。"""
import json
from types import SimpleNamespace
import httpx
import pytest
from openai import OpenAI
from xiaoan_eval_core import llm_adapter as adapter, model_config
import company_eval_plugins as plugins

@pytest.mark.parametrize('model,wire', [('gpt-test','responses'),('o4-mini','responses'),('claude-test','messages'),('gemini-test','gemini_native')])
def test_defaults(model, wire):
    assert adapter.wire_api(model, {}) == wire

def test_file_options_merge_delete_and_isolation(tmp_path, monkeypatch):
    env = tmp_path / '.env'
    env.write_text('XIAOAN_OPENAI_REQUEST_BODY=\'{"reasoning":{"effort":"low"},"temperature":null}\'\nXIAOAN_MODEL_REQUEST_BODIES=\'{"gpt-test":{"reasoning":{"effort":"high"},"max_output_tokens":99}}\'\n')
    monkeypatch.setenv('XIAOAN_OPENAI_REQUEST_BODY', '{"temperature":9}')
    body = {'model':'gpt-test','messages':[{'role':'user','content':'hello'}],'temperature':0.3,'max_tokens':10}
    result = adapter.adapt_body(body,'responses',model_config.read_env(env))
    assert result['reasoning'] == {'effort':'high'}
    assert result['max_output_tokens'] == 99
    assert 'temperature' not in result and 'messages' not in result
    assert body['temperature'] == 0.3

@pytest.mark.parametrize('raw', ['[]','invalid','{"stream":true}','{"extra_body":{"model":"other"}}'])
def test_bad_options(raw):
    with pytest.raises(ValueError):
        adapter.adapt_body({'model':'gpt-test','messages':[]},'responses',{'XIAOAN_OPENAI_REQUEST_BODY':raw})

def test_messages_schema_and_history():
    body = {'model':'claude-test','messages':[{'role':'system','content':'rules'},{'role':'user','content':'hi'},{'role':'assistant','content':'reply'},{'role':'user','content':'next'}], 'reasoning_effort':'high','store':False,'max_tokens':100,'response_format':{'type':'json_schema','json_schema':{'name':'result','schema':{'type':'object'}}}}
    result = adapter.adapt_body(body,'messages',{'XIAOAN_CLAUDE_REQUEST_BODY':'{"temperature":0.5}'})
    assert result['system'] == 'rules'
    assert [m['role'] for m in result['messages']] == ['user','assistant','user']
    assert result['tools'][0]['input_schema'] == {'type':'object'}
    assert result['temperature'] == 0.5
    assert not {'store','reasoning_effort','response_format'} & result.keys()
    assert result['thinking'] == {'type': 'disabled'}

@pytest.mark.parametrize('suffix',['','/messages','/responses','/chat/completions'])
def test_endpoint(suffix):
    assert adapter.endpoint('https://test/v1'+suffix,'responses') == 'https://test/v1/responses'

@pytest.mark.parametrize('model,family,wire', [('gpt-test','OPENAI','responses'), ('claude-test','CLAUDE','messages'), ('gemini-test','GEMINI','gemini_native')])
def test_async_http_contract(model, family, wire, monkeypatch):
    import asyncio
    captured=[]
    def handle(request):
        captured.append(request)
        if wire == 'responses':
            events=[{'type':'response.output_text.delta','delta':'hello'}, {'type':'response.completed','response':{'id':'resp-1','status':'completed','usage':{'input_tokens':3,'output_tokens':2}}}]
        elif wire == 'messages':
            events=[{'type':'content_block_delta','delta':{'text':'hello'}}]
        elif wire == 'gemini_native':
            return httpx.Response(200, json={'responseId':'gem-1','candidates':[{'content':{'parts':[{'text':'hello'}]}}], 'usageMetadata':{'promptTokenCount':3,'candidatesTokenCount':2,'totalTokenCount':5}})
        else:
            events=[{'choices':[{'delta':{'content':'hello'}}]}]
        content=''.join('data: '+json.dumps(e)+'\n\n' for e in events)
        if wire == 'chat_completions': content+='data: [DONE]\n\n'
        return httpx.Response(200, content=content, headers={'Content-Type':'text/event-stream'})
    original=httpx.AsyncClient
    monkeypatch.setattr(httpx,'AsyncClient',lambda **kw:original(transport=httpx.MockTransport(handle),**kw))
    config={f'XIAOAN_{family}_BASE_URL':'https://test',f'XIAOAN_{family}_API_KEY':'test-only', 'XIAOAN_GEMINI_WIRE_API':'gemini_native'}
    result=asyncio.run(adapter.arequest({'model':model,'messages':[{'role':'system','content':'rules'},{'role':'user','content':'hi'}],'max_tokens':99,'stream':True},config,provider=family))
    body=json.loads(captured[0].content)
    assert (str(captured[0].url)==adapter.gemini_endpoint('https://test', model, 'test-only') if wire == 'gemini_native' else str(captured[0].url)==adapter.endpoint('https://test',wire))
    if wire=='messages':
        assert captured[0].headers['x-api-key']=='test-only'
        assert body['system']=='rules' and body['max_tokens']==99
        assert result['content'][0]['text']=='hello'
    elif wire=='responses':
        assert body['max_output_tokens']==99 and 'messages' not in body
        assert result['output_text']=='hello'
    elif wire == 'gemini_native':
        assert body['contents'] == [{'role':'user','parts':[{'text':'hi'}]}]
        assert body['systemInstruction'] == {'parts':[{'text':'rules'}]}
        assert result['choices'][0]['message']['content']=='hello'
        assert captured[0].url.params['key'] == 'test-only'
    else:
        assert result['choices'][0]['message']['content']=='hello'
def test_gemini_assessment_schema_inlines_local_refs():
    from xiaoan_eval_core import llm_adapter as adapter
    from xiaoan_eval_core.configuration import schema
    original=schema('claim-assessment')
    body={'model':'gemini-test','messages':[{'role':'user','content':'synthetic'}],
          'response_format':{'type':'json_schema','json_schema':{'schema':original}}}
    converted=adapter.adapt_gemini_body(body,{})['generationConfig']['responseSchema']
    dimension=converted['properties']['claims']['items']['properties']['faithfulness']
    assert dimension['required']==['verdict','evidence','reason']
    assert dimension['properties']['verdict']['enum']
    assert '$defs' not in converted and '$schema' not in converted
    assert original['properties']['claims']['items']['properties']['faithfulness']=={'$ref':'#/$defs/dimension'}
