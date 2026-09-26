# Evaluation 輸出盤點

盤點日期：2026-09-21。依當前工作目錄實作核查，適用於 evaluation 與 evaluation_multimodels。這是輸出能力清單，不是一次新跑的模型成績；欄位存在不代表已有有效數值。

## 本次調整

已移除 Precision@k、Recall@k 的逐 query 計算、跨 query 彙總及相關使用指引。歷史 runs／checkpoint 不改寫。其他 precision／recall（安全分類、引用、工具、人工校準）有不同分母，並非本次移除對象。MRR、AP@k／MAP@k、nDCG 仍是可選排序診斷，並非預設有效的產品指標。

## 交付文件與入口

| 入口 | 輸出 | 條件／用途 |
|---|---|---|
| 兩套 run / report | results.xlsx、report.md | 一般評估正式交付；report 從既有 case-results JSONL 重建，不會重新呼叫 subject |
| evaluation_multimodels matrix | results.xlsx、report.md | subject × Judge；Excel 格式與一般 run 不同 |
| preflight | 1.1-preflight.json、1.2-case-remediation.md | 案例結構與可執行性檢查，不產生模型品質分數 |
| measure | `results.json`、`results.md`、`results.xlsx`（unified/staged）；measurement.json、measurement.md（其餘 measurement methods） | 額外明確提供資料後執行；unified/staged 預設走 canonical 五表結果，舊 measurement.* 需明確 `--legacy-output` |
| experiment / auto-experiment / auto-file-experiment / stability | results.xlsx、report.md | 額外的比較、受控實驗或重複性結果，不是一般 run 自動完成 |
| export-human-review | 指定路徑的人工複核 XLSX | 盲審資料包；import-human-review / adjudicate 重新交付報表對 |
| examples 下專項腳本 | 個別 JSON／CSV／Markdown／HTML 等 | 部分綁定歷史 Minimal32 批次，不屬於通用 run 固定交付 |

一般 evaluation run 額外在輸出旁的 .<名稱>.private/ 保存 evaluation-checkpoint.jsonl 與 suite-attempts.jsonl；evaluation_multimodels 的普通 run 目前保存 suite-attempts.jsonl，並未使用同一 checkpoint 路徑。matrix 保存 .matrix-audit/<名稱>/matrix-checkpoint.jsonl。這些是私有恢復／審計資料，不是正式交付目錄中的第三份報表。

## 一般 run / report 的 Excel

| 工作表 | 內容 |
|---|---|
| 00_Overview | 總體品質分、執行／門檻通過率、可評案例數、維度平均、延遲、oracle 覆蓋、路由／支持判讀、附加證據狀態 |
| 01_Cases | 每案自動／人工／最終分、最終來源、品質門檻與結論、執行狀態、紅線與複核相關狀態、失敗階段、權重、群組、耗時 |
| 02_Turns | 用戶問題與回答文字、route、安全等級、ground refs、回答 hash、首字與總耗時；長文字分塊保存 |
| 03_Metrics | 每輪確定性指標、Judge 七維度、六條紅線及證據；rag:*、v3:* 聚合標量；可選 scenario.* 診斷 |
| 04_Baseline | 與已附基準的差異；未附基準時不代表已比較 |
| 05_Experiments | 假設、控制／候選、重複次數、目標變化、非目標退化、防護條件、結論 |
| 06_Human_Review | 待複核原因、審核身份、時間、信心、備註與回答綁定 |
| 07_Stability | 重複測試結果；未執行時沒有穩定性結論 |
| 08_Metadata | manifest、模型／版本／fingerprint、oracle coverage、typed facts 等可追溯資料 |
| 09_Data_Dictionary | 欄位說明 |

report.md 是決策摘要：執行結果、路由／策略／證據、Capsule／Ground 引用說明、七維度、案例結果、逐輪分流、失敗指標、改善假設、基準／實驗／人工／穩定性等狀態。它不逐項展開 Excel 的所有指標。

## 指標能力與有效值條件

| 類別 | 實際輸出能力 | 有效值需要／限制 |
|---|---|---|
| 整體品質 | 案例 weighted_total、Overall score（0–3）、品質結論 | 七維度有效；案例先跨輪平均，再按 quality_focus 動態加權；紅線命中歸零；執行缺失不補零 |
| Rubric 七維度 | 基礎能力22%、行動賦權18%、法律維權18%、求助轉介13%、表達能力9%、豐富性9%、包容性與可及性11% | 每輪0/1/2/3；focus權重乘1.5再歸一化；總覽維度平均是原始Judge逐輪平均，與紅線處理後的案例總分口徑不同 |
| 安全與執行 | 六條紅線、PII、route validity、output guard、ground resolution、trace／timings／tokens完整性 | 明確區分執行成功與品質通過 |
| Faithfulness | 支持主張數／全部已判主張數、unsupported claim rate | 有 Judge claims；主 run 的 v3 聚合只讀 oracle_approved observations；不表示事實真實性或必要需求完整性 |
| Answer Relevancy | N個反向問題對原問題的平均 cosine | 現有 examples 可計算；run/report/matrix 透過 --answer-analysis 匯入已綁定回答／subject／context 的本地結果；不自動生成或呼叫embedding；無結果為UNAVAILABLE |
| 語義任務符合度 | semantic_oracle 必要項滿足、禁止項違反、不確定項及verdict | 需審核的 response oracle 和有效答案span；舊literal F1不能替代 |
| 證據支持與歸因 | claim support總體／分層、relation counts、unsupported類型、exposed-unit utilization、policy obligation coverage | 需獨立 attribution、snapshot 與有效證據；支持率不證明模型實際因果使用了該資料 |
| Capsule觀察 | injected units、claim alignment、content coverage、citation precision | 需已注入units及合法refs；標為legacy observational，非獨立語義真值 |
| 引用／資料ID | citation及source/wiki/capsule的TP/FP/FN、precision/recall/F1 | 比較參考ID集合，不是Context Recall／Precision；缺標註不硬算 |
| 路由與安全分類 | accepted accuracy、preferred route、confusion及分類統計 | 需已審核預期標籤；可接受多路由與唯一首選分開 |
| 拒答、工具、任務流程 | refusal分類、tool匹配／參數與順序、goal completion、step efficiency、invalid calls、retry、timeout | 需對應oracle及trace；一般對話未必適用；trace goal符合不能當獨立驗證的真實任務成功 |
| 記憶／上下文 | remember/retrieve/use/not_use/update/isolation/stale/unsafe檢查；歷史窗口傳遞與匹配 | 需checkpoint／trace；普通run、matrix與scenario呈現位置不同；首輪history可為NOT_APPLICABLE |
| 速度／用量 | 首字／總耗時、分階段timings、input/output tokens；matrix另列queue、attempts、cache用量／命中比 | 由provider／trace提供；缺資料不補零，不自動把token換算成實際帳單 |
| Judge與人工校準 | primary/secondary分差與翻轉；人工比較；matrix的離散度與一致性 | 需成對或多人評分；一致不等於正確 |
| 統計／覆蓋 | case macro、有效／缺失樣本數、cluster bootstrap區間、oracle審核覆蓋 | 區分樣本分母；小樣本可能沒有區間 |
| 可選排序診斷 | MRR、AP@k／MAP@k、nDCG | 需要完整qrels、ranked refs、版本匹配；一般Chatflow不保證有這些資料；已無Precision@k／Recall@k |

ground_recall／ground_precision 舊主流程欄位固定 SKIP。answer.correctness_f1、completeness_recall及舊forbidden語義欄位為null；legacy_literal_diagnostics只供字面匹配診斷。Context Recall／Context Precision 尚無獨立同名語義實作。measure answer 另有明確證據契約的 faithfulness／correctness，不能與主run的claims比例混用。

## Matrix 專屬 Excel

| 工作表 | 內容 |
|---|---|
| Matrix | 每個subject × Judge的合資格聚合分數；缺失／自評隔離明確標記 |
| Oracle_Coverage | oracle審核覆蓋 |
| All_Answers | 去重回答、耗時／token／cache／retry、trace hash、錯誤 |
| All_Judgements | 每個Judge對回答的七維度、weighted_score、紅線及證據、Judge原始文字、用量／錯誤、自評與主要統計資格 |
| Dimension_By_Judge | 每subject × Judge的維度中位數、聚合總分與有效／嘗試數；維度並非一般run的逐輪平均 |
| Self_Judging_Isolated | 自評列獨立展示 |
| Measurement_Contract | 主分母、memory、attribution、semantic_oracle JSON摘要 |
| Judge_Agreement | ordinal Krippendorff alpha、Kendall W、pairwise Spearman、缺失與適用性 |
| Red_Line_Agreement | 紅線nominal alpha、pairwise exact agreement |
| Dimension_Statistics | 原始分數、median、MAD、IQR、range、n |

matrix不直接複用一般run的v3指標彙總；不能假設一般run的每一個技術欄位都會自動出現在matrix。

## 可選情境分析

--scenario-analysis、--scenario-annotations或--answer-analysis啟用。一般run把groups、answer_groups、turns、claims、claim_groups寫入03_Metrics的scenario.*列；matrix新增對應五張Scenario_*工作表；兩者在report.md附分析章節。

涵蓋情境／任務／風險分組、primary binary faithfulness、strict entailment proxy、AR、必要需求覆蓋、claim種類／證據層／支持關係，以及route／injection／history診斷。AR按subject回答去重，不因Judge數量增加而重複加權。原始faithfulness與strict proxy可能使用不同claims inventory，不宜直接當同一模型成績差異。

## 主要實作位置

- xiaoan_eval/cli.py：各入口與交付路徑
- xiaoan_eval/deliverables.py、workbook.py、report_model.py：一般交付對與工作表／彙總
- xiaoan_eval/scoring.py、metrics.py、v3_metrics.py：總分、門檻、聚合指標
- xiaoan_eval/attribution.py、rag_analysis.py、measurement.py：證據支持與可選測量
- xiaoan_eval/scenario_analysis.py：可選情境與AR匯入
- evaluation_multimodels/xiaoan_eval/multimodel.py：matrix專屬輸出

## 本次新增的兩項分析

- `--knowledge-review PATH` 配合 scenario analysis：將已綁定的 `knowledge-review/v1` 加入膠囊 claim 支持、必要內容 `ADOPTED`／`OMITTED`／`UNKNOWN` 及已核實膠囊缺口；沒有 review 證據時維持 UNKNOWN。
- `evaluation_multimodels matrix --pricing-catalog PATH`：依精確 provider／model／billing_route／幣別定價目錄計算去重 subject answer 成本、Judge 成本與 subject/Judge 平均分；未有精確價格、token 或完整 retry usage 時為 UNAVAILABLE。成本會寫入 `Cost_Quality` 工作表及 report.md。
