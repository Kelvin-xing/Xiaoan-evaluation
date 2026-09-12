# XiaoAn Agent 評估方法與兩套 evaluator 審閱

日期：2026-09-13。審閱對象：本機 `<workspace>/xiaoan` **當前工作樹**，包括未提交檔案；不是只看 HEAD，也不是對某次私有 run 的評分覆核。

配套文件：

- [八篇文章、原始來源、指標公式與限制](2026-09-13-rag-agent-sources.zh-HK.md)。這是方法研究正文；本文件是實作對照與改善設計。
- [可重跑的離線診斷腳本](2026-09-13-evaluation-audit-probes.py)。只使用合成資料、注入的假 runner/judge 和暫存 workbook，不呼叫外部模型。

> 後續實作：使用者已要求修改。本文保留修改前的審閱證據；目前修復、兼容性與仍待審閱的案例見 [評分契約 v2](../../evaluation/README/measurement-contract-v2.zh-HK.md)。不要把下列原始反例當成修改後現狀。

## 1. 審閱結論

目前框架的方向是合理的：有安全紅線、approved oracle、trace、內容快照、claim/evidence attribution、人工校準工具、版本與實驗控制。**主要不足已不是缺少更多指標名稱，而是同名指標的測量契約、執行分支和報表不一致，以及測試資料沒有提供足够 oracle。**

最優先修正：

1. 一般 pipeline 把部分執行失敗寫成品質零分，報表真的把它納入平均；不只是內部暫存值。
2. `PASS` 同時承擔「執行成功」「未觸發 gate」「品質合格」；低品質回答可以顯示 Quality verdict PASS。
3. 同一組維度分數，普通評估、matrix、suite 的總分有三種計算法；matrix 的 Markdown 和 Excel 更會顯示不同數字。
4. claim unsupported rate、空 route oracle、memory lifecycle 和 agreement 的邊界條件有可重現錯誤。
5. 現有案例數量不少，但 response/task oracle、記憶更新／隔離、工具結果與獨立危機標籤覆蓋不足；不能因已有對應函式就宣称已完成 agent 評估。

這次只新增研究及診斷文件，沒有修改 evaluator、rubric 或案例，沒有執行付費 API，也沒有推送 Git。

## 2. 方法總結：RAG 評估與 Agent 評估如何接起來

### 2.1 先定義評估對象，再挑指標

文章中的大量方法評估的是 `問題 → 檢索文件 → 回答`。XiaoAn 還有風險分級、路由、capsule、ground resolver、跨輪狀態和 output guard。工具型 agent 更有權限、工具副作用、環境狀態、停止條件。**RAG 指標只覆蓋其中一部分。**

| 層次 | 評估問題 | 必須收集的事實 | 不能推論的事 |
|---|---|---|---|
| 執行與可觀測性 | 完成了嗎？缺什麼？ | 預期/實際輪數、attempt、error、截斷、trace schema、時間、token | 成功回傳不等於答得好 |
| 安全與權限 | 有沒有不可接受行為？ | 紅線證據、危機 oracle、資料外洩、未授權工具副作用、guard 前後輸出 | guard 通過不等於所有危害均被測到 |
| 任務結果 | 使用者目標/本輪要求是否達成？ | 人工批准的必要行為、禁忌、可接受替代行為、外部狀態驗證 | LLM 自稱完成不等於世界真的改變 |
| 過程與路由 | 哪一步開始偏離？ | risk、route、candidate/selected/injected context、工具呼叫/結果、狀態差異 | route 合法或 ref 存在不等於選擇正確 |
| 證據與回答 | 忠實、正確、相關、完整嗎？ | 原子 claims、answer spans、context spans、reference facts、引用對應 | 忠實於錯誤資料仍可能事實錯誤 |
| 使用體驗 | 清楚、適切、尊重自主、可及嗎？ | 領域 rubric、使用情境、適用性、人工評分 | 冗長/溫暖不能補償錯誤或危害 |
| 穩定性與成本 | 重跑、對抗、負載下表現如何？ | 重複試驗、缺失率、tail latency、重試成本、樣本分層 | 單次高分不能代表可靠性 |

### 2.2 各類方法的實際操作

**確定性檢查。** 用程式檢查 schema、允許路由、必需步驟、工具參數、引用能否解析、權限及最終狀態。適合可明確定義的條件；自然語言是否有同理心、建議是否合乎情境不能簡化成字串包含。

**有標準答案的檢索評估。** 為 query 建立人工 relevance judgments，分別計算 Precision@k、Recall@k、MRR、AP/MAP、nDCG。保留查詢、corpus/chunk 版本、k、reranker 和 relevance 等級。沒有有序候選列表及標註，就不能把 resolver refs 包裝成 retrieval ranking。

**有/無 reference 的回答評估。** Faithfulness 對照實際上下文；correctness 對照獨立真值；relevance 對照問題；completeness 對照必要資訊集合。四者各有分母，不能用一個「grounded」分數替代。具體公式、Ragas 變體、AWS 官方尺度见配套來源研究。

**LLM-as-a-judge。** 先提供任務、rubric、資料時效、回答與必要證據；要求結構化輸出、原文定位、正負證據和不確定性。之後本地驗證 JSON、枚舉、span、ref、重複項及分數範圍。這只能排除格式/引用偽造，仍須人工 benchmark 驗證語義判斷。

**成對比較。** 固定同一輸入及可比條件，盲化版本名，隨機 A/B；保留 ties；安排相反順序重測。評的是版本間偏好，不能變成安全或品質的絕對合格證明。不能只把两段回答交给 Judge 而不提供用户需求。

**人工評估。** 用風險、類型、語言、長度、正負例分層，獨立標註後仲裁；凍結 gold 集，單獨留出未用於調 prompt 的測試集。量 Judge 的紅線 sensitivity/precision、逐維度誤差、claim extraction recall 和 evidence relation agreement；保留樣本數及信賴區間。

**線上/使用者評估。** 先影子測試，再小流量對照，觀察問題解决、重複求助、人工接手是否適切、退出是否順暢。家暴支持不應把對話越長、點擊越多、依賴程度越高當成功。真實安全改善需要另設研究，不能由離線 rubric 推導。

**對抗與擾動。** 測 context 有錯／過時／相互衝突、無答案、prompt injection、長對話、user 更正資訊、跨 session 污染、工具超時、部分成功和重試。不要求所有文字完全相同，要求應保持的安全/任務性質保持，應隨情境改變的行為確實改變。

**控制實驗。** 固定案例與快照，只改一個 hypothesis 相關變量，成對比較 case 層結果、guardrails、失敗率和成本；同一案例的多輪與多個 Judge 是相關觀測，不是獨立樣本。

## 3. 本地架構與目前資料覆蓋

### 3.1 實際流程

普通評估：`cases → runner → EvaluationPipeline → deterministic metrics + primary Judge (+ attribution/secondary) → case quality → report_model → workbook/report`。Suite 路徑另產生 `TurnDimensionFact/CaseScoreFact/ScenarioScoreFact`。

Matrix：`subjects × cases` 生成回答，回答綁定 answer ID，fan-out 給 Judges，保存 answer/judgement/cell checkpoint，產生 matrix 和分維度報表；可配置 attribution pass。Matrix 有自己的 Judge schema 和分數計算，並不是把普通 pipeline 完整運行五遍。

保留得好的設計：

- 普通單輪 Judge 的 0–3 anchored scores、紅線先判定、動態 focus 權重有明確程式實作。
- Matrix 對 invalid response/invalid Judge JSON 保留 `UNAVAILABLE`，而不是直接設品質零分。
- 有 immutable answer 關聯、checkpoint、bounded concurrency，以及 Judge retry 與 subject answer 的區分。
- attribution parser 驗證 answer/evidence spans，區分支持、部分支持、背景、矛盾、不支持；已有 policy applicability，非單純統計 ref。
- `calibration.py` 已有抽樣、benchmark freeze、盲化 review packet、span matching、agreement；不能把它描述為完全不存在。
- 既有實驗模組能限制註冊參數單變量變更；需要補強的主要是驗收與統計。

### 3.2 案例盤點（兩個目錄數量相同）

| 盤點項 | 每套數量 | 意義 |
|---|---:|---|
| YAML 案例 | 74 | 不是 74 個獨立生產流量樣本 |
| 對話輪次 | 217 | 同案例各輪相關 |
| oracle_provenance.status=reviewed | 74 | reviewed 不代表每個指標都有 gold |
| 明示 route_ids 的輪次 | 4 | 其餘 capsule_ids 不會自動變成 route_ids |
| 明示 safety_levels 的輪次 | 24 | 危機分類覆蓋遠少於全部輪次 |
| 明示 capsule_ids 的輪次 | 217 | 可做 capsule identity 檢查，不能代表回答正確性 |
| 非空 response_oracle | 0 | 當前標準案例未填必要 claims、goal、工具等此層欄位 |
| must_include / forbidden_behaviors | 各 24 | 可供 Judge 參考，不能當作已執行独立 outcome 測量 |
| memory checkpoints | 6，全部默認 use | 沒有現成 not_use/update/isolation/stale 專項 |
| 明示 maturity | 0 | parser 由 reviewed 推導 REVIEWED；不自動等於 APPROVED_AGGREGATE |

盤點範圍是兩個 `test-cases/*.yaml`，不包括 tests 內 synthetic fixtures、其他 suite 外部資料或私有 run。`cases.py:259` 定義 maturity 預設，`:332` 明確獨立解析 route_ids 和 capsule_ids。`TC-17` 有 4 輪，`TC-52` 有 2 輪；5×5×6=150 個 cell，但只有兩種案例、每個 subject 六個回答，並非 150 個獨立情境。只有這兩案的矩陣不能推廣到整個支援系統。

## 4. 已確認問題：按修復優先級

以下 P1 是會誤導合格／排序／缺失解讀，P2 是統計、診斷或擴展能力缺口。標記「重現」表示附帶脚本已執行；「靜態」表示讀過實際程式；「設計」表示建議，不是已證實某次 run 發生事故。共有程式兩邊相同時，以下主要指向 `evaluation/`。

### F01 / P1：operational failure 仍進入品質平均【重現】

位置：`evaluation/xiaoan_eval/pipeline.py:314`；`report_model.py:245`、`:369`。同份 pipeline/report_model 也存在 multimodels 的普通評估路徑。

當 `hard_gate_failed`、`run.status == error` 或沒有可用 qualities，pipeline 建立所有維度及 weighted_total=0 的 CaseScore。報表 `_case_row`、`_overview_rows` 按數值取分，沒有因 ERROR 排除。合成 timeout 實際輸出 `status=ERROR, quality=0, Overall score=0 AVAILABLE, Quality verdict=FAIL`。

影響：provider/解析問題降低模型品質平均，違反既定 UNAVAILABLE 契約；這與 matrix invalid JSON 的處理不同。branch 還會重設 red_line flags，應保留已觀察的安全事實而不是把它覆蓋。

修正：把 execution_status、safety_outcome、quality_status/value 拆開。未知品質設 null，安全違規仍保留 FAIL。全不可用的 run 不能顯示品質 0 或 Quality FAIL；應顯示 UNAVAILABLE/INCOMPLETE。驗收：成功分 3 加一個 timeout，品質平均仍 3，coverage=1/2，operational_failure=1/2。

### F02 / P1：PASS 並不要求品質達標【重現】

位置：`pipeline.py:587`；`scoring.py:51`；`report_model.py:377`。`quality_threshold` 主要参与是否請求第二 Judge（`pipeline.py:262`），不是 `_case_status` 的合格條件。

所有维度=1、無紅線、合法 trace 的合成回答仍得到 PASS，報表稱 Quality verdict PASS。1 的 anchor 明確表示嚴重缺失；即使可以把這個 PASS 定義為 execution PASS，報表標成 quality verdict 仍不成立。

修正：保留明確 `execution_complete`，另以預先批准的 quality threshold、逐維度最低標準和任務結果判定 release。未設定閾值時顯示 NOT_CONFIGURED，不能默認品質合格。

### F03 / P1：三個總分不是同一個量【重現】

位置：`scoring.py:32`、`:129`；`cli.py:430`；`evaluation_multimodels/xiaoan_eval/multimodel.py:239`、`:965`。

只給「行動賦權」3、其他維度0，focus=行動賦權：

| 路徑 | 公式 | 實際結果 |
|---|---|---:|
| 普通 score_case | 七維度，focus 權重×1.5後正規化 | 0.743119 |
| Matrix weighted_score | 七維度基礎權重，未讀 focus | 0.54 |
| Suite score_case_fact | 只取 focus 維度，再正規化 | 3.0 |

Focused score 可作另一個有用量，但必須另命名；不能讓使用者跨路徑比較「總分」。Matrix Judge request 也未提供 case.quality_focus。

修正：共用版本化 scoring contract，明示 scope、維度適用性、focus、權重和 turn/case 聚合。若三種都要保留，分别命名 `overall_dynamic_quality`、`overall_base_quality`、`focused_quality`。驗收同一輸入跨 CLI/API/Excel/Markdown 得同一指定公式結果。

### F04 / P1：Matrix Markdown 用 median，Excel 用 mean【重現】

位置：`evaluation_multimodels/xiaoan_eval/multimodel.py:1070`、`:1139`。維度區塊也應一併核對。

同一 subject/judge 三輪分數 `[0,0,3]`，Markdown 主矩陣=0.0000，Excel Matrix!B2=1。Markdown 卻標示 Weighted average，部分標題稱 Dimension averages。

修正：先建立唯一 MatrixSummary facts，再由兩個 renderer 讀同一結果。把跨輪、跨案例、跨Judge 的聚合順序分開；median 不應隱藏任何一輪紅線。驗收以含 outlier、多輪不同長度、缺失與 self rows 的合成資料對齊所有表格。

### F05 / P1：空 route oracle 被計成答錯【重現】

位置：`v3_metrics.py:190` 附近 `route_accepted.append(...)`；對照 `metrics.py:237` 的空 oracle SKIP。

`expected.route_ids=[]` 且實際 baseline，deterministic route 是 SKIP，但 summarize_v3 的 accepted_accuracy=0。現有217輪只有4輪明示 route_ids，因此不是罕見邊界。safety_accepted 也只有 sequence 判斷而沒有非空判斷，具有同類問題。

修正：只有非空且審核過的 accepted labels 進分母；零標籤→NOT_APPLICABLE 或 UNAVAILABLE。不要把 capsule_ids 偷偷當新 route gold，應先經案例審核。驗收空oracle的輪次不降低 accuracy，並報 excluded_reason=ORACLE_MISSING。

### F06 / P1：unsupported_claim_rate 用錯分子【重現】

位置：`v3_metrics.py:44`、`:249`。`score_claims` 的 fp 只計「不在 required 集的 unsupported extras」；summary 卻把 fp/全部claims 命名 unsupported_claim_rate。

只有一個 required claim、Judge 判 unsupported，結果 faithfulness=0、unsupported_claim_rate=0，同時出現完全不忠實與零不支持率。這不是合理的互補定義。

修正：支持數/所有可評 claims 用於 faithfulness；不支持數/所有可評 claims 用於 unsupported rate；矛盾另外計數。必要內容 coverage 用 stable gold claim ID + 語義對應，不要與 hallucination FP 混用。`correctness_f1` 目前只是 completeness_f1 alias，也應重命名或引入獨立 truth labels。

### F07 / P1：Memory schema 接受多類型，普通 evaluator 全當「必須使用」【重現】

位置：`cases.py:370`；`metrics.py:209`；matrix 的 `multimodel.py:651`。

普通 evaluate_memory_checkpoint 不讀 check_type。對 not_use，資料保留但 memory_used=false，本應滿足「不用」，卻 FAIL。Matrix 有按類型分支，但 state={} 時 use 和 isolation 會變 FAIL，retrieve 才 SKIP；缺 telemetry 被不同類型不一致地判定。

修正：統一 lifecycle evaluator：remember/retrieve/use/not_use/update/isolation/stale/unsafe 各有必需欄位、局部 oracle、N/A/缺失規則。缺 telemetry→UNAVAILABLE，不是 FAIL。memory_used 這個自報布林還不能證明哪個 fact 真的影響回答；需要 fact ID、retrieval/used spans，以及必要時行為對照。

### F08 / P1：Matrix 自評默認仍進主要分數【靜態】

位置：`multimodel.py:717` 默認 `isolate_self_judging=False`；`:962`；`cli.py:185`。`METHODOLOGY.md:126` 卻要求 self cells 不混主要排名。

agreement_report 一律排除 self；score summary 默認包括 self。同一報表的「品質」與「一致性」其實用不同評委母體。primary_denominator 的 self_judging_n 計所有 self，報表卻稱 isolated，亦可能誤導。

修正：默認主比較排除同模型自評、獨立展示 diagonal；記錄實際 excluded_n。再處理剩下每個 subject 評委集合不同的問題：使用共同外部 Judge panel 或交集分層比較，不能認為移除對角線後就完全公平。

### F09 / P2：退化資料的 alpha=1 掩蓋無法估計【重現】

位置：`methodology_metrics.py:377` 的 `_ordinal_alpha`、`:418` 的 `_nominal_alpha`。

所有 Judge 對所有項目都給3，或所有紅線皆false，expected disagreement=0；目前回傳1。可以另外說觀測一致率100%，但 alpha 的 `1−Do/De` 此時為0/0，不能當作充分驗證裁判可靠。

修正：alpha=null，reason=NO_LABEL_VARIATION；另報 exact agreement、positive/negative prevalence、可比較單元及 Judge 數。對紅線更要看人工 gold 的 sensitivity/precision，不能只看大量「無紅線」的一致。

### F10 / P2：Kendall W 插補與 Spearman 母體限制【靜態／設計】

位置：`methodology_metrics.py:208`、`:438`。W 先把缺失 cell 插成中位 rank，再算完整矩陣 W；程式沒有區分缺失到底是 self excluded 還是 provider failed，卻統一標 SELF_EXCLUDED_MIDRANK。這是有假設的 heuristic，不能稱為未插補的標準 W。

Spearman 跨 case/turn 的共同 cell 計算，可能反映哪些案例普遍容易，而不是同一情境下哪個 subject 更好。報告已標 DESCRIPTIVE_ONLY 是好的，但缺失機制與樣本母體仍要說清。

修正：完整共同 panel/共同 subject 子集的 W；不完整資料用有驗證的方法或不報。保留 ordinal alpha、逐case相關和一致率，報每個pair的共同n；按case做cluster bootstrap，不把所有cell獨立重抽。

### F11 / P2：Pairwise 有函式，但未具備完整評分上下文與版本勝率【重現／靜態】

位置：`methodology_metrics.py:102`、`:161`。呼叫搜尋顯示函式定義和 tests，兩個主要 CLI 未接入 run_pairwise_pass。

實際 provider request 只有左右 answer、case/turn ID、簡短 instruction和control hash；不含user/history/rubric/evidence原文。hash 不會讓Judge知道這些內容。summary主要是left_wins/right_wins；隨機顯示位置下，它不是A版本/B版本勝率。每次只跑一個方向，也不保證有完整反序重測。

修正：immutable answer bundle 綁 user/history/必要evidence/rubric，同一控制組校驗；用answer identity歸因勝負，位置結果另外報。排程平衡 A/B與反序子集；語義無效回應→UNAVAILABLE。接入獨立命令和報表後才稱有可用 pairwise pipeline。

### F12 / P2：Agent goal_completion 與 efficiency 命名大於證據【重現／靜態】

位置：`v3_metrics.py:229`、`:288`；`pipeline.py:411`。

goal_completion_rate 計 `expected_goal == actual_goal`，因此 expected=false、actual=false 也=100%。它是 goal-status agreement；如果期待不完成危險任務，可以叫task-outcome conformity，但不能叫任務完成率。steps 指標為 min(1,max_steps/steps)，所有未超budget的過程都是1，未條件化任務成功；快速失敗也可能高效率。missing invalid_calls/retries/timeouts 被預設0。

修正：拆為desired_outcome_pass、verified_goal_completed、success_conditioned_cost/steps、budget_compliance。外部工具完成以模擬環境或實際授權狀態驗證。缺telemetry保留null。對XiaoAn限定為「本輪支持任務」完成，不推論使用者現實處境改善。

### F13 / P2：工具匹配只覆蓋較簡單的規格【靜態／設計】

位置：`v3_metrics.py:383`。目前以工具名稱 multiset 算TP/FP/FN、同名第一個配對的arguments exact equality、工具名稱exact sequence。

不足：兩次同名工具不同參數會被貪婪配對錯置；等價可交換工具序列被判失敗；沒有驗證結果、權限、重試後重複副作用、停止条件。沒有設定工具oracle時，空expected和空actual還可能進exact_sequence denominator。

修正：oracle宣告strict order或partial order、必要/可選/禁止工具、參數語義validator、pre/postcondition與idempotency。先界定產品是否真的使用外部工具；未使用時NOT_APPLICABLE，不為好看硬加tool accuracy。

### F14 / P2：Claim extraction 的漏判不能靠ref驗證發現【設計】

位置：`attribution_judge.py:79`、`attribution.py:22`。本地span驗證能證明「這個片段存在」，不能證明Judge已抽出所有重要主張。漏抽最危險一句會縮小分母、抬高faithfulness。`PARTIAL=0.5` 是產品計分選擇，不是自然常數。

目前overall support 允許 CURRENT_INPUT/PRIOR_ASSISTANT 等層支持；使用者自述能支持「使用者曾這樣說」，不能驗證外部法律事實。各層support也可以重疊，不能相加當內容來源百分比分解。

修正：人工標註claim inventory、extraction recall、false splits/merges；獨立報source-grounded factual support、conversation consistency和policy compliance；高風險claim權重另經批准。不要用support總分替代真實正確性或因果歸因。

### F15 / P2：校準工具已存在，但不等於這一組Judge已校準【靜態／設計】

位置：`calibration.py:46`、`:142`、`:437`；matrix row及runtime。

既有工具值得保留；本次沒有讀私有benchmark或run，因此不能斷言沒有人工成果，也不能宣稱目前所有provider/model/prompt組合已validated。主要矩陣分數不會因缺benchmark自動變成已校準的證據。

修正：每run綁judge/model/prompt/rule/schema版本、benchmark hash/日期/n、held-out誤差、紅線檢出率、claim/span agreement與漂移狀態。未校準仍可探索性顯示，但明確 `VALIDITY_NOT_ESTABLISHED`。secondary Judge optional可以保留，不强迫每個run都雙評；正式release必須有獨立人工/已批准證據。

### F16 / P2：0–3 rubric 缺情境適用性與逐維度anchors【靜態／設計】

位置：`evaluation/ratings rule.yml:6`、`:33`、`:63`。

七維度共用抽象0–3 anchors，positive/negative條目多而非互斥；未定義「出現哪種缺口必須降至哪一檔」。法律維權要求法律與案例，求助轉介要求渠道時間，豐富性鼓勵跨維度；情緒支持或短危機回應並非每次都應包含這些內容。這會鼓勵冗長、無需求法律資訊或機械提問。

RL-02「以lawwiki收錄版本為准」「無法判断過時時按不一致處理」，把時效不確定與錯誤混在一起；法律維度又說相似問題可以「未達紅線程度」，沒有severity邊界。RL-03與弱化越界承諾也需例子。

修正：不直接改動使用者既定七維度/權重，而先加入dimension applicability矩陣、任務條件、每檔正反例、紅線邊界與UNCERTAIN→人工覆核。法規/資源truth需jurisdiction、有效日期、版本和核驗證據；本報告不對任何具體法律內容作法律結論。

### F17 / P2：信賴區間和案例聚合缺乏獨立單元控制【靜態／設計】

位置：`v3_metrics.py:445`；matrix報表聚合。

bootstrap目前按turn布林值重抽；單例回傳[x,x]，全成功小樣本也退化為[1,1]。這不是已確證風險為零。Matrix按有效turn聚合，較長案例影響更大；可用Judge和缺失情境也可能因subject不同。

修正：預先定義case-macro vs turn-micro，兩者分開展示。版本比較用共同case、cluster bootstrap及paired delta；rate用合適的二項區間作補充。零事件/n不等於0風險；例如獨立伯努利假設下常用rule-of-three只是近似上界，不能把相關多輪套入。缺失要按provider/subject/judge/case原因分層，設最低coverage，必要時報不可比較。

### F18 / P2：複製核心造成兩套實作漂移【靜態】

`xiaoan_eval` 共有40個同名Python檔案內容完全相同；另外5個同名檔不同，evaluation另有checkpoint.py，matrix另有multimodel.py。這次發現的memory/schema/score/report差異已展示維護風險。

修正：先共用或建立一致性檢查的純核心（rules/scoring/metrics/status/summary/schema），保留provider與matrix orchestration adapter。不要先全面重寫；先用上述反例鎖定契約，再逐步去重。独立release也要跑同一組contract fixtures。

## 5. 應建立的 metric contract

每項至少具有：`metric_id/version`、測量對象、unit、required_inputs、oracle版本及批准狀態、eligibility、numerator/denominator、missing/NA policy、方向、範圍、聚合順序、threshold及依據、evidence refs、judge/程式版本、uncertainty。不是只在README寫一段定義。

| 指標 | 建議單元／分母 | 應如何解讀與處理缺失 |
|---|---|---|
| execution completion | 完成全部預期輪次的case / attempted cases | 故障保留類型、attempt與成本 |
| quality coverage | 可正式評品質的case / attempted cases | 與條件式品質平均並列 |
| red-line incidence | 已可評case中至少一輪違規 / 可評case | 另列每RL與危機cohort，不能用median抹掉 |
| red-line judge sensitivity | 人工陽性中Judge檢出 / 人工陽性 | 无陽性→UNAVAILABLE，不是100% |
| route acceptance | actual屬於非空approved accepted set / eligible turns | 空oracle排除；registered validity另算 |
| capsule delivery | 正確選中且所需內容成功注入 / eligible turns | 與semantic support分開 |
| evidence coverage | required facts被context支持 / required facts | context與reference都要有版本；不強制恢复已停用的ground_ref oracle |
| faithfulness | context-supported extracted claims / eligible extracted claims | 同列extraction coverage、unsupported、contradiction |
| factual correctness | 人工/權威reference支持的claims與必要內容 | 不依賴模型自身的retrieved corpus作唯一真值 |
| task outcome | 通過所有必需條件且無禁止行為的case / eligible cases | 多個可接受方案用集合/條件，不拘一段gold文字 |
| weighted quality | 明定適用維度、focus、權重後的case分數 | 不能補償red-line；與focused score不同ID |
| memory lifecycle | 每一type自身可評checkpoint | 正確不用也是成功；未知telemetry非失敗 |
| tool outcome | 可評工具任務的pre/postcondition | syntactic call match只是子指標 |
| cost/latency | 每case或每verified success | cold/warm、subject/judge、重試、p50/p95/p99分開 |
| pairwise preference | A wins / (A wins+B wins)，ties單獨報 | 主版本identity，位置偏差另報；不默認tie半分 |
| judge agreement | 同一unit的多Judge觀測 | descriptive；無變異/不足/缺失需理由 |

推薦狀態資料結構（設計，不是已修改）：

```yaml
metric_id: answer.faithfulness
metric_version: v2
unit: answer_claim
status: AVAILABLE  # UNAVAILABLE / NOT_APPLICABLE / NOT_RUN
value: 0.8
numerator: 8
denominator: 10
expected_units: 12
eligible_units: 10
excluded_by_reason: {JUDGE_UNAVAILABLE: 2}
oracle_version: reviewed-claims-v1
evidence_snapshot_hash: sha256:...
judge_contract_hash: sha256:...
aggregation: claim_micro
threshold: null
validity_status: NOT_CALIBRATED
```

安全拒答、該澄清時澄清、尊重不聯絡外部資源的選擇，都可能是任務成功；須在oracle定義，不能把「沒給更多資訊」一律當不完整。

## 6. 如何把分數用來改善 Chatflow

| 症狀 | 先檢查 | 可測試hypothesis | 尚不能斷言 |
|---|---|---|---|
| 可用率下降 | provider/timeout/truncation/schema | 參數相容、重試、併發或token上限 | 模型語義能力變差 |
| 危機oracle不符 | safety輸入與分級trace | 危機門檻/提示/上下文截斷 | composer一定有錯 |
| route錯，輸入及risk正確 | router候選、state、TTL | eligibility、activation threshold | 增加RAG top-k就能解決 |
| route對，內容未到 | capsule loader、ground resolver、snapshot | 解析/注入故障 | recall低必定是embedding問題 |
| context缺必要事實 | corpus覆蓋與相關性標註 | 修資料、解析、檢索或排序 | prompting足以修正來源缺漏 |
| context正確但回答不支持 | claims、evidence、prompt順序 | composer citation/context use | 僅靠ref數證明模型忽略了哪段 |
| 事實正確但不可行 | user constraints與rubric applicability | action planning/限制辨識 | 多給資源就更好 |
| 記得但不該用仍使用 | session、memory read與answer | eligibility/expiry/isolation | memory retention高就是好 |
| 分數提高但Judge也換了 | measurement hash、calibration | 固定Judge重評舊/新immutable answers | 產品真的改善 |

因果證據應来自控制實驗，例如固定輸入、模型、案例和其他context，只移除特定capsule内容，觀察**預先指定**的必要行為及安全guardrails差異。單純「有這個ref而且答案提到了」只能證明可追溯支持，不證明該來源是生成原因。內容可能在prompt、wiki和history重複，更不能做唯一來源百分比分攤。

## 7. 實施順序與驗收

### 第一批：先修測量錯誤，不改模型

- F01/F02狀態及quality eligibility；F03/F04同分同表；F05/F06分母；F07memory缺失。
- 用附帶反例擴充真正測語義契約的測試，並在兩個project運行；測試期待應由測量規格決定，不能只assert目前函式輸出。
- 不要拿修正前後的舊總分直接宣稱模型改善。先在同一批immutable answers上重評，記為measurement-version change。

### 第二批：把案例變成可判定的任務

- 每case補必要行為、禁止行為、可接受替代、適用維度、風險cohort、時效/地區、oracle來源與審閱者。
- 對現有217輪逐一决定哪些需要route/safety/response oracle；未標註先排除，不自動生成人工已批准標籤。
- TC-17：可用「處理疑似監控前確認安全限制」「不把可能引發風險的設備變更當唯一無條件答案」「尊重使用者對風險的描述」作**待領域審核**行為候選；本報告沒有把它們直接寫入gold。
- TC-52：測不認同自責/貶抑、對挑釁式自我辱罵仍維持尊重、適量支持且不强推行動；加變體看是否只是背到某句模板。
- 補無答案/衝突資訊、跨輪更正、not_use、update、isolation、stale、prompt injection與partial failure，維持小型smoke與較大回歸集分離。

### 第三批：裁判有效性與跨模型公平性

- 凍結分層人工benchmark，雙人獨立標註/仲裁，保留holdout；校準紅線、七維度、claim extraction和evidence relations。
- 主要comparison使用共同Judge與共同case；self diagonal分開；missing原因和最低coverage可見。
- 實作有完整輸入的pairwise命令、identity勝率與反序測試；使用case層CI。
- 預先登記改善target與non-target guardrails。若僅兩個案例，結論限於兩案，不做總體模型排名。

### 第四批：整合核心與日常回歸

- 共用scoring/status/summary核心與gold fixtures；兩個獨立交付目錄都驗證。
- 報表至少呈現：run completion、eligible coverage、red-lines、task outcome、逐維度、route/ground/attribution、memory、成本、Judge validity、版本差異與可重現證據。
- 維持既有 `results.xlsx + report.md` 的使用入口；不用再增加一堆使用者必須拼接的中間檔。私有trace仍按現有邊界管理。

## 8. 驗證、限制與重跑方式

已運行現有完整測試（自動pytest插件停用）：

| 目錄 | 結果 |
|---|---|
| evaluation | 227 passed，18.75秒 |
| evaluation_multimodels | 267 passed，21.46秒 |

测试通過只證明現有assertions滿足；本報告的反例同樣在兩套實作重現，顯示需要補的是指標語義的驗收。

```bash
# 任意cwd皆可；腳本會切到指定project，兩套需分開process避免同名package快取。
/Users/mingjiexing/anaconda3/bin/python3 <workspace>/xiaoan/docs/research/2026-09-13-evaluation-audit-probes.py <workspace>/xiaoan/evaluation
/Users/mingjiexing/anaconda3/bin/python3 <workspace>/xiaoan/docs/research/2026-09-13-evaluation-audit-probes.py <workspace>/xiaoan/evaluation_multimodels
```

關鍵觀察：error quality=0並進overview；低分quality=1仍PASS；not_use被判fail；unsupported required claim給unsupported rate=0；空route oracle accuracy=0；false/false goal給completion=1；常數alpha=1；動態/base/focus總分0.743119/0.54/3；matrix [0,0,3] Markdown=0而Excel=1；缺memory telemetry use/isolation=fail。

限制：沒有執行真實模型、沒有讀私有runs或人工標註內容、沒有驗證外部法規時效、沒有重新評分既有答案。來源可讀性和逐篇細節以配套來源文件為準。`RTK.md` 在根目錄不存在，本次沒有可讀的該檔指令；已遵守可取得的AGENTS範圍與保留工作樹要求。文中程式行號是本次審閱定位，後續工作樹修改可能使行號移動。
