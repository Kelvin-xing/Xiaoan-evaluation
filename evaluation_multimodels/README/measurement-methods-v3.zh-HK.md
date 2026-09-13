# 評估方法 v3：操作與資料契約

此版本實作稽核中九類方法的程式入口，兩個project均可使用。**程式與合成測試完成，不代表人工gold、正式檢索標註、真實工具觀測或線上研究已完成。** 不使用DeepEval API，也不自動啟動付費評估或部署流量。

## 執行

在各project自己的環境與目錄執行，兩者不能安裝到同一virtualenv（import與CLI同名）：

```bash
python -m xiaoan_eval measure retrieval examples/measurement/retrieval.json --output /tmp/retrieval-v3
python -m xiaoan_eval measure oracle examples/measurement/oracle.json --output /tmp/oracle-v3
python -m xiaoan_eval measure answer examples/measurement/answer.json --output /tmp/answer-v3
python -m xiaoan_eval measure pairwise examples/measurement/pairwise.json --provider measurement_example_plugins:pairwise --egress-validator measurement_example_plugins:allow_synthetic --output /tmp/pairwise-v3
python -m xiaoan_eval measure cluster examples/measurement/cluster.json --output /tmp/cluster-v3
python -m xiaoan_eval measure outcome examples/measurement/outcome.json --output /tmp/outcome-v3
python -m xiaoan_eval measure perturbation examples/measurement/perturbation.json --provider measurement_example_plugins:harness --egress-validator measurement_example_plugins:allow_synthetic --output /tmp/perturbation-v3
python -m xiaoan_eval measure calibration examples/measurement/calibration.json --output /tmp/calibration-v3
python -m xiaoan_eval measure online examples/measurement/online.json --output /tmp/online-v3
```

每個輸入必須有`schema_version: evaluation-methods/v3`，範例JSON是可直接修改的完整契約。輸出為`measurement.json`及`measurement.md`，附input hash、分母與缺失數。既有輸出拒絕覆蓋；包含對話或資料的結果應保存在私人run位置，不能把它們當作公開範例。

`measurement_example_plugins`是**離線合成假實作**，用來驗證CLI接線。它沒有測量XiaoAn，也不能用其PASS宣稱context injection、session isolation等產品能力通過。真實pairwise與probe需更換明確指定的provider/harness及egress validator。harness負責實際建立/清理session、設定超時、注入fault、收集獨立telemetry；若它沒有提供可驗證結果，評估只能UNAVAILABLE。

## 各類方法

| 方法 | 輸入與判定 | 缺失與邊界 |
|---|---|---|
| 確定性／結果驗證 | outcome：綁定task、snapshot與獨立observer；比較外部facts的明確期望值；檢查工具授權、成功狀態、額外副作用與先後依賴 | subject不能同時當observer。身份是受信任adapter的配置契約，不是密碼學身分驗證。缺facts/授權/工具狀態不當通過 |
| 檢索排序 | retrieval：完整judged universe、非負graded qrels、有序不重複候選、k、corpus/chunk/retriever/reranker/qrels版本 | 未標註top-k候選→UNAVAILABLE；沒有正相關gold時recall/AP/RR/nDCG為null，precision仍可算 |
| 回答評估 | answer：逐原子claim的答案span、context evidence、獨立truth evidence；另有relevance與必要項完整性 | faithfulness與correctness各有known/unknown分母。語意標籤仍來自Judge/人工，span校驗不能證明標籤正確 |
| LLM Judge | 普通與matrix主流程新增semantic oracle契約，逐R/F ID作SATISFIED/VIOLATED/UNCERTAIN判定並提供原文span | 舊provider不回新欄位→語意任務評估UNAVAILABLE，不能由七維度分數推斷通過。缺全部ID或假span拒絕 |
| 成對比較 | pairwise：同case/turn/question/history/rubric/context/control下的凍結答案，每Judge正反順序各一次，勝方映回version | TIE=0.5勝分；INVALID或左右反轉不一致的pair不進分數，另報missing/order inconsistency |
| 人工評估／校準 | calibration：frozen benchmark hash、兩名獨立reviewer及不同adjudicator、disjoint calibration/held_out、綁定prediction | 檢查case與content hash不得跨split洩漏；不生成或代替人工標註，不把評測標準核准當成Judge校準完成 |
| 線上／使用者 | online：實驗/assignment/mode/arm分層的匿名session事件，真實觀察的task resolved、適切轉介、成功退出與operation failure | 未完整觀察或欄位未知不當false；shadow不自動表示有真實使用者結果。只描述，不宣稱因果改善或真實安全效果 |
| 對抗與擾動 | perturbation：注入相同controls的baseline/variant，由harness回傳facts；斷言same/different/equals | 範例含context衝突/過時/無答案/注入/長對話/更正/session隔離/timeout/部分成功/重試副作用；案例標籤不證明故障真的注入成功 |
| 控制實驗與統計 | cluster：對齊case+unit，先計case mean再按case重抽，paired計variant−baseline | 同案多輪/多Judge不當独立樣本；缺成對結果另報。少於兩個case沒有CI，不能輸出假精確區間 |

## Oracle主流程接線

`JudgeClient`在送往provider前加入`oracle_contract`，其binding包含oracle文本、答案、使用者問題及history。內建provider的JSON schema新增`oracle_assessment`。主pipeline把驗證後的assessment寫入observations，普通workbook/report在`v3.semantic_oracle`輸出coverage、uncertain、satisfaction/violation及獨立task verdict。

R必要項滿足、F禁止項違反需要非空的有效答案span。缺漏R可用空span但必須解釋；F項只是被引述後否定不算違反。Judge仍需作語意判斷；本地不以字串完全相等評定是否涵蓋R/F。

matrix請求包含同一契約，row與checkpoint保存assessment，`Measurement_Contract`sheet及Markdown輸出摘要。matrix prompt版本升至v2避免靜默沿用舊prompt結果。自評排除仍按現有primary eligibility政策。獨立`measure pairwise`用於正式雙序版本比較；舊`run_pairwise_pass`保留兼容，不將其單序helper當新流程。

舊`score_claims`／`answer.correctness_f1`保留作歷史相容，明確標記`DEPRECATED_LITERAL_MATCH_NOT_TASK_CORRECTNESS`。新任務符合度讀`semantic_oracle`；獨立事實正確性讀`measure answer`的correctness，不把舊F1重新命名成真值正確率。七維度品質門檻與任務verdict分開，不用任務分數偷偷改動quality權重。

## 檢索公式與主流程

- Precision@k = top-k相關個數/k；不足k個候選仍以k為分母。
- Recall@k = top-k相關個數/完整gold相關個數。
- RR@k = top-k第一個相關項排名倒數；有相關gold但沒有命中為0。
- AP@k = 各相關位置的precision總和 / min(完整相關個數,k)。這是截斷版本，不能當全庫AP；跨query平均為MAP@k。
- nDCG@k = DCG/IDCG，採明確的linear relevance gain及log2(rank+1)折扣。

只有同版本／k的query才聚合，報告保留strata與每metric n。主case可選填`expected.retrieval_oracle`（與retrieval JSON row一致但不含ranked_ids）；case loader驗證它。trace需提供`ground.ranked_refs`與四個相符的`ground.retrieval_versions`。已reviewed oracle、版本匹配且實際排序存在時才進主RAG報告。此次不憑空為74案填retrieval gold；原resolver refs不當完整候選排名。

## 人工與線上資料

人工benchmark的`gold`可含red_lines、dimensions、claim_ids及relations。prediction用相同item/content/benchmark hash綁定。輸出紅線TP/FP/FN/TN、precision/sensitivity、逐維度MAE、claim extraction recall與relation agreement，分開calibration與held_out。claim matched IDs需由既有span matching/人工確認產生，不能把任意自評ID當作獨立標準。

統計報告提供case macro估計、case/unit/missing n及2000次seeded cluster bootstrap。區間是觀測樣本下的不確定性描述，不保證小樣本覆蓋率或外推效力。online另報latency/cost的p50/p95/p99、成功session的平均cost；不能把對話長度、點擊或依賴增加當任務成功。

## 尚需真實運行完成的工作

程式具備入口後，團隊仍需提供：人工relevance qrels、獨立factual gold、完成盲審與仲裁的benchmark、接到真實SUT及observer的harness，以及經批准收集的線上session事件。這些不是用mock可以「完成」的研究結果。Oracle批准狀態與APPROVED_AGGREGATE保持既有人工決策，未自動擴大suite或宣稱模型能力已驗證。
