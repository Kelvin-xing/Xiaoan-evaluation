import asyncio
import json

import httpx

from xiaoan_eval_core import llm_adapter


def test_karo_rate_limits_event_before_response_created(monkeypatch):
    original = httpx.AsyncClient

    def respond(request):
        events = [
            {'type': 'codex.rate_limits', 'rate_limits': {}},
            {'type': 'response.created', 'response': {'id': 'r1', 'status': 'in_progress'}},
            {'type': 'response.output_text.delta', 'delta': 'hello'},
            {'type': 'response.completed', 'response': {'id': 'r1', 'status': 'completed', 'usage': {'input_tokens': 3}}},
        ]
        return httpx.Response(200, headers={'Content-Type': 'text/event-stream'},
                              text=''.join('data: ' + json.dumps(event) + '\n\n' for event in events))

    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    config = {'XIAOAN_OPENAI_BASE_URL': 'https://api.karoapi.com/v1',
              'XIAOAN_OPENAI_API_KEY': 'fixture', 'XIAOAN_OPENAI_WIRE_API': 'responses'}
    metadata = []

    async def run():
        return [part async for part in llm_adapter.astream(None, {'model': 'gpt-test',
                'messages': [{'role': 'user', 'content': 'hi'}]}, config, completion_callback=metadata.append)]

    assert asyncio.run(run()) == ['hello']
    assert metadata[0]['id'] == 'r1'
    assert metadata[0]['usage']['input_tokens'] == 3


def test_claude_tool_json_stream_is_returned_to_router(monkeypatch):
    original = httpx.AsyncClient
    tool_result = '{"capsule_id":"baseline","confidence":0.8,"reason":"ok","should_continue_active_capsule":false}'

    def respond(request):
        sent = json.loads(request.content)
        assert sent['tool_choice'] == {'type': 'tool', 'name': 'submit_result'}
        events = [
            {'type': 'message_start', 'message': {'id': 'm1', 'usage': {'input_tokens': 5}}},
            {'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'tool_use', 'name': 'submit_result'}},
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': tool_result[:35]}},
            {'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'input_json_delta', 'partial_json': tool_result[35:]}},
            {'type': 'message_stop'},
        ]
        return httpx.Response(200, headers={'Content-Type': 'text/event-stream'},
                              text=''.join('data: ' + json.dumps(event) + '\n\n' for event in events))

    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kwargs: original(transport=httpx.MockTransport(respond), **kwargs))
    config = {'XIAOAN_CLAUDE_BASE_URL': 'https://example.test/v1',
              'XIAOAN_CLAUDE_API_KEY': 'fixture', 'XIAOAN_CLAUDE_WIRE_API': 'messages'}
    body = {'model': 'claude-test', 'messages': [{'role': 'user', 'content': 'route'}],
            'response_format': {'type': 'json_schema', 'json_schema': {
                'name': 'xiaoan_route', 'strict': True, 'schema': {'type': 'object'}}}}

    async def run():
        return [part async for part in llm_adapter.astream(None, body, config)]

    assert asyncio.run(run()) == [tool_result]
