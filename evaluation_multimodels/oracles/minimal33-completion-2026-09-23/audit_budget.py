from pathlib import Path
import sys,json,itertools,warnings
R=Path(__file__).resolve().parents[3];sys.path.insert(0,str(R/'tech/chatflow/poc'))
from ground import resolve_ground_branches,ground_item_size
from capsule_content import GroundBranch
idx=json.loads((R/'evaluation_multimodels/oracles/content-index-2026-09-23.json').read_text());rows=json.loads((R/'evaluation_multimodels/oracles/minimal33-reference-repair-2026-09-23/remaining-work.json').read_text())['turns']
import yaml
results=[]
for row in rows:
 if row['ground']!='required':continue
 e=yaml.safe_load((R/'evaluation_multimodels/test-cases'/(row['case']+'.yaml')).read_text())['turns'][row['turn']-1]['expected'];refs={r.removeprefix('content/') for r in e['source_refs']};ns=set(e['reference_oracle']['ground']['required_node_ids']);routes={}
 for rt,info in row['routes'].items():
  if rt not in idx['capsules']:continue
  bs=[GroundBranch(**b) for b in idx['capsules'][rt]['ground_branches']];found=None
  for count in range(1,min(3,len(bs))+1):
   for combo in itertools.combinations(range(1,len(bs)+1),count):
    if not ns<={bs[i-1].node_id for i in combo}:continue
    with warnings.catch_warnings():
     warnings.simplefilter('ignore');items,w=resolve_ground_branches(bs,combo,strict_headings=True,max_chars=8000)
    actual={x.ref for x in items}|{x.source_ref for x in items}
    if refs<=actual:
     found={'branches':combo,'chars':sum(ground_item_size(x) for x in items),'warnings':w,'conditions':[bs[i-1].condition for i in combo]};break
   if found:break
  routes[rt]=found
 results.append({'case':row['case'],'turn':row['turn'],'routes':routes,'covered':any(routes.values())})
out=R/'evaluation_multimodels/oracles/minimal33-completion-2026-09-23/budget-audit.json';out.write_text(json.dumps(results,ensure_ascii=False,indent=2)+'\n')
print('required turns:',len(results),'budget failures:',[(x['case'],x['turn']) for x in results if not x['covered']])
for x in results:
 if x['case'] in ['TC-12','TC-29','TC-42','TC-53','TC-62','TC-72']:print(x)
