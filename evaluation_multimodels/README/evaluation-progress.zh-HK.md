# XiaoAn Evaluation 進度與結論邊界

更新：2026-08-30

## 目前已完成

- versioned YAML case、reviewed oracle 與 provenance gate；
- canonical `pipeline.observations`，把 expected oracle、Chatflow trace、ranked retrieval、tool calls 和 judge claims 接在同一個 turn；
- retrieval TP/FP/FN、precision/recall/F1、MRR、nDCG；
- route/safety accepted accuracy、confusion matrix、macro/micro F1；
- refusal TP/FP/FN/TN、claim completeness/faithfulness、citation metrics；
- tool precision/recall/F1、argument accuracy、sequence accuracy、goal completion、step efficiency、retry/timeout/invalid-call；
- bootstrap confidence intervals、judge disagreement、AI-human agreement、Cohen's kappa；
- 每次 run 只公開 `results.xlsx` 與 `report.md`；後者是人類決策入口，前者是完整 case/turn/metric audit 與 baseline 正式來源；
- human review、experiment 與 stability 都附加回同一 pair，不再新增公開 JSON/JSONL/Markdown。

## 可以自動下的結論

以下結論只依賴 approved oracle 與可驗證 trace，適合直接標記為 observed finding：

| 訊號 | 可下的結論 |
| --- | --- |
| safety accepted accuracy/recall 下降 | safety/risk classification stage 出現漏判或誤判 |
| route confusion 增加 | router/capsule selection stage 有 route regression |
| retrieval FN 增加、Recall@k 下降 | 必要 evidence 沒有被取回 |
| retrieval FP 增加、precision 下降 | 取回內容包含較多不相關 evidence |
| MRR/nDCG 下降 | relevant evidence 排名變差 |
| 高 retrieval recall + 低 faithfulness | generation/context assembly 需要調查 |
| citation recall 下降 | 回答沒有覆蓋必要引用 |
| refusal FN 增加 | 該拒答的情況未被攔截 |
| refusal FP 增加 | 系統過度拒答 |
| tool argument accuracy 下降 | 工具參數生成或 schema 對齊有問題 |
| goal completion 下降 | agent workflow 未完成任務，即使個別 tool call 正確 |
| p95/timeout/retry 上升 | latency、context size、模型或 orchestration 可能退化 |

這些是「哪一層的可觀測結果變差」，不是對唯一 root cause 的證明。

## 不能直接自動證明的結論

單次 run 不能直接證明：

- 應把 `top_k` 改成某個特定值；
- 應更換 embedding model、reranker 或 chunk size；
- 應修改某一段 prompt；
- 某一個 trace failure 一定由某個參數造成；
- judge 的語義分數一定等同於真實使用者滿意度；
- 未提供 finite candidate universe 時的 TN；
- 缺少 production trace 時的 source authority、freshness、Wiki contradiction 或 capsule unit attribution。

這些只能先寫成 `hypothesis`，再透過 controlled repeated experiment 驗證。

## 從 finding 到改動的必要條件

1. 固定 golden queries、oracle、model/prompt version 和 runtime controls。
2. 每次只改一個主要變因。
3. 重跑至少 3 次；高風險變更增加人工抽查。
4. 比較 target metric、overall quality、hard gates、p95 latency 和 cost/query。
5. 使用 paired bootstrap/randomization 檢查改善是否穩定。
6. 只有在 target 改善、critical hard-gate regressions 為 0 且副作用可接受時，才把 recommendation 從 `hypothesis` 改為 `validated`。

## 人類閱讀入口

只需先看：

```text
report.md
```

需要追查時再按以下順序打開：

```text
results.xlsx / 00_Overview   # 整體結論、分項、速度、coverage
results.xlsx / 01_Cases      # case facts
results.xlsx / 02_Turns      # turn facts 與對話 linkage
results.xlsx / 03_Metrics    # deterministic、judge、RAG、V3 metrics
results.xlsx / 05_Experiments # controlled experiment results
```
