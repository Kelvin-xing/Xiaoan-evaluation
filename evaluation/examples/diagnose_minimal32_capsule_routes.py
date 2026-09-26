"""Read-only, offline diagnosis of selected minimal32 routes. Never calls a model."""
import argparse, collections, hashlib, json, sys
from pathlib import Path
import yaml
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'evaluation/runs/2026-09-14-minimal32-regression'
sys.path.insert(0,str(ROOT/'tech/chatflow/poc'))
from router import eligible_router_capsules, validate_decision
from parameter_contract import sha256_digest

def load(p):return json.loads(p.read_text())
def branch(r):return r if r in {'baseline','crisis_sop'} else 'capsule'

def main():
 parser=argparse.ArgumentParser();parser.add_argument('--assert-no-known-contract-defects',action='store_true');args=parser.parse_args()
 rows=load(OUT/'diagnostic-selected-turns.json');answered=[r for r in rows if r['execution']=='ANSWERED'];bad=[r for r in answered if not r['route_matches_candidate']]
 assert len(answered)==89 and len(bad)==9
 caps=load(ROOT/'tech/chatflow/poc/capsules.json');registry={c['id']:c for c in caps};cache={};evidence=[];pref=[];hashes={}
 for row in answered:
  rid=row['answer_attempt'];directory=ROOT/('evaluation/runs/.'+rid+'.private')
  if rid not in cache:
   manifest=load(directory/'manifest.json')
   for rel in ['tech/chatflow/poc/capsules.json','tech/chatflow/poc/router.py']:
    digest=hashlib.sha256((ROOT/rel).read_bytes()).hexdigest();assert digest==manifest['source_hashes'][rel];hashes[rel]=digest
   records=[json.loads(l) for l in (directory/'evaluation-checkpoint.jsonl').open()]
   cache[rid]=[r for r in records if r.get('event')=='subject_turn']
  case=yaml.safe_load((directory/'cases'/f"{row['case_id']}.yaml").read_text());turn=next(t for t in case['turns'] if t['turn']==row['turn']);ex=turn['expected']
  if row['route']!=ex.get('preferred_route_id'):pref.append({'case_id':row['case_id'],'turn':row['turn'],'actual':row['route'],'preferred':ex.get('preferred_route_id'),'accepted':row['route_matches_candidate']})
  if row not in bad:continue
  matches=[r for r in cache[rid] if r['case_id']==row['case_id'] and r['turn']==row['turn'] and r.get('response')==row['answer']];assert len(matches)==1
  rec=matches[0];trace=rec['trace'];snap=trace['effective_context_snapshot'];assert snap['snapshot_id']==row['snapshot_id'];inv=snap['invocations']['router'];req=inv['provider_request'];assert sha256_digest(req)==inv['request_digest']
  for boundary in ['router','composer']:
   for unit in snap['invocations'][boundary]['context_units']:assert sha256_digest(unit['content'])==unit['content_hash']
  payload=json.loads(req['input'][0]['content']);cards={c['id']:c for c in payload['candidates']}
  observed={u['entity_id']:u['inclusion_state'] for u in inv['context_units'] if u['field_path']=='router_card'}
  assert set(cards)-{'baseline'}=={c for c,state in observed.items() if state=='EXPOSED'}
  comparisons=[]
  for cid in dict.fromkeys([row['route'],*row['candidate_routes']]):
   c=registry.get(cid)
   comparisons.append({'id':cid,'title':c['title'] if c else cid,'path':c['path'] if c else ('content/sops/crisis-sop.md' if cid=='crisis_sop' else 'content/sops/main-agent-baseline-sop.md'),'in_wire_candidates':cid in cards,'snapshot_inclusion_state':observed.get(cid,'SPECIAL_BRANCH_OR_BASELINE'),'wire_card':cards.get(cid),'version_matched_catalog':c,'counterfactual_not_injected':cid!=row['route']})
  cu=snap['invocations']['composer']['context_units'];evidence.append({'case_id':row['case_id'],'turn':row['turn'],'answer_attempt':rid,'snapshot_id':row['snapshot_id'],'router_request_digest':inv['request_digest'],'user':row['user'],'history':payload['conversation_context'],'router_instructions':req.get('instructions'),'active_capsule':payload['active_capsule_id'],'wire_candidate_ids':list(cards),'router_decision':trace['route'],'expected':ex,'comparison':comparisons,'answer':row['answer'],'response_assessment':row['oracle_assessment'],'ground':trace['ground'],'composer_capsule_units':[u for u in cu if u['layer']=='CAPSULE' and u['inclusion_state']=='EXPOSED'],'composer_reference_index':[{'ref':u['ref'],'layer':u['layer'],'content_hash':u['content_hash']} for u in cu if u['layer'] in {'WIKI','SOURCE'} and u['inclusion_state']=='EXPOSED']})
 # One-variable deterministic probe at the actual prefilter seam.
 r=next(r for r in evidence if r['case_id']=='TC-15');h=r['history'];original={c['id'] for c in eligible_router_capsules(r['user'],caps,active_capsule_id=r['active_capsule'],conversation_context=h)}
 h2=[dict(t,user=t['user'].replace('分手','分开')) for t in h];control={c['id'] for c in eligible_router_capsules(r['user'],caps,active_capsule_id=r['active_capsule'],conversation_context=h2)}
 assert 'n6a' not in original and 'n6a' in control
 empty=validate_decision({},caps,'llm');assert empty.capsule_id=='baseline' and empty.confidence==0 and empty.reason==''
 summary={'scope':'89 selected answers; 9 outside acceptable candidate sets; no live calls, no oracle or product edits','actual_branches':dict(collections.Counter(branch(r['route']) for r in answered)),'acceptable_mismatch':len(bad),'preferred_mismatch':len(pref),'preferred_only_mismatch':sum(x['accepted'] for x in pref),'hashes_verified':hashes,'exact_answer_and_snapshot_bindings':len(evidence),'router_wire_and_exposed_catalog_agree':len(evidence),'probes':{'n6a_prefilter':{'original_eligible':False,'single_word_control_eligible':True,'finding':'confirmed lexical prefilter exclusion; does not prove model would select n6a'},'empty_router_payload':{'accepted_as':'baseline','confidence':0,'reason':'','finding':'confirmed validator contract hole; actual TC61 raw response not recorded, cause remains unproven'}},'preferred_differences':pref}
 (OUT/'capsule-route-diagnosis-evidence.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2))
 (OUT/'capsule-route-diagnosis-audit.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2))
 print(json.dumps({k:v for k,v in summary.items() if k not in {'preferred_differences','hashes_verified'}},ensure_ascii=False,indent=2))
 if args.assert_no_known_contract_defects:
  print('KNOWN_DEFECTS_PRESENT: n6a lexical exclusion; incomplete JSON accepted as baseline');return 1
 return 0
if __name__=='__main__':raise SystemExit(main())
