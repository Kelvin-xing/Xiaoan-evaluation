# 最小32案的用戶前綴情境標註

`turn-annotations.json` 是 `scenario-annotations/v1` 獨立sidecar，96條，覆蓋89輪已回答及7輪未回答。標籤只使用該案截至本輪的用戶輸入，不使用subject回答、route、scanner、case設計者知道但未說出的前提。狀態一律 `PROVISIONAL`，方法 `CODEX_USER_PREFIX_REVIEW`；尚未經獨立人工審核，不是評分gold。

每行使用 `case_id` + `turn` 定位。`user_history_sha256` = SHA-256(JSON([{"turn":n,"user":text}, ...]))，JSON `ensure_ascii=False, sort_keys=True, separators=(',',':')`，UTF-8；包含本輪前所有用戶輸入。不同模型可共享同一情境標籤，前綴文字變更必須重新核對，不能沿用舊標籤。

|欄位|含义|
|---|---|
|task|本輪詳細需求，允許多值；本批由Codex逐輪審閱用戶前綴並選一個主要需求|
|task_family|optional，六類粗分，便於分組；由task明確映射，非新增Judge判斷|
|topic|截至本輪已可見的情境主題；可多值|
|constraints|明示用戶限制／角色；字詞證據在constraint_evidence中，跨輪保留；不從妻子推定性別，不從失業推定完全無資產|
|dialogue|首輪/多輪後續/有此前用戶上下文/本輪任務變化/表達修正/省略式追問；「有此前上下文」不等於回答必須依賴歷史|
|risk|用戶文字支持的風險標籤；未確立急性危險不代表已安全，亦不直接決定route gold|
|need_summary|本輪需求的可審核中文描述|
|user_evidence|逐輪完整用戶前綴，與hash相綁定；不含assistant內容|
|constraint_evidence|限制標籤對應的明示用戶原文|

`taxonomy_version=minimal32-scenario/v1`。task_family為：傾訴支持與澄清、即時安全與風險澄清、知識與邊界解釋、程序與救濟查詢、簡化重述、行動與安全規劃。完整細標籤可直接由annotations列舉；未標示限制是空陣列，不等於沒有任何限制。

重建：在repo根目錄執行 `python evaluation/examples/build_minimal32_scenario_analysis.py`。此命令只讀既有凍結run及歸因，不調用API。輸出到 `evaluation/runs/2026-09-21-minimal32-scenario-analysis/`。生成器內SPECS、CONSTRAINT_RULES、SPECIAL_RISK為標註來源，修改JSON後若重建會覆蓋，應同步修改來源並更新taxonomy版本。

分析限制：task細分有許多單案例，只能作診斷索引；多標籤的組別不能相加，多輪不能假定獨立。根因鏈中可直接觀測的是route、snapshot及凍結Judge判定，因果歸因仍需oracle複核與控制變因實驗。原獨立claim inventory不是原子聲明v2；多條PARTIAL可能需聯合證據重判。
