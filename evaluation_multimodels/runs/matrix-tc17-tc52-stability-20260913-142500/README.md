# TC-17／TC-52：2026-09-13 5×5 評估與穩定度比較

- [最終分析報告](comparison/findings.zh-HK.md)
- [正式 run Excel](fresh/results.xlsx)／[正式 run 報告](fresh/report.md)
- [固定答案重評 Excel](frozen-repeat/results.xlsx)／[固定答案重評報告](frozen-repeat/report.md)
- [逐項穩定度比較 Excel](comparison/stability-comparison.xlsx)
- [矩陣圖](comparison/matrix.png)

正式 run 重試後為 99/150 有效逐輪評分；固定答案首次重評為 82/99，失敗補試後為 93/99。UNAVAILABLE 保留缺失，不計零分。正式 run 與重評交付採首次有效品質結果，不挑最高分。主要穩定度統計採首次重評，補試統計另列。自評格保留，另提供排除自評統計。

公開交付包含兩案測試回答、Judge 評分及歷史回答比較；不包含原始 checkpoint、完整 trace、執行日誌、憑證與輸入內容快照。來源 hash 與評分選用紀錄供追溯，不能單靠此交付完整重播模型 API。發布副本僅移除本機工作目錄前綴並調整連結，分數與回答不變。

來源與驗證：[provenance](provenance.json)、[完整性](snapshot-integrity.json)、[選用規則](finalization.json)、[原始交付驗證](verification.json)。verification.json 的 108 檔掃描指本機原始交付；本次公開檔案清單及雜湊另見 [publication-manifest](publication-manifest.json)。
