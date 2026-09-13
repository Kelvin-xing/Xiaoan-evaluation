# 評估方法 v3 驗收紀錄（2026-09-13）

本輪完成九類方法的軟體入口、資料契約、主要報表接線和合成回歸；未執行 live API、真實人工校準、正式檢索 gold 評測或線上實驗。

## 驗證

- standalone evaluation：274 passed。
- standalone evaluation_multimodels：318 passed。
- 兩套各九種 measure CLI 示例：18/18 成功輸出 JSON/Markdown。
- git diff --check：通過。
- 測試環境：Python，PYTEST_DISABLE_PLUGIN_AUTOLOAD=1；全為離線／mock，不是模型案例通過率。

## Standards review

審查發現並修復：null 擾動 facts 假 PASS、工具預期呼叫缺失、插件原始例外可能帶入憑證。新增缺失／型別／安全錯誤碼回歸。

## Spec review

審查發現並修復：probe/arm/session 綁定、literal 指標被誤讀為語意正確性、matrix 未批准 oracle 進摘要、calibration 缺失 matching 未計分母。複核後，在上述範圍沒有剩餘阻擋問題。

## 尚待真實研究資料

人工 qrels、獨立 factual gold、雙人盲審與仲裁 benchmark、實際 SUT observer/harness 和線上事件仍需提供及驗證。此次保留既有案例核准狀態，不增加 APPROVED_AGGREGATE，不把 synthetic harness 的 PASS 當作真實工具／memory 能力證明。
