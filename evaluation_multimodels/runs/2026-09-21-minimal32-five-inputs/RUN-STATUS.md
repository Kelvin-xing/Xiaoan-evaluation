# 五案多模型試跑結果

狀態：COMPLETED_WITH_UNAVAILABLE。85/85 則模型回答成功；425 個預定評分單元中 258 個有效，167 個 UNAVAILABLE。PASS 在此表示執行成功，不代表回答品質合格。

案例：TC-01、TC-05、TC-17、TC-29、TC-62，來自既有 Minimal32，共 17 輪 × 5 個作答模型。自評已納入，未排除同模型評分。

## 執行覆盖

| Judge | 有效評分 / 85 | UNAVAILABLE |
|---|---:|---:|
| claude | 85 | 0 |
| gpt | 84 | 1 |
| gemini | 85 | 0 |
| qwen | 4 | 81 |
| kimi | 0 | 85 |

Qwen Judge 出現重複串流未完整結束，Kimi Judge 出現帳戶限流及重試後逾時。保留已成功評分，對剩餘單元開啟本次試跑專用 circuit breaker；其 `TRIAL_CIRCUIT_OPEN_NOT_ATTEMPTED` 表示該次恢復未呼叫，不表示先前完全未嘗試。失敗／未執行不算品質零。早期本機 debug 403 已修復並重新生成全部回答。

## 如何閱讀

- `report.md`：case-macro 加權整體分數（0–3）、評估契約與分析。
- `results.xlsx`：85 則完整回答、425 個評分單元、各維度評分及 Judge 原文／扣分證據、情境分析、Judge 一致性。
- `pairs/`：25 個 subject–Judge 組合工作簿；部分組合無完整案例，不能當成完整比較。
- `answers.md`：五案逐輪問題及五個模型的完整回答，供人工質性閱讀。
- 跨模型比較優先使用完成全部五案的共同 Judge；Qwen 部分評分不應與完整面板直接混合排序。

## 尚未量測的項目

本次未啟用獨立 attribution／知識缺口人工 review，不能宣稱得到經驗證的膠囊支持率或完整必要內容遺漏與知識缺口分析。主報表中的 NOT_RUN／UNAVAILABLE 為實際測量邊界。

Subject trace 未提供 token usage。Judge 的已記錄 tokens 不涵蓋所有中斷、重試或帳單計費，且未載入已核實的中轉站價格版本，總費用及成本—品質比為 UNAVAILABLE，並非免費或零成本。

## 發布範圍

依使用者授權，發布這五案的 YAML、模型設定、預檢、完整問題／回答、必要評估結果及報表。排除 `.env`、API keys、私人 checkpoint、完整 debug traces、快取和無關工作目錄變更。`summarize_run.py` 為內部 checkpoint 彙整工具；公開包不含該 checkpoint，因此它不是獨立可重跑的資料來源。模型設定保留供重跑，需另行配置端點及憑證。

補充：GPT Judge 對 Gemini 作答的 TC-05 第 4 輪重試後仍 TIMEOUT，該配對的 case-macro 分數排除不完整 TC-05。發布報表將含 TRIAL_CIRCUIT_OPEN_NOT_ATTEMPTED 的本地跳過紀錄 error_type 由通用分類器誤判的 TIMEOUT 改為 NOT_ATTEMPTED；原始錯誤文字及私人 checkpoint 保留。Claude 回報 input tokens 合計僅 170，數值也應視為供應商原始回報而非可靠帳單依據。
