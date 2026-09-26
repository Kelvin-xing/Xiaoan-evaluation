"""Google official batchEmbedContents, bounded batches and resumable exact-text cache."""
import argparse,json,sys,statistics,time
from pathlib import Path
import httpx
from answer_metric_contracts import digest,cosine
ROOT=Path(__file__).resolve().parents[2];DIR=ROOT/'evaluation/runs/2026-09-15-minimal32-answer-metrics';PRIVATE=ROOT/'evaluation/runs/.2026-09-15-minimal32-answer-relevancy.private'

def parse_vectors(payload,texts,dimensions):
 items=payload.get('embeddings',[])
 if len(items)!=len(texts):raise ValueError('embedding count mismatch')
 values={}
 for text,item in zip(texts,items):
  v=item.get('values')
  if not isinstance(v,list) or len(v)!=dimensions:raise ValueError('embedding dimensions mismatch')
  cosine(v,v) # reject nonnumeric, nonfinite or zero vector
  values[text]=v
 return values

def main():
 sys.path.insert(0,str(ROOT/"evaluation"))
 from xiaoan_eval_core import model_config
 p=argparse.ArgumentParser();p.add_argument('--execute',action='store_true');p.add_argument('--pause-seconds',type=float,default=25);a=p.parse_args()
 if not 0<=a.pause_seconds<=60:raise ValueError('pause must be 0..60 seconds')
 env=model_config.read_env();get=lambda k:model_config.required(k,env)
 base=get('GOOGLE_EMBEDDING_BASE_URL').rstrip('/');model=model_config.model('GOOGLE_EMBEDDING_MODEL',values=env);task=get('GOOGLE_EMBEDDING_TASK_TYPE');dim=int(get('GOOGLE_EMBEDDING_DIMENSIONS'));key=get('GOOGLE_EMBEDDING_API_KEY')
 if base!='https://generativelanguage.googleapis.com/v1beta' or model!='gemini-embedding-001' or task!='SEMANTIC_SIMILARITY' or dim!=3072:raise ValueError('configuration differs from approved pinned metric; create new run instead')
 tasks=json.loads((DIR/'relevancy-tasks.json').read_text());texts=set()
 allowed={p.stem for p in (ROOT/'evaluation/runs/2026-09-13-minimal32-inputs/cases').glob('*.yaml')}
 if len(tasks)!=89 or not {t['task']['case_id'] for t in tasks}<=allowed:raise ValueError('outside prepared 89-turn scope')
 for item in tasks:
  t=item['task'];assert digest(t)==item['binding'];f=PRIVATE/f"{t['case_id']}-T{t['turn']}.json"
  if not f.exists():continue
  g=json.loads(f.read_text())
  if g.get('binding')!=item['binding']:raise ValueError('stale generation')
  if g['status']!='AVAILABLE':continue
  qs=g['questions']
  if len(qs)!=t['n'] or any(not isinstance(q,str) or not q.strip() for q in qs):raise ValueError('invalid questions')
  texts.update([t['original_question'],*qs])
 config={'base_url':base,'model_id':model,'task_type':task,'dimensions':dim};path=PRIVATE/'google-embedding-vectors.json';prior=json.loads(path.read_text()) if path.exists() else None
 if prior and prior['config']!=config:raise ValueError('embedding cache config mismatch')
 result=prior or {'model_id':model,'revision':'gemini-embedding-001;SEMANTIC_SIMILARITY;3072;backend_version_UNVERIFIED','config':config,'vectors':{},'attempts':[]}
 for v in result['vectors'].values():
  if len(v)!=dim:raise ValueError('cached dimensions mismatch')
  cosine(v,v)
 pending=sorted(texts-set(result['vectors']));print(json.dumps({'needed_texts':len(texts),'cached_texts':len(texts)-len(pending),'pending_texts':len(pending),'key_configured':bool(key),'execute':a.execute}),flush=True)
 if not a.execute:return
 if not key:raise SystemExit('GOOGLE_EMBEDDING_API_KEY is empty in evaluation_multimodels/.env; no request sent')
 PRIVATE.mkdir(exist_ok=True)
 with httpx.Client(timeout=90,follow_redirects=False) as client:
  for start in range(0,len(pending),32):
   batch=pending[start:start+32];request={'requests':[{'model':'models/'+model,'content':{'parts':[{'text':t}]},'taskType':task,'outputDimensionality':dim} for t in batch]};attempt={'input_digest':digest(batch),'count':len(batch)}
   try:
    response=client.post(base+'/models/'+model+':batchEmbedContents',headers={'x-goog-api-key':key},json=request)
    attempt['http_status']=response.status_code
    response.raise_for_status();vs=parse_vectors(response.json(),batch,dim);result['vectors'].update(vs);attempt['status']='AVAILABLE'
   except Exception as exc:attempt.update(status='UNAVAILABLE',error_type=type(exc).__name__) # never serialize headers, response errors or secrets
   result['attempts'].append(attempt);path.write_text(json.dumps(result,ensure_ascii=False));print(json.dumps(attempt),flush=True)
   if attempt['status']!='AVAILABLE':break # bounded retries: resume explicitly, retain successful cache
   if start+32<len(pending):time.sleep(a.pause_seconds)
 print('Embedding cache saved; score with run_answer_relevancy.py --embeddings '+str(path))
if __name__=='__main__':main()
