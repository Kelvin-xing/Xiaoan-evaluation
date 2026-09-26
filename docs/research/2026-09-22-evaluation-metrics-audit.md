# 評測工作簿：指標與欄位盤點及精簡提案

日期：2026-09-22。範圍：只讀兩個 evaluator 的 exporter 與四份本地工作簿；沒有發起模型呼叫、沒有改寫結果。以下「现況」與「提案」嚴格分開。程式的現行 schema 與歷史工作簿不是同一版本。

## 結論

目前的困惑來自把品質分數、計數分母、狀態、標籤、技術追溯資料都當成「metrics」。建議對使用者只呈現 **10 個核心數值（7 個 rubric 維度＋其加權總分＋Faithfulness＋Answer Relevancy）**；有已核准 oracle 時另報 **第 11 個 required-content coverage**。加權總分由前 7 項派生，不是第 8 個獨立品質構念。Red line、任務結果、可用狀態與未知數必須保留，但不是新品質分數。

保留 5 張表：總覽、回答、評分、claims、評分理由。計算與追溯仍完整保留在機器檔案；Excel 不展開每個 hash、token 欄位和內部 JSON。

## 現況一：有多少 sheets、欄位？

計數口徑：「欄位槽」是各表欄數相加；跨表的 answer_id 等重複計入。它不是不重複欄名數，更不是品質指標數。空表的 placeholder 欄也計入實際工作簿欄位槽。

### 現行 exporter

|工作簿|工作表|欄數|
|---|---|---:|
|單模型 results.xlsx|00_Overview / 01_Cases / 02_Turns / 03_Metrics|5 / 22 / 44 / 17|
|同上|04_Baseline / 05_Experiments / 06_Human_Review / 07_Stability|9 / 10 / 10 / 4|
|同上|08_Metadata / 09_Data_Dictionary|3 / 4|
|同上|Claims / Evidence / Relevancy / Requirements / Groups|14 / 17 / 18 / 14 / 18|
|多模型 results.xlsx|Matrix / Oracle_Coverage / All_Answers / All_Judgements|1＋Judge 數 / 4 / 34 / 24＋rubric 維度數|
|同上|Dimension_By_Judge / Self_Judging_Isolated / Measurement_Contract|5＋rubric 維度數 / 7 / 2|
|同上|Judge_Agreement / Red_Line_Agreement / Dimension_Statistics|10 / 6 / 9|
|同上|Claims / Evidence / Relevancy / Requirements / Groups|14 / 17 / 18 / 14 / 18|

單模型現行為 **15 表、209 欄位槽**；多模型在 5 Judge、7 rubric 維度下為 **15 表、202 欄位槽**。Evidence 表拆開本來有助追溯，但多處同時保留總覽、長格式 metric、scenario JSON 與投影表，造成同一事實重複呈現。

證據：`evaluation/xiaoan_eval/workbook.py:20` 定義 10 個舊表並加 5 個 detail tables；`:29` 定義 headers，`:175` 把 19 個 TURN_COLUMNS 加入原本 25 欄。`evaluation/xiaoan_eval/detail_tables.py:6` 定義 5 表、各表欄位及 TURN_COLUMNS。兩目錄這兩個檔案逐位元相同。多模型見 `evaluation_multimodels/xiaoan_eval/multimodel.py:1121`；追加及擴充欄位見 `evaluation/xiaoan_eval/scenario_analysis.py:323`。

### 實際工作簿抽樣（只讀欄名、行數）

|檔案|實際表數|欄位槽|重要差異|
|---|---:|---:|---|
|`evaluation/runs/2026-09-21-minimal32-integrated-report/results.xlsx`|10|109|02_Turns 仍 25 欄；03_Metrics 有 3,374 行、259 個不同 metric_id|
|`evaluation_multimodels/runs/2026-09-21-minimal32-five-self-included/results.xlsx`|15|160|85 答案、425 Judge 行；舊 Scenario_* 表，All_Answers 21 欄|
|`evaluation_multimodels/runs/report-labels-2026-09-22/results.xlsx`|18|205|增加 Scenario_Annotations、Router_Oracle_Drafts、Label_Completeness；仍非新 exporter 完整 schema|
|`evaluation/runs/unified-v1-offline-demo-20260922/measurement.xlsx`|6|61|offline demo 僅 1 個 cell，不代表完整真實矩陣|

「259」是該單模型樣本的 **metric_id 數**，絕不能宣稱有 259 個品質指標。例如它包含 `.status`、`.method`、`.seed`、`.evaluated_turns`、路由混淆矩陣格子，以及 `scenario.turns` / `scenario.claims` 等結構。原因是 summary 的所有 scalar leaves 都被轉成 metric rows：`evaluation/xiaoan_eval/report_model.py:472`。

### unified measurement.xlsx 是另一條輸出

它有 Cells、Inventory、Claims、Requirements、Conversations、Ablation 共 6 表；欄位由實際資料鍵動態聯集產生，沒有固定全表 schema。空表只寫 `No available observations`。demo 的欄數依序為 **22、7、13、12、6、1**。Cells 內 10 個 metric-related 欄位是 Faithfulness/Correctness 各自的 strict_rate、known_support_rate、known_coverage、unknown_n、eligible_n，並非 10 個獨立品質構念。

證據：`evaluation/xiaoan_eval_core/reporting.py:7` 與 `:62`。因此不能把 measurement.xlsx 出現過視為已整合進 results.xlsx。

## 現況二：哪些資訊混在一起？

|類型|代表內容|精簡方向|
|---|---|---|
|品質分數|rubric 七維、weighted score、不同 faithfulness、required coverage、AR|選定一個版本口徑，主表只放核心分數|
|必要解讀條件|可用樣本數、分母、UNKNOWN、自評隔離、oracle 審核|保留；不可只留平均分|
|分類與分析維度|router、task、topic、constraints、dialogue、risk|每回答存一次；是分組鍵，不是分數|
|重複派生值|automatic/human/final、同一 claim 多種支持率、同一總分多張匯總表|只在真的有複核或對照時提供額外視圖|
|運行資料|tokens、cache、queue、attempt、raw judge_text|移至運行檔；正文只在失敗分析時引用|
|追溯資料|response/context/snapshot hashes、版本、原始 prompt|保存 manifest 與證據包；Excel 只留短 ID/連結|
|專項實驗|baseline、ablation、judge agreement、stability、human calibration|按需產出，不佔每次常規測試的空白表|

目前已有正確的 AR 去重機制：`evaluation/xiaoan_eval/detail_tables.py:61` 以 subject/case/turn/answer hash/context hash 組合去重，標示 ANSWER_LEVEL；`:96` 用 answer_groups 彙總。重構應保留此語意，改為不可變 answer_id＋AR contract 作唯一鍵，而不是每個 Judge 各算一次。

## 提案：5 張可讀表，80 個欄位槽

以下是新 schema 提案，**尚未實作**。中文顯示欄名可以另外映射；穩定 machine key 如下。標籤可以用簡單分隔文字顯示，底層仍保留型別化值。

### 1. Overview：11 欄

`group_axis, group_label, subject_id, judge_id, metric, value, available_n, planned_n, unavailable_n, aggregation, note`

每列為一個分組的一項統計；`group_axis=overall` 表示總體。只預設展示整體及最差的有足夠樣本群組。AR 的 judge_id 固定為 ANSWER_LEVEL；不把多 Judge 的重複 answer 納入 AR 平均。缺測數和聚合方式與分數同列。

### 2. Answers：20 欄

`answer_id, subject_id, case_id, turn, user, answer, route, task_family, task, topic, constraints, dialogue, risk, annotation_status, answer_status, context_status, answer_relevancy, relevancy_status, analysis_ref, snapshot_ref`

一個 subject × case × turn × frozen generation 一列。多輪歷史按 case/subject/turn 重建。情境標籤附帶 annotation_status；草擬標籤不可默認成已驗證金標。`analysis_ref` 連到 AR 反向問題及相似度明細；`snapshot_ref` 連到當輪實際曝光上下文及版本清單。重跑結果不可覆蓋同一 answer_id。

### 3. Scores：24 欄

`answer_id, judge_id, rubric_status, faithfulness_status, primary_eligible, 基础能力, 行动赋权, 法律维权, 求助转介, 表达能力, 丰富性, 包容性与可及性, weighted_total, faithfulness, supported_claim_n, applicable_claim_n, unknown_claim_n, red_line, required_coverage, requirement_status, satisfied_requirement_n, applicable_requirement_n, unknown_requirement_n, task_status`

一個 answer × Judge profile 一列；profile 在 manifest 指明 rubric Judge 和 faithfulness Judge 的模型/版本。兩個 Judge 的執行狀態分開；一者失敗不吞掉另一者成功結果。required coverage 沒有已核准 oracle 時留空並標 NOT_EVALUATED。Counts 是分母/缺測保護，不是新品質分數。UNKNOWN 不可顯示成「unsupported 已確認」。明確選定 faithfulness 分母及零適用 claim 的處理，不同歷史算法不可靜默重標。

### 4. Claims：14 欄

`answer_id, judge_id, claim_id, kind, claim_text, answer_quote, applicable, verdict, evidence_layer, evidence_ref, evidence_quote, reason, status, evidence_detail_ref`

一個 claim × Judge 一列，所有 Judge 使用同一份 extraction 的 claim_id 與文字。主要證據有原文與層級可直接讀；多段聯合證據或長證據鏈在 evidence_detail_ref 連出的完整證據資料，不壓成巨大 JSON。不要為每段證據複製 claim 列而誤增分母。

### 5. Rating_Details：11 欄

`answer_id, judge_id, item_type, item_id, item_text, score, verdict, answer_quote, reason, status, evidence_ref`

item_type 限定 rubric / red_line / requirement；每一條評分或檢查理由一列。數值 rubric 放 score，其他放 verdict。報告能從問題找到具體扣分依據，不必讀 raw Judge JSON。證據不能只留一句「表現不好」，需指出回答片段及適用規則。

合計 **11＋20＋24＋14＋11＝80 欄位槽**。這比 15–18 sheets 容易定位，也不犧牲 answer、claim、reason、分母與缺測。版號、run ID、schema、模型設定與資料字典放在同目錄 manifest/schema 文件，工作簿以屬性或頂部說明連結它們，不需要獨立 metadata 表。長文字超過 Excel cell 限制時明確標示節錄並附完整文字連結；不得無提示截斷。

## 遷移檢查點

1. 同一批 frozen answers 不重跑 chatflow；先以離線 fixture 建新 schema。
2. 核對答案唯一性、Judge cells 完整性、7 維加權總分、紅線規則、缺測及 UNKNOWN，核對 Excel 與底層事實。
3. 確認 AR 的樣本數等於已成功完成 AR 的唯一答案數，不等於 Judge cell 數。
4. 確認每個 claim/扣分/需求判定都有可定位原文；所有統計可由明細重算。
5. 新表先平行輸出供人工比對，舊檔只讀保存；新舊分數口徑不相同者明確標版本，不製造虛假的進步幅度。

獨立 correctness、capsule ablation、agreement、calibration 仍有研究價值，但預設常規表不加對應整套欄位。當資源事實正確性或安全疑點需要調查時，再開專項評估與附錄。
