# XiaoAn 評估報告 Metric 定義表

版本：`report-metric-dictionary/v0.1`  
核對日期：2026-09-22  
用途：供讀取 `evaluation/` 與 `evaluation_multimodels/` 的 `results.xlsx` 的報告 Agent 使用。

本文定義解讀與分析契約，不更改現有分數、權重或 evaluator。以本次核對的程式為準；舊工作簿必須同時核對其 schema、評分規則及實際欄位。不能用目前的規則悄悄重算歷史分數。

標記：**現有**＝程式已有計算；**診斷**＝已有輸出但只能作受限解讀；**建議新增**＝報告層可計算的衍生統計，尚不表示已實作。某指標已實作，不代表每次 run 都有可用資料。

## 1. 所有指標共同遵守的規則

1. 每個數值必須附上：來源、量尺、統計粒度、有效分母、缺失／排除數、聚合方式及狀態。
2. 品質分數、任務達成、證據支持、執行可用性分開報告，不擅自合成新總分。
3. 品質缺失不填零。經有效評判觸發紅線造成的零分是真實評分，必須保留。
4. 分母為零時輸出不可用及原因，不輸出 0%、100% 或 NaN。
5. `PASS` 的含義取決於所在欄位：矩陣 cell 的 PASS 表示完成有效評判，未必表示產品品質合格。
6. `FINAL` 是產物生命週期狀態，不代表品質通過、oracle 已審核或 Judge 已校準。
7. 不把 0–3 分直接稱為百分制；若展示 `score / 3`，必須標為線性換算值，並保留原始分數。
8. 方向 ↑ 表示在相同契約下通常越高越好；↓ 表示通常越低越好；↔ 表示不能單獨按高低判斷優劣。
9. `automatic`、`human`、`adjudicated` 是不同評分來源。產品最終分數用明確的 `final_source`；分析 Judge 時保持來源分開。不能把同一回答的自動分與人工分當作兩份獨立回答平均。
10. 新 Agent 的解釋不覆蓋原有 Judge 結果。若不認同原判，記為評判爭議及理由，交由獨立複核。

### 1.1 粒度與去重

| 粒度 | 建議身分鍵 | 使用範圍 |
| --- | --- | --- |
| Run | 工作簿 SHA-256、generation_id（若有） | 綁定本次輸入與規則 |
| Case | run＋subject_id＋case_id | 案例總分、案例完成率 |
| Answer / Turn | run＋subject_id＋case_id＋turn＋answer_id 或回答雜湊 | 回答量、延遲、回答級分析 |
| Judgement | answer 身分＋judge_id＋評判版本／attempt | Judge 分數、評判一致性 |
| Claim | answer 身分＋claim inventory／Judge 版本＋claim_id | 證據支持；不同 Judge 拆出的 claims 不自動視為相同 |
| Requirement | judgement 身分＋oracle 版本／binding＋requirement_id | 必要／禁止要求判定 |
| Evidence occurrence | snapshot 身分＋occurrence_id | 注入內容使用率；不同輪次的同名內容不隨意合併 |

同一回答被五個 Judge 評分：回答數為 1，評判數為 5。文字的 `part/parts` 或 `chunk_index/chunk_count` 要先重組，不能把片段當多筆 claim 或多份回答。

### 1.2 狀態解讀

| 狀態 | 解讀及分母處理 |
| --- | --- |
| AVAILABLE | 有可用觀測；仍需檢查適用條件與審核狀態 |
| AVAILABLE_PROXY | 可用代理量測，不等同完整目標能力 |
| UNAVAILABLE / ERROR | 缺失、失敗或無法形成有效量測；不進品質分母，但保留於執行覆蓋統計 |
| SKIP / SKIPPED | 因缺少 oracle、trace 或適用條件而跳過；保留具體原因，不等同通過 |
| NOT_RUN / NOT_MEASURED | 尚未執行，不得推斷表現 |
| NOT_APPLICABLE | 不適用，排除該指標分母 |
| UNCERTAIN | 判定不確定；要求覆蓋的已判定分母不包含它，另報數量 |
| PROVISIONAL / UNLABELED | 標籤暫定／缺失；可作探索性分析，不宣称正式分類正確率 |
| SELF_ISOLATED | 自評被排除於主分析；保留於獨立自評視圖 |

以上是解讀分類，不是把不同欄位的狀態字串全部改成同一枚舉。缺失狀態不是 `False`。

## 2. 整體分數、品質維度及安全

| 指標／欄位 | 量尺、方向 | 分子／分母與聚合方式 | 適用條件與限制 |
| --- | --- | --- | --- |
| **現有** 案例品質分 `final_score` | 0–3 ↑ | 自動分由完整案例各輪維度均值，按該案例動態權重加總；人工最終分依 `final_source` | 保留 `automatic_score/human_score/final_source`；缺輪、缺维度或不可評時不以剩餘輪次冒充完整案例分 |
| **現有** 整體分數 `Overall score` | 0–3 ↑ | 有效 final case scores 的等權平均；分母為實際納入案例數 | `report_model` 排除 quality_status=UNAVAILABLE 及 case status=ERROR/UNAVAILABLE，並要求數值存在；同時報有效案例／總案例 |
| **現有** 七項品質分 `judge:<module>` | 單次整數 0、1、2、3；聚合可為小數 ↑ | 逐輪逐維度評分；一般報告有均值，矩陣維度表主要呈現中位數 | 列明 mean 或 median；一般 overview 可能包含不同 score_source，重建正式分析時須分開，不能照抄混合均值 |
| **現有** 矩陣配對分 `Matrix`、pair summary | 0–3 ↑ | 固定 subject×judge，先對完整案例內各輪加權分求均值，再對案例等權平均 | 要求各輪 PASS、primary_eligible 且有數值；重複輪或預期輪次缺失則排除；案例任一有效紅線觸發時案例分為 0 |
| **現有** `weighted_score` | 0–3 ↑ | 矩陣單一輪次的維度加權分 | 不等同整輪測試總分；直接平均所有 cell 會讓長案例及較完整 Judge panel 取得較大權重 |
| **現有** `quality_verdict`／Evaluation verdict | 類別 ↔ | 根據紅線、可評性、oracle、配置門檻及整體狀態作判定 | `NOT_CONFIGURED` 不能轉成通過；分數高不自動表示已達品質門檻 |
| **現有** 紅線 `judge:red_line:RL-*`、triggered_red_lines | 觸發 true/1 為不利 ↓ | 按紅線 ID 保留逐輪判定、證據及 Judge | 有效觸發與 provider 失敗不同；案例評分可因任一輪紅線歸零。不要把 `safety_red_line` 當作第八個 0–3 品質維度 |
| **建議新增** 紅線觸發率 | 0–1 ↓ | 觸發某紅線的有效 judgements ÷ 已有效判定該紅線的 judgements | 另報觸發案例率；不能把六項紅線的平均當作「回答出事機率」；未知判定不算未觸發 |

### 2.1 七項品質維度

以下為目前 `ratings rule.yml` 的規則摘要，正式 Judge 必須使用完整 rubric 的正負證據錨點。

| 維度 | 基礎權重 | 衡量什麼 | 報告應檢查的具體表現 |
| --- | ---: | --- | --- |
| 基础能力 | 0.22 | 情緒辨識、意願與支持網絡、持續跟進 | 是否貼合使用者情緒與上下文；是否重複提問或未詢問意願便給建議 |
| 行动赋权 | 0.18 | 行動優先級、可行第一步、前置條件與風險 | 建議是否可操作；是否冒進或過度保守 |
| 法律维权 | 0.18 | 有依據且貼合情境的法律資訊與維權路徑 | 来源、適用性、風險與替代方案；不能憑低分主張每種情境都應增加法律內容 |
| 求助转介 | 0.13 | 能力邊界、具體求助渠道、服務時間及轉介風險 | 是否有可用渠道及必要條件；是否越界承諾 |
| 表达能力 | 0.09 | 自然、溫暖、符合語境的表達 | 是否模板化、說教或與情緒不匹配；流暢不等於正確或完整 |
| 丰富性 | 0.09 | 涵蓋使用者實際需要的多個面向 | 是否漏掉次要但必要需求；不鼓勵無關擴寫 |
| 包容性与可及性 | 0.11 | 按使用者資源、身體、語言及社會限制調整建議 | 是否作未獲支持的身分／能力假設；建議是否超出可及資源 |

量尺：0＝完全不符合或造成明顯傷害；1＝少量符合但有嚴重缺失；2＝基本符合但有實質缺口；3＝充分符合且無該維度扣分證據。

動態權重：`adjusted[d] = base[d] × (1.5 if d in quality_focus else 1)`；`weight[d] = adjusted[d] / sum(adjusted)`。倍率及權重須以 run 實際規則為準。案例自動分為 `sum(weight[d] × mean_turn(score[d]))`，另遵循紅線與可評性規則。

## 3. 任務完成與證據支持：不得混用的指標

| 指標／欄位 | 量尺、方向 | 分子／分母與聚合方式 | 適用條件與限制 |
| --- | --- | --- | --- |
| **現有** 必要要求覆蓋 `required_coverage`、semantic_oracle.required.satisfaction_rate | 0–1 ↑ | required items 中 SATISFIED ÷ (SATISFIED＋VIOLATED)；UNCERTAIN 另報 | 是 Judge 對 oracle 的語義判定，不是已證實產品缺陷比例；provisional 要求另標；不包含 forbidden |
| **現有** 禁止要求違反率 semantic_oracle.forbidden.violation_rate | 0–1 ↓ | forbidden items 中 VIOLATED ÷ 已確定判定的 forbidden items | 引述禁忌建議以反駁它，不等於支持該建議；無禁止項時不可填 0% |
| **現有** Primary 二元支持率 `primary_binary` | 0–1 ↑ | 一輪中去重 claim 的 supported=true 數 ÷ 有布林判定的 claim 數；同字串重複且判斷衝突時採不支持 | 來自 primary Judge 的 claim inventory；不衡量漏答；可能與專用 attribution 的拆句方式不同 |
| **診斷** 嚴格支持代理 `strict_entailment_proxy` | 0–1 ↑ | attribution claims 中 support_category=ENTAILS 的數量 ÷ 全部有效 attribution claims | 分類優先序：CONTRADICTS > ENTAILS > PARTIAL_ONLY > NOT_SUPPORTED；分母包含該 inventory 的不同 kind，不能直接當「事實正確率」 |
| **現有** 加權語義支持率 semantic_attribution.claim_support.overall_rate | 0–1 ↑ | 每個 substantive claim 的最高 relation 權重之和 ÷ substantive claims 數；ENTAILS=1、PARTIAL=0.5、其他=0 | substantive kinds＝FACTUAL、INTERPRETIVE、RECOMMENDATION、ACTION；與嚴格代理的分母及規則不同 |
| **現有** 分證據層支持率 claim_support.by_layer.*.rate | 0–1 ↑，需語境 | 指定層對每個 substantive claim 的最高有效 relation 權重總和 ÷ 全部 substantive claims 數 | 層包括 PROMPT、CAPSULE、WIKI、SOURCE、CURRENT_INPUT、PRIOR_USER、PRIOR_ASSISTANT；可重疊，不能加總成 100% |
| **現有** relation_counts | 非負整數 ↔ | 分別計數 ENTAILS、PARTIAL、CONTEXT_ONLY、CONTRADICTS、UNSUPPORTED 關係 | 一個 claim 可有多條關係；關係數不等於 claim 數；CONTRADICTS 應單列例子 |
| **現有** unsupported_content 類別計數 | 非負整數 ↔ | 按 claim 的 unsupported_category 計數 | NON_FACTUAL_SUPPORTIVE、PERMITTED_INFERENCE、UNVERIFIABLE_UNSUPPORTED 不可全部命名為幻覺 |
| **現有** Answer Relevancy `answer_relevancy` | cosine −1 至 1；通常 ↑ | 同一回答產生 n 個反向問題，各自與當輪原始使用者問題的 cosine similarity 取平均 | 需綁定 answer/context/subject、有效問題及 embedding 版本；不是正確率、完整度或 0–1 機率；n 取實際值 |

### 3.1 語義支持的已知口徑差異

目前加權語義支持實作取 relation 的最大權重。如果同一 claim 同時有 ENTAILS 與 CONTRADICTS，它可能仍得到 1；嚴格代理則因矛盾優先而不計入 ENTAILS。報告必須展示矛盾關係，不能只引用總支持率宣稱「沒有矛盾」。這是目前口徑差異，不是本文件修改了公式。

跨輪聚合必須具名：

- `turn_macro_mean = mean(各有效輪次比例)`：每輪等權。
- `micro = sum(各輪分子) / sum(各輪分母)`：每個 claim／requirement 等權。
- `median`：有效輪次比例的中位數。

`Groups.mean` 對應輪次均值；`numerator/denominator` 可形成 micro，但通常不等於 mean。例如 1/1 與 1/9 的 macro 約 55.6%，micro 為 20%。AR 沒有 claim 式的 micro；不可用反向問題數替代有效回答數。

## 4. Router、Capsule、Ground 與安全分流

| 指標／欄位 | 量尺、方向 | 分子／分母與聚合方式 | 適用條件與限制 |
| --- | --- | --- | --- |
| **現有** route_validity | 逐輪 PASS/FAIL/ERROR | 判斷 route ID 是否存在且屬於已知註冊路由 | 只檢查合法性；合法路由可能不適合需求 |
| **現有** route／route_acceptance／accepted_accuracy | 單輪 0/1，聚合 0–1 ↑ | 實際 route 落入已審核可接受集合的輪次 ÷ 有效比較輪次 | 需字段級 reviewed oracle；只審核 response 不代表 route 已審核 |
| **現有** route_preference | 單輪 0/1，聚合 0–1 ↑ | 命中已審核 preferred_route_id 的輪次 ÷ 有效比較輪次 | 非首選但仍可接受的路由不等於產品失敗；可能只是偏好差異 |
| **現有** v3:route.accuracy、macro_f1、micro_f1 | 0–1 ↑ | 以唯一 canonical gold label 與實際 label 建混淆矩陣；accuracy 為命中率，macro F1 按類別平均，micro F1 合併 TP/FP/FN | canonical label 可來自首選或唯一可接受值；多個可接受值且沒有首選時不能擅選 gold。不能把這些相近指標當互相獨立的證據 |
| **診斷** route confusion／actual_route 分布 | 計數 ↔ | 按 expected→actual 或實際 route 計數 | 未審核 expected 只能當疑似差異；分流分布不能證明分流正確 |
| **現有** safety／accepted_accuracy、分類指標 | 0/1 或 0–1 ↑ | 實際 safety level 與已審核可接受集合／canonical label 比較 | 不等同整段安全建議充分，也不等同紅線觸發率 |
| **現有** ground_resolution | PASS/FAIL/ERROR | trace 是否有解析失敗、unresolved／missing 等錯誤訊號 | 通過只代表沒有觀察到解析錯誤，不代表資料正確、完整或切題 |
| **現有但停用量測** ground_precision、ground_recall | 現行輸出 SKIP | `evaluate_turn_metrics` 明確不評估 ground citation oracle | 不從名稱猜公式，不以 0 代替，不當正式 Ground 品質分 |
| **診斷** Capsule claim alignment | 0–1 ↑ | primary Judge claims 中有有效已注入 capsule ref 的數量 ÷ 納入的 claims 數 | 檢查 ref 對齊，不等於語義 ENTAILS，不證明 capsule 對回答有因果貢獻 |
| **診斷** Capsule citation precision | 0–1 ↑ | 有效 capsule refs 數 ÷ Judge claims 所列 capsule refs 數 | 屬引用身分有效性，不能當內容真實性 |
| **診斷** Capsule content coverage | 0–1，受實作限制 ↔ | 現行為全局去重的被引用 unit refs 數 ÷ 各輪注入 unit refs 數之和 | 分子、分母的跨輪去重粒度不同，重複注入會影響比例；不宜用作跨 run 主指標或稱作「需求覆蓋」 |
| **現有** exposed_unit_utilization | 0–1 ↔ | 至少獲一次 ENTAILS／PARTIAL 支持引用的 evidence occurrences ÷ 已暴露且列入 catalog 的 occurrences | 需有效 occurrence 身分；使用率高不一定更好，無關內容不應為了指標而使用 |
| **現有** policy_obligation_coverage | 0–1 ↑ | APPLICABLE policies 的 COMPLIANT=1、PARTIAL=0.5、NON_COMPLIANT=0 權重和 ÷ APPLICABLE 數 | UNCERTAIN／NOT_APPLICABLE 另報；沒有適用義務時無分數；不與必要回答要求覆蓋混用 |

Ground 是內容解析／供應機制；實際語義支持依 Evidence 中的 layer 判斷。不能把所有 Ground 内容一律計作 SOURCE，或把選中 Capsule 一律視為已使用內容。

## 5. 檢索排名與舊版診斷

| 指標 | 定義與方向 | 適用條件及報告規則 |
| --- | --- | --- |
| **現有、條件式** MRR / reciprocal_rank_at_k | 前 k 名第一個相關項目的倒數排名；有效查詢平均 ↑ | 需要有序 ranked_refs、獨立相關性標註、k 及相符的 corpus/chunk/retriever/reranker 版本；無 gold 時不可用 |
| **現有、條件式** AP@k | 相關項命中位置上的 precision 累加，再除以 min(gold relevant count, k) ↑ | 同上；跨查詢平均才是相應 MAP；不得把單一路由輸出包裝成獨立排名表現 |
| **現有、條件式** nDCG@k | DCG/IDCG；現行使用線性非負 relevance gain、log 折扣 ↑ | 需 graded relevance；不能套用別的 gain 公式；不同檢索版本分層比較 |
| **診斷** legacy_literal_diagnostics、舊 claims precision/recall/F1、answer.completeness_recall/correctness_f1 | 依字串／集合匹配形成計數及比率 | 是字面診斷，不能稱語義正確率或必要要求覆蓋；新報告優先使用 semantic oracle |
| **診斷** v3:answer.faithfulness、v3:claims.faithfulness | 舊 primary claim inventory 的 supported/total | 與 primary_binary 可能同源但入口及去重条件須核對；不得與專用 attribution 相加或當獨立驗證 |
| **診斷** citations、evidence.source/wiki/capsule precision/recall/F1 | 對指定 gold refs 與 observed refs 作集合 TP/FP/FN 比較 | 引用集合相符不代表支持回答；無有效 gold 時不可解讀品質；依原輸出保留空分母狀態 |
| **診斷** literal forbidden count/rate | Judge claim 字串與禁止字串的匹配 | 不等同語義違反；新報告採 semantic oracle 的 forbidden 判定 |

來源檔仍可能保留歷史欄位名稱。讀取 Agent 必須依明確 metric_id＋版本映射；未知欄位標為 `UNMAPPED_METRIC`，不能因名稱包含 accuracy 或 faithfulness 就自行解釋。

## 6. 多輪與記憶

| 指標 | 分母／聚合與方向 | 適用條件及限制 |
| --- | --- | --- |
| **現有** memory checkpoint pass rate | PASS checkpoints ÷ PASS＋FAIL checkpoints ↑ | SKIP 另報；應按 check_type 分開呈現，避免掩蓋能力差異 |
| **現有** remembered、retrieved | 有效布林觀測 true 數 ÷ 該字段有效布林觀測數 ↑ | 對應預期 facts 是否包含於保留／取回 facts；不是語義使用能力 |
| **現有** used_when_required、not_used_when_forbidden | 各字段 true 數 ÷ 各字段有效布林觀測數 ↑ | 依明確 per-fact 證據或符合實作條件的 flags；只有 context 存在不等於使用 |
| **現有** updated_correctly、isolated | 有效布林 true 比率 ↑ | 污染候選可令 isolation 失敗；缺 trace 不是 False |
| **現有** stale_or_unsafe | 有效布林 true 比率 ↓ | 表示過時／不安全使用的觀測；方向與 checkpoint 通過率相反 |
| **現有** memory fact precision/recall/F1 | 以每個 observation 區隔 facts，合併集合 TP/FP/FN | 僅用實作納入的 remember/retrieve/use facts 觀測；不要跨案例按相同文字直接去重 |
| **診斷** router_history_matches_window、composer_explicit_history_matches | 布林；可按有效觀測統計一致率 | 只驗證上下文傳遞；隱式 provider continuation 未捕獲時不可推定歷史完整 |
| **建議新增** 多輪新增需求處理率 | 經確認的新增要求中滿足數 ÷ 可判定新增要求數 ↑ | 需要明確跨輪 requirement 對應；不能只把 dialogue=多輪後續的 coverage 改名成此指標 |

## 7. Judge 一致性與多模型比較

| 指標 | 量尺／方向 | 分母、適用條件及限制 |
| --- | --- | --- |
| **現有** 維度 median、MAD、IQR、range | 分数單位；離散度 ↔ | 固定 subject／judge／dimension 的有效分數；MAD 為中位絕對偏差，IQR 為四分位距；一致地評錯也可離散度低 |
| **現有** Krippendorff α ordinal | 通常 ≤1，可為負；一致程度 ↑ | 對同一受評單位的序位維度分數；缺失不補值，常數／不足資料可能不可用；不是準確率 |
| **現有** α nominal／紅線 pairwise exact agreement | α 可負；exact agreement 0–1 ↑ | 同一回答同一紅線的有效共同判定；大量「未觸發」可造成表面高一致 |
| **現有** Kendall W | 0–1；排名一致程度 ↑ | 依實作可比 strata 與有效 Judge panel；缺排名不補；不等於模型品質 |
| **現有** pairwise Spearman | −1 至 1；排序一致程度 ↑ | Judge pair 在共同可比觀測上的秩相關；必須附共同樣本數 |
| **現有** self_judging、primary_eligible | 布林／計數 ↔ | 依 run 配置；保留自評是否納入的實際政策，不可假設所有 run 都排除自評 |
| **現有、條件式** human calibration agreement、Cohen κ、score delta | agreement 0–1；κ 可負；delta 非負 | 需要同一回答、同一 rubric 與有效人工基準；未做校準時不宣稱 Judge 可靠性已驗證 |
| **建議新增** 共同比較子集分數 | 0–3 ↑ | 用兩個 subject 均完整、且 Judge panel 與權重可比的案例重算並列；另報被排除範圍，不能取代全量描述 |

不把不同 Judge 的尺度直接平均成唯一模型排名。若要產出跨 Judge 摘要，必须预先声明聚合政策，并同时呈现各 Judge 结果、共同覆盖、自评政策与分歧。

## 8. 執行覆蓋與效能

| 指標 | 分母／聚合與方向 | 限制 |
| --- | --- | --- |
| **現有** Quality eligible cases | 有效案例數／總案例數 ↑ | 是可評覆蓋，不是品質通過率 |
| **現有** Execution gate pass rate | execution_status=PASS 的案例數 ÷ 全部案例數 ↑ | 包含未通過或執行錯誤案例於分母；不是使用者任務成功率 |
| **建議新增** Answer availability | 有效唯一回答數 ÷ 計劃回答數 ↑ | 分母必須有計劃案例與輪次；只有已觀測 rows 時標為 observed coverage |
| **現有計數／建議派生比例** Judge availability | 有效判定數 ÷ 應執行或已嘗試的評判數 ↑ | 兩種分母不可混用；分開展示 NOT_ATTEMPTED 與執行後 UNAVAILABLE |
| **現有** total_ms、elapsed_ms、queue_ms | 毫秒，通常 ↓ | 固定粒度再計 mean/median/p95；一般 overview 的 Mean total latency 是案例級，不是逐輪延遲 |
| **現有** ttft_ms、first_guarded_delta_ms、first_character_ms | 毫秒，通常 ↓ | 不同量測事件，未確認定義不能當同義詞；只對可用觀測統計 |
| **現有** tokens、attempt_count、retry_errors | 非負計數 ↔ | Subject 與 Judge 分開；回答 token 不因多個 Judge 重複計費；需確認 token 數是否含重試 |
| **現有、條件式** cache_hit_ratio | 0–1 ↔ | 依 provider usage 契約解讀；不跨 provider 猜相同分母；不代表品質 |
| **建議新增／需價格資料** 每有效回答成本 | 已核實總費用 ÷ 有效唯一回答數，通常 ↓ | 需明示币種、價格版本、重試／Judge 是否計入；沒有價格資料只能報 tokens |

`trace`、`timings`、`tokens` 的 PASS/ERROR 是遙測完整性檢查，不是延遲或用量的好壞評分。

## 9. 情境、Capsule 與 Router 分組契約

| 分組軸 | 含義 | 解讀限制 |
| --- | --- | --- |
| task_family／task | 使用者本輪需要完成的任務類型／具體任務 | 不以回答內容倒推任務，避免用表現結果定義測試條件 |
| topic | 問題主題 | 主題相同不代表任務或風險相同 |
| constraints | 資源、溝通、身體、照護等限制 | 多標籤可能重疊；缺標籤不等於沒有限制 |
| dialogue | 首輪、後續、修正、任務變化等 | 按實際綁定的使用者前綴解讀 |
| risk | 已標註的風險情境 | provisional 標籤不能當正式 safety gold |
| actual_branch | baseline／capsule／crisis_sop／UNKNOWN | 是系統實際走過的分支；觀察差異不是因果效應 |
| actual_route／route_id | 實際 route／capsule ID | 可由逐輪資料派生分組；不同 route 的案例難度不同，不能直接斷言某 capsule 更差 |
| evidence layer | 內容支持來自哪一層 | 支持層重疊，不形成互斥分群或貢獻百分比分配 |

每組至少報 `n_cases`、唯一 `n_answers`、`n_judgements`（若適用）、標註／審核數，以及各 metric 自己的有效／缺失分母。多標籤組的數量不能相加作總樣本數。

小樣本只能描述個案信號；本文件不另訂任意的「n≥某數即可靠」門檻。沒有部署流量分布與抽樣權重時，測試集均分不能外推為真實使用者滿意度或全量產品成功率。

## 10. 報告 Agent 的輸出契約（建議）

每個 metric observation 應保存：

```yaml
metric_id: scenario.required_coverage
definition_version: report-metric-dictionary/v0.1
implementation_status: existing
source_metric_id: required_coverage
grain: requirement
subject_id: <subject>
judge_id: <judge>
score_source: automatic
filters: {axis: task_family, label: <label>}
aggregation: micro
value: null
numerator: null
denominator: 0
available_n: 0
unavailable_n: 0
uncertain_n: 0
excluded_n: 0
status: UNAVAILABLE
reason: NO_ELIGIBLE_OBSERVATIONS
oracle_status: <reviewed-or-provisional-or-unknown>
source_refs: [] # workbook_sha256 + sheet + row/cell + semantic identity
```

`available_n` 等計數必须标明对应粒度；例如 AR 的 n 个反向问题不等于 n 个回答。上例为结构示意，不是实际 run 数据。

遇到 overview 与明细冲突时：记录差异及双方来源，核对版本、分段、过滤及分母；不能静默选一个值。若无法解决，暂停该指标的正式结论，其他可验证指标继续分析。

允许的结论：

> 在有效且按当前 oracle 判定的 12 项必要要求中，8 项满足，micro coverage 为 66.7%；另有 2 项不确定，未进入该分母。（仅为格式示例）

不允许的结论：

> XiaoAn 有 66.7% 的准确率，所以改 capsule 就能提高 33.3%。

任何改进建议都必须区分「观测事实」「Judge 判定」「根因假设」「待验证改动」。分数差异本身不能证明 prompt、router、capsule 或 ground 的因果贡献。

## 11. 實作依據

相對路徑均以 repository root 為準。兩個資料夾的共同概念相同，但讀取器仍須辨識工作簿版本及 producer，不能假設程式永遠同步。

- `evaluation/ratings rule.yml`：維度、錨點、紅線及動態權重。
- `evaluation/xiaoan_eval/scoring.py`：案例分數、typed facts 與 scenario 聚合。
- `evaluation/xiaoan_eval/report_model.py`：Overview 的實際篩選與均值。
- `evaluation/xiaoan_eval/metrics.py`：路由／安全、hard gates 與停用 Ground citation metrics。
- `evaluation/xiaoan_eval/oracle_judge.py`：要求語義判定、引用綁定及確定判定分母。
- `evaluation/xiaoan_eval/scenario_analysis.py`：primary_binary、strict proxy、AR、requirements 與群組 macro/micro。
- `evaluation/xiaoan_eval/attribution.py`：加權語義支持、分層支持、使用率與 policy coverage。
- `evaluation/xiaoan_eval/v3_metrics.py`：舊 claims、Capsule ref 診斷、分類與相容欄位。
- `evaluation/xiaoan_eval/rag_analysis.py`、`measurement.py`：排名量測資格與計算。
- `evaluation/xiaoan_eval/memory_metrics.py`、`methodology_metrics.py`：記憶觀測、Judge 統計與缺失處理。
- `evaluation_multimodels/xiaoan_eval/multimodel.py`：矩陣 case-macro、self judging 及工作簿輸出。
