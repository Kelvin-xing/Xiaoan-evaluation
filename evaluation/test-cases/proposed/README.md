# 待審閱案例：2026-09-13 measurement audit

這九份案例是 **PROVISIONAL_DESCRIPTIVE** 草案，沒有人工批准；預設 `test-cases/*.yaml` 不會載入此子目錄。不要把原有74案的 reviewed 狀態套到這些新增oracle。

- TC-17 / TC-52：沿用原案例，提出 response_oracle 必要／禁止行為；必須由領域審閱者決定粒度、可接受替代及證據，再合併回正式案。
- TC-75–81：remember、retrieve、not_use、update、isolation、stale、unsafe 的合成候選。既有正式案例仍涵蓋 use。
- memory fact ID 是待對接的 telemetry 契約示例；缺遙測只能 SKIP/UNAVAILABLE。多session isolation 必須由能建立隔離session並注入合成標記的harness驗證，本目錄單輪文字本身不能證明隔離。
- 草案可以用 `load_cases("test-cases/proposed", rule)` 作本地schema/coverage檢查。不得將未reviewed的內容納入正式route/safety/response/memory gate。

審核時逐案記錄：哪些oracle適用、正反例、fact ID與trace欄位如何對應、資料來源／日期、審閱者；完成後才設定reviewed，再另行決定是否APPROVED_AGGREGATE。沒有設定goal/tool的產品情境仍維持未覆蓋，不以無內容的oracle冒充完成。
