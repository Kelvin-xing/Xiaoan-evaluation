# 評測 legacy surface 盤點（2026-09-23）

## 目的

本盤點區分「已成為目前 contract 的程式」、「仍被活躍入口引用的相容層」和「可安全移除的未引用程式」。本輪只移除新 unified/staged 流程的 legacy 預設 exporter，避免把仍被 `run`、matrix 或 Report Agent 使用的模組誤判為 dead code。

## 目前 contract

| Surface | 現行用途 | 狀態 |
|---|---|---|
| `evaluation/xiaoan_eval_core/runtime.py` | Chatflow answer、claim extraction、faithfulness barrier | current |
| `evaluation/xiaoan_eval_core/rubric.py` | ratings rule judge stage | current |
| `evaluation/xiaoan_eval_core/relevancy.py` | reverse question、embedding Answer Relevancy | current |
| `evaluation/xiaoan_eval_core/results.py` | 五張 canonical tables：Overview、Answers、Scores、Claims、Rating_Details | current |
| `evaluation/xiaoan_eval_core/orchestration.py` | rubric、faithfulness、relevancy 三條 stage pipeline | current |
| `results.json` / `results.md` / `results.xlsx` | unified/staged 的預設交付物 | current |

## 仍在活躍引用，不能直接刪除

| Surface | 活躍引用或責任 | 處理 |
|---|---|---|
| `xiaoan_eval/workbook.py` | baseline、deliverables、review workbook、CLI、舊測試 | 保留為相容層 |
| `xiaoan_eval/report_model.py` | legacy `run`／Report Agent 的 report model | 保留，待 report agent 完成 canonical-only migration |
| `xiaoan_eval/scenario_analysis.py` | CLI 與 matrix 的離線 scenario/claim diagnostics | 保留為 optional diagnostic |
| `xiaoan_eval/v3_metrics.py` | report model 與既有指標摘要仍會呼叫 | 保留其他非 claim 摘要；claim 評分已改讀 shared semantic contract |
| `xiaoan_eval/methodology_runtime.py` | multimodel matrix attribution 與 summaries | 保留，屬 active matrix compatibility |
| `xiaoan_eval/deliverables.py`、`multimodel.py` | 舊 `run`／matrix 入口和 review/export 流程 | 保留，另行遷移 |

## Optional diagnostics

`measurement.py`、`comparative.py`、`calibration.py`、`memory_metrics.py`、`parameter_diagnosis.py`、knowledge diagnostics 和 capsule ablation 仍由明確 CLI 或測試使用。它們不是 unified/staged 主流程指標；未來應在 CLI help 與文件中標示 optional/diagnostic，而不是混入 canonical score。

## 本輪已移除的 legacy default

`measure unified` 和 `measure staged` 不再預設寫入 `measurement.json`、`measurement.md` 或 legacy `measurement.xlsx`。兩者現在只寫 canonical `results.*` 三件套。需要重跑舊 consumer 時，必須明確加 `--legacy-output`；這個旗標只作過渡用途，不能作為新 report 的輸入 contract。

`measure capsule-ablation`、`answer`、`retrieval` 等非 canonical measurement methods 仍輸出 `measurement.*`，因為它們是獨立 measurement/diagnostic contract，不應與 unified/staged 結果混名。

本輪另外移除兩份完全沒有引用的 `audit_dag.py` helper。它們沒有 production import、CLI 入口、Report Agent consumer 或測試覆蓋，且不參與目前的 orchestration；保留只會增加未接線 contract。

Claim 評分也已完成合併：兩套 `v3_metrics.py` 不再執行文字 `required_claims` 對 `faithfulness_claims` 的 literal matching，不再輸出 `TP/FP/FN/F1`、`legacy_literal_diagnostics` 或 `v3:claims.f1`。若 records 帶有 shared core 的 `inventory` 與 semantic `assessment`，只使用 `claim_metrics()` 的 verdict、coverage 和 contradiction 指標；舊 records 沒有這些欄位時標記 `UNAVAILABLE`。

## 移除判準

只有同時滿足以下條件才可刪除 legacy module：

1. `rg` 顯示沒有 production CLI、Report Agent、matrix 或 test import；
2. canonical `results.*` 已涵蓋其必要資料；
3. 舊檔案 consumer 已遷移或明確退役；
4. single evaluator、multimodel evaluator、Report Agent focused/full tests 均通過。

除上述 `audit_dag.py` 和已移除的 literal claim scoring 外，目前盤點沒有符合全部條件的 legacy module，因此其他 legacy metrics/module 採用「先撤掉預設路徑，再逐模組遷移」策略。
