"""Configured network boundaries for canonical evaluation; credentials never enter artifacts."""
from __future__ import annotations

import asyncio
from copy import deepcopy
import json
from pathlib import Path
from threading import Lock, Thread
from uuid import uuid4

from xiaoan_eval_core import model_config, llm_adapter
from xiaoan_eval_core.contracts import digest


def transport_options(values):
    return {k:v for k,v in values.items() if k.endswith(('_REQUEST_BODY','_REQUEST_BODIES','_WIRE_API','_REASONING_EFFORT','_PROMPT_CACHE_MODE','_BASE_URL'))
            or k in ('XIAOAN_PROMPT_CACHE_MODE','XIAOAN_PROMPT_CACHE_TTL','XIAOAN_MAX_OUTPUT_TOKENS',
                     'GOOGLE_EMBEDDING_MODEL','GOOGLE_EMBEDDING_TASK_TYPE','GOOGLE_EMBEDDING_DIMENSIONS',
                     'XIAOAN_EMBEDDING_MODEL','XIAOAN_EMBEDDING_REVISION')}


def identity(role, *, model=None):
    values = model_config.read_env()
    selected = model or model_config.model(role, values=values)
    if selected not in model_config.configured_models(values):
        raise ValueError('Unconfigured model')
    return {'id': selected, 'provider': model_config.provider_for_model(selected, values),
            'model': selected, 'family': model_config.provider_for_model(selected, values),
            'prompt_version': 'frozen-evaluation/v1'}


def response_text(raw):
    if raw.get('error') or raw.get('status') in ('failed', 'incomplete'):
        raise ValueError('Provider returned failed/incomplete response')
    if 'output' in raw or 'output_text' in raw:
        return llm_adapter.normalize_responses(raw)['choices'][0]['message']['content']
    if 'choices' in raw:
        choice = raw['choices'][0]
        if choice.get('finish_reason') in ('length', 'content_filter'):
            raise ValueError('Provider output incomplete')
        return choice['message'].get('content', '')
    content = raw.get('content', [])
    tool_inputs = [block.get('input') for block in content
                   if isinstance(block, dict) and block.get('type') == 'tool_use'
                   and isinstance(block.get('input'), dict)]
    if tool_inputs:
        return json.dumps(tool_inputs[-1], ensure_ascii=False)
    text = ''.join(x.get('text', '') for x in content if x.get('type') == 'text')
    if raw.get('stop_reason') in {'max_tokens', 'end_turn'} and not text:
        raise ValueError('Provider returned incomplete response without structured output')
    return text


def usage(raw):
    u = raw.get('usage') or {}
    incoming = u.get('input_tokens', u.get('prompt_tokens'))
    outgoing = u.get('output_tokens', u.get('completion_tokens'))
    written=u.get('cache_write_tokens',u.get('cache_creation_input_tokens'))
    if incoming is not None and ('cache_read_input_tokens' in u or 'cache_creation_input_tokens' in u):
        incoming += (u.get('cache_read_input_tokens') or 0)+(u.get('cache_creation_input_tokens') or 0)
    return {'input_tokens': incoming, 'output_tokens': outgoing,
            'total_tokens': u.get('total_tokens', incoming + outgoing if incoming is not None and outgoing is not None else None),
            'cached_input_tokens': u.get('input_tokens_details', u.get('prompt_tokens_details', {})).get('cached_tokens', u.get('cache_read_input_tokens')),
            'cache_write_tokens':written,
            'input_token_semantics':'total_including_cache',
            'raw_usage': u}


def normalize_quote_offsets(payload, request):
    """Repair only a uniquely exact quote; never fuzzy-match or change quoted text."""
    result=deepcopy(payload)
    repairs=[]
    answer=request.get('answer','')
    catalog={u['ref']:u['content'] for name in ('context','reference_facts') for u in request.get(name,[])}
    def repair(quote,content,path):
        if not isinstance(quote,dict) or not isinstance(content,str):return
        text=quote.get('text')
        if not isinstance(text,str) or not text:return
        start,end=quote.get('start'),quote.get('end')
        if type(start) is int and type(end) is int and 0<=start<end<=len(content) and content[start:end]==text:return
        position=content.find(text)
        if position<0 or content.find(text,position+1)>=0:return
        repairs.append({'path':path,'original_start':start,'original_end':end,'start':position,'end':position+len(text)})
        quote.update(start=position,end=position+len(text))
    for i,claim in enumerate(result.get('claims',[])):
        repair(claim.get('answer_span'),answer,f'/claims/{i}/answer_span')
        for axis in ('faithfulness','correctness'):
            for n,quote in enumerate(claim.get(axis,{}).get('evidence',[])):
                repair(quote,catalog.get(quote.get('ref')),f'/claims/{i}/{axis}/evidence/{n}')
    for i,requirement in enumerate(result.get('requirements',[])):
        for n,quote in enumerate(requirement.get('answer_spans',[])):
            repair(quote,answer,f'/requirements/{i}/answer_spans/{n}')
    definitions={r['id']:r for r in request.get('requirements',[])}
    for i,requirement in enumerate(result.get('requirements',[])):
        definition=definitions.get(requirement.get('id'),{})
        observation=request.get('observations',{}).get(requirement.get('id'),{})
        if not (definition.get('runtime_check') or definition.get('kind') in ('route','evidence')):continue
        verdict=None
        if observation.get('status')=='NOT_APPLICABLE':verdict='NOT_APPLICABLE'
        elif observation.get('status')=='AVAILABLE' and type(observation.get('value')) is bool:
            verdict='SATISFIED' if observation['value'] else 'VIOLATED'
        if verdict is not None:
            repairs.append({'path':f'/requirements/{i}','original':deepcopy(requirement),
                            'rule':'bound-deterministic-observation/v1','observation':observation})
            requirement.update(verdict=verdict,reason='程式依凍結 observation 的確定性比對結果判定。',
                               answer_spans=[],source='deterministic')
    return result,repairs


def parse_response_json(content):
    decoder=json.JSONDecoder()
    value,end=decoder.raw_decode(content.strip())
    rest=content.strip()[end:].strip()
    while rest:
        repeated,end=decoder.raw_decode(rest)
        if repeated!=value:raise ValueError('Multiple different provider JSON objects')
        rest=rest[end:].strip()
    return value


class ConfiguredProvider:
    def __init__(self, artifact_dir=None):
        self.values = model_config.read_env()
        self.artifact_dir = Path(artifact_dir) if artifact_dir else None
        self._pool_lock = Lock()
        self._loop = None
        self._thread = None
        self._client = None

    async def _pooled_request(self, body):
        if self._client is None:
            import httpx
            self._client = httpx.AsyncClient(timeout=float(self.values.get('XIAOAN_PROVIDER_TIMEOUT', '120')))
        return await llm_adapter.arequest(body, self.values, client=self._client)

    def _run_pooled(self, body):
        with self._pool_lock:
            if self._loop is None:
                self._loop = asyncio.new_event_loop()
                self._thread = Thread(target=self._loop.run_forever, daemon=True)
                self._thread.start()
            loop = self._loop
        return asyncio.run_coroutine_threadsafe(self._pooled_request(body), loop).result()

    def close(self):
        with self._pool_lock:
            loop, thread = self._loop, self._thread
            self._loop = self._thread = None
        if loop is None:
            return
        try:
            if self._client is not None:
                asyncio.run_coroutine_threadsafe(self._client.aclose(), loop).result()
                self._client = None
        finally:
            loop.call_soon_threadsafe(loop.stop)
            thread.join()
            loop.close()

    def _request(self, body):
        if body['model'] not in model_config.configured_models(self.values):
            raise ValueError('Model not present in shared configuration')
        body = {**body, 'stream': llm_adapter.wire_api(body['model'],self.values) == 'responses'}
        raw = self._run_pooled(body)
        if self.artifact_dir:
            self.artifact_dir.mkdir(parents=True, exist_ok=True)
            path = self.artifact_dir / (digest(body) + '-' + uuid4().hex + '.json')
            wire=llm_adapter.wire_api(body['model'],self.values)
            effective=llm_adapter.adapt_body(body,wire,self.values)
            path.write_text(json.dumps({'request': effective, 'wire':wire,'response': raw}, ensure_ascii=False, indent=2))
            path.chmod(0o600)
        return raw

    def __call__(self, request):
        if 'provider_options' in request and request['provider_options'] != transport_options(self.values):
            raise ValueError('Provider transport options changed; freeze a new evaluation configuration')
        model = request.get('identity', {}).get('model')
        if not model or model in ('unspecified','configured'):
            model = model_config.model('XIAOAN_RELEVANCY_MODEL', values=self.values)
        instructions = request.get('instructions', 'Return only a JSON object.')
        payload = {k:v for k,v in request.items() if k != 'instructions'}
        response_schema = request.get('response_schema')
        response_format = {'type': 'json_object'}
        # The configured DeepSeek Chat Completions endpoint accepts json_object
        # but rejects json_schema; local contract validation still applies.
        if isinstance(response_schema, dict) and not (
                model_config.provider_for_model(model, self.values) == 'deepseek'
                and llm_adapter.wire_api(model, self.values) == 'chat_completions'):
            response_format = {
                'type': 'json_schema',
                'json_schema': {
                    'name': f"xiaoan_{request.get('task', 'result')}",
                    'strict': True,
                    'schema': response_schema,
                },
            }
        body = {'model': model, 'messages': [{'role':'system','content':instructions},
                {'role':'user','content':json.dumps(payload,ensure_ascii=False)}],
                'response_format': response_format, 'store':False}
        raw = self._request(body)
        content = response_text(raw).strip()
        if content.startswith('```'):
            content = content.split('\n',1)[1].rsplit('```',1)[0].strip()
        payload,repairs=normalize_quote_offsets(parse_response_json(content),request)
        # The response is from this synchronous invocation; bind locally rather
        # than requiring an LLM to transcribe a long digest. Supplied/cached
        # responses still pass the strict core binding validator unchanged.
        if request.get('binding') and payload.get('binding') != request['binding']:
            repairs.append({'path':'/binding','original':payload.get('binding'),
                            'binding':request['binding'],'rule':'current-provider-invocation/v1'})
            payload['binding']=request['binding']
        if repairs and self.artifact_dir:
            receipt=self.artifact_dir/(digest(request)+'-quote-normalization.json')
            receipt.write_text(json.dumps({'request_digest':digest(request),'repairs':repairs,'rule':'unique-exact-quote/v1'},ensure_ascii=False,indent=2))
            receipt.chmod(0o600)
        return {'payload':payload, 'usage': usage(raw), 'provider_request_id':raw.get('id')}

    def subject(self, subject, question, history, context):
        messages = []
        if context:
            messages.append({'role':'system','content':'\n\n'.join(x['content'] for x in context)})
        messages.extend(history)
        messages.append({'role':'user','content':question})
        body = {'model':subject['model'],'messages':messages,'store':False}
        raw = self._request(body)
        return {'text':response_text(raw),'usage':usage(raw),'request_id':raw.get('id'),
                'request_hash':digest(body)}

    def embeddings(self, texts, task):
        import httpx
        model = self.values.get('XIAOAN_EMBEDDING_MODEL') or self.values.get('GOOGLE_EMBEDDING_MODEL')
        if not model:
            raise ValueError('Configure XIAOAN_EMBEDDING_MODEL or GOOGLE_EMBEDDING_MODEL')
        if model.startswith('gemini') and self.values.get('GOOGLE_EMBEDDING_API_KEY'):
            base = self.values.get('GOOGLE_EMBEDDING_BASE_URL','https://generativelanguage.googleapis.com/v1beta').rstrip('/')
            body = {'requests':[{'model':'models/'+model,'content':{'parts':[{'text':text}]},
                      'taskType':self.values.get('GOOGLE_EMBEDDING_TASK_TYPE','SEMANTIC_SIMILARITY'),
                      'outputDimensionality':int(self.values.get('GOOGLE_EMBEDDING_DIMENSIONS','3072'))} for text in texts]}
            with httpx.Client(timeout=float(self.values.get('XIAOAN_PROVIDER_TIMEOUT','120'))) as client:
                response=client.post(base+'/models/'+model+':batchEmbedContents',
                    headers={'x-goog-api-key':self.values['GOOGLE_EMBEDDING_API_KEY']},json=body)
                response.raise_for_status();raw=response.json()
            if len(raw.get('embeddings',[])) != len(texts):
                raise ValueError('Embedding count mismatch')
            return {'model_id':model,'revision':self.values.get('XIAOAN_EMBEDDING_REVISION','provider-unspecified'),
                    'vectors':{text:item['values'] for text,item in zip(texts,raw['embeddings'])},'usage':usage(raw)}
        if model.startswith('gemini'):
            base = self.values.get('XIAOAN_GEMINI_BASE_URL','https://generativelanguage.googleapis.com/v1beta/openai').rstrip('/')
            key = self.values.get('XIAOAN_GEMINI_API_KEY','')
        else:
            base = self.values.get('XIAOAN_OPENAI_BASE_URL','https://api.openai.com/v1').rstrip('/')
            key = self.values.get('XIAOAN_OPENAI_API_KEY','')
        with httpx.Client(timeout=float(self.values.get('XIAOAN_PROVIDER_TIMEOUT','120'))) as client:
            response = client.post(base+'/embeddings',headers={'Authorization':'Bearer '+key},json={'model':model,'input':texts})
            response.raise_for_status()
            raw = response.json()
        ordered = sorted(raw['data'],key=lambda x:x['index'])
        if len(ordered)!=len(texts):
            raise ValueError('Embedding count mismatch')
        return {'model_id':model,'revision':self.values.get('XIAOAN_EMBEDDING_REVISION','provider-unspecified'),
                'vectors':{text:item['embedding'] for text,item in zip(texts,ordered)},
                'usage':usage(raw)}
