"""Deterministic capsule-to-composer integration; no live Router/LLM claims."""
from pathlib import Path
import json,sys,yaml
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent
sys.path.insert(0,str(R/'tech/chatflow/poc'))
from capsule_test import CapsuleIsolationSession
from ground_selector import GroundSelection
from ground import ground_item_size
class FixedSelector:
 def __init__(self,numbers):self.numbers=tuple(numbers)
 def select(self,*args,**kwargs):return GroundSelection(self.numbers,'offline audit: explicitly supplied branches')
class Capture:
 def __init__(self):self.items=[]
 def compose(self,message,context,items,**kwargs):self.items=items;return '先确认安全，再讨论可行选项。','offline-response'
rows=json.loads((O/'budget-audit.json').read_text());results=[]
for row in rows:
 d=yaml.safe_load((R/'evaluation_multimodels/test-cases'/(row['case']+'.yaml')).read_text());t=d['turns'][row['turn']-1];e=t['expected'];preferred=e.get('preferred_route_id');covered={k:v for k,v in row['routes'].items() if v}
 rt=preferred if preferred in covered else next(iter(covered));numbers=covered[rt]['branches']
 if (row['case'],row['turn'])==('TC-62',3):numbers=[2,10,11]
 cap=Capture();session=CapsuleIsolationSession(rt,ground_selector=FixedSelector(numbers),support_agent=cap)
 # User history is supplied as synthetic test context; no prior answer is fabricated as evidence.
 for prev in d['turns'][:row['turn']-1]:session.state.record_turn(redacted_user_message=prev['user'],assistant_response='',route_id=rt,safety_level='normal',history_limit=10)
 result=session.respond(t['user']);actual={x.ref for x in cap.items}|{x.source_ref for x in cap.items};required={x.removeprefix('content/') for x in e['source_refs']}
 results.append({'case':row['case'],'turn':row['turn'],'route':rt,'branches':numbers,'ground_loaded':result.ground_loaded,'missing_required_refs':sorted(required-actual),'chars':sum(ground_item_size(x) for x in cap.items),'selector':'forced_offline','answer':'fixed_placeholder_not_evaluated'})
summary={'tested_turns':len(results),'passed':sum(x['ground_loaded'] and not x['missing_required_refs'] for x in results),'network_calls':0,'scope':'runtime gate, exact source resolution, budget and composer injection; does not test LLM selector, Router or generated answer'}
(O/'isolation-audit.json').write_text(json.dumps({'summary':summary,'turns':results},ensure_ascii=False,indent=2)+'\n')
print(summary)
for x in results:
 if x['missing_required_refs']:print(x)
