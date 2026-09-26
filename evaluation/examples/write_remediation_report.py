"""Build a local, evidence-linked research report from completed frozen runs."""
from pathlib import Path
import argparse,json,csv
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]

def write(run_id):
 out=ROOT/'evaluation/runs'/run_id
 retry_path=out/'retry-summary.json'; retry=json.loads(retry_path.read_text()) if retry_path.exists() else {}
 summary=json.loads((out/'summary.json').read_text());rows=json.loads((out/'turn-review.json').read_text());matrix=json.loads((out/'metric-matrix.json').read_text())
 attrs=ROOT/'evaluation/runs'/('.'+run_id+'-attribution.private')
 findings=[];counts=Counter();available=0;corrections=0
 for r in rows:
  if r['route_matches_candidate'] is False:
   findings.append({'category':'ROUTE_CANDIDATE_MISMATCH','case_id':r['case_id'],'turn':r['turn'],'user':r['user'],'answer_quote':r['answer'],'evidence_quote':'','detail':f"actual={r['route']}; acceptable={r['candidate_routes']}",'interpretation':'待审核路由差异，不自动改gold'})
  for item in (r.get('oracle_assessment') or {}).get('items',[]):
   if item['verdict']!='SATISFIED':
    findings.append({'category':'RESPONSE_'+item['verdict'],'case_id':r['case_id'],'turn':r['turn'],'user':r['user'],'answer_quote':' | '.join(s['quote'] for s in item.get('spans',[])),'evidence_quote':'','detail':item['id']+': '+item['reason'],'interpretation':'保留Judge候选判断；缺省引文表示要求遗漏，不是伪造空引文'})
  path=attrs/f"{r['case_id']}-T{r['turn']}.json"
  if not path.exists():continue
  a=json.loads(path.read_text())
  if a.get('status')!='AVAILABLE':continue
  # The matrix already checks answer and snapshot binding; use its validity here too.
  if not any(m['case_id']==r['case_id'] and m['turn']==r['turn'] and m['metric'] in {'capsule_semantic_attribution','sop_semantic_attribution'} and m['status']=='AVAILABLE' for m in matrix):continue
  available+=1;corrections+=len(a.get('span_corrections',[]))
  for c in a['assessment']['claims']:
   counts['claims']+=1
   ordinary=r['route'] not in {'baseline','crisis_sop'}
   if ordinary:counts['ordinary_capsule_claims']+=1
   if ordinary and any(x['layer']=='CAPSULE' and x['relation'] in {'ENTAILS','PARTIAL'} for x in c['relations']):counts['ordinary_capsule_supported_claims']+=1
   if any(x['layer']=='CAPSULE' and x['relation'] in {'ENTAILS','PARTIAL'} for x in c['relations']):counts['claims_with_capsule_support']+=1
   if any(x['layer']=='SOURCE' and x['relation'] in {'ENTAILS','PARTIAL'} for x in c['relations']):counts['claims_with_source_support']+=1
   for rel in c['relations']:counts['relation_'+rel['relation']]+=1
   if c.get('unsupported_category')=='UNVERIFIABLE_UNSUPPORTED':
    counts['unverifiable_claims']+=1
    findings.append({'category':'UNVERIFIABLE_CANDIDATE','case_id':r['case_id'],'turn':r['turn'],'user':r['user'],'answer_quote':c['answer_span']['text'],'evidence_quote':'','detail':c.get('uncertainty',''),'interpretation':'证据不足候选；须区分实际错误、问句/建议误判和来源/政策缺口'})
   for rel in c['relations']:
    if rel['relation']=='CONTRADICTS':
     counts['contradiction_relations']+=1
     findings.append({'category':'CONTRADICTION_CANDIDATE','case_id':r['case_id'],'turn':r['turn'],'user':r['user'],'answer_quote':c['answer_span']['text'],'evidence_quote':(rel.get('evidence_span') or {}).get('text',''),'detail':rel['evidence_ref'],'interpretation':'精确引文已验证，矛盾含义仍需核查适用条件'})
 attr_summary={'available_turns':available,'counts':dict(counts),'span_corrections':corrections,'warning':'Attribution is semantic evidence, not causal proof or an exhaustive policy compliance gate.'}
 (out/'attribution-summary.json').write_text(json.dumps(attr_summary,ensure_ascii=False,indent=2))
 (out/'research-findings.json').write_text(json.dumps(findings,ensure_ascii=False,indent=2))
 if findings:
  with (out/'research-findings.csv').open('w',encoding='utf-8-sig',newline='') as f:
   w=csv.DictWriter(f,fieldnames=list(findings[0]));w.writeheader();w.writerows(findings)
 def ratio(k):
  v=summary[k];return f"{v['pass']}/{v['eligible']}（失败{v['fail']}）"
 paired=[r for r in rows if r['execution']=='ANSWERED' and r['old_route']]
 old_matches=sum(r['old_route'] in r['candidate_routes'] for r in paired)
 new_matches=sum(r['route_matches_candidate'] for r in paired)
 mismatch=[f"{r['case_id']}/T{r['turn']} `{r['route']}`" for r in rows if r['route_matches_candidate'] is False]
 data=f'''# 最小32案：整改后同版回归与研究入口

执行状态：{'首轮批次已完成，运营失败另列' if summary.get('execution_complete') else '进行中，以下为中间结果'}。

版本：`{summary['version']}`。原32案96轮；使用 KaroAPI，Router/回答 gpt-5.6-luna（xhigh），Judge gpt-5.6-sol（medium）。本地改动和运行产物没有推送。

## 实际结果

| 指标 | 本次结果 |
|---|---|
| 执行状态 | {json.dumps(summary['execution'],ensure_ascii=False)} |
| 实际分支 | {json.dumps(summary.get('route_branches',{}),ensure_ascii=False)} |
| 有效快照 | {ratio('snapshot')} |
| Composer后续轮历史一致 | {ratio('history')} |
| 选定capsule/SOP实际注入 | {ratio('capsule_exposure')} |
| 已触发红旗时crisis优先 | {ratio('red_flag_precedence')} |
| 独立危机候选要求接管 | {ratio('candidate_crisis_takeover')} |
| 候选route可接受集合一致 | {ratio('candidate_route_agreement')} |
| 主Judge结果通过合同及引文校验 | {summary['judge_validated']}轮 |
| 首轮回答补评后Judge可用 | {summary['judge_validated']+retry.get('first_run_recovered_judges',0)}轮；首轮失败仍保留 |
| 回应要求全部满足 | {ratio('response_oracle')}；含UNCERTAIN且无明确失败的轮次不计通过 |
| 实际注入Source | {summary['source_exposed_turns']}轮；不等同语义使用 |
| 独立逐引文归因可用 | {available}轮、{counts['claims']}项主张 |
| 至少有capsule/SOP语义支持的主张 | {counts['claims_with_capsule_support']}；不是完整遵循率 |
| 普通capsule分支主张 | {counts['ordinary_capsule_claims']}项，其中{counts['ordinary_capsule_supported_claims']}项有capsule支持；其余可能由用户/Source等支持，不能直接判不遵循 |
| 至少有Source语义支持的主张 | {counts['claims_with_source_support']} |
| 无法核实补充候选 | {counts['unverifiable_claims']}项；不统称幻觉 |

在同一候选标签下，可配对的{len(paired)}轮路由一致数从旧回答的{old_matches}变为新回答的{new_matches}；这只是描述性前后比较，不构成单变量因果证明。

上表按每项有效分母计算。Provider失败、输出护栏拒绝、依赖未运行分别保留，不记质量零分。首轮结果不被重试诊断覆盖。路由和风险候选标签仍未逐项人工批准；用户已确认的是产品边界。31项×96轮的可用性与阻塞原因见首轮指标表。原6轮Judge失败仍留在首轮表内；新增补评与诊断选择另表展示，避免覆盖运营证据。

## 本轮已修复且有回归证据的工程问题

1. 补足当前持刀/自伤动作表述识别；危机延续到明确安全解除，新危险仍优先。负例包括新增表达的否定、历史、假设、日常做饭。它仍是规则扫描器，不是完整风险语义分类器。
2. ChatService向同步/流式Composer传递真实历史，并在实际快照保留用户及助手历史；原生Responses续接不重复注入，KaroAPI兼容保留。
3. 按标题与锚点迁移21个Wiki文件，隔离2处退役/不可核实材料；87个Source Markdown未改。新版expected引用重新绑定，两包清单一致。
4. 捕获provider流式ReadTimeout，作为单轮运营失败返回，不使整批崩溃。
5. Judge依据哈希验证后的当轮Composer Wiki/Source快照，按完整证据总字数限流；修复12引用上限并避免以当前文件冒充旧证据。TC-72旧回答复评4/4校验通过。

本地检查：Chatflow169项；evaluation308项；evaluation_multimodels337项。引用完整性检查通过。没有把这些程序测试当成回答语义正确的证明。

## 补跑诊断

[补跑与对话链选择](RETRIES.zh-CN.md)保留首轮结果并单列恢复情况。当前诊断视图覆盖{retry.get('execution',{}).get('ANSWERED',0)}/96轮回答、{retry.get('complete_answer_cases',0)}/32案完整对话；不是以此替换首轮成功率。

## 研究顺序与未解决项

先看危机路径的必要行为遗漏及安全澄清缺失，再看身份/前文是否真正用于回答、路由差异，最后逐条审阅法律/医疗/其他无来源补充及Judge误判。每个候选问题均保留原话和证据；不要按总分直接调整prompt。

候选路由差异：{', '.join(mismatch) or '无'}。

原18轮危机不一致已拆为2个当前动作漏检、1个跨轮合同缺口、15个边界校准项。原4个SOP矛盾、21轮36项不可核实补充不能整体确认为缺陷。原80个回应VIOLATED/UNCERTAIN仍有逐项裁定工作，本轮研究清单也不冒充人工审核完成。

4条Wiki文档级引用仍缺精确锚点，其兼容层警告只出现在stderr、未进入结构化ground.warnings，因此后者为空不能证明来源解析完整；全74案引用清单中有25轮专题来源缺口、24轮候选ground节点覆盖差距；其中本32案分别涉及11轮和11轮，二者可能重叠。正式Wiki source-manifest未提升为已验收。结构化policy_ids、事实记忆生命周期/跨session探针、精确ground recall、capsule因果消融仍有缺口，详见各项NOT_APPROVED／ORACLE_MISSING／TRACE_MISSING／NOT_APPLICABLE，不将其填成零分或通过。

## 可审阅材料

- [逐轮新旧回答与证据（可筛选）](review.html)
- [31项首轮指标矩阵](metric-matrix.csv) · [各项可用性统计](metric-summary.json)
- [路由、回应与归因候选问题](research-findings.csv) · [独立归因摘要](attribution-summary.json)
- [逐轮原始汇总](turn-review.csv) · [首轮运行摘要](summary.json)
- [下一批具体修复与验收](../../oracles/minimal32-remediation/NEXT-FIXES.zh-CN.md) · [运行与恢复说明](../../oracles/minimal32-remediation/RUNBOOK.zh-CN.md)
- [新版回答二次校准](../../oracles/minimal32-remediation/FOLLOWUP-CALIBRATION.zh-CN.md)
- [整改与校准依据](../../oracles/minimal32-remediation/REVIEW.zh-CN.md) · [15轮边界变化](../../oracles/minimal32-remediation/boundary-review-v2.json)

此次为多项修复前后诊断，不是单变量因果实验。下一轮应集中修复已人工校准的高风险语义问题并定向验证，暂不再次盲跑整套或宣布可发布。
'''
 (out/'README.zh-CN.md').write_text(data)
 print(json.dumps({'findings':len(findings),'attribution':attr_summary},ensure_ascii=False))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('run_id');write(p.parse_args().run_id)
