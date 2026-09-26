"""Fresh, version-bound remediation run through real FastAPI/SSE; no model doubles.

Uses only the previously authorized minimal32 cases and the configured KaroAPI.
--execute is required. Each case gets its own store/session, with sequential turns.
Old runs are never modified. Failed attempts are retained rather than quality zero.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import io
import json
import logging
import os
from pathlib import Path
import sys
from urllib.error import HTTPError

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'evaluation'), str(ROOT/'tech/chatflow/poc')]
from fastapi.testclient import TestClient
from server import create_app
from chat_service import ChatService
from conversation_store import InMemoryConversationStore
from xiaoan_eval.transport import FastAPITransport
from xiaoan_eval.runner import EvaluationRunner
from xiaoan_eval.cases import load_cases
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval.config import load_evaluator_config
from xiaoan_eval.judge_client import JudgeClient
from xiaoan_eval.pipeline import EvaluationPipeline
from xiaoan_eval.checkpoint import JsonlCheckpoint
import company_eval_plugins as plugins

TARGET_IDS = ['TC-01','TC-04','TC-05','TC-10','TC-29','TC-30','TC-48','TC-72','TC-74']

class Response:
    def __init__(self, response):
        self.status=response.status_code
        self.body=io.BytesIO(response.content)
    def read(self): return self.body.read()
    def readline(self): return self.body.readline()
    def __enter__(self): return self
    def __exit__(self,*args): pass

class Opener:
    def __init__(self,client): self.client=client
    def open(self,request,timeout):
        response=self.client.request(request.get_method(),request.full_url,content=request.data,headers=dict(request.header_items()))
        if response.status_code>=400:
            raise HTTPError(request.full_url,response.status_code,'ASGI error',{},io.BytesIO(response.content))
        return Response(response)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--execute',action='store_true')
    parser.add_argument('--workers',type=int,default=4)
    parser.add_argument('--timeout-seconds',type=int,default=180)
    parser.add_argument('--run-id',default='2026-09-14-minimal32-targeted-remediation')
    parser.add_argument('--cases',nargs='+',default=TARGET_IDS)
    args=parser.parse_args()
    if not 1 <= args.workers <= 6 or not 30 <= args.timeout_seconds <= 600: raise ValueError('invalid execution limits')
    if Path(args.run_id).name!=args.run_id: raise ValueError('run-id must be a directory name')
    allowed={p.stem for p in (ROOT/'evaluation/runs/2026-09-13-minimal32-inputs/cases').glob('TC-*.yaml')}
    if not set(args.cases)<=allowed: raise ValueError('case outside authorized minimal32')
    if len(set(args.cases))!=len(args.cases): raise ValueError('duplicate cases')
    os.umask(0o077)
    logging.disable(logging.CRITICAL)
    output=ROOT/'evaluation/runs'/args.run_id
    private=ROOT/'evaluation/runs'/('.'+args.run_id+'.private')
    output.mkdir(exist_ok=True); private.mkdir(exist_ok=True)
    inputs=private/'cases'; inputs.mkdir(exist_ok=True)
    for cid in args.cases:
        original=ROOT/'evaluation/test-cases'/(cid+'.yaml')
        target=inputs/original.name
        if target.exists() and target.read_bytes()!=original.read_bytes(): raise ValueError('case version changed')
        target.write_bytes(original.read_bytes())
    rule=load_rating_rule(ROOT/'evaluation/ratings rule.yml')
    config=load_evaluator_config(ROOT/'evaluation/evaluator-config.yml')
    loaded=load_cases(inputs,rule)
    if any(r.case is None for r in loaded): raise ValueError('invalid test case')
    cases=[r.case for r in loaded]
    paths=[*sorted((ROOT/'tech/chatflow/poc').glob('*.py')),*sorted((ROOT/'content').rglob('*.md')),
           ROOT/'tech/chatflow/poc/capsules.json',ROOT/'evaluation/company_eval_plugins.py',ROOT/'evaluation/ratings rule.yml',*sorted((ROOT/'evaluation/xiaoan_eval').glob('*.py')),Path(__file__).resolve(),*sorted(inputs.glob('*.yaml'))]
    hashes={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    version=hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()
    manifest={'run_id':args.run_id,'version':version,'source_hashes':hashes,'case_ids':[c.id for c in cases],
              'case_count':len(cases),'turn_count':sum(len(c.turns) for c in cases),'oracle_status':'provisional',
              'transport':'real FastAPI ASGI/SSE; TestClient replaces loopback network only',
              'comparison':'before/after diagnostic; not single-variable causal proof',
              'execution_limits':{'workers':args.workers,'provider_read_timeout_seconds':args.timeout_seconds,'sdk_max_retries':0},
              'models':{k:plugins._evaluation_value(k,'') for k in ('XIAOAN_ROUTER_MODEL','XIAOAN_RESPONSE_MODEL','XIAOAN_JUDGE_MODEL','XIAOAN_MODEL_REASONING_EFFORT','XIAOAN_JUDGE_REASONING_EFFORT')}}
    mp=private/'manifest.json'
    if mp.exists() and json.loads(mp.read_text())!=manifest: raise ValueError('run version changed; use a new run-id')
    mp.write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({k:v for k,v in manifest.items() if k!='source_hashes'},ensure_ascii=False),flush=True)
    if not args.execute:return
    from settings import get_openai_base_url
    from urllib.parse import urlparse
    if urlparse(get_openai_base_url() or '').hostname!='api.karoapi.com' or plugins._openai_client().base_url.host!='api.karoapi.com':
        raise ValueError('provider outside scoped KaroAPI consent')
    # Diagnostic-only limits. Keep the endpoint, wire format, models and prompts
    # unchanged; do not modify the user's .env or production transport settings.
    import openai
    original_sync, original_async = openai.OpenAI, openai.AsyncOpenAI
    class BoundedOpenAI(original_sync):
        def __init__(self,*a,**kw):
            kw.update(timeout=args.timeout_seconds,max_retries=0)
            super().__init__(*a,**kw)
    class BoundedAsyncOpenAI(original_async):
        def __init__(self,*a,**kw):
            kw.update(timeout=args.timeout_seconds,max_retries=0)
            super().__init__(*a,**kw)
    openai.OpenAI=BoundedOpenAI;openai.AsyncOpenAI=BoundedAsyncOpenAI
    plugins.OpenAI=BoundedOpenAI
    with JsonlCheckpoint(private/'evaluation-checkpoint.jsonl',version) as checkpoint:
        def evaluate(case):
            cache=private/(case.id+'.json')
            if cache.exists():
                print(case.id,'CACHED',flush=True);return json.loads(cache.read_text())
            app=create_app(chat_service=ChatService.from_settings(safety_model=plugins._evaluation_value("XIAOAN_SAFETY_MODEL",""), router_model=plugins._evaluation_value("XIAOAN_ROUTER_MODEL",""), response_model=plugins._evaluation_value("XIAOAN_RESPONSE_MODEL","")), conversation_store=InMemoryConversationStore(ttl_seconds=86400),offline=False,cookie_secure=False,debug_enabled=True)
            with TestClient(app,base_url='http://testserver') as client:
                transport=FastAPITransport('http://testserver',retries=0,opener=Opener(client))
                def record(event):
                    checkpoint(event)
                    if event.get('event')=='subject_turn':print(case.id,'T'+str(event['turn']),'SUBJECT', 'UNAVAILABLE' if event.get('error') else 'ANSWERED',flush=True)
                def judge(request):
                    result=plugins.judge(request)
                    print(case.id,'T'+str(request['turn']),'JUDGE RETURNED',flush=True)
                    return result
                pipeline=EvaluationPipeline(EvaluationRunner(transport,checkpoint=record),rule,config,
                    primary_judge=JudgeClient(judge,rule,checkpoint=checkpoint,checkpoint_event='primary_judge'),
                    authoritative_context_provider=plugins.authoritative_context,
                    known_route_ids=frozenset(['baseline','crisis_sop',*[c['id'] for c in __import__('router').load_capsules()]]))
                result=pipeline.evaluate_case(case)
                checkpoint({'event':'case_result','case_id':case.id,'record':result})
                cache.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
                print(case.id,'COMPLETE',flush=True)
                return result
        def safe_evaluate(case):
            try:return evaluate(case)
            except Exception as exc:
                # Operational exception must not abort unrelated cases or expose
                # provider headers/messages. Completed turn checkpoints survive.
                result={'case_id':case.id,'status':'ERROR','evaluator_exception':True,'error_type':type(exc).__name__}
                checkpoint({'event':'case_execution_error',**result})
                (private/(case.id+'.json')).write_text(json.dumps(result)+'\n')
                print(case.id,'UNAVAILABLE',type(exc).__name__,flush=True)
                return result
        with ThreadPoolExecutor(max_workers=args.workers) as pool:
            records=[f.result() for f in as_completed([pool.submit(safe_evaluate,c) for c in cases])]
    for name,digest in hashes.items():
        if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('source changed during run: '+name)
    (output/'case-results.json').write_text(json.dumps(sorted(records,key=lambda r:r['case_id']),ensure_ascii=False,indent=2)+'\n')
    print('COMPLETE',output,flush=True)

if __name__=='__main__':main()
