from pathlib import Path
import importlib.util,sys,json,yaml,hashlib,copy
from dataclasses import asdict
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;C=O/'candidate';sys.path.insert(0,str(R/'tech/chatflow/poc'))
import ground
from capsule_loader import parse_capsule
from capsule_content import parse_ground_branches
from ground_selector import GroundSelection
from capsule_test import CapsuleIsolationSession
spec=importlib.util.spec_from_file_location('candidate_refresh',R/'evaluation_multimodels/oracles/refresh_current.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);m.ROOT=C;m.OUT=O/'candidate-oracles';m.OUT.mkdir(exist_ok=True);m.DATE='2026-09-24';m.main()
index=json.loads((m.OUT/'content-index-2026-09-24.json').read_text());assert not index['reference_errors']
ids=json.loads((R/'docs/plans/evaluation-minimal33.selection.json').read_text())['case_ids'];updates=[]
for cid in ids:
 p=C/'evaluation_multimodels/test-cases'/(cid+'.yaml');d=yaml.safe_load(p.read_text())
 for t in d['turns']:
  r=t['expected']['reference_oracle'];old=r['snapshot_id'];r['snapshot_id']=index['snapshot_id']
  for route in r['route_contracts']:
   if route in index['capsules']:
    r['route_contracts'][route]=copy.deepcopy(index['capsules'][route]);r['route_contracts'][route]['ground_policy']='conditional_on_demand'
  ns=set(r['ground']['required_node_ids']);r['runtime_ground_gaps']={rt:sorted(ns-set(c['configured_ground_node_ids'])) for rt,c in r['route_contracts'].items() if ns-set(c['configured_ground_node_ids'])}
  if r['status']=='reviewed':
   r['reviewed_snapshot_id']=old;r['technical_rebind']={'authored_by':'codex','date':'2026-09-24','scope':'用户接受的路由/安全/必需来源标签不变；仅刷新内容快照及可配置分支清单','not_new_human_review':True}
 for pkg in ['evaluation','evaluation_multimodels']:(C/pkg/'test-cases'/p.name).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=120))
# Exercise real preparation and composer injection against isolated candidate directories.
ground.REPO_ROOT=C;ground.KNOWLEDGE_DIR=C/'content/knowledge';ground.SOURCE_DIR=ground.KNOWLEDGE_DIR/'source';ground.WIKI_NODE_DIR=ground.KNOWLEDGE_DIR/'wiki/nodes'
caps=[parse_capsule(p) for p in (C/'content/capsule').glob('*.md') if p.name not in ['AGENTS.md','template.md']]
class Selector:
 def __init__(self,n):self.n=tuple(n)
 def select(self,*args,**kwargs):return GroundSelection(self.n,'candidate deterministic injection audit')
class Capture:
 def __init__(self):self.items=[]
 def compose(self,msg,ctx,items,**kwargs):self.items=items;return '先确认安全，再讨论可行选项。','offline-candidate'
results=[]
for x in json.loads((O/'candidate-validation.json').read_text())['checks']:
 d=yaml.safe_load((C/'evaluation_multimodels/test-cases'/(x['case']+'.yaml')).read_text());t=d['turns'][x['turn']-1];cap=Capture();s=CapsuleIsolationSession(x['route'],capsule_provider=lambda:caps,ground_selector=Selector(x['branches']),support_agent=cap)
 for old in d['turns'][:x['turn']-1]:s.state.record_turn(redacted_user_message=old['user'],assistant_response='',route_id=x['route'],safety_level='normal',history_limit=10)
 result=s.respond(t['user']);want={ref.removeprefix('content/') for ref in (t['expected']['source_refs'] or t['expected']['reference_oracle']['ground']['background_source_refs'])};actual={i.ref for i in cap.items}|{i.source_ref for i in cap.items};assert want<=actual,(x,want-actual)
 results.append({**x,'runtime_ground_loaded':result.ground_loaded,'injection_passed':True})
summary={'candidate_only':True,'cases':33,'turns':100,'source_count':len(list(ground.SOURCE_DIR.glob('[0-9][0-9][0-9]-*.md'))),'node_count':len(index['nodes']),'content_reference_errors':0,'runtime_combinations_passed':len(results),'network_calls':0,'meaning':'proposed classifications; strict refs, budget and forced-branch injection; not online or human approval'}
(O/'candidate-integration-audit.json').write_text(json.dumps({'summary':summary,'checks':results},ensure_ascii=False,indent=2)+'\n');print(summary)
