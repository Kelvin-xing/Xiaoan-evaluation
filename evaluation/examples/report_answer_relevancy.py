"""Build frozen answer relevancy reports; no network calls."""
import collections,csv,hashlib,html,json,statistics
from pathlib import Path
from answer_metric_contracts import digest
ROOT=Path(__file__).resolve().parents[2];D=ROOT/'evaluation/runs/2026-09-15-minimal32-answer-metrics';P=ROOT/'evaluation/runs/.2026-09-15-minimal32-answer-relevancy.private'

def main():
 scores=json.loads((D/'answer-relevancy-scores.json').read_text());tasks=json.loads((D/'relevancy-tasks.json').read_text());turns=json.loads((D/'turn-metrics.json').read_text());tl={(t['task']['case_id'],t['task']['turn']):t for t in tasks};tr={(t['case_id'],t['turn']):t for t in turns};rows=[]
 for s in scores:
  k=s['case_id'],s['turn'];task=tl[k]['task'];g=json.loads((P/f'{k[0]}-T{k[1]}.json').read_text());assert g['binding']==s['binding']==digest(task)
  rows.append({**s,'branch':tr[k]['branch'],'user':task['original_question'],'answer':task['generation_input']['answer'],'reverse_questions':g['questions'],'primary_faithfulness':tr[k]['faithfulness']['primary_binary']['score'],'independent_entailment_proxy':tr[k]['faithfulness']['independent_strict_entailment_proxy']['score']})
 valid=[r for r in rows if r['status']=='AVAILABLE'];vs=[r['score'] for r in valid]
 def stats(xs):
  if not xs:return {'n':0,'mean':None}
  q=statistics.quantiles(xs,n=4,method='inclusive') if len(xs)>1 else [xs[0]]*3
  return {'n':len(xs),'mean':statistics.mean(xs),'median':statistics.median(xs),'q1':q[0],'q3':q[2],'min':min(xs),'max':max(xs),'std_population':statistics.pstdev(xs)}
 cases=collections.defaultdict(list)
 for t in turns:cases[t['case_id']].append(t)
 byid={(r['case_id'],r['turn']):r for r in valid};complete=[]
 for c,ts in cases.items():
  if all((c,t['turn']) in byid for t in ts):complete.append(statistics.mean(byid[c,t['turn']]['score'] for t in ts))
 embed=json.loads((P/'google-embedding-vectors.json').read_text());attempts=embed['attempts'];usage=collections.Counter();gens=0;errors=collections.Counter()
 for f in P.glob('TC-*.json'):
  g=json.loads(f.read_text())
  for a in g['attempts']:
   gens+=1
   if a.get('error_type'):errors[a['error_type']]+=1
   for key in ['input_tokens','output_tokens','total_tokens']:usage[key]+=a.get('usage',{}).get(key,0) or 0
 result={'version':'answer-relevancy-reverse-q/v1','question_mode':'raw_current_user','planned_turns':96,'answered_turns':89,'available_scores':len(valid),'n_per_answer':3,'question_count':267,'all_query_pair_mean':statistics.mean(x for r in valid for x in r['similarities']) if valid else None,'turn_statistics':stats(vs),'by_branch':{b:stats([r['score'] for r in valid if r['branch']==b]) for b in ['baseline','crisis_sop','capsule']},'complete_case_macro':stats(complete),'duplicate_question_count':sum(r.get('duplicate_questions',0) for r in valid),'embedding_config':embed['config'],'backend_version':'UNVERIFIED','operations':{'generation_attempts_recorded':gens,'generation_errors':dict(errors),'generation_reported_tokens':dict(usage),'embedding_success_batches':sum(a['status']=='AVAILABLE' for a in attempts),'embedding_failed_batches':sum(a['status']!='AVAILABLE' for a in attempts),'embedding_http_statuses':dict(collections.Counter(str(a.get('http_status')) for a in attempts)),'unique_vectors':len(embed['vectors']),'billed_cost':None},'limits':['Cosine is not a success probability. No pass/fail threshold calibrated.','Raw current messages may require prior conversation; generator sees answer only.','Similar questions do not establish completeness, concision, factual accuracy or safety.','Only latest selected Luna answers, not a cross-model comparison.']}
 (D/'answer-relevancy-summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(D/'answer-relevancy-review.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2))
 with (D/'answer-relevancy-by-turn.csv').open('w') as f:
  w=csv.writer(f);w.writerow(['case','turn','branch','status','mean_cosine','q1_cosine','q2_cosine','q3_cosine','user','reverse_question_1','reverse_question_2','reverse_question_3'])
  for r in rows:w.writerow([r['case_id'],r['turn'],r['branch'],r['status'],r['score'],*(r.get('similarities') or [None]*3),r['user'],*r['reverse_questions']])
 esc=lambda s:html.escape(str(s));cards=[]
 for r in sorted(rows,key=lambda r:r['score'] if r['score'] is not None else -2):
  pairs=''.join(f'<li>{esc(q)} <strong>{v:.4f}</strong></li>' for q,v in zip(r['reverse_questions'],r.get('similarities',[])))
  cards.append(f"<article><h2>{r['case_id']} / T{r['turn']} · {r['branch']} · {r['score']:.4f}</h2><p><b>原问题：</b>{esc(r['user'])}</p><p><b>原回答：</b>{esc(r['answer'])}</p><ol>{pairs}</ol></article>" if r['score'] is not None else f'<article>{esc(r)}</article>')
 (D/'answer-relevancy-review.html').write_text('<!doctype html><meta charset="utf-8"><title>Answer Relevancy 逐轮审阅</title><style>body{max-width:1050px;margin:32px auto;font:16px/1.7 system-ui;background:#f5f4ef;color:#183342}article{padding:24px;margin:20px 0;background:white;border:1px solid #ddd}h2{color:#087f8c}strong{float:right}</style><h1>Answer Relevancy：按分数升序审阅</h1><p>平均余弦不是正确率；低分是核查入口，不是自动失败。生成器只见回答，N=3。</p>'+''.join(cards))
 lines=['# Answer Relevancy 实测结果 · 2026-09-15\n',f"**{len(valid)}/89轮有回答的样本完成评分**；32案96轮中的其余7轮没有回答，保留执行失败/依赖未运行，不计质量零。N=3，共267个反向问题。\n",'## 实测统计\n',f"逐轮平均余弦的均值：**{statistics.mean(vs):.4f}**；中位数{statistics.median(vs):.4f}；范围{min(vs):.4f}–{max(vs):.4f}。这不是百分制准确率。\n",'| 分支 | 回答数 | 平均余弦 | 中位数 |\n|---|---:|---:|---:|']
 for b,s in result['by_branch'].items():lines.append(f"| {b} | {s['n']} | {s['mean']:.4f} | {s['median']:.4f} |")
 lines += [f"\n完整对话案宏平均：{statistics.mean(complete):.4f}（{len(complete)}/32案）。与89轮的均值分母不同，不能混用。\n",'## 计算与配置\n','每轮由KaroAPI gpt-5.6-sol（medium）仅根据回答生成3个问题；不向生成器发送原问题、历史、oracle或capsule。原问题和3个问题均由Google官方gemini-embedding-001编码，SEMANTIC_SIMILARITY、3072维，取3个原始余弦的平均。未做裁剪至[0,1]、拒答惩罚或选择最好一次。服务端模型版本未能独立固定。\n','## 分数最低的五轮：核查入口，不是失败标签\n']
 for r in sorted(valid,key=lambda r:r['score'])[:5]:
  lines += [f"### {r['case_id']}/T{r['turn']} · {r['score']:.4f}\n",f"原问题：{r['user']}\n",f"原回答：{r['answer']}\n",'反向问题：\n']
  for q,v in zip(r['reverse_questions'],r['similarities']):lines.append(f'- {q}（{v:.4f}）')
 lines += ['\n## 使用边界\n','这批只有Luna回答，不能用来比较其他subject模型。原始短句和指代句未改写，多轮语境可能降低表面相似度；高分也不能证明回答覆盖所有需求或没有冗余。需结合必要行为、忠实性和安全判定审阅，不设置未经校准的通过阈值。\n','## 运营记录\n',f"Google成功批次{result['operations']['embedding_success_batches']}，失败批次{result['operations']['embedding_failed_batches']}；状态分布{result['operations']['embedding_http_statuses']}。限流后采用25秒间隔续跑，成功向量缓存复用。生成错误保留：{dict(errors)}。用量见summary，未推算缺少账单依据的美元费用。\n",'## 证据\n','- [逐轮原问题、回答、3个生成问题及相似度](answer-relevancy-review.html)\n- [CSV](answer-relevancy-by-turn.csv)\n- [完整统计和配置](answer-relevancy-summary.json)\n- [两项指标设计](../../oracles/minimal32-remediation/ANSWER-FAITHFULNESS-RELEVANCY.zh-CN.md)\n']
 (D/'ANSWER-RELEVANCY-RESULTS.zh-CN.md').write_text('\n'.join(lines));print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
