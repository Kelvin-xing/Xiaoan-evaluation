# XiaoAn Evaluation Test Plan v3

版本：3.0-draft  
狀態：可實施增量方案

## Implementation status（2026-08-30）

目前已完成第一個 v3 vertical slice：

- strict typed response、citation、refusal 與 tool oracle；
- 串接 oracle、trace 與 judge claims 的 approved-turn observation；
- retrieval TP/FP/FN、MRR、nDCG、route/safety confusion、macro/micro F1；
- claim completeness/faithfulness、citation、abstention、tool argument、
  goal completion、step efficiency、retry/timeout/invalid-call metrics；
- deterministic bootstrap confidence interval 與 judge/human agreement；
- JSON/Markdown v3 report，以及 YAML-to-report 端到端測試。

若 production trace 尚未提供必要欄位，metric 會標記 unavailable/skip，
不會推測結果。Source authority/freshness、Wiki effective-date/contradiction、
capsule unit attribution 與 production online drift 留待後續 phase。

## 1. 目的與範圍

v3 將 XiaoAn 視為 `source → LLM Wiki → capsule → ground → response → state` 的分層 agent，而不是普通向量 RAG。每一層都要能獨立診斷、比較與調優；`ratings rule.yml` 保留為業務品質 reward 與 release gate，不取代各層原始 metrics。

## 2. 評估資料契約

每個 approved turn 應逐步補充 `source_oracle`、`wiki_oracle`、`capsule_oracle`、`ground_oracle`、`response_oracle`。oracle 必須記錄 provenance、reviewer、版本與有效日期。沒有有限候選全集時，TN 必須為 null，不得猜測。

## 3. 六層 metrics

### 3.1 Source authority

評估 source validity、authority、freshness、ACL 與衝突檢測。報 `source_precision`、`source_recall`、stale-source rate、lineage coverage。

### 3.2 Wiki interpretation

把 wiki 輸出拆成 atomic claims，評估 fact precision/recall、unsupported claim rate、contradiction rate、effective-date correctness 與 uncertainty calibration。

### 3.3 Capsule routing

評估 accepted/preferred route、multiclass confusion matrix、high-risk route recall、fallback error rate 與 route confidence calibration。

### 3.4 Ground resolution

評估 resolution success、required evidence recall、relevant evidence precision、unresolved/stale/conflicting evidence rate。對 refs 計算 TP/FP/FN、precision、recall、F1；TN 僅在 trace 提供 finite universe 時計算。

### 3.5 Response

程式化檢查 schema、PII、forbidden behaviours、citation existence 與 abstention；judge/human 評估 claim correctness、faithfulness、relevancy、completeness、citation correctness、harm avoidance。

### 3.6 Agent/state

評估 tool/argument correctness、goal completion、step efficiency、retry/timeout、memory retention、cross-turn consistency 與 state contamination。

## 4. Reward 與 release gates

`ratings rule.yml` 的加權分數作為 optimization reward。PII、unsafe response、未知 route、ground resolution error 等 hard gates 先行；任何 hard-gate failure 都不得由平均 reward 抵銷。報告同時保留 component scores、TP/FP/FN counts 與 macro/micro aggregates。

## 5. Judge 可信度方案

Judge 必須固定 model、prompt hash、rubric、temperature、schema 與版本；輸入包含 user、oracle、resolved evidence、response。每個 claim 要返回 evidence refs、理由與 uncertainty。

固定 calibration set 做 3–5 次重跑，報告 score variance、pass/fail flip rate、human agreement、Cohen's kappa/ICC、confidence calibration、false-pass/false-fail。比較 variant 時盲化名稱並隨機化 A/B 順序。deterministic checks 優先於 judge；高風險 disagreement 必須進人工 review。

## 6. 調優實驗

固定 golden queries，涵蓋 answerable/unanswerable、多跳、過時 source、source conflict、中英混合與危機情境。每次只改一個主要變因，記錄 source recall、wiki claim recall、capsule accuracy、ground F1、faithfulness、answer correctness、safety recall、p95 latency 與 cost/query。以 paired bootstrap/randomization test 判定回歸，並以 quality-cost-latency Pareto 選擇候選。

## 7. 實施階段

1. 完成分層 trace 與 oracle schema。
2. 將 TP/FP/FN/F1、MRR、nDCG、route confusion matrix 接入 reports。
3. 接入 claim-level response 與 agent trajectory metrics。
4. 建立 judge calibration/regression suite。
5. 加入 variant sweep、online sampling、drift 與成本監控。

## 8. v3 驗收條件

- 每個 metric 可標示 `pass/fail/error/skip`，不可用 telemetry 不得被當成零分。
- retrieval 結果輸出可審計的 TP/FP/FN；TN 缺少 universe 時為 null。
- release report 不以單一 composite score 掩蓋 source、capsule、ground 或 safety 回歸。
- judge 變更必須通過 calibration set，且保留人工 disagreement queue。
