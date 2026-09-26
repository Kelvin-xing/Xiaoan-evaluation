"""Fresh Judge on explicitly selected frozen cases; never regenerates subject answers."""
from pathlib import Path
import sys,json,argparse,hashlib
from concurrent.futures import ThreadPoolExecutor
ROOT=Path(__file__).resolve().parents[2]
sys.path[:0]=[str(ROOT/'evaluation'),str(ROOT/'tech/chatflow/poc')]
from xiaoan_eval.runner import CaseRunResult,TurnRunResult
from xiaoan_eval.pipeline import EvaluationPipeline
from xiaoan_eval.judge_client import JudgeClient
from xiaoan_eval.checkpoint import JsonlCheckpoint
from xiaoan_eval.cases import load_cases
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval.config import load_evaluator_config
import company_eval_plugins as plugins

def main():
 p=argparse.ArgumentParser();p.add_argument('--source-run',required=True);p.add_argument('--output-run',required=True);p.add_argument('--cases',nargs='+',required=True);p.add_argument('--execute',action='store_true');p.add_argument('--only-missing',action='store_true');p.add_argument('--workers',type=int,default=2);a=p.parse_args()
 if not 1<=a.workers<=4:raise ValueError('invalid workers')
 if any(Path(x).name!=x for x in [a.source_run,a.output_run]):raise ValueError('invalid run id')
 source=ROOT/'evaluation/runs'/('.'+a.source_run+'.private');out=ROOT/'evaluation/runs'/('.'+a.output_run+'.private');out.mkdir(exist_ok=True,mode=0o700)
 events=[json.loads(l) for l in (source/'evaluation-checkpoint.jsonl').read_text().splitlines()];subjects={}
 for e in events:
  if e.get('event')=='subject_turn':subjects.setdefault((e['case_id'],e['turn']),e)
 allowed={f.stem for f in (ROOT/'evaluation/runs/2026-09-13-minimal32-inputs/cases').glob('*.yaml')}
 if not set(a.cases)<=allowed:raise ValueError('outside authorized cases')
 rule=load_rating_rule(ROOT/'evaluation/ratings rule.yml');config=load_evaluator_config(ROOT/'evaluation/evaluator-config.yml')
 cases=[r.case for r in load_cases(source/'cases',rule) if r.case and r.case.id in a.cases]
 manifest={'source_run':a.source_run,'cases':a.cases,'source_checkpoint_sha256':hashlib.sha256((source/'evaluation-checkpoint.jsonl').read_bytes()).hexdigest(),'provider_code_sha256':hashlib.sha256(Path(plugins.__file__).read_bytes()).hexdigest(),'mode':'fresh judge diagnostic; frozen first subject answers; original results retained','only_missing':a.only_missing,'workers':a.workers,'models':{k:plugins._evaluation_value(k,'') for k in ('XIAOAN_JUDGE_MODEL','XIAOAN_JUDGE_REASONING_EFFORT')}}
 binding=hashlib.sha256(json.dumps(manifest,sort_keys=True).encode()).hexdigest();mp=out/'manifest.json'
 if mp.exists() and json.loads(mp.read_text())!=manifest:raise ValueError('replay changed')
 mp.write_text(json.dumps(manifest,indent=2))
 if a.only_missing:
  source_manifest=json.loads((source/'manifest.json').read_text())
  for key,value in manifest['models'].items():
   if source_manifest['models'].get(key)!=value:raise ValueError('Judge model settings changed')
  for name,digest in source_manifest['source_hashes'].items():
   if name.startswith('evaluation/xiaoan_eval/') or name in {'evaluation/company_eval_plugins.py','evaluation/ratings rule.yml'} or '/cases/' in name:
    if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:raise ValueError('frozen Judge contract or cases changed: '+name)
 if not a.execute:return
 if plugins._openai_client().base_url.host!='api.karoapi.com':raise ValueError('unapproved endpoint')
 original=plugins.OpenAI
 class Bounded(original):
  def __init__(self,*args,**kwargs):kwargs.update(timeout=180,max_retries=0);super().__init__(*args,**kwargs)
 plugins.OpenAI=Bounded
 with JsonlCheckpoint(out/'evaluation-checkpoint.jsonl',binding) as cp:
  def one(case):
   cache=out/(case.id+'.json')
   if cache.exists():return
   rows=[subjects[(case.id,t.turn)] for t in case.turns if (case.id,t.turn) in subjects]
   class Frozen:
    def run_cases(self,_):return [CaseRunResult(case.id,'COMPLETED','frozen',[TurnRunResult(e['turn'],e.get('response'),e['trace'],e.get('error')) for e in rows])]
   original_record=json.loads((source/(case.id+'.json')).read_text())
   valid_turns={o['turn'] for o in original_record.get('pipeline',{}).get('observations',[]) if o.get('judge',{}).get('oracle_assessment')}
   prior_raw={e['turn']:e['raw_response'] for e in events if e.get('event')=='primary_judge' and e.get('case_id')==case.id and e.get('raw_response')}
   if a.only_missing:
    source_manifest=json.loads((source/'manifest.json').read_text())
    if source_manifest['source_hashes']['evaluation/company_eval_plugins.py']!=manifest['provider_code_sha256']:raise ValueError('cannot reuse Judge under changed provider evidence contract')
   def judge(req):
    if a.only_missing and req['turn'] in valid_turns and req['turn'] in prior_raw:return prior_raw[req['turn']]
    result=plugins.judge(req);print(case.id,req['turn'],'JUDGE RETURNED',flush=True);return result
   pipe=EvaluationPipeline(Frozen(),rule,config,primary_judge=JudgeClient(judge,rule,checkpoint=cp,checkpoint_event='primary_judge'),authoritative_context_provider=plugins.authoritative_context)
   result=pipe.evaluate_case(case);cache.write_text(json.dumps(result,ensure_ascii=False,indent=2));print(case.id,'COMPLETE',flush=True)
  with ThreadPoolExecutor(max_workers=a.workers) as pool:list(pool.map(one,cases))
if __name__=='__main__':main()
