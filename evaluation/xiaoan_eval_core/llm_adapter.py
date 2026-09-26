"""纯请求适配：配置由调用方从共享 .env 读取，不读取进程环境。"""
from __future__ import annotations

from copy import deepcopy
from contextlib import nullcontext
import json
from typing import Any, Mapping


def family(model: str, config: Mapping[str, str]) -> str:
    for name in ('OPENAI', 'CLAUDE', 'GEMINI', 'DEEPSEEK', 'QWEN', 'KIMI'):
        prefix = 'GPT' if name == 'OPENAI' else name
        if any(config.get(f'XIAOAN_{prefix}_{tier}_MODEL') == model for tier in ('LATEST', 'SECOND', 'JUDGE')):
            return name
    lower = model.lower()
    return next((name for name in ('CLAUDE', 'GEMINI', 'DEEPSEEK', 'QWEN', 'KIMI') if lower.startswith(name.lower())), 'OPENAI')


def wire_api(model: str, config: Mapping[str, str], provider: str | None = None) -> str:
    name = provider or family(model, config)
    default = {'OPENAI': 'responses', 'CLAUDE': 'messages', 'GEMINI': 'gemini_native'}.get(name, 'chat_completions')
    value = config.get(f'XIAOAN_{name}_WIRE_API', '').strip().lower()
    if not value and name == 'CLAUDE':
        legacy = config.get('XIAOAN_CLAUDE_API_MODE', '').strip().lower()
        value = 'chat_completions' if legacy == 'openai' else 'messages'
    value = value or default
    value = {'response': 'responses', 'message': 'messages', 'anthropic_messages': 'messages', 'auto': default}.get(value, value)
    if value not in {'responses', 'messages', 'chat_completions', 'gemini_native'}:
        raise ValueError(f'XIAOAN_{name}_WIRE_API 必须是 responses、messages、chat_completions 或 gemini_native')
    return value


def endpoint(base_url: str, wire: str) -> str:
    base = base_url.rstrip('/')
    for suffix in ('/chat/completions', '/responses', '/messages'):
        if base.endswith(suffix):
            base = base[:-len(suffix)]
            break
    return base + {'responses': '/responses', 'messages': '/messages', 'chat_completions': '/chat/completions'}[wire]


def _gemini_part(content: Any) -> list[dict[str, str]]:
    if isinstance(content, str):
        return [{'text': content}]
    if isinstance(content, list):
        return [{'text': str(block.get('text', ''))} for block in content
                if isinstance(block, Mapping) and block.get('text') is not None]
    return [{'text': str(content)}]


def gemini_endpoint(base_url: str, model: str, api_key: str) -> str:
    base = base_url.rstrip('/')
    if base.endswith('/v1beta'):
        return f'{base}/models/{model}:generateContent?key={api_key}'
    if '/models/' in base and ':generateContent' in base:
        return base if '?key=' in base else f'{base}?key={api_key}'
    return f'{base}/v1beta/models/{model}:generateContent?key={api_key}'


def adapt_gemini_body(body: Mapping[str, Any], config: Mapping[str, str]) -> dict:
    result = deepcopy(dict(body))
    messages = result.pop('messages', [])
    contents = []
    system_parts = []
    for message in messages:
        role = message.get('role', 'user')
        parts = _gemini_part(message.get('content', ''))
        if role in {'system', 'developer'}:
            system_parts.extend(parts)
        else:
            contents.append({'role': 'model' if role == 'assistant' else 'user', 'parts': parts})
    result.pop('model', None)
    result.pop('stream', None)
    result.pop('max_tokens', None)
    result.pop('max_output_tokens', None)
    result.pop('response_format', None)
    result.pop('reasoning_effort', None)
    result.pop('store', None)
    native = {'contents': contents}
    if system_parts:
        native['systemInstruction'] = {'parts': system_parts}
    generation = {}
    for source, target in (('temperature', 'temperature'), ('top_p', 'topP'), ('top_k', 'topK'),
                           ('max_tokens', 'maxOutputTokens'), ('max_output_tokens', 'maxOutputTokens')):
        if source in body:
            generation[target] = body[source]
    fmt = body.get('response_format')
    if fmt:
        generation['responseMimeType'] = 'application/json'
        schema = fmt.get('json_schema', {}).get('schema') if fmt.get('type') == 'json_schema' else None
        if schema:
            # Gemini responseSchema does not preserve our local $defs references.
            definitions = schema.get('$defs', {})
            def inline(value):
                if isinstance(value, list):
                    return [inline(item) for item in value]
                if not isinstance(value, dict):
                    return value
                if '$ref' in value:
                    name = value['$ref'].removeprefix('#/$defs/')
                    if value['$ref'] != '#/$defs/'+name or name not in definitions:
                        raise ValueError('Unsupported Gemini response schema reference')
                    return inline(definitions[name])
                return {k:inline(v) for k,v in value.items() if k not in {'$defs','$schema'}}
            generation['responseSchema'] = inline(schema)
    if generation:
        native['generationConfig'] = generation
    native['model'] = body['model']
    native = apply_options(native, config, 'GEMINI')
    native.pop('model', None)
    return native


def _object(raw: str, setting: str) -> dict:
    try:
        value = json.loads(raw or '{}')
    except json.JSONDecodeError:
        raise ValueError(f'{setting} 必须是 JSON 对象') from None
    if not isinstance(value, dict):
        raise ValueError(f'{setting} 必须是 JSON 对象')
    return value


def _merge(body: dict, patch: dict) -> None:
    for key, value in patch.items():
        if value is None:
            body.pop(key, None)
        elif isinstance(value, dict):
            if not isinstance(body.get(key), dict):
                body[key] = {}
            _merge(body[key], value)
        else:
            body[key] = deepcopy(value)


def apply_options(body: Mapping[str, Any], config: Mapping[str, str], provider: str | None = None) -> dict:
    result = deepcopy(dict(body))
    model = result['model']
    name = f'XIAOAN_{provider or family(model, config)}_REQUEST_BODY'
    patches = [_object(config.get(name, ''), name)]
    models_name = 'XIAOAN_MODEL_REQUEST_BODIES'
    models = _object(config.get(models_name, ''), models_name)
    if any(not isinstance(patch, dict) for patch in models.values()):
        raise ValueError(f'{models_name} 的每个模型值必须是 JSON 对象')
    patches.append(models.get(model, {}))
    protected = {'extra_body', 'model', 'messages', 'input', 'instructions', 'system', 'systemInstruction', 'contents', 'tools', 'tool_choice', 'response_format', 'stream', 'stream_options', 'previous_response_id'}
    for patch in patches:
        if protected.intersection(patch) or ('text' in patch and (not isinstance(patch['text'], dict) or 'format' in patch['text'])):
            raise ValueError('REQUEST_BODY 不允许覆盖消息、模型、结构化输出或传输控制字段')
        _merge(result, patch)
    return result


def _apply_cache(result: dict, wire: str, config: Mapping[str, str], provider: str | None = None) -> dict:
    """统一 cache 开关；默认只保留稳定前缀，不宣称 provider 已命中。"""
    import hashlib
    name = provider or family(str(result.get('model', '')), config)
    mode = config.get(f'XIAOAN_{name}_PROMPT_CACHE_MODE', config.get('XIAOAN_PROMPT_CACHE_MODE', 'prefix_only')).strip().lower()
    if mode not in {'off', 'prefix_only', 'explicit'}:
        raise ValueError('PROMPT_CACHE_MODE 必须是 off、prefix_only 或 explicit')
    if mode != 'explicit':
        return result
    stable = json.dumps({k: result.get(k) for k in ('instructions', 'system', 'input', 'messages') if k in result}, ensure_ascii=False, sort_keys=True)
    key = 'xiaoan:' + hashlib.sha256(stable.encode()).hexdigest()[:24]
    if wire == 'responses':
        result.setdefault('prompt_cache_key', key)
        result.setdefault('prompt_cache_options', {'mode': 'explicit', 'ttl': config.get('XIAOAN_PROMPT_CACHE_TTL', '30m')})
    elif wire == 'messages' and isinstance(result.get('system'), str):
        result['system'] = [{'type': 'text', 'text': result['system'], 'cache_control': {'type': 'ephemeral'}}]
    elif wire == 'chat_completions':
        result.setdefault('prompt_cache_key', key)
    return result


def adapt_body(body: Mapping[str, Any], wire: str, config: Mapping[str, str], provider: str | None = None) -> dict:
    if wire == 'gemini_native':
        return adapt_gemini_body(body, config)
    result = deepcopy(dict(body))
    result.update(result.pop('extra_body', {}) or {})
    if wire == 'responses' and 'messages' in result:
        result['input'] = result.pop('messages')
        if 'max_tokens' in result:
            result['max_output_tokens'] = result.pop('max_tokens')
        if 'reasoning_effort' in result:
            result['reasoning'] = {'effort': result.pop('reasoning_effort')}
        fmt = result.pop('response_format', None)
        if fmt:
            result['text'] = {'format': {'type': 'json_schema', **fmt['json_schema']} if fmt['type'] == 'json_schema' else fmt}
        result.pop('stream_options', None)
    elif wire == 'messages':
        messages = result.get('messages', [])
        systems = [m['content'] for m in messages if m['role'] in {'system', 'developer'}]
        result['messages'] = [m for m in messages if m['role'] not in {'system', 'developer'}]
        if systems:
            blocks = []
            for content in systems:
                blocks.extend([{'type': 'text', 'text': content}] if isinstance(content, str) else content)
            result['system'] = '\n\n'.join(systems) if all(isinstance(s, str) for s in systems) else blocks
        result.setdefault('max_tokens', int(config.get('XIAOAN_MAX_OUTPUT_TOKENS') or '2048'))
        # Structured evaluator calls need the whole budget for the submitted
        # JSON/tool result; hidden reasoning must be an explicit opt-in.
        if config.get('XIAOAN_CLAUDE_STRUCTURED_OUTPUT_MODE', 'tool').strip().lower() != 'off':
            result.setdefault('thinking', {'type': 'disabled'})
        fmt = result.pop('response_format', None)
        if fmt and fmt['type'] == 'json_schema':
            result['tools'] = [{'name': 'submit_result', 'description': 'Submit the result',
                                'input_schema': fmt['json_schema']['schema'],
                                'strict': fmt['json_schema'].get('strict', False)}]
            result['tool_choice'] = {'type': 'tool', 'name': 'submit_result'}
        elif fmt:
            instruction = 'Return only a JSON object.'
            system = result.get('system', '')
            result['system'] = system + '\n' + instruction if isinstance(system, str) else system + [{'type': 'text', 'text': instruction}]
        for key in ('reasoning_effort', 'reasoning', 'store', 'stream_options', 'prompt_cache_key', 'prompt_cache_options'):
            result.pop(key, None)
    result = apply_options(result, config, provider)
    return _apply_cache(result, wire, config, provider)


def normalize_responses(payload: Mapping[str, Any]) -> dict:
    if payload.get('error') or payload.get('status') in {'failed', 'incomplete'}:
        raise RuntimeError('Responses request failed or was incomplete')
    text = ''.join(block.get('text', '') for item in payload.get('output', [])
                   if item.get('type') == 'message' for block in item.get('content', [])
                   if block.get('type') == 'output_text')
    text = text or str(payload.get('output_text', '') or '')
    return {**payload, 'choices': [{'message': {'content': text}}]}


def sdk_options(body: Mapping[str, Any], wire: str, config: Mapping[str, str]) -> dict:
    """将供应商扩展字段放入 SDK extra_body，标准字段仍由 SDK 处理。"""
    import inspect
    from openai.resources.chat.completions import Completions
    from openai.resources.responses import Responses

    result = adapt_body(body, wire, config)
    method = Responses.create if wire == 'responses' else Completions.create
    known = inspect.signature(method).parameters
    extras = {key: result.pop(key) for key in list(result) if key not in known}
    if extras:
        result['extra_body'] = extras
    return result


class EvaluationClient:
    """保留评估器的同步 SDK 接口，实际协议由模型配置决定。"""

    def __init__(self, client: Any, config: Mapping[str, str]):
        from types import SimpleNamespace
        self.client = client
        self.config = dict(config)
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self.chat_create))
        self.responses = SimpleNamespace(create=self.responses_create)

    def _complete(self, body: dict) -> Any:
        import asyncio
        from types import SimpleNamespace
        async def call():
            wire = wire_api(body['model'], self.config)
            if wire == 'messages':
                return await acomplete(None, body, self.config)
            from openai import AsyncOpenAI
            api_key = getattr(self.client, 'api_key', '') or ''
            base_url = getattr(self.client, 'base_url', None)
            async_client = AsyncOpenAI(api_key=api_key, **({'base_url': str(base_url)} if base_url else {}))
            async with async_client:
                return await acomplete(async_client, body, self.config)
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(call())
        import threading
        result, errors = [], []
        def runner():
            try: result.append(asyncio.run(call()))
            except BaseException as exc: errors.append(exc)
        thread = threading.Thread(target=runner)
        thread.start(); thread.join()
        if errors: raise errors[0]
        return result[0]

    def complete(self, **body: Any) -> Any:
        return self._complete(body)

    def stream(self, **body: Any):
        # Sync compatibility surface; the underlying protocol adapter remains
        # the sole owner of request translation and stream collection.
        return iter([self._complete(body)])

    def chat_create(self, **body: Any) -> Any:
        return self.complete(**body)

    def responses_create(self, **body: Any) -> Any:
        from types import SimpleNamespace
        wire = wire_api(body['model'], self.config)
        if wire == 'responses':
            return self.client.responses.create(**sdk_options(body, wire, self.config))
        stream = body.pop('stream', False)
        incoming = body.pop('input', '')
        messages = [{'role': 'user', 'content': incoming}] if isinstance(incoming, str) else deepcopy(incoming)
        if body.get('instructions'):
            messages.insert(0, {'role': 'system', 'content': body.pop('instructions')})
        for message in messages:
            if isinstance(message.get('content'), list):
                message['content'] = ''.join(block.get('text', '') for block in message['content'])
        body['messages'] = messages
        if 'max_output_tokens' in body:
            body['max_tokens'] = body.pop('max_output_tokens')
        if 'reasoning' in body:
            body['reasoning_effort'] = body.pop('reasoning').get('effort')
        fmt = body.pop('text', {}).get('format')
        if fmt:
            body['response_format'] = {'type': 'json_schema', 'json_schema': {k: v for k, v in fmt.items() if k != 'type'}} if fmt['type'] == 'json_schema' else fmt
        response = self._complete(body)
        result = SimpleNamespace(id=response.id, usage=response.usage, output_text=response.choices[0].message.content)
        if stream:
            # Messages fallback is buffered; do not claim provider token streaming.
            return iter([SimpleNamespace(type='response.output_text.delta', delta=result.output_text),
                         SimpleNamespace(type='response.completed', response=result)])
        return result

async def astream(client: Any, body: Mapping[str, Any], config: Mapping[str, str], *, completion_callback=None):
    """统一异步流式入口；每个 provider 都转换成 text delta。"""
    import asyncio
    wire = wire_api(str(body['model']), config)
    if wire == 'gemini_native':
        result = await arequest({**body, 'stream': False}, config, provider='GEMINI')
        text = result.get('choices', [{}])[0].get('message', {}).get('content', '')
        if text:
            yield text
        if completion_callback:
            completion_callback(result)
        return
    if wire == 'responses':
        from urllib.parse import urlparse
        base_url = config.get('XIAOAN_OPENAI_BASE_URL', '')
        if urlparse(base_url).hostname == 'api.karoapi.com':
            final = await arequest({**body, 'stream': True}, config)
            if final.get('status') != 'completed':
                raise ValueError('Responses stream did not complete')
            text = final.get('output_text', '')
            if text:
                yield text
            if completion_callback:
                completion_callback(final)
            return
        request = sdk_options(body, wire, config)
        async with client.responses.stream(**request) as stream:
            async for event in stream:
                if getattr(event, 'type', '') == 'response.output_text.delta':
                    delta = getattr(event, 'delta', '') or ''
                    if delta:
                        yield delta
            final = await stream.get_final_response()
            if completion_callback and final is not None:
                value=final.model_dump() if hasattr(final,'model_dump') else vars(final)
                completion_callback(value)
        return
    if wire == 'chat_completions':
        request = sdk_options(body, wire, config)
        if completion_callback:request['stream_options']={'include_usage':True}
        stream = await client.chat.completions.create(**request, stream=True)
        async with stream:
            async for chunk in stream:
                if completion_callback and getattr(chunk,'usage',None):
                    u=chunk.usage.model_dump() if hasattr(chunk.usage,'model_dump') else chunk.usage
                    completion_callback({'id':getattr(chunk,'id',None),'usage':u})
                choices = getattr(chunk, 'choices', ())
                if choices:
                    delta = getattr(choices[0].delta, 'content', None) or ''
                    if delta:
                        yield delta
        return
    # Anthropic Messages native SSE. The sync HTTP path is retained only as
    # a compatibility fallback when httpx is not installed.
    import httpx
    request = adapt_body(body, wire, config)
    endpoint_url = endpoint(config.get('XIAOAN_CLAUDE_BASE_URL', 'https://api.anthropic.com/v1'), 'messages')
    request['stream'] = True
    headers = {'x-api-key': config.get('XIAOAN_CLAUDE_API_KEY', ''), 'anthropic-version': '2023-06-01'}
    metadata={'usage':{}}
    tool_json = []
    async with httpx.AsyncClient(timeout=float(config.get('XIAOAN_PROVIDER_TIMEOUT', '120'))) as http:
        async with http.stream('POST', endpoint_url, json=request, headers=headers) as response:
            if response.is_error:
                await response.aread()
            response.raise_for_status()
            async for line in response.aiter_lines():
                if not line.startswith('data:'):
                    continue
                payload = json.loads(line[5:].strip())
                if payload.get('type')=='message_start':
                    metadata.update(id=payload.get('message',{}).get('id'))
                    metadata['usage'].update(payload.get('message',{}).get('usage',{}))
                if payload.get('type')=='message_delta':metadata['usage'].update(payload.get('usage',{}))
                if payload.get('type') == 'content_block_delta':
                    delta = payload.get('delta', {})
                    if delta.get('type') == 'input_json_delta':
                        tool_json.append(delta.get('partial_json', ''))
                    text = delta.get('text', '')
                    if text:
                        yield text
    if tool_json:
        yield ''.join(tool_json)
    if completion_callback:completion_callback(metadata)


async def acomplete(client: Any, body: Mapping[str, Any], config: Mapping[str, str]) -> Any:
    """统一异步完整响应入口；实现仍通过 astream，保证流式和非流式语义一致。"""
    from types import SimpleNamespace
    parts: list[str] = []
    metadata=[]
    async for delta in astream(client, body, config, completion_callback=metadata.append):
        parts.append(delta)
    final=metadata[-1] if metadata else {}
    return SimpleNamespace(id=final.get('id',''),usage=final.get('usage'), output_text=''.join(parts), choices=[SimpleNamespace(message=SimpleNamespace(content=''.join(parts)))])

async def arequest(body: Mapping[str, Any], config: Mapping[str, str], *, provider: str | None = None,
                   client: Any = None) -> dict:
    """无 SDK 依赖的统一异步 HTTP 请求；返回供应商原始 JSON/聚合流。"""
    import httpx
    model = str(body['model'])
    name = provider or family(model, config)
    wire = wire_api(model, config, name)
    request = adapt_body(body, wire, config, name)
    family_name = 'OPENAI' if name == 'OPENAI' else name
    defaults = {'OPENAI': 'https://api.openai.com/v1', 'CLAUDE': 'https://api.anthropic.com/v1', 'GEMINI': 'https://globalai.vip/v1beta', 'DEEPSEEK': 'https://api.deepseek.com'}
    base_url = config.get(f'XIAOAN_{family_name}_BASE_URL', '').strip() or defaults[family_name]
    url = gemini_endpoint(base_url, model, config.get('XIAOAN_GEMINI_API_KEY', '')) if wire == 'gemini_native' else endpoint(base_url, wire)
    headers = {'Content-Type': 'application/json', 'Accept': 'text/event-stream' if request.get('stream') else 'application/json'}
    if wire == 'messages':
        headers.update({'x-api-key': config.get('XIAOAN_CLAUDE_API_KEY', ''), 'anthropic-version': '2023-06-01'})
    elif wire == 'gemini_native':
        headers['Accept'] = 'application/json'
    else:
        headers['Authorization'] = f"Bearer {config.get(f'XIAOAN_{family_name}_API_KEY', '')}"
    async with (nullcontext(client) if client is not None else
                httpx.AsyncClient(timeout=float(config.get('XIAOAN_PROVIDER_TIMEOUT', '120')))) as client:
        if wire == 'gemini_native':
            response = await client.post(url, json=request, headers=headers)
            try:
                response.raise_for_status()
            except httpx.HTTPStatusError as exc:
                raise RuntimeError(f'Gemini request failed with HTTP {exc.response.status_code}') from None
            payload = response.json()
            text = ''.join(part.get('text', '') for candidate in payload.get('candidates', [])
                            for part in candidate.get('content', {}).get('parts', [])
                            if isinstance(part, Mapping))
            usage = payload.get('usageMetadata', {})
            return {'id': payload.get('responseId'), 'choices': [{'message': {'content': text}}],
                    'usage': {'prompt_tokens': usage.get('promptTokenCount', 0),
                              'completion_tokens': usage.get('candidatesTokenCount', 0),
                              'total_tokens': usage.get('totalTokenCount', 0)},
                    'candidates': payload.get('candidates', [])}
        if request.get('stream'):
            chunks: list[str] = []
            async with client.stream('POST', url, json=request, headers=headers) as response:
                if response.is_error:
                    await response.aread()
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith('data:'):
                        continue
                    raw = line[5:].strip()
                    if raw == '[DONE]':
                        break
                    event = json.loads(raw)
                    if wire == 'responses':
                        if event.get('type') == 'response.output_text.delta': chunks.append(event.get('delta', ''))
                        if event.get('type') == 'response.completed': return {**event.get('response', {}), 'output_text': ''.join(chunks)}
                    elif wire == 'messages':
                        if event.get('type') == 'content_block_delta': chunks.append(event.get('delta', {}).get('text', ''))
                    else:
                        for choice in event.get('choices', []): chunks.append(choice.get('delta', {}).get('content', ''))
            if wire == 'messages':
                return {'content': [{'type': 'text', 'text': ''.join(chunks)}]}
            return {'choices': [{'message': {'content': ''.join(chunks)}}]}
        response = await client.post(url, json=request, headers=headers)
        response.raise_for_status()
        return response.json()
