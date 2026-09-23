# 32 案裸模型 5×3 基準：完整執行紀錄

矩陣包含對角線自評；分數為 0–3。每格先計完整案例分數，再對案例取平均。
紅線觸發的完整案例為 0；缺輪／呼叫失敗排除分母，不補零。

回答：480/480；評分格：1440/1440。
回答狀態：{'PASS': 387, 'UNAVAILABLE': 93}。
評分狀態：{'PASS': 1127, 'UNAVAILABLE': 313}。

## Subject × Judge

| 回答模型 / Judge | claude | gpt | gemini |
| --- | ---: | ---: | ---: |
| claude | 1.7070 | 0.9358 | 1.7709 |
| gpt | 2.6061 | 2.1899 | 2.9012 |
| gemini | 1.5756 | 0.6940 | 2.4075 |
| qwen | 2.4582 | 1.4845 | 2.7099 |
| kimi | 2.2550 | UNAVAILABLE | 2.5472 |

## 每格有效案例數（滿額 32）

| Subject | claude | gpt | gemini |
| --- | ---: | ---: | ---: |
| claude | 32 | 32 | 32 |
| gpt | 32 | 32 | 32 |
| gemini | 32 | 32 | 32 |
| qwen | 31 | 14 | 31 |
| kimi | 1 | 0 | 1 |

## 其他指標與閱讀位置

- `results.xlsx`：七維度、Judge 一致性、紅線一致性、分數分布、原始回答及評分。
- `semantic_oracle.csv`：逐條 required/forbidden claim 的滿足、違反、不確定判定及答案證據。
- `semantic_oracle_summary.json`：各 Subject × Judge 的要求滿足率、禁止內容違反率及缺失數。
- `pair_coverage.csv`：每格有效案例及輪次、紅線輪次數。
- `usage_summary.csv`：目前保留呼叫的 token 及耗時；未回傳用量或被替代重試的消耗不包含，不能當完整帳單。

## 解讀限制

無 system prompt、capsule、wiki、檢索或工具。僅同案 user/assistant 多輪歷史。
未計算 Faithfulness、Answer Relevancy；沒有獨立查證法律/資源時效。
自評已納入矩陣；一致性統計仍依原框架使用 non-self 觀察。
模型、端點、推理強度、token 預算見 manifest.json 及 run-settings.json；這是這組設定下的描述性基準，不代表一般能力排名。
