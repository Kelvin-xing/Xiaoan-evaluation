# 報告標籤補齊包（2026-09-22）

範圍：已檢查的 Minimal32 單模型 32 案／96 輪，以及其中五案多模型 17 輪。

- `turn-annotations.json`：96 輪完整情境標籤，沿用既有逐輪草案；與當前兩套 YAML 的用戶前綴完全匹配，可用 `--scenario-annotations` 載入。
- `router-oracles.json`：96 輪可接受路由、首選路由、安全標籤、依據與爭議。為審核包，不是 evaluator 的新輸入格式。
- `router-review.csv`：逐輪人工校對入口；reviewed_by／reviewed_at 留空，未冒用既有 reviewer。
- `validation.json`：來源 hash、資料覆蓋、原始分數及回答不變的驗證結果。
- `../../runs/report-labels-2026-09-22/results.xlsx`：補齊後副本。新增 Scenario_Annotations、Router_Oracle_Drafts、Label_Completeness。多模型 Scenario_turns 及兩張分組表已重建，425 筆 Judge 記錄均有情境標籤；同一回答按 85 份去重聚合。

## 狀態與使用限制

資料完整性核對不等於 domain review。既有情境標籤及 Router oracle 全部保留 PROVISIONAL／provisional；正式 Router 準確率仍為 UNAVAILABLE。這次沒有重新裁定法律、醫療或來源正確性，也沒有重新呼叫 Subject／Judge。空 constraints 表示未標註到明示限制，並非缺失輪次。

單模型 96 輪原本已有標籤；本次把 oracle 草案與其一起帶入工作簿。多模型缺少的是標籤接入，沒有從 Subject 回答或實際路由反推期望。用戶前綴另外與該 run 保存的 answers.md 17 輪問題核對。

Router 草案為事後分析附件，不覆寫歷史 run 的 oracle 或評分；引用的原始 snapshot_id 保留，沒有冒稱是重新審核的當前內容快照。未补齐全部 74 案及歷史所有 runs，也未重建 25 份 pair 工作簿。

人工審核後須明確記錄核准欄位範圍，再更新 source oracle 並離線重新計算適用指標。現有 reference_oracle.status 涵蓋 route、安全與 source 等多欄位，不可只審過 route 就把整個 reference_oracle 一律 approved。

## 重建

在 repo 根目錄執行 `python evaluation/examples/complete_report_labels.py`（需要 PyYAML、openpyxl）。讀入原工作簿，輸出到獨立目录；請勿把私人 runs 或用戶對話直接發布。
