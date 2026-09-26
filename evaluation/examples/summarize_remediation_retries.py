"""Explicitly selected, conversation-coherent diagnostic view; first run remains intact."""
from pathlib import Path
from collections import Counter
import json,hashlib
ROOT=Path(__file__).resolve().parents[2]
FIRST='2026-09-14-minimal32-regression';RETRY='2026-09-14-minimal32-provider-retry';JUDGE='2026-09-14-minimal32-judge-retry'
def main():
 base=ROOT/'evaluation/runs';out=base/FIRST
 rows=json.loads((out/'turn-review.json').read_text());other=json.loads((base/RETRY/'turn-review.json').read_text())
 manifests={name:json.loads((base/('.'+name+'.private')/'manifest.json').read_text()) for name in [FIRST,RETRY]}
 core=lambda m:{k:v for k,v in m['source_hashes'].items() if not k.startswith('evaluation/runs/')}
 if core(manifests[FIRST])!=core(manifests[RETRY]) or manifests[FIRST]['models']!=manifests[RETRY]['models']:raise ValueError('retry runtime or models differ')
 source_cases={cid:FIRST for cid in manifests[FIRST]['case_ids']}
 for cid in manifests[RETRY]['case_ids']:
  a=(base/('.'+FIRST+'.private')/'cases'/(cid+'.yaml')).read_bytes();b=(base/('.'+RETRY+'.private')/'cases'/(cid+'.yaml')).read_bytes()
  if a!=b:raise ValueError('case oracle changed')
  case_rows=[r for r in other if r['case_id']==cid]
  if all(r['execution']=='ANSWERED' for r in case_rows):source_cases[cid]=RETRY
 selected=[];recovered_judges=[]
 for old in rows:
  cid=old['case_id'];turn=old['turn'];attempt=source_cases[cid]
  chosen=old if attempt==FIRST else next(r for r in other if r['case_id']==cid and r['turn']==turn)
  chosen=dict(chosen,answer_attempt=attempt,judge_attempt=attempt)
  if attempt==FIRST and chosen['execution']=='ANSWERED' and not chosen['judge_validated']:
   p=base/('.'+JUDGE+'.private')/(cid+'.json')
   if p.exists():
    obs=next((o for o in json.loads(p.read_text()).get('pipeline',{}).get('observations',[]) if o['turn']==turn),{})
    assessment=obs.get('judge',{}).get('oracle_assessment')
    if assessment:
     chosen.update(judge_validated=True,oracle_assessment=assessment,judge_attempt=JUDGE,faithfulness_claims=obs.get('judge',{}).get('faithfulness_claims',[]))
     verdicts=Counter(i['verdict'] for i in assessment['items']);chosen['response_oracle_verdicts']=dict(verdicts)
     chosen['response_oracle_all_satisfied']=False if verdicts['VIOLATED'] else None if verdicts['UNCERTAIN'] else True
     recovered_judges.append({'case_id':cid,'turn':turn,'assessment':assessment})
  attr_path=base/('.'+attempt+'-attribution.private')/f"{cid}-T{turn}.json"
  attr=json.loads(attr_path.read_text()) if attr_path.exists() else {}
  chosen['independent_attribution_valid']=bool(attr.get('status')=='AVAILABLE' and attr.get('answer_sha256')==hashlib.sha256((chosen.get('answer') or '').encode()).hexdigest() and attr.get('snapshot_id')==chosen.get('snapshot_id')) if chosen['execution']=='ANSWERED' else None
  selected.append(chosen)
 def ratio(key):
  eligible=[r[key] for r in selected if r[key] is not None];return {'pass':sum(v is True for v in eligible),'fail':sum(v is False for v in eligible),'eligible':len(eligible)}
 complete_cases=sum(all(r['execution']=='ANSWERED' for r in selected if r['case_id']==cid) for cid in source_cases)
 result={'interpretation':'Diagnostic selection only; each case uses one complete answer attempt; no mixing conversation histories. First-run metrics and failures remain unchanged.',
  'same_runtime_and_models':True,'case_answer_attempts':source_cases,'complete_answer_cases':complete_cases,'planned_cases':32,'execution':dict(Counter(r['execution'] for r in selected)),
  'snapshot':ratio('snapshot_valid'),'history':ratio('history_matches'),'capsule_exposure':ratio('selected_capsule_exposed'),'candidate_routes':ratio('route_matches_candidate'),'candidate_crisis':ratio('crisis_takeover'),
  'independent_attribution':ratio('independent_attribution_valid'),'validated_judges':sum(r['judge_validated'] for r in selected),'response_oracle':ratio('response_oracle_all_satisfied'),'first_run_recovered_judges':len(recovered_judges)}
 (out/'retry-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
 (out/'diagnostic-selected-turns.json').write_text(json.dumps(selected,ensure_ascii=False,indent=2))
 (out/'judge-retry-assessments.json').write_text(json.dumps(recovered_judges,ensure_ascii=False,indent=2))
 text=f'''# 运营失败补跑：独立诊断视图

首轮数据不变。回答补跑采用相同代码、知识、oracle与模型；降低并发为2。TC-48、63、72、74恢复完整回答；TC-61新尝试在第二轮被护栏拒绝，保留原批次已完成的两轮，其第三轮仍未验证。每案只选一条真实对话链，不拼接不同尝试的前后文。

- 完整回答案例：{complete_cases}/32。
- 按上述完整案例选择后，回答及未完成状态：{json.dumps(result['execution'],ensure_ascii=False)}。
- 原批次主Judge补评恢复：{len(recovered_judges)}/6轮；原71轮通过校验的结果保留。
- 诊断视图独立归因结果通过校验：{result['independent_attribution']}；不等同语义全通过。
- 诊断视图主Judge有效结果：{result['validated_judges']}轮。
- 快照：{result['snapshot']}；历史：{result['history']}；注入身份：{result['capsule_exposure']}。
- 候选路由：{result['candidate_routes']}；候选强制危机：{result['candidate_crisis']}。候选不是批准gold。
- 回应要求：{result['response_oracle']}；为Judge候选判断，仍需校准。

[逐轮选择及证据](diagnostic-selected-turns.json) · [选择清单及汇总](retry-summary.json) · [新增Judge结果](judge-retry-assessments.json) · [回答补跑独立报告](../{RETRY}/README.zh-CN.md)

这是运营失败补跑后的诊断覆盖，不能替换首轮77/96回答成功率，也不能用重试选择后的质量指标宣称同一次无偏全量结果。所有运营失败与护栏拒绝保留，不计质量零分。
'''
 (out/'RETRIES.zh-CN.md').write_text(text)
 print(json.dumps({k:v for k,v in result.items() if k not in {'case_answer_attempts','interpretation'}},ensure_ascii=False))
if __name__=='__main__':main()
