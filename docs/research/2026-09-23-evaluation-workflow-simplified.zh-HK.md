# Evaluation 工作流架構精簡稿

本文記錄逐項確認的目標架構；程式遷移尚未完成。本次不需要歷史資料匯入、舊格式相容層或過渡 alias；新入口、producer 和 consumer 一次切換至新契約。現況依據見 [工作流交接盤點](2026-09-23-evaluation-workflow-handoff-inventory.zh-HK.md)。

評測架構分成五個生命週期階段：案例與版本、答案生成與凍結、評估執行、結果投影、人工審查。每個階段只保留一個責任；不同 CLI 可以共用同一階段，也可以在某個階段停止，不再被描述成互相競爭的完整 pipeline。

## 1. 案例與版本

這個階段負責載入並預檢案例，確認案例 ID、輪次、oracle、評分規則和審批狀態；同時建立不可變的 suite manifest，記錄本次評測使用的案例摘要、模型、提示、知識、評分和重試版本。它只產生「可執行的評測計劃」或「帶原因的不可執行結果」，不產生答案，也不執行 Judge。

`needs_remediation` 表示案例仍可被讀取，但資料或審批狀態需要修正；`invalid` 表示案例無法可靠解析或不符合基本 schema。這兩種狀態都必須保留原因，不能在下游被靜默丟棄。對 `needs_remediation` 案例應否阻止整批、保留為 unavailable，或只排除正式聚合，屬於執行政策，另行決定。

完整的 manifest 和 preflight 結果是評測的追溯來源。`results.xlsx` 應保留 manifest ID 或 digest、案例狀態與原因、模型身分、評分與 evaluator 版本，以及納入、排除或 unavailable 的範圍；`report.md` 只呈現會影響結果解讀的摘要，不需要暴露程式類別名稱。

## 2. 答案生成與凍結

這個階段負責按照案例計劃產生回答，保存每輪的問題、回答、對話歷史、subject 身分、回答狀態、執行遙測和有效 context snapshot，並以 `answer_id`、內容 hash 和執行 manifest 將它們凍結。它不執行語義 Judge，也不產生最終品質結論。`run` 和 `matrix` 是這一階段的兩種生成模式：前者面向部署回歸和 Chatflow trace，後者面向多 subject 的答案生成；Judge 配對在評估階段展開；兩者都必須交付同一種可追溯的 frozen answer record。

答案凍結時保留完整原始 trace、provider event 和中間資料，作為日後重建與重新解析的 provenance source；同時產生一份 canonical frozen record，作為後續評估的唯一接入口。下游不應各自重新解讀 raw event。raw event、canonical record、answer hash 和 manifest identity 必須互相綁定；遙測缺失時保留缺失狀態，不能補造數值。

## 3. 評估執行

這個階段接收 canonical frozen answer record 和具版本的評估計劃，由同一個評估引擎執行計劃指定的 evaluator。案例清單決定測試哪些對話；評估計劃決定評估項目、評委及使用的規則版本。每個結果都綁定原始答案、evaluator 身分、相關規則與提示版本、證據和執行狀態，形成完整 evaluation envelope，交給下一階段產生 workbook 和報告。

日常 Minimal33 評測使用一份固定的預設評估計劃，避免每次逐項配置；需要補評或調整方法時，可另建計劃版本，重用同一批凍結答案。引擎負責各項依賴，例如 claim assessment 必須使用已完成的 claim inventory。結果分開記錄未計劃、已計劃但未執行、執行後不可用和成功，不將缺失判定記為零分。

預設計劃已確認啟用 rubric、claims／requirements、relevancy，以及按適用條件執行的確定性檢查；既有 `unified`／`staged` CLI 直接退役，不保留過渡 alias；所有呼叫端改用 `frozen-answer-evaluation`。

### 3.1 品質評分（rubric）：預設啟用

品質評分根據問題、回答、對話歷史、案例指定的評分維度和評分規則，評估回答品質。結果保留各維度分數、判定理由、支持與扣分證據，以及紅線判定，讓每項評分都可以回到回答原文核對。

每個 Judge 的每個維度分數及每項紅線判定均須附非空判定理由，說明如何對應評分準則與可取得的證據。完整理由保存於 JSON，並在 Excel 的 Rating Details 逐項展示；Scores 可連至相應明細。滿分、未觸發紅線也需理由；缺失行為可用明確遺漏說明，不補造引文。呼叫失敗時保存失敗原因，不生成虛構的評分理由。Validator 檢查必需理由欄位，Report Agent 可引用原判定而不代替 Judge 補寫。

`run` 和 `matrix` 共用一套 rubric evaluator；單評委或多評委由評估計劃指定，各評委結果分別保存。此項目列入 Minimal33 的固定預設評估計劃。

紅線觸發後仍完成各維度評分，按既定權重保存 rubric 總分，不因紅線將維度或總分全部歸零。紅線另存判定、理由及證據，令對應 gate 不通過；Excel 和報告並列呈現品質分數與紅線／gate。高分不抵銷 gate 失敗，維度分數仍按自身評分準則判定。實作時同步更新 rating rule、Judge 指令、scoring、輸出及測試，使用新評分契約版本。

### 3.2 Claim／evidence 評估：預設啟用

每份答案抽取一次主張清單，多個 Judge 共用同一份清單並分別判定。Faithfulness 評估主張是否獲當時提供給模型的 context 支持；correctness 評估主張是否符合獨立核准的 reference facts。兩者分開呈現，不合成一個分數。

結果保留主張原文與位置、證據引文與來源、判定和理由。缺少所需證據時保留 UNKNOWN 或不可評原因，不補造事實或分數。此項目列入 Minimal33 的固定預設評估計劃。

Case YAML 的 expected／response oracle 是評估資料的編寫與接入入口，由共用 adapter 轉成 frozen-row spec。必要／禁止回答內容轉成 requirements；事實性參考內容及其來源轉成 reference_facts，並保留核准範圍、來源與版本。只有具備獨立事實依據且已核准的資料才標記 truth_status=approved；缺少依據的行為要求仍作 requirements，不因案例通過審閱而自動成為事實真值。既有欄位不足以表達來源時，在案例契約中補足，具體映射於資料流轉規則中定義。

Claim 評估統一到 shared core 的 extractor＋assessment 路徑。刪除舊主 Judge 的 faithfulness_claims 分支及獨立 attribution Judge 執行路徑；rubric 品質評分保留。舊 attribution 的語義判定由 claim assessment Judge 承接，使用共用 inventory，不再另行抽取或呼叫 attribution 模型。來源對照與統計由程式從其驗證結果派生，具體映射見第 18 節。

效能設計採用受限 async 並行：不同答案的 extraction 可並行，完成全批 extraction 終態後，不同 answer × Judge assessment 可並行；同一答案的所有 claims 仍在一次 assessment 內處理。按 provider 設定並行與速率限制，結果依穩定主鍵保存。Provider prompt caching 與本地結果重用分開處理：前者將穩定指令／schema 放在共用前綴、動態答案與證據放在後段，實際接入依 provider 能力驗證；後者按完整請求與 evaluator 配置綁定成功且驗證通過的結果，重跑只補缺失或失敗項。新增 async 時須處理相同請求去重與 checkpoint 並行寫入。

### 3.3 Requirements 評估：預設啟用

Requirements 評估檢查必要內容、禁止行為及跨輪限制是否滿足，列入 Minimal33 的固定預設評估計劃。要求由 Case YAML 轉入，保留要求 ID、種類、關鍵性、適用輪次及核准狀態。每項結果保存判定、理由與證據；遺漏判定可沒有回答引文，缺少必要歷史或執行觀察時保留不確定狀態。

Claims 與 requirements 在邏輯及結果結構上分開，預設由同一次 assessment 呼叫完成。兩組結果各自驗證及記錄狀態；共同的請求失敗會影響兩組，局部驗證失敗依第 14.4 節保存與重試。是否拆成獨立呼叫，以同批凍結答案比較漏判、驗證失敗、人工一致性、token 和延遲後再決定。

關鍵 requirement 違反使對應 gate 不通過，不額外扣減或改寫 rubric 分數。與 rubric 紅線重疊的要求建立對應，保留兩種判定來源，避免另加一次扣分；rubric 紅線同樣只影響對應 gate，不強制將品質分數歸零。

每個 gate 在其適用範圍內按以下優先順序判定：任何適用關鍵要求明確違反或紅線明確觸發，為 FAIL；沒有明確違反但必要判定缺失或不確定，為 UNDETERMINED；所有適用必要條件均確認滿足，為 PASS；沒有適用條件，為 NOT_APPLICABLE。若適用性本身無法確定，使用 UNDETERMINED，不略過該條件。

UNDETERMINED 保留原因，不扣分、不計為通過，列為人工審查候選；其他評估與結果交付繼續。Gate 結果獨立於 execution_status、availability 及單項 requirement verdict 保存；明確違反與證據缺失並存時，gate 仍為 FAIL，缺失原因另行保留。

### 3.4 回答相關性（relevancy）：預設啟用

回答相關性列入 Minimal33 的固定預設評估計劃。沿用從答案反向生成問題，再以 embeddings 比較反向問題與原問題相似度的評估方法，每份凍結答案產生一份 relevancy 結果，不因多個 assessment Judge 而重複計算。

結果保留反向問題、各項相似度、彙總分數、生成模型與 embedding 模型版本、答案綁定及執行狀態，支援追溯與相同請求結果重用。失敗或缺失保留不可用狀態，不記為零分。Relevancy 每次按預設計劃計算並獨立展示，不加入 rubric 總分，也不直接觸發 gate；報告可引用它比較相關性及分析個案。

### 3.5 確定性檢查：按適用條件預設執行

使用程式比對實際 trace 與案例期待，檢查路由、安全分類、工具呼叫及跨輪狀態等可觀測行為，不額外呼叫 Judge。有適用要求及有效 trace 時執行；有要求但缺少必要 trace 時記為不可評並保留原因，不判為行為失敗，也不從回答文字推測執行行為。沒有適用要求的項目記為不適用，與缺少觀察分開。

每項結果保留要求 ID、實際觀察、證據來源、判定與狀態，供 requirements 評估及結果投影使用。

## 4. 結果投影

### 4.1 results.json：完整評估結果

採用一套完整、具版本的結構化結果格式，保存所有計劃評估單位，包括成功、失敗、未執行及不可評項目。單模型與多模型使用同一格式，以 subject／Judge 身分區分。JSON 是重建 Excel 和報告的依據，包含：

- Spec 與版本：案例／輪次清單、各模型角色、啟用項目、prompt／rubric／知識版本、生成參數、並行與重試配置、preflight 結果。
- 問題與答案：每輪問題、完整回答、對話歷史、case／turn／subject／answer ID、狀態及錯誤原因。
- 生成與評估依據：context snapshot、路由／工具／狀態觀察、requirements、reference facts、來源內容、適用範圍、核准資訊及版本／hash。
- 完整評估明細：rubric 維度、權重、分數與紅線；claim inventory、原文位置及逐 Judge 的 faithfulness／correctness；requirements 判定及 gates；relevancy 反向問題、相似度及模型版本；確定性檢查的預期值、觀察與結果。每項保存理由、證據及狀態。
- 時間與用量：答案生成、各評估呼叫和重試的時間、延遲、token、可取得的 cache usage，以及缺失原因。
- 執行與恢復：階段狀態、請求身分、嘗試紀錄、錯誤、checkpoint 重用與抽取審核結果。
- 聚合結果：數值、公式版本、分子／分母、納入／排除範圍、Judge 納入政策及缺失覆蓋。
- 來源索引：原始事件、完整請求／回應和附件的相對路徑、hash 及關聯主鍵。

評分、判定、理由、證據引文和 snapshot 等完整評估內容直接保存在 JSON。原始 provider events、串流碎片和 raw trace 可另存附件，由 JSON 索引綁定；JSON 與附件共同構成完整交付包。API key 等憑證不進入產物。

### 4.2 results.xlsx：人類閱讀的核心資料

Excel 由共用 exporter 從完整結果產生，固定八張核心表：

| 工作表 | 每列粒度 | 核心內容 |
| --- | --- | --- |
| Overview | 摘要指標或模型比較項 | 範圍、答案／Judge 可用率、完成案例數、主要評分、紅線、耗時與 token 摘要 |
| Spec | 配置項或案例狀態 | 案例清單、模型角色、啟用項目、規則版本、生成參數、preflight、排除原因 |
| Answers | subject × case × turn 的答案 | 問題、完整回答、狀態、路由、時間、生成 token、relevancy |
| Scores | answer × evaluator role × Judge | 各 rubric 維度、總分、紅線、faithfulness／correctness 摘要、requirements 摘要、評判耗時與 token |
| Claims | answer × claim × Judge | 主張、種類、回答引文、兩種判定、證據來源與引文、理由 |
| Requirements | answer × requirement × 判定者 | 要求、關鍵性、判定、回答引文、理由；程式檢查標明判定來源 |
| Rating Details | answer × Judge × 維度或紅線 | 分數／紅線判定、支持與扣分證據、理由 |
| Human Review | answer × Judge | 問題、回答、評估摘要與連結、優先標記、decision、notes、reviewer、reviewed_at |

Spec 顯示有效配置摘要及必要追溯 ID，完整 prompt、schema 和 hash 清單留在 JSON。時間區分日期、生成耗時、評判耗時和整批實際耗時，不把並行呼叫耗時之和當作整批等待時間。Token 按 subject、extractor、assessment、rubric、relevancy 分開核算；共用答案、claim inventory 及 assessment 呼叫不因多表或多 Judge 展示而重複計數。

未知、未執行和失敗保留文字狀態，缺失數值不填零。超出 Excel 儲存限制的長內容顯示明確提示和 JSON 定位，完整原文保留在 JSON。Excel 不搬入 raw events、完整請求、重試日誌或大段 context。

### 4.3 report.md：統一 Report Agent

合併 package 內建 Report Agent 與 root evaluation_report_agent，保留一套共用報告引擎。新流程讀取完整 results.json 及其綁定證據；直接移除舊 workbook／snapshot 報告入口，不設相容 adapter。

報告聚焦主要結果、具體失敗模式、Judge 分歧及改善建議，引用案例／輪次和具體證據。數字由程式計算，Agent 負責解釋，區分觀察結果、Judge 判定、根因假設及改進提案。保留來源綁定、引用與引文驗證、查詢稽核及成功請求重用能力；缺少歷史證據時明確記錄，不用目前檔案補造歷史內容。

JSON 驗證完成即保存；Excel 與報告可各自生成，成功產物先交付。報告獨立生成、獨立記錄狀態及重試。報告失敗不阻擋評估結果交付，也不重跑答案生成或評分。在同一重構中完成 consumer 接線並移除舊報告引擎及重複實作，以新契約驗證。

## 5. 人工審查

每次評測完成後都安排全量人工審閱，先交付自動結果，再由人工讀取所有回答及各 Judge 的評分、理由與證據。Human Review 每列對應一份回答 × 一個 Judge，列出該 Judge 所有已執行 evaluator 的評估及明細連結；不同 Judge 分別批准，不合併為一次批准。

APPROVE 表示認可該 Judge 的評估判定，不表示回答品質良好，也不將 FAIL gate 改為 PASS。人工填寫 decision（APPROVE／REJECT／NEEDS_INFO；空白表示待審）、notes、reviewer 和 reviewed_at。REJECT／NEEDS_INFO 須說明原因及涉及的維度／claim／requirement。原始分數、答案、理由及證據欄位不可直接改寫；評估修正與重新審閱另留版本及 provenance。

每列以 review_id、generation、answer_id、judge_id、回答 hash 和評估 digest 綁定；import 驗證身分、內容未遭修改及來源版本。缺失評估明示原因，不以空白冒充已評；NEEDS_INFO 保持待處理。所有列完成閱讀與填寫的覆蓋，與全部獲 APPROVE 的批准覆蓋分開統計。

第 16.6–16.9 節的紅線、分歧及不確定規則只建立優先閱讀標記與原因；沒有標記的回答與評分仍須審閱。資料缺失先按恢復規則處理，自動結果交付不等待人工完成。

人工審查產生新的 result generation，保存完整 `results.json` 並記錄 parent generation；原始自動結果與人工提交保持不可變。Excel 只投影狀態、結論、分歧與引用；`report.md` 說明人工覆蓋範圍及仍未審查的部分。自動完成、報告完成、人工完成和正式 aggregate eligibility 分開表示。

## 6. 資料流轉規則

人工 REJECT 後先記錄理由與涉及的評估項目，不自動重跑或覆寫 Judge 分數。需要修正時，由人工明確提交修訂判定，保存原判定、修訂值、理由、證據及 reviewer，經驗證後產生新 result generation。REJECT 本身不等於已取得正確替代標籤；Judge 校準流程另行確認。

已確認：REJECT 項目只有完成明確人工修訂值、理由和證據後，才可作為校準基準；缺資料或仍有爭議的項目保留待處理。只需修訂理由時，保留已認可的分數並明示修訂範圍。

五個階段共用一條不可變資料鏈：

```text
Case YAML + version config
  → evaluation plan / suite manifest
  → raw events + canonical frozen answer records
  → evaluation envelope
  → results.json
  → results.xlsx / report.md / full review packet
```

每一階段只增加資料，不修改前一階段的 frozen artifact。下游以穩定主鍵和 digest join，不依靠檔名、工作表行號或答案文字猜測關係。

### 6.1 階段輸入、輸出與 owner

| 階段 | 主要輸入 | canonical 輸出 | 欄位 owner |
| --- | --- | --- | --- |
| 案例與版本 | Case YAML、rating rule、模型／provider／prompt／knowledge 設定 | suite manifest、case preflight、evaluation plan | case loader、manifest builder |
| 答案生成與凍結 | evaluation plan、subject、transport | raw event bundle、canonical frozen answer record | subject runner、freeze adapter |
| 評估執行 | frozen answer、evaluation plan、requirements／reference facts | evaluation envelope、inventories、assessments、metrics、stage receipts | evaluator orchestrator、各 evaluator |
| 結果投影 | 完整 evaluation envelope | results.json、results.xlsx、報告輸入 manifest | canonical exporter、Report Agent |
| 人工審查 | 全量 frozen result、證據索引、優先閱讀標記 | review packet、human／adjudication／final provenance | review exporter、review importer |

### 6.2 跨階段主鍵與綁定

- `suite_id`／`manifest_digest` 綁定案例範圍、版本設定和執行計劃。
- `case_id`、`turn` 綁定案例輪次；`subject_id` 綁定被測模型或服務。
- `planned_unit_id` 識別生成計劃中的 subject × case × turn；`answer_id` 識別該單位的一次凍結生成版本。重新生成答案使用新 answer_id；只補評不改 answer_id。
- `answer_sha256` 僅計算回答原文的 UTF-8 hash；無回答時為 null。`row_digest` 另綁定問題、歷史、回答、身分、狀態及證據引用；review 的 response_sha256 與 answer_sha256 指同一內容 hash。
- `inventory_id` 綁定一份答案的 claim inventory；inventory 必須引用 `answer_id` 和 extractor identity。
- `assessment_id`／`assessment_request_id` 綁定一份 inventory × Judge × 評估設定；不可用、重試和快取都以 request digest 識別。
- `evidence_ref` 綁定 context、reference fact、trace observation 或回答 span；資料存在時須有 `context_version`／`truth_version`；資料缺失時版本為 null 並記原因。Evaluator／prompt 版本必須明確。
- `generation_id`／`core_digest` 綁定完整結果與投影；Excel、報告和 review packet 不得混用不同 generation。

### 6.3 狀態傳遞

執行狀態、資料可用性、語義判定及人工審查狀態分欄保存，具體規則見第 14 節。缺少資料不轉成零分；未計劃不等於執行失敗；成功完成評判仍可能得到 `UNKNOWN`，它不等於 `UNSUPPORTED`。計數保存於對應粒度的摘要，不要求每個原始單位攜帶聚合計數。

階段完成只表示該階段的 planned units 已有終態，不表示下游報告或人工審查完成。結果交付狀態至少分開表示 `evaluation_status`、`projection_status`、`report_status`、`human_review_status` 和 `aggregate_eligibility`。

### 6.4 恢復與重用

詳細規則以第 14 節為準。所有外部呼叫先建立 request digest，再以完整輸入、版本和綁定驗證 checkpoint。成功且通過 schema／evidence validator 的結果可重用；輸入、prompt、模型、context、truth 或契約變更時產生新 digest。重跑只補缺失或失敗的 stage，不重新生成已凍結答案，也不覆寫成功的歷史結果。並行 worker 必須使用原子 checkpoint 寫入和相同 request 去重。

### 6.5 無損投影規則

`results.json` 是唯一完整結果來源；Excel 和 Markdown 都是可重建 projection。Exporter 必須以 `answer_id` join answer、inventory、assessment、requirements、relevancy 和人工結果，再按工作表粒度展開；不得從 `cell.inventory` 等局部欄位猜測全域 inventory。每個展示 claim、requirements gate、metric 和報告引用都要能回到完整結果中的來源 ID、evidence ref 和原文 span。

Excel 只省略不適合人讀的 raw event、完整 request／response 和大段 context；省略欄位要保留 JSON 定位。完整 JSON 必須保留 correctness、requirements、gates、inventory audit、evidence、status 和分母資訊；Excel 可依八表規則選取摘要與引文，其餘保留 JSON 定位。若資料無法投影，Exporter 應報錯或標記不可用，不靜默產生部分完整的結果。

### 6.6 端到端驗證

以固定 fixture 驗證：同一 `answer_id` 能連到回答、inventory、每個 Judge assessment、rubric、requirements、relevancy、Excel 行和報告引用；每個 evidence ref 能定位到原文或 snapshot；重跑能重用成功 stage；不可用、未計劃和未知狀態在 JSON、Excel、報告中的分母一致。新流程通過這些驗證，且舊 exporter、舊 Report Agent 和重複 consumer 已移除，才算重構完成。

### 6.7 Evaluation plan／suite manifest 契約

`evaluation plan` 描述本次要執行哪些單位和 evaluator；`suite manifest` 凍結案例範圍與所有影響結果解讀的版本。兩者可以在同一份 spec envelope 中保存，但責任分開：plan 是「要做什麼」，manifest 是「用什麼條件做」。

必要欄位包括：

- `schema_version`、`suite_id`、`run_id`、`manifest_digest`、建立時間和 owner。
- 有序 `case_ids`、每案預期輪次、case source digest、preflight status、maturity、scenario／coverage／comparability metadata。
- subject、extractor、Judge、rubric、relevancy generator／embedding model 的完整 identity、provider、model、prompt／contract version；provider 未提供的 revision 保存 null，不虛構。
- 啟用的 evaluator branches、依賴關係、評估有效性與聚合資格、人工審查觸發政策和 aggregate policy。
- product／runtime／safety／output guard／knowledge／capsule／router 版本，以及生成參數、seed、retry、concurrency、rate limit 和 cache policy。
- 輸入 artifact digest、reference facts／oracle 版本、輸出目錄、checkpoint policy 和資料保留範圍。

Manifest 必須把 planned units 明確列出，包括預期但尚未取得回答的 case × turn × subject；不得只記錄成功 rows。欄位更新、案例順序、模型或 evaluator 版本改變，都產生新的 manifest digest；歷史 manifest 不原地修改。

Excel 的 `Spec` 表只顯示上述設定的可讀摘要、版本和 digest；完整 prompt、schema、case source 清單、並行設定、artifact index 和原始配置保存在 `results.json` 及其 manifest 附件。報告只引用會改變結果解讀的 scope、版本、排除和可用性摘要。

### 6.8 Canonical frozen answer record 契約

每個 planned_unit_id 預留紀錄；一次生成嘗試選定成功或失敗終態後，凍結為帶 answer_id 的 record。它是所有 evaluator、exporter、Report Agent 和人工審查共同使用的答案輸入；下游不可重新從 raw event 或目前 prompt 讀取內容替代它。

必要欄位包括（可缺失資料保留 null 與原因）：

- 身分：`planned_unit_id`、`answer_id`、`suite_id`、`manifest_digest`、`case_id`、`turn`、`subject_id`、subject provider／model／revision。
- 輸入與回答：原始 `question`、完整 canonical `history`、`answer`、`execution_status`、`availability`、`reason`、`answer_sha256`、`row_digest`。
- 執行證據：`context_capture`、`context_version`、normalized context snapshot reference、route／tool／state observations、trace／event bundle reference。
- 用量與時間：開始／完成時間、elapsed／queue／TTFT、input／output／total tokens、cache usage、attempt count 和 retry errors；缺失 telemetry 保留 null 及原因。
- 來源綁定：raw event artifact path／digest、capture adapter version、subject request hash、answer generation ID。

答案採用第 14.1 節的 execution_status 與 availability。有效回答及身分綁定通過即可為 AVAILABLE；context 與 telemetry 的可用性另外記錄，缺少它們不降低答案可用性。部分生成的回答標為 PARTIAL，預設不當成完整回答送評。未嘗試的單位沒有 attempt；實際失敗才記錄錯誤、attempt 與可重試性。

Raw event bundle 保留 provider event、串流片段和完整 trace；canonical record 只保存下游需要的 normalized 欄位及附件索引。Raw event 和 canonical record 都以 `answer_id`、內容 hash、manifest digest 綁定，任何一方變更都產生新 generation，不覆寫既有 frozen record。

### 6.9 Evaluation envelope 契約

每個 evaluation envelope 以 `answer_id` 為中心，收集同一份 frozen answer 的所有評估結果；批次、案例和 suite 摘要由這些 answer-level records 派生，不另建一份無法回溯的平行結果。Envelope 保存 evaluator identity、request digest、輸入版本、輸出、證據、狀態和時間／用量。

每個 envelope 至少包含：

- `answer_ref`：`answer_id`、case／turn／subject、answer hash、manifest／generation digest。
- `deterministic_checks`：適用要求、預期值、實際觀察、比較結果、trace evidence 和不可評原因。
- `rubric`：每個 Judge 的 dimensions、weights、scores、red lines、supporting／deduction evidence、reason 和 status。
- `inventory_id`：引用全域 inventories 中唯一保存的 claims、kind、conditions、answer spans、extractor identity 及 audit；抽取失敗時為 null 並保存失敗 receipt。
- `assessments`：每個 Judge 對每個 claim 的 faithfulness／correctness、requirements items／gates、evidence spans、reason、request digest 和 status。
- `relevancy`：反向問題、embedding identity、相似度、summary score、binding 和 status；每個 answer 一份，不按 Judge 複製。
- `human_review`：是否觸發、packet／review／adjudication refs、automatic／human／final provenance 和 status。
- `stage_receipts`：各階段 planned／started／completed 時間、attempt、token、error、checkpoint reuse 和 retryability。

Evaluator 輸出必須帶有明確 status。成功結果需通過 schema、binding 和 evidence validator；失敗保存錯誤類別和 request digest；未計劃、未執行、不可評和不適用分開表示。Envelope 不把 rubric 分數、claim metrics、requirements gates 或 relevancy score 互相覆蓋，也不把 UNKNOWN 轉為零。

批次 summary 只由 envelope 中具備明確 eligibility 和完整分母的結果計算，並同時輸出 planned、available、unknown、unavailable、excluded 計數。Excel 與 report 使用這些 summary，但保留回到 envelope 的 `answer_id`、stage ID 和 evidence refs；Consumer 只能使用共用聚合程式；額外分組須明示篩選和公式版本並保存來源 receipt（見第 13.2 節）。

## 7. 現況程式映射與第一批缺口

### 7.1 已有的可重用零件

| 目標責任 | 目前入口 | 現況判定 |
| --- | --- | --- |
| 案例與 preflight | `evaluation/xiaoan_eval/cases.py`、`manifest.py` | 有 typed case、preflight、maturity 和 manifest digest；尚未成為兩條答案入口共用的完整 plan envelope |
| 答案生成 | `runner.py`、`pipeline.py`、`multimodel.py:run_matrix` | `run`／`matrix` 各自保存 answer、trace、checkpoint 和 telemetry；canonical record 尚未統一 |
| frozen-row adapter | `unified.py:load_records/prepare` | 可把部分 case record／matrix row 轉成 frozen rows；不會由 Case YAML 自動產生完整 requirements／truth plan |
| claim extraction／assessment | `xiaoan_eval_core/runtime.py`、`contracts.py` | 已有一次抽取、多 Judge assessment、batch barrier、evidence validator 和 checkpoint |
| rubric／relevancy | `orchestration.py`、`rubric.py`、`relevancy.py` | Python orchestration 可並列執行；CLI 投影和 stage receipts 尚未完整統一 |
| 舊 deterministic／Judge | `metrics.py`、`pipeline.py`、`multimodel.py` | 功能可用但沒有全部轉入 shared envelope |
| workbook exporter | `workbook.py`、`results.py`、`multimodel.py` | 有多套 workbook schema；compact projection 仍有欄位遺失與 consumer 不相容 |
| Report Agent | package `report_agent.py`、root `evaluation_report_agent/` | 兩套入口並存；已決定以 canonical results.json + evidence bundle 歸一 |
| 人工審查 | `review_workbook.py`、`deliverables.py` | 有 export/import/adjudicate 和 trust digest；compact／matrix schema 尚未全部接通 |

### 7.2 P1 缺口

1. 建立唯一的 `evaluation plan → canonical frozen answer record` adapter，讓 `run`、`matrix` 和 Case YAML 都能產出同一份 planned rows；保留 unavailable rows 和 source digests。
2. 將 Case YAML 的 expected／response oracle 映射成 requirements、reference facts、truth／oracle status 和跨輪 constraints；映射結果在執行前凍結，不由 evaluator 臨時推斷。
3. 讓 `measure frozen-answer-evaluation` 成為唯一正式入口；移除 `measure unified`／`measure staged`，所有呼叫端使用同一 ingress、canonical record 和完整 evaluation envelope。
4. 把完整 core envelope 作為 results.json source of truth；修正 exporter 的 inventory join，保留 correctness、requirements、gates、audit、evidence、stage receipts 和分母。
5. 讓 `results.xlsx` 八張表和 frozen-answer-evaluation／matrix consumer 由同一 exporter 產生，並以 generation／digest 拒絕混代資料。
6. 移除兩套 Report Agent 的舊輸入，統一接到 canonical engine；報告不再直接依賴某一種 workbook schema。
7. 將 rubric、claims、requirements、relevancy、deterministic checks 的 status、用量、checkpoint 和錯誤統一寫入 envelope，支援受限 async、去重和重跑。

### 7.3 驗收順序

先用一個離線 Minimal33 fixture 驗證 plan、frozen rows、envelope、JSON、Excel 和 report 的 join；再接一個不含 provider 呼叫的 matrix fixture；最後才遷移 live `run`／`matrix` 和人工 review。所有步驟均須能回溯 `answer_id → evidence → projection`；不設舊 consumer 過渡期。

## 8. P1-1：Canonical ingress adapter

### 8.1 目標

建立唯一 ingress，由 Case YAML 建立 evaluation plan，讓 `run`／`matrix` producer 直接輸出 canonical frozen rows；不接收歷史 case records、matrix cells 或舊 workbook。Adapter 只負責解析、對齊、補上可由來源確定的欄位和拒絕不一致資料；不呼叫 subject、Judge 或 Report Agent。

### 8.2 輸入與標準化

1. 讀取 suite manifest 和有序 Case YAML，建立完整 `case_id × turn` 計劃，包括尚未有回答的 planned units。
2. 讀取 subject identity 和執行設定，展開 `subject × case × turn`，產生穩定 planned_unit_id；凍結時建立 answer_id，同一計劃單位重新生成時保留新版本而不覆寫。
3. 由 `run`／`matrix` producer 的共用 freeze adapter 收集 answer、history、status、trace snapshot、telemetry 和 source digest，直接產生 canonical row。
4. 驗證 question、turn、subject、answer hash 和 context snapshot 的一致性；有衝突就輸出拒絕原因，不以最新資料覆蓋舊資料。
5. 由 Case YAML adapter 寫入 requirements、reference facts、oracle／truth status、跨輪 constraints 和 quality focus；無法確定的欄位保留缺失或 provisional，不臨時推斷。
6. 產生 adapter manifest，記錄輸入 artifact hashes、來源 row／event refs、轉換版本和每個 planned unit 的 included／excluded／unavailable 原因。

### 8.3 Canonical row 最小欄位

`answer_id`、`case_id`、`turn`、`subject_id`、subject provider／model、`question`、`history`、`answer`、answer status／reason、`answer_sha256`、`context_capture`、`context_version`、normalized `context`、`reference_facts`、`truth_status`／`truth_version`、`requirements`、`observations`、quality／scenario metadata、source artifact refs 和 manifest digest。

答案 availability=AVAILABLE 必須有通過 binding 的問題、完整回答和 subject identity；context availability 獨立判定，回答不存在或來源失敗的 planned unit 仍保留為 `UNAVAILABLE`。snapshot 缺失不能讀目前知識或 prompt 補回；reference facts 缺失不能把 correctness 變成可判定。

### 8.4 驗收條件

- 同一計劃及同一份模擬生成回應，經新版 run／matrix producer 與直接 frozen-row fixture 應得到一致的 planned units、正規化內容及 oracle binding；不同實際生成不要求 answer_id 相同。
- 每個 answer_id 能定位一個不可變 canonical row；補評可引用它，重新生成使用新 ID。
- 所有 planned units 都有明確紀錄；執行前可為 PENDING，生成批次結束時須有終態。缺失回答、snapshot、truth 和 oracle 分別記原因。
- adapter 輸出可直接供 frozen-answer-evaluation 的 rubric、relevancy 和 deterministic checks 使用，不需要 consumer 另行重建 history 或 plan。
- fixture 能證明 source artifact hash、answer hash、context／truth version 和 manifest digest 在 JSON、Excel、report 引用中一致。

## 9. P1-2：Case oracle 到 evaluator contract 的映射

### 9.1 映射原則

Case YAML 是測試意圖和 oracle 的編寫入口；adapter 在答案生成前建立 versioned evaluator plan，在 frozen row 建立後只補入實際 answer／snapshot。Evaluator 不得自行從案例文字或目前知識檔推導新的要求和真值。

### 9.2 欄位映射

| Case YAML | canonical evaluator 欄位 | 語義 |
| --- | --- | --- |
| `turns[].user` | `question` | 本輪原始問題；不可由回答反推 |
| `expected.safety_levels` | safety requirement／deterministic expectation | 只在有對應 runtime observation 時判定 |
| `expected.route_ids`、`preferred_route_id` | route requirement／expected route | 由 trace observation 判定，不能從回答風格推斷 |
| `expected.must_include` | `requirements[kind=task]` | 回答應滿足的必要要求；需綁定回答 span 或合理的缺失理由 |
| `expected.forbidden_behaviors` | `requirements[kind=safety/constraint]` | 禁止行為；由回答與可觀測 trace 分別評估 |
| `response_oracle.required_claims` | requirements，必要時拆成多個可判定 item | 要求回答包含的內容，不是獨立事實真值 |
| `response_oracle.forbidden_claims` | requirements，禁止項 | 禁止回答內容，不自動等於 rubric red line |
| `response_oracle.must_cite` | evidence／citation requirement | 需有指定來源或有效 evidence ref |
| `response_oracle.should_abstain` | safety／constraint requirement | 保留 abstention 條件和判定範圍 |
| `response_oracle.expected_tools` | tool deterministic requirement | 只檢查有效 trace 中的工具呼叫 |
| `response_oracle.max_chars` | constraint requirement／字數檢查 | 凍結計數規則，按回答原文檢查 |
| `response_oracle.reference_answer` | 核准範圍內的參考回答 | 不自動作為事實真值；需與獨立來源綁定 |
| `expected.capsule_ids` | route／evidence expectation | 按標註範圍與實際觀察判定 |
| `response_oracle.goal_completed`、`max_steps` | task／interaction requirement | 需要完整輪次和執行 observation |
| `expected.source_refs`、`wiki_refs` | reference facts 或 evidence requirements | 只有來源內容、scope 和核准狀態明確時才進入 reference facts |
| `expected.reference_oracle` | truth／oracle metadata、context scope、ground contract | 記錄 reference version、snapshot、批准範圍和缺失狀態 |
| `memory_checkpoints` | 跨輪 requirements／deterministic observations | 按 `after_turn` 固定生效範圍，不改寫前輪結果 |

### 9.3 Reference facts 的生成邊界

`reference_facts` 只保存可獨立核對的事實單元，每項包含 `ref`、`content`、`layer`、source digest、scope 和 truth version。`SOURCE`／`REFERENCE` 內容必須有明確 provenance 和 approved status；Case 的 `required_claims`、preferred route、capsule 指令和 rubric 說明不能直接當作事實。沒有獨立核准內容時，row 仍可執行 requirements、rubric 和 faithfulness，但需要事實真值的 claim，其 correctness 為 `UNKNOWN`；非事實性項目依契約保留 `NOT_APPLICABLE`。

Adapter 輸出 `oracle_status`、`truth_status` 和每個 requirement 的 `provenance`。案例整體 `REVIEWED` 不自動代表所有 reference facts 已批准，也不自動成為 `APPROVED_AGGREGATE`；批准範圍必須逐項或按明確 snapshot scope 保存。

### 9.4 跨輪展開

Adapter 將跨輪限制展開為帶 `start_turn`／`end_turn` 的 requirements；每一輪只接收已生效的限制和正確的 conversation history。若某一項需要前輪事實、memory 或 route observation，而該資料缺失，該 requirement 判定為 `UNCERTAIN`，所需 observation 記為 `UNAVAILABLE`，不把缺失當作違反要求。

### 9.5 驗收條件

- 同一 Case YAML 重建 plan 時，requirements／reference facts／constraints 的 ID、順序、版本和 scope 穩定。
- 每個 requirement 都有來源路徑、kind、critical、適用輪次和 oracle status；無法映射的欄位進入明確 remediation，不靜默丟棄。
- `reference_facts` 只包含經過核准且可獨立核對的內容；行為要求、提示詞和回答期望不會混入 factual correctness gold。
- 生成的 frozen rows 可在無 Case YAML 現場讀取的情況下完成 evaluator；所有必要 oracle 和 truth metadata 已被凍結在 plan／row 中。

## 10. P1-3：Frozen Answer Evaluation ingress 與 orchestration

### 10.1 統一入口

`frozen-answer-evaluation` 必須先接收 canonical frozen rows，再由同一個 ingress 完成 schema、identity、history、context snapshot、truth、requirements 和 source digest 驗證。舊 `unified`／`staged` CLI 直接移除，呼叫端遷移至新入口；未正規化資料須先經 adapter。

共同入口依序執行：

1. 載入並驗證 evaluation plan、manifest 和 planned rows。
2. 由共用 freeze adapter 提供 frozen answer；正規化 `effective-context-snapshot/v1`。
3. 將 Case YAML oracle adapter 的 requirements、reference facts、constraints 凍結到 row。
4. 建立 canonical row digest 和 stage dependency graph。
5. 驗證所有 planned units 均有紀錄；依第 14 節，在所需 frozen answer 就緒後啟動獨立分支，claim assessment 保留全批 extraction 終態 barrier。

### 10.2 單一入口，以計劃選擇 evaluator branches

- `frozen-answer-evaluation` 由 plan 啟用 deterministic checks、claim extraction、claim／requirements assessment，以及 rubric／relevancy 等 branches；所有 branches 共用同一輸入。
- Reverse questions／embeddings 是預設 relevancy 的依賴步驟，不另設第二個 relevancy 模式；所有 evaluator 共用同一 frozen answer。
- Plan 記錄各 branch 是否啟用；實際執行、可用性與判定依第 14.1 節分欄保存。

唯一正式入口產生同一種 evaluation envelope；consumer 遷移至新契約，不保留舊模式的 projection 分支。

### 10.3 Stage dependency 與恢復

Claim assessment 只使用成功且驗證通過的 inventory；失敗的 extraction 使依賴項不可執行，relevancy 依賴 frozen question／answer binding；requirements 的 route／evidence 判定依賴 deterministic observations；rubric 可獨立依賴 frozen answer 和 rating rule。Stage receipt 記錄 parent stage IDs、request digest、provider identity、status、重試和 checkpoint reuse。

單一 branch 失敗不重跑無關 branch，也不改寫已成功的 inventory 或其他 Judge assessment。重新執行依第 14.4 節只補可重試失敗或已恢復依賴的 stage；若 frozen row 或任何 parent digest 改變，產生新 evaluation generation。

### 10.4 驗收條件

- 同一 frozen-row fixture 經 canonical CLI 或 Python API 後，canonical row、context snapshot、requirements、truth metadata、answer hash 和 source digest 完全一致。
- 各 evaluator 的 branch status、stage receipts、request binding 和 unavailable 分母可在同一 envelope schema 中表示。
- CLI 和 Python API 共用 normalization；測試確認舊 `unified`／`staged` 命令不再註冊。
- 任一 branch 的輸出都能以 `answer_id` 回到同一 frozen answer，並被同一個 JSON／Excel exporter 消費。
- 加入 missing snapshot、missing truth 和 provider failure fixture，驗證三者各自得到正確狀態和原因。

## 11. P1-4：完整 results.json 與無損 exporter

### 11.1 Source of truth 結構

`results.json` 的頂層 envelope 固定保存 `schema_version`、`contract`、`run_ref`、`manifest`、`plan`、`answers`、`envelopes`、`inventories`、`stages`、`aggregates`、`artifacts` 和 `provenance`。`answers` 保存 canonical frozen answer；`inventories` 以 `inventory_id` 保存每份答案的一次 claim extraction；`envelopes` 以 `answer_id` 保存 deterministic、rubric、assessment、requirements、relevancy 和 review；`aggregates` 只保存由上述資料派生的摘要。

每個全域集合都以明確 ID 索引，禁止把 inventory 只嵌在某一個 Judge cell 內：

```text
answers[answer_id]
  ├─ inventories[inventory_id]
  ├─ envelopes[answer_id]
  │    ├─ rubric[judge_id]
  │    ├─ assessments[judge_id]
  │    │    └─ requirements（每個 Judge 的判定）
  │    └─ relevancy
  └─ artifacts／evidence refs
```

Exporter 必須先驗證：`inventory.answer_id == answer_id`、assessment 的 `inventory_id` 相同、claim IDs 完整匹配、requirement IDs 完整匹配、evidence refs 能在 context／truth／answer span catalog 找到。已標記成功資料若 join 不一致，記為 export integrity error 並停止該投影發布；來源本身已記錄的缺失則正常投影其狀態，不把程式組裝錯誤偽裝成 provider 不可用。

### 11.2 投影規則

- `Answers` 只從 `answers` 和其 envelope 的 relevancy／deterministic summary 產生，每個 `answer_id` 一列。
- `Scores` 從 envelope 的 rubric 和 assessment summary 展開，每個 answer × evaluator／Judge 一列；所有 Judge 使用相同納入規則，不按自評或模型系列排除、降權或加標記。
- `Claims` 先由 `envelopes[answer_id].assessments[judge_id]` 找 assessment，再以 `inventory_id` join `inventories` 的 claim 原文；每個 answer × claim × Judge 一列。
- `Requirements` 從同一 assessment 的 requirements items 展開，另外標示 deterministic 或 Judge 判定來源、gate 類型和 oracle status。
- `Rating Details` 從 rubric dimensions、red lines 和其他可讀 detail 展開，不重建分數。
- `Overview` 只讀 aggregates 和 availability counts；每個數字保留 numerator、denominator、eligibility、status 和 source refs。
- `Spec` 從 manifest／plan 投影可讀版本和範圍；不從答案或 workbook 反推配置。

Evidence quote、answer span 和 evidence ref 的完整版本留在 JSON；Excel 顯示可讀引文和定位 ID。Report Agent 只讀 JSON 的 aggregates、envelopes、evidence catalog 和 artifact index，不把 Excel 當作唯一證據來源。

### 11.3 防止資料遺失

Exporter 不可把 `correctness`、requirements gates、inventory audit、evidence spans、stage receipts、UNKNOWN／UNAVAILABLE、Judge 分歧或人工 provenance 壓成單一分數。Excel 不適合展示的欄位保留 `json_pointer`／artifact ref；report 若未讀取完整單位，必須說明覆蓋範圍。

新流程只支援新結果契約，不設 `LEGACY_PARTIAL` 狀態或舊格式輸出分支。不設歷史資料匯入或轉換流程。JSON 通過 schema、join 和 hash 驗證後獨立保存；Excel 通過來源 digest 與 row count 驗證後交付，失敗可從同一 JSON 重建；報告引用的 generation digest 必須與兩者一致。

### 11.4 驗收條件

- synthetic fixture 中每個 claim 的 `claim`、`kind`、`answer_quote`、faithfulness／correctness、evidence quote 和 reason 在 JSON 及 Claims sheet 均可回溯。
- 不同 Judge 共用同一 inventory，inventory 不重複且不出現 null claim projection。
- requirements、gates、relevancy、deterministic checks、human review 和 stage receipts 在 JSON 有完整資料，Excel 有相應摘要或定位。
- 同一 metric／scope 在 JSON、Excel、報告的狀態和分母一致；answer、claim、Judge 等不同粒度使用各自計數。
- 修改 manifest、answer、inventory、assessment 或 exporter contract 任一 digest 後，舊 JSON／Excel／report pair 不會被新 generation 靜默覆蓋。


## 12. P1-5：八表 Excel exporter

### 12.1 單一輸入與輸出

Exporter 只接收通過驗證的完整 results.json，單模型與多模型共用一套八表格式。它不呼叫模型、不重評答案、不自行改變聚合政策；Excel 是可重建的閱讀視圖。Report Agent 直接讀 JSON，由程式 exporter 產生 Excel，兩者分別執行。

### 12.2 工作表映射與閱讀順序

| 表 | 唯一列鍵 | 主要來源 | 閱讀重點 |
| --- | --- | --- | --- |
| Overview | metric ID＋scope＋subject／Judge＋聚合版本 | aggregates | 指標、數值、狀態、有效／計劃數、分母與排除原因 |
| Spec | 配置或案例項目 ID | manifest、plan、preflight | 模型、案例、版本、啟用項目及執行參數摘要 |
| Answers | answer_id | answers、relevancy | case、turn、subject、問題、回答、狀態、時間、生成 token、相關性 |
| Scores | answer_id＋evaluator role＋judge_id | rubric、assessment summary | 評分與分支狀態、呼叫時間與 token |
| Claims | answer_id＋inventory_id＋claim_id＋judge_id | inventory join assessment | 主張、種類、回答引文、忠實度、正確性、各自證據及理由 |
| Requirements | answer_id＋requirement_id＋判定來源 ID | frozen requirements、assessment、checks | 要求、關鍵性、判定、證據、理由及 gate 關聯 |
| Rating Details | answer_id＋judge_id＋detail type＋detail ID | rubric | 逐維度分數、紅線、支持與扣分證據 |
| Human Review | generation＋answer_id＋judge_id | answers、評估與審閱紀錄 | 全量閱讀、逐 Judge 批准、原因與審閱身分 |

共用可讀身分欄位放在左側，追溯 ID／JSON pointer 放在右側；表頭凍結並啟用篩選，長文字換行。Scores 的 evaluator role 明確區分 rubric 與 claim／requirements，未適用欄位留空，避免暗示所有 Judge 都執行相同任務。多個證據引文按 ref 列出，超長時顯示截斷提示與完整 JSON 定位。

### 12.3 缺失、用量與重建

Answers 保留所有計劃答案單位；Scores 保留計劃的 answer × evaluator × Judge，包括未執行與失敗。未抽取出 inventory 時不虛構 Claims 列，由 Answers／Scores 顯示缺失原因。已知 inventory 但 Judge 失敗時，可列出原有 claims 並標記判定不可用。

每個外部呼叫以 request／attempt ID 核算用量。Claims 和 Requirements 共用的 assessment 用量只計一次；重複展示的 stage 引用不重複加總。未回傳 token 的呼叫保留 null，Overview 同時顯示用量覆蓋；本地 cache reuse 不新增 provider token 消耗。各指標使用自己的分母，不要求 claim、answer 和 Judge 層級的計數相等。

### 12.4 驗收

以相同凍結輸入核對單模型及多模型八表的列鍵唯一性、來源定位和數值一致性。測試覆蓋多 Judge 共用 inventory、缺失回答、失敗 assessment、UNKNOWN correctness、多證據、長引文、重試及快取重用。Human Review 允許編輯的欄位由 review importer 另行驗證；重建前保存未匯入的人工填寫，不覆蓋進行中的審閱。重建 Excel 不呼叫 provider，不改 JSON；跨表可重複呈現資料，但總用量與聚合分母必須與 JSON 相同。

## 13. P1-6：統一 Report Agent 契約

### 13.1 唯一入口與來源綁定

Report Agent 只接收通過新契約驗證的 results.json、其綁定證據附件及報告配置。移除 package 內建與 root 報告流程的重複引擎及舊 workbook 輸入，不設相容入口。啟動時凍結 results digest、evaluation generation、附件 hashes、報告模型、prompt／metric dictionary／工具契約版本及執行限制；來源變更時建立新的 report generation。

Excel 與 Report Agent 都是完整結果的 consumer。報告不依賴 Excel 成功產生，也不產生 Excel；JSON／Excel 的交付與 report status 分開管理。

### 13.2 只讀查詢與分析

共用 evidence store 提供分頁查詢：評測範圍與配置、aggregates、案例／答案、rubric、claims、requirements、relevancy、deterministic checks、人工結果，以及對應的證據原文。每次查詢回傳穩定 ID、JSON pointer、來源 digest 和分頁資訊，並記錄 Agent 實際看過哪些資料。完整保存的 raw events 不等於全部送入模型；只暴露與查詢有關且屬本次凍結資料的內容。

數值、分母、eligibility 和分組摘要由程式產生；Agent 引用它們解釋主要結果、失敗模式、Judge 分歧與改善建議。額外分組若需要新摘要，須由共用聚合程式按明確篩選條件計算並產生來源 receipt。Agent 不自行重評或改寫原始分數，不從目前 prompt／知識檔補回缺失的執行證據。

### 13.3 Findings 與引用驗證

每項 finding 保存 ID、類型（觀察事實／Judge 判定／假設／建議）、結論文字、來源 refs、必要引文和分析範圍。數值結論綁定 metric／aggregate ID 及分母；個案結論綁定 answer、Judge／requirement／claim ID；改進建議連回支持它的 findings，並附驗證方式。

發布前驗證來源存在、generation 一致、引用已經查詢暴露、引文逐字匹配、數值與程式摘要一致，以及結構化 findings 與 Markdown 引用對應。報告明示已閱讀的案例／答案範圍及關鍵證據缺失；不能將抽樣閱讀寫成全量核對。程式驗證保障引用和資料一致性，分析推論的正確性仍由報告審閱處理。

### 13.4 輸出、失敗與恢復

報告產物包括 report.md、findings.json、報告 manifest、validation 結果、查詢紀錄及 request／attempt receipts。它們綁定來源 results digest，不回寫凍結的評估 JSON；報告自身的時間、token 和重試用量另存於 report receipts，避免與答案／Judge 用量混算。

Report status 區分未計劃、待執行、執行中、完成及失敗。只有引用與結構驗證通過的報告才標記完成；失敗保留 draft 和原因。重試只執行報告階段，相同完整請求可重用已成功且驗證通過的回應。修復輪次受報告配置限制，來源或報告配置變更時不沿用不匹配的快取。

### 13.5 驗收

離線 fixture 覆蓋單模型／多模型、Judge 分歧、缺失 evidence、錯誤引用、偽造引文、錯誤分母、來源 digest 改變及報告中途失敗。驗證報告失敗時 JSON／Excel 仍可交付；重試不呼叫 subject 或 evaluator；報告與 findings 的每個引用均可定位到同一 generation 的資料。移除舊報告入口的測試和文件一併更新，不保留雙引擎。

## 14. P1-7：執行狀態、並行、快取與恢復

### 14.1 狀態分層

| 欄位 | 狀態 | 用途 |
| --- | --- | --- |
| execution_status | NOT_PLANNED、PENDING、RUNNING、BLOCKED、SUCCEEDED、FAILED、SKIPPED | 工作是否啟用、正在等待依賴、完成或失敗 |
| availability | AVAILABLE、PARTIAL、UNAVAILABLE | 該項輸出實際可用程度 |
| verdict | 各 evaluator 的既定判定，如 UNKNOWN、ENTAILED、VIOLATED、NOT_APPLICABLE | 評估內容的結論 |
| review_status | NOT_REQUESTED、PENDING_REVIEW、REVIEWED | 人工審查進度 |

四者不互相代替：Judge 成功回傳 UNKNOWN 是成功執行但無法確定內容；provider 失敗則沒有語義 verdict。回答可用而 snapshot 缺失時，答案 availability 仍為 AVAILABLE，context availability 另記；只阻擋需要該證據的分支。適用性在呼叫前已能確定為不適用時，可 SKIPPED 並記原因，不產生模型分數。

Stage 完成表示所有計劃單位已完成、失敗、略過，或因上游終態失敗而確定不可執行；BLOCKED 需記錄依賴及阻擋是否已終結。不能僅因暫時沒有可執行工作就宣告完成。

### 14.2 並行與依賴

凍結答案之間的 extraction 可受限並行；保留全批 extraction 終態 barrier，之後對成功 inventory 執行 answer × Judge assessment。失敗 inventory 的 assessment 保存依賴失敗原因，不送出請求。Rubric、relevancy 及確定性檢查可在其輸入就緒後獨立執行；route／evidence requirements 判定需先取得相應 observation 或明確缺失狀態。Relevancy 的反向問題生成完成並驗證後才執行 embedding。

設定全域及各 provider 的在途請求上限與速率限制；重試同樣消耗限制額度。完成順序不影響主鍵、輸出排序和聚合結果。同一 stateful subject case 的回答生成仍保持輪次順序，這與評估分支並行分開管理。

### 14.3 Request、attempt 與 receipt

每個工作保存 stage ID、answer ID、evaluator 身分、parent refs、request digest 及狀態。每次實際呼叫另建 attempt ID，記錄開始／結束時間、provider request ID、延遲、token、錯誤類型與 retryability；未知用量保留 null。

Request digest 綁定實際輸入、模型及影響輸出的參數、prompt／schema／validator 版本和證據內容。新 report generation、輸出目錄、排隊時間等執行位置資訊不單獨使相同模型請求失效。一次合併 assessment 可產生 claims 和 requirements 兩組輸出，但只對應一筆實際呼叫用量。

### 14.4 快取與重試

本地結果快取只重用請求完全匹配且重新通過驗證的成功回應；receipt 明示 reused_from，保留原呼叫用量，本次新增 provider 用量為零。Provider prompt cache 另外記錄供應商回傳的使用量，沒有 telemetry 就不推定命中。

同一程序內同 digest 的請求共用一個進行中的工作；checkpoint 以原子寫入及單一工作 owner 防止重複發布。程序中斷但 provider 可能已處理的 attempt 記為結果未知；自動恢復無法保證外部呼叫只發生一次，需保存可能重複呼叫與用量未知的紀錄。

暫時性網路、限流及服務錯誤依有上限的 retry policy 處理；認證、無效配置和本地 binding 衝突先停止相應工作。重試耗盡後保留失敗，其他獨立工作繼續。UNKNOWN 判定不作為自動重試理由。補跑只選取已恢復依賴的工作或允許重試的失敗項，保留成功 inventory 與判定。

合併 assessment 先驗共同 binding，再分別驗 claims 和 requirements。共同 binding 錯誤使兩組都不可用；局部驗證失敗時保留另一組已通過的結果及 PARTIAL 狀態。預設以相同合併請求重試，但只補入缺失部分，保留其 attempt provenance；新回應若與已保存結果衝突，記錄衝突而不覆寫或靜默混合。未完整通過的原始回應不標為完整成功快取。

### 14.5 驗收

離線 provider 替身驗證並行上限、barrier、相同請求去重、原子 checkpoint、暫時失敗後恢復、不可重試錯誤、局部 assessment 失敗及中途重啟。成功工作補跑不再呼叫 provider，輸入版本改變不誤用快取。相同 fixture 在順序與並行執行下產生相同語義結果及分母；時間和 attempt 紀錄可不同。用量按實際 attempt 去重核算，cache reuse 不重複計費。


## 15. 實作順序與完成條件

以下是待執行工作，不是已通過的測試。章節 1–5 記錄產品決定；6、8–14 定義契約；第 7 節只記錄盤點時的程式現況。實作時按依賴順序完成，不把 P1 編號當成施工順序，也不建立過渡相容層。

| 順序 | 工作與範圍 | 必須通過的驗收 |
| --- | --- | --- |
| 1 | P1-1／2／4／7 的共用 schema：plan、IDs、hash、分層狀態、evidence、envelope | 單輪 fixture 能往返序列化；錯配 ID／引用／hash 被拒絕；snapshot 缺失不使答案消失 |
| 2 | Case adapter 與 run／matrix producer 接線（P1-1／2） | 完整 planned 清單、多輪 history、缺失狀態及 oracle scope 可追溯；不呼叫真實 provider |
| 3 | 單一 Frozen Answer Evaluation 引擎及執行層（P1-3／7） | 所有預設分支、依賴、並行上限、checkpoint、去重、局部失敗及重啟測試通過 |
| 4 | 完整 JSON 與共用聚合（P1-4） | inventory join、correctness、requirements、evidence、分母、用量均完整；成功資料不接受懸空引用 |
| 5 | 八表 Excel（P1-5） | 單／多 subject、失敗 Judge、長引文、快取與重試用量投影正確，無 provider 呼叫 |
| 6 | 單一 Report Agent（P1-6） | 引用／數值／版本驗證；失敗可獨立重試；不阻擋 JSON／Excel |
| 7 | 全量人工審查接線 | packet 綁定、重複提交、錯代提交及 adjudication 驗證；新 generation 保留自動與人工 provenance |
| 8 | CLI、文件與重複實作清理 | 移除 unified／staged、舊 claims／attribution Judge、舊 exporter 及重複報告入口；active callers 全部使用新契約 |

先用小型 fixture 覆蓋失敗邊界，再用 Minimal33 的計劃範圍搭配模擬回應跑完整鏈。最後執行相關 evaluator、CLI、exporter、report、review 測試；真實 provider 驗證另列紀錄，不用離線通過代替 live 成功。

完成清單：單一入口與契約；各預設 evaluator 可執行；原始資料與完整 JSON 可追溯；八表可重建；報告獨立重試；人工結果不覆寫既有 generation；用量和分母可核對；舊入口沒有 active caller；必要測試通過且未驗證項明示。

## 16. 尚待確認的政策

下列項目不影響先完成 schema、adapter 及離線資料鏈，但在啟用相應評分／正式結論前必須確定；不得由重構順手改變。

| 項目 | 已確定 | 仍需確定 |
| --- | --- | --- |
| Minimal33 就緒與正式聚合資格 | 使用者確認另一工作已完成；直接以其最終政策與版本接入，不重新制定 | 實作時定位並核對最終產物的版本與 digest |
| Requirements／rubric gate | 保留品質分數；gate 按第 3.3 節使用 FAIL／UNDETERMINED／PASS／NOT_APPLICABLE，待確認不扣分也不計通過 | 本項政策已確認；與案例條件的具體映射於實作驗證 |
| Relevancy | 預設啟用並獨立展示，不影響 rubric 總分或 gate | 本項政策已確認 |
| 跨 Judge 與 case 聚合 | 各 Judge 分開；rubric／claims 按完整案例等權；gate 使用四態及已確認通過率；詳見 16.1–16.5 | 本項政策已確認 |
| 人工審查 | 每次全量審閱；逐 answer × Judge 批准；REJECT 不自動重跑，由使用者確認修訂；校準規則見第 17 節 | 本項政策已確認 |
| 舊 attribution 特有診斷 | Claim assessment 承接；來源層與引用覆蓋保留為診斷；policy／abstention 統一到 requirements | 本項政策已確認；具體映射見第 18 節 |

### 16.1 Judge 統一納入政策

所有 Judge 的有效結果預設直接納入主摘要；不因與 subject 同模型或同系列而排除、降權或分類。JSON、Excel、報告及內部判定不新增或保留 self_judging、same_model_family 標記；仍保存 subject 與 Judge 的 provider／model／版本身分供追溯。實作移除模型身分比較造成的 primary_eligible 排除邏輯；資料有效性、缺失及其他適用資格維持共用規則。

### 16.2 品質分數的矩陣與案例聚合

主摘要以被測 LLM 為列、Judge 為欄，分別呈現每個 LLM × Judge 的品質分數；各品質維度採相同分組。不計算跨 Judge 平均分、跨 Judge 總分或由此產生的唯一排名。JSON aggregates、Excel Overview 和報告均保留 judge_id，讓讀者直接比較不同 Judge 對不同 LLM 的評分。

每個矩陣格先按案例評分規則計算該 Judge 對每個 case 的分數，再對符合納入條件的 case 等權平均：格內分數 = 納入 case 分數之和 ÷ 納入 case 數。案例輪數不改變 case 權重；逐輪評分、各 case 分數與計算依據完整保留。每格附有效案例數、計劃案例數及排除原因；有效案例數為零時數值為 null。

每個 LLM × Judge 只有在案例全部預期輪次的必要 rubric 評分齊全、有效，且符合已接入的案例聚合資格時，才將該 case 納入主品質摘要均值。缺輪或必要評分缺失的 case 保留有效逐輪明細，記錄排除原因，不補零；另一個 Judge 若對該 case 評分完整，仍可納入其自己的摘要。Claims、relevancy 等其他分支失敗不直接使已完整的 rubric case 失去資格；紅線／gate 失敗同樣不排除已完整的品質分數。

每格保存納入與排除的 case IDs、原因及有效／計劃案例數，供核對不同 Judge 的覆蓋差異。Claims 與 gate 的彙總另行定義，不將此品質分數公式直接套用到其他指標。

### 16.3 主摘要的覆蓋矩陣與適用性統計

Overview 必須並列提供品質分數矩陣和獨立的有效／計劃案例數矩陣，兩者均以被測 LLM 為列、Judge 為欄，排列一致。覆蓋矩陣每格顯示有效 case 數／計劃 case 數，並保留原始數值供篩選或匯出；不僅在分數旁加註。各品質維度與其他指標若使用不同納入集合，使用各自的覆蓋統計，不借用品質總分的分母。

Overview 另設「適用性與缺失統計」區塊，維持八張工作表。按 LLM、Judge（適用時）、evaluator／指標／rubric 維度列出計數粒度、計劃數、成功評估數、適用數、NOT_APPLICABLE 數、不確定數、未取得有效評估數，以及摘要納入／排除的案例數和原因定位。完整數值和公式保存在 JSON aggregates，報告設相應統計段落。

統計分開呈現執行覆蓋與語義判定：UNKNOWN／UNCERTAIN 可來自成功評估，不能與執行失敗相加當作互斥分類。NOT_APPLICABLE 須有明確適用性依據；缺證據或 Judge 失敗不歸入其中。Rubric 只統計其契約實際允許的不適用項，不能把 claim verdict 當成品質分數。各表明示粒度與分母，適用數為零時比例為 null。

Claims 的 case 等權及 UNKNOWN 分母規則見第 16.4 節。

### 16.4 Claims 的案例聚合

每個 LLM × Judge 先在各 case 內計算 claim 指標，再對符合納入條件且該指標有有效分母的 case 等權平均。Faithfulness 和 correctness 分別彙總，各 Judge 分開呈現，不跨 Judge 平均。保留逐 claim 判定、case 指標、納入 case IDs、有效／計劃案例数及適用性統計，不用全批 claim 數直接決定案例權重。

主摘要使用「已確認支持率」：每個 case、每個 Judge、每個維度分別計算 ENTAILED 數 ÷ 適用 claims 數；適用分母包含 UNKNOWN，排除 NOT_APPLICABLE。PARTIAL 不計入 ENTAILED，不另給部分權重。另行保存並展示 UNKNOWN 數 ÷ 同一適用分母的未知比例及各判定計數；UNKNOWN 保留為無法確定，不標為已證實錯誤。適用分母為零時比例為 null，不記滿分或零分。

主摘要對具有效分母且符合納入條件的 case 支持率等權平均；未知比例使用相同 case 集合等權平均。完整 JSON 保留各 case 的分子、分母和判定計數；全批 claim 計數統計與 case 等權比例分開命名。Provider／抽取失敗不轉成 UNKNOWN claim。

每個 LLM × Judge × 維度（faithfulness 或 correctness）只有在案例全部預期輪次的完整答案、有效 claim inventory 及該 Judge 對該維度所有 claims 的合法判定齊全時，才納入主摘要；另須符合已接入的案例聚合資格且全案適用分母非零。成功回傳 UNKNOWN 算判定齊全，保留於適用分母；抽取或評判失敗則排除該 case，保留有效明細與原因。

兩個維度獨立檢查完整性，共同 binding 或 inventory 失敗才同時影響兩者。某輪經驗證沒有可評 claims 可保留空 inventory；全案沒有適用 claims 時，比例為 null，列入無適用項統計而不進均值。未完成抽取不能冒充空 inventory。每個維度分別展示有效／計劃案例數矩陣及排除原因。

### 16.5 Case gate 彙總

在同一 LLM × Judge × gate 類型內，依完整案例的預期輪次彙總：任一輪 FAIL 則 case gate 為 FAIL；沒有 FAIL，但存在 UNDETERMINED 或必要判定缺失則為 UNDETERMINED；所有適用輪次均 PASS 且其餘輪次已確認不適用時為 PASS；所有輪次均確認不適用時為 NOT_APPLICABLE。

不同 Judge 的 case gate 分別保存及展示，不投票、不平均。已知 FAIL 與缺失輪次並存時仍保留 FAIL，同時記錄缺失輪次、原因及判定覆蓋。Case gate 引用逐輪結果及其證據，不因 rubric 高分或其他輪次通過而抵銷失敗。

主摘要按 LLM × Judge × gate 類型計算已確認通過率 = PASS 案例數 ÷（PASS＋FAIL＋UNDETERMINED 案例數）。NOT_APPLICABLE 排除，分母為零時為 null。另列四種狀態的案例數，以及 UNDETERMINED ÷ 同一分母的待確認比例；待確認不標成已證實失敗。各矩陣保留計劃範圍及原因引用，不以 rubric 或 claims 的完整案例篩選結果刪去待確認 gate 案例。

### 16.6 人工審查：紅線與關鍵違反

任一 Judge 判定 rubric 紅線觸發或關鍵 requirement 違反，即自動建立優先閱讀標記，附凍結答案、各 Judge 的原始判定、理由、證據及版本。其他 Judge 判通過不取消審查，自動結果照常交付，不等待人工完成。

同一結果 generation、同一 answer_id、同一問題建立一個審查項目，彙集不同 Judge 的意見。以 red_line_id／requirement_id 及明確的對應映射識別同一問題；沒有明確映射的項目分別保留，不以相似文字擅自合併。重跑不得重複建立相同審查項目。

### 16.7 人工審查：Rubric 分歧

同一結果 generation、同一 answer_id、同一 rubric 維度，在相同評分準則版本及 0–3 量尺下，至少兩個 Judge 有有效分數，且最高分減最低分 ≥2 時，自動建立優先閱讀標記。每個項目保存維度 ID、分差、各 Judge 的分數、理由及證據，並以 generation＋answer_id＋維度 ID 去重。

缺失、失敗或不適用評分不當作零分參與分差；不足兩個有效 Judge 時不產生分差判定，另保留覆蓋狀態。此門檻只觸發人工審查，不改分、不跨 Judge 平均，也不阻擋自動結果交付。

### 16.8 人工審查：Claims 支持／矛盾衝突

同一結果 generation、answer_id、inventory_id、claim_id 及同一評估維度，在相同證據與判定契約下，不同 Judge 的有效判定出現 ENTAILED 與 CONTRADICTED 並存時，自動建立優先閱讀標記。Faithfulness 和 correctness 分別檢查，不把兩個維度的不同結果視為跨 Judge 衝突。

項目附主張、回答引文、來源版本、各 Judge 的判定、證據引文及理由，以 generation＋answer_id＋inventory_id＋claim_id＋維度去重。保留所有原始判定，不投票改判，不阻擋自動結果交付。

其他 claim 判定差異（例如 ENTAILED／PARTIAL、ENTAILED／UNSUPPORTED、UNKNOWN／其他判定）預設只保留明細、統計及篩選能力，不單憑此差異建立優先閱讀標記。若同時符合紅線、關鍵違反或其他已確認的獨立送審條件，仍按該條件標記優先閱讀；gate 待確認按第 16.9 節分流。

### 16.9 人工審查：Gate 待確認分流

Gate 為 UNDETERMINED 時，按必要輸入的可用性及判定原因分流。所需資料齊全、Judge 仍無法確定時，自動建立內容審查優先標記，附要求、回答、各判定理由及證據。資料是否齊全由綁定輸入與驗證結果確認，不只依 Judge 自述。

缺少答案、trace 或有效評判結果時，先進補資料／重試清單，沿用第 14 節的有界恢復規則；gate 保持 UNDETERMINED。凍結資料缺失不能用目前知識或推測補造；若必須重新生成答案，建立新的答案版本。恢復無法完成時提示人工處理缺失原因，與內容審查分開，不要求人工在無證據下判定通過或失敗。

同時存在缺資料與判定不確定時，先處理缺資料，再重新檢查送審條件；其他已確認的獨立優先閱讀觸發仍保留。分流、恢復與送審均記錄來源項目及原因，不阻擋其他評估和自動結果交付。

## 17. Evaluator 配置獨立成檔

已確認將 prompt、評分規則和流程配置獨立保存，由執行程式直接載入唯一來源，不維護與程式分離的說明副本。目標目錄如下；本節為重構規格，尚未建立配置或切換 runtime：

```text
evaluation/evaluator-config/
  prompts/
    rubric.md
    claim-extraction.md
    claim-assessment.md
    relevancy.md
  rating-rule.yml
  workflow.yml
  schemas/
  calibration/
    README.md
```

Prompt 檔案保存任務、評判步驟、證據原則及經選定的示例；rating-rule.yml 保存唯一維度、錨點、權重與紅線定義；workflow.yml 保存分支、依賴、模型角色引用、並行及重試設定。模型角色引用既有共用模型配置，不另複製金鑰或建立第二套模型設定。Schemas 與程式 validator 共同檢查欄位、綁定及引用；呼叫、計算與恢復邏輯仍由 Python 執行。

每次執行凍結實際載入的配置內容及 hash，綁定結果與 request digest。變更後建立新配置版本並驗證快取資格；紅線不歸零等影響確定性計分的決策須同步修改 scoring 與測試，不能只改文字。Calibration README 定義人工修訂資料契約、切分、執行與比較方式；實際凍結標籤及校準輸出保存於 run artifacts，以 manifest 引用，不直接混入 prompt。

校準採用工作區代理分析＋固定校準腳本，暫不新增內建校準 agent。代理負責診斷及提出候選修改；腳本負責資料驗證、版本凍結、評估執行及新舊比較，不讓自由分析取代資料驗證。

### 17.1 校準工作流

1. 使用者提交填寫完成的 Human Review Excel；匯入腳本核對答案與評估 digest、人工決定、修訂值、理由及證據，產生可追溯的凍結人工標籤。
2. 以 case 為單位分開校準集與獨立驗證集，同 case 的不同輪次和不同 subject 回答不跨集合。兩者保存明確清單及版本；修改 prompt 的分析過程不讀取獨立驗證集內容與人工標籤。
3. 工作區代理分析校準集，區分 rubric／prompt、extractor、證據供應及 scoring 問題，提出具體差異與修改理由。候選版本另存，原版及人工標籤不改寫。
4. 固定腳本在相同凍結答案及證據上比較原版與候選 Judge，各 Judge 分別報告逐維度一致性、嚴重分差、紅線／關鍵要求漏判與誤報、claims 判定與證據問題，以及用量／延遲。若修改影響 extractor，另記 inventory 版本與抽取比較，不能冒充純 Judge 變更。
5. 獨立驗證集只用於最後驗證，輸出改善、退步和未解決項。若依該結果繼續調整，須記錄驗證集已被用於開發，重新建立未參與調整的驗證資料後才作獨立驗證結論。
6. 根據比較結果決定是否採用新版；不因校準腳本完成便自動替換預設配置。採用與否及所依據的 benchmark／配置版本記入決策紀錄。

校準集／驗證集的選樣規模見第 17.3 節；新版採用方式見第 17.4 節。每次校準不重新生成 subject 答案，不將保留驗證標籤送入 Judge 請求。

### 17.2 人工基準的最終確認者

目前由使用者擔任人工修訂標籤的最終確認者，不強制要求第二位審閱者。腳本負責格式、來源及版本綁定驗證；工作區代理可檢查證據和指出矛盾，但不能代替使用者批准或擅自改變標籤。有爭議的項目保持待確認，經使用者確認修訂值、理由及證據後，才納入校準基準。

保存實際 reviewer 身分、確認時間、修訂範圍及來源提交 ID；不補造第二位 reviewer 或雙人仲裁紀錄。現有校準 validator 若強制要求兩份人工提交，須改為支援本次明確採用的單一最終確認者政策，並在 benchmark manifest 記錄政策版本。

### 17.3 首版校準／驗證切分

Minimal33 首版按 case 分為 22 案校準集和 11 案獨立驗證集。每案的全部輪次、不同 subject 回答及 Judge 判定留在同一組，不跨集合。選案兼顧場景、紅線及已知誤判類型，凍結 case IDs、選樣依據與切分版本；實際名單待接入最終 Minimal33 產物後產生，不在本規格中猜定。

22 案供工作區代理分析與修改配置；11 案僅供固定腳本最後驗證，遵循第 17.1 節的資料隔離規則。這是初步驗證規模，後續以新增案例補充。人工標籤未確認或執行缺失的項目保留原因，分開報告計劃與有效覆蓋，不為湊足數量而自動搬動案例或補造標籤。

### 17.4 新版 Judge 的採用

首版不設自動切換門檻。校準腳本逐 Judge 輸出改善、退步及未解決項，包含紅線／關鍵要求漏判與誤報、rubric 嚴重分差、claims 判定差異、有效覆蓋、token 和延遲變化；由使用者閱讀比較報告後明確確認是否採用。未確認時維持原版。

採用紀錄包含確認者、時間、涉及的 evaluator／Judge、原版與候選配置 digest、benchmark 及比較報告引用。局部採用時明示範圍，不能將一個 Judge 的改善自動推廣至所有模型。

### 17.5 校準所需的獨立檔案

第 17 節的 prompts、rating-rule.yml、workflow.yml 和 schemas 都保存為獨立可閱讀檔案，由程式直接載入。另以 examples 檔案保存選定的 few-shot 示例，明示來源 case 和用途；不得混入保留驗證集內容。Rubric、claim extraction、claim／requirements assessment、relevancy 各有自己的 prompt 與版本引用，不把規則藏在 provider transport 字串中。

每次校準的 run artifacts 至少包含以下資料，實際目錄由既有 runs 配置決定：

```text
calibration/<calibration-id>/
  manifest.json
  baseline-config/       # 本次原版 prompt、規則、流程、schema、示例的精確快照
  candidate-config/      # 候選配置檔案，確認前不改生效版本
  changes.md             # 問題分類、修改理由及差異摘要
  benchmark-manifest.json # 校準／驗證集清單與人工標籤引用、hash
  comparison.json
  comparison.md
  adoption.json          # 待確認／採用／不採用及決策範圍
```

每次比較凍結當時的候選檔案與 digest；繼續修改時建立新候選版本，不覆寫已比較的快照。配置 manifest 對每個 evaluator 明確指定 prompt、rating rule、schema 和示例路徑。保存模型實際收到的完整 request 與組裝版本於既有 request receipts，方便核對檔案如何形成模型輸入；不複製 API key 或憑證。生效配置仍只有一個來源，baseline／candidate 快照僅用於版本比較與重現。

## 18. Attribution 功能歸入 Claim assessment

已確認由 claim assessment Judge 承接舊 attribution 的語義判定，配合共用 extractor 與確定性統計，取消獨立 attribution Judge。此決定是目標責任分配，尚未代表 runtime 已完成接線。

### 18.1 證據來源層

Chatflow snapshot 記錄實際提供給 Composer 的內容；assessment Judge 對每個 claim 回傳判定、evidence refs、引文及理由；程式將 refs 對照本次凍結 evidence catalog 的 layer 和來源 ID。JSON 及 Claims 表保存來源層、來源 ID 和證據引文，不另設來源層品質分數。Faithfulness 引用 context，correctness 引用獨立 reference facts，兩個證據範圍分開保存及驗證。

多層可共同支持同一主張，記錄的是判定時的證據參與，不將各層當作互斥貢獻比例。只保留 Chatflow 實際回傳且通過綁定驗證的 snapshot；缺失時明示原因，不推定任何部署都具備相同 trace 能力。

### 18.2 其餘功能的對應範圍

舊 claim support／unsupported 診斷對應新 faithfulness／correctness 判定及計數，不恢復已被新契約取代的 PARTIAL 半分算法。Context unit 引用統計由 assessment refs 與 snapshot unit 索引派生；policy 適用性／遵循及 abstention 判定統一在同一 assessment 的 requirements 中處理，映射規則見下文。涉及新增 requirement 的部分須在評估前凍結，不能由 Judge 臨時改寫要求。

### 18.3 評估證據引用覆蓋

保留評估證據引用覆蓋診斷，由程式對照有效 Composer snapshot 與 claim assessment 的 faithfulness evidence refs 計算，不新增 Judge 呼叫。每個 answer × Judge 的分母為當輪 snapshot 中提供給 Composer 的內容單元 occurrence 數；分子為該 Judge 在有效 claim 判定中引用的唯一 occurrence 數。相同 occurrence 被多個 claim 引用只計一次；不同 occurrence 即使文字相同仍按 snapshot 身分區分。Correctness 的獨立 reference facts 不計入此 context 覆蓋。

各來源層分別列出引用數、提供數與比例，並保留 ref／occurrence 清單、判定與來源綁定。引用可能用於支持或指出矛盾，本指標不等同支持率。未被引用的內容仍可能影響語氣或行為，因此不稱為模型實際使用率或因果貢獻，不納入品質總分或 gate。

完整 assessment 且沒有引用時分子為零；snapshot 或必要 assessment 缺失時保留不可用，不能當成零引用；分母為零時比例為 null。JSON 保存完整明細，Excel Overview 的診斷區展示每個 LLM／case／turn／Judge 的引用數、提供數及來源層，Claims 表保留引文與來源定位。跨答案彙總如另行需要，須明示粒度與公式，不把跨 Judge 重複引用合計成模型使用率。

### 18.4 Policy 遵循統一到 Requirements

要評估的行為 policy 明確映射為 requirements，保存 policy ID、來源 ref／版本、原文、適用條件與 critical 設定，由同一次 claim／requirements assessment 判定，沿用既定 verdict、理由及回答證據契約。不另設 policy Judge 或 policy 品質分數。

同一規則已存在於 Case YAML 時，以明確對應連到同一 requirement ID，不重複評估或扣分；僅語句相似不足以自動合併。候選 policy 與其適用條件在評估前凍結，Judge 依條件判定是否適用，不臨時新增要求。未知適用性保留不確定，已確認不適用才標記 NOT_APPLICABLE。

只有明確標為 critical 的 policy requirement 按已確認規則影響對應 gate；不得僅因規則來自 system prompt 或 capsule 就自動提升為 critical。JSON 和 Excel Requirements 表保留來源映射及判定，人工審閱沿用同一 answer × Judge 流程。

### 18.5 Abstention 統一到 Requirements

將案例中的 should_abstain 及適用規則轉成具體 requirements，明確界定應拒絕或暫不下結論的部分、適用條件，以及仍需提供的支持。由同一次 assessment 依 requirements 契約輸出 SATISFIED／VIOLATED／UNCERTAIN／NOT_APPLICABLE、理由及回答引文。不另設整段 ANSWERED／ABSTAINED 二元評分或獨立拒答 Judge。

例如拒絕替使用者決定是否離婚與持續提供決策支持可同時成立，分別由明確要求評估。只有布林 should_abstain 而缺少必要範圍時，adapter 保留來源並標記需補充，不能讓 Judge 臨時猜定禁答範圍；未提供此欄位也不自動等於允許或要求拒答。適用的 requirement 是否影響 gate，沿用明確 critical 設定及已確認 gate 規則，不因出現拒答便自動判定好壞。

JSON 與 Excel Requirements 表保存來源、適用範圍、判定、理由及證據，納入同一 Human Review 流程。舊 abstention 欄位不再作為另一份結果來源。
