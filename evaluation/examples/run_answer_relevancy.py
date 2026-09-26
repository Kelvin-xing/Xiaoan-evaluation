"""Generate reverse questions via scoped KaroAPI; score supplied fixed embeddings.
Embeddings are loaded from a JSON artifact, not obtained from an assumed endpoint.
"""
import argparse,concurrent.futures,json,sys
from pathlib import Path
from answer_metric_contracts import answer_relevancy,digest
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'evaluation'))
DIR=ROOT/'evaluation/runs/2026-09-15-minimal32-answer-metrics';PRIVATE=ROOT/'evaluation/runs/.2026-09-15-minimal32-answer-relevancy.private'

def main():
 p=argparse.ArgumentParser();p.add_argument('--generate',action='store_true');p.add_argument('--execute',action='store_true');p.add_argument('--workers',type=int,default=2);p.add_argument('--limit',type=int);p.add_argument('--embeddings',type=Path);a=p.parse_args()
 if not 1<=a.workers<=4:raise ValueError('workers 1..4')
 if a.limit is not None and a.limit<1:raise ValueError('positive limit')
 tasks=json.loads((DIR/'relevancy-tasks.json').read_text());allowed={p.stem for p in (ROOT/'evaluation/runs/2026-09-13-minimal32-inputs/cases').glob('*.yaml')}
 if not {t['task']['case_id'] for t in tasks}<=allowed:raise ValueError('out of scope')
 PRIVATE.mkdir(exist_ok=True)
 def one(item):
  task=item['task'];key=f"{task['case_id']}-T{task['turn']}";path=PRIVATE/(key+'.json');prior=json.loads(path.read_text()) if path.exists() else None
  assert digest(task)==item['binding']
  if prior and prior.get('binding')!=item['binding']:raise ValueError('cache binding mismatch')
  if prior and prior['status']=='AVAILABLE':return key,'CACHED'
  if not (a.generate and a.execute):return key,'READY'
  from company_eval_plugins import _openai_client,_collect_responses_stream
  from xiaoan_eval_core import model_config
  selected=model_config.model("XIAOAN_RELEVANCY_MODEL",task["generator_model"])
  client=_openai_client(selected).with_options(timeout=180,max_retries=0)
  if client.base_url.host!='api.karoapi.com':raise ValueError('KaroAPI scope mismatch')
  g=task['generation_input'];schema={'type':'object','properties':{'questions':{'type':'array','items':{'type':'string'}}},'required':['questions'],'additionalProperties':False}
  result={'binding':item['binding'],'status':'UNAVAILABLE','questions':None,'attempts':list(prior.get('attempts',[])) if prior else []}
  attempt={}
  try:
   raw=_collect_responses_stream(client,{'model':selected,'reasoning':{'effort':task['generator_reasoning']},'instructions':g['instructions'],'input':json.dumps({'answer':g['answer'],'n':g['n']},ensure_ascii=False),'store':False,'text':{'format':{'type':'json_schema','name':'xiaoan_reverse_questions_v1','strict':True,'schema':schema}}})
   attempt.update(raw_response=str(raw),usage=getattr(raw,'usage',{}));data=json.loads(str(raw));qs=data['questions']
   if len(qs)!=task['n'] or any(not isinstance(q,str) or not q.strip() for q in qs):raise ValueError('invalid questions')
   result.update(status='AVAILABLE',questions=qs)
  except Exception as exc:attempt.update(error_type=type(exc).__name__) # Do not serialize secrets/provider URLs/errors.
  result['attempts'].append(attempt);path.write_text(json.dumps(result,ensure_ascii=False,indent=2));return key,result['status']
 with concurrent.futures.ThreadPoolExecutor(max_workers=a.workers) as pool:
  for key,status in pool.map(one,tasks[:a.limit] if a.limit else tasks):print(key,status,flush=True)
 embeddings=json.loads(a.embeddings.read_text()) if a.embeddings else None
 scores=[];embedding_texts=set();generated=0
 for item in tasks:
  t=item['task'];path=PRIVATE/f"{t['case_id']}-T{t['turn']}.json";g=json.loads(path.read_text()) if path.exists() else None
  if g and g['status']=='AVAILABLE':generated+=1;embedding_texts.update([t['original_question'],*g['questions']])
  score=answer_relevancy(t,g if g and g['status']=='AVAILABLE' else None,embeddings)
  scores.append({'case_id':t['case_id'],'turn':t['turn'],**score})
 (DIR/'answer-relevancy-scores.json').write_text(json.dumps(scores,ensure_ascii=False,indent=2))
 (DIR/'embedding-inputs.json').write_text(json.dumps({'status':'AWAITING_PINNED_EMBEDDING_CONFIG','generated_turns':generated,'texts':sorted(embedding_texts),'format_expected':{'model_id':'provider model ID','revision':'immutable version or deployment/config version; backend unverified if unavailable','vectors':{'exact text':[0.1,0.2]}}},ensure_ascii=False,indent=2))
 valid=[s for s in scores if s['status']=='AVAILABLE']
 summary_path=DIR/'summary.json';summary=json.loads(summary_path.read_text())
 summary['answer_relevancy']={'status':'AVAILABLE' if len(valid)==len(tasks) else 'PARTIAL' if valid else 'UNAVAILABLE','n':3,'prepared_turns':len(tasks),'generated_turns':generated,'generated_questions':generated*3,'scored_turns':len(valid),'turn_macro':sum(s['score'] for s in valid)/len(valid) if valid else None,'reason':None if len(valid)==len(tasks) else 'GENERATION_OR_EMBEDDING_PENDING','embedding_model':embeddings.get('model_id') if embeddings else None,'embedding_revision':embeddings.get('revision') if embeddings else None}
 summary_path.write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 turn_path=DIR/'turn-metrics.json';turns=json.loads(turn_path.read_text());lookup={(s['case_id'],s['turn']):s for s in scores}
 for t in turns:
  if (t['case_id'],t['turn']) in lookup:t['answer_relevancy']=lookup[t['case_id'],t['turn']]
 turn_path.write_text(json.dumps(turns,ensure_ascii=False,indent=2))
 print(json.dumps(summary['answer_relevancy'],ensure_ascii=False))
if __name__=='__main__':main()
