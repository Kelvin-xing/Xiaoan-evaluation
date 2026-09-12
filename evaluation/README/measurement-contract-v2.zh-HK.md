# 評分契約 v2 與審閱修復（2026-09-13）

本次針對一般 evaluation、suite、evaluation_multimodels matrix，以及 Markdown／Excel／人工覆核之間的測量不一致作修復。評分契約版本是 `response-effectiveness/v2`；正式 workbook schema 是 `2.1`。這些是離線實作驗證，不是新一輪模型能力評估。

## 1. 執行、品質、安全與批准狀態

- provider timeout、缺少預期輪次、Judge／必要證據不可用，不產生品質 0 分：`quality.status=UNAVAILABLE`、`weighted_total=null`，排除 Overall score 分母。原始錯誤仍保留。
- 真正的品質 0 分仍是數字 0；已判定紅線仍保留 FAIL，不因同一案例另有缺失而隱藏。
- `execution_status` 表達執行及確定性門檻；`quality_verdict` 表達品質與可評資格。`Execution gate pass rate` 不再冒充品質通過率。
- 品質門檻由 manifest 的 `run_config.quality_threshold` 設定，範圍 0–3，必須有限。沒有設定時顯示 `NOT_CONFIGURED`，不自動宣告品質 PASS；未批准 oracle 顯示 `NOT_APPROVED`。
- 例：全部維度 1 分、門檻 2，品質 FAIL；正常執行仍可是 execution PASS。API timeout 則是 UNAVAILABLE，而不是品質 FAIL/0。
- 確定性硬門檻已知違反時為 false；必要檢查發生 ERROR 時為 unknown/null。報告保留安全失敗與品質不可用的差別。

設定示例（`2.0` 僅示範配置，不是已完成校準的建議門檻）：

```json
{"run_config": {"quality_threshold": 2.0}}
```

## 2. 一致的總分與聚合

對維度 d，基礎權重為 b_d，focus 倍率為 m（目前 rubric 為 1.5）：

```text
w_d = b_d × (m if d in quality_focus else 1)
W_d = w_d / sum(w)
turn_score = sum(W_d × dimension_score_d)
case_score = mean(所有預期輪次的 turn_score)
```

所有七個 rubric 維度都進入計算，focus 是提高權重，不是刪除其餘維度。已判定案例紅線時 case score 為 0。任何預期輪次不可評，整案品質不可用；不以已成功的部分輪次冒充整案。

- 普通、suite、matrix 的同一份完整評分使用同一契約。
- 同一 subject×judge cell 先算完整 case 分數，再對案例作 macro mean，避免長案例獲得更多權重。
- Matrix 維度表是有效輪次的 median，是診斷分布；不是總分公式。Markdown 和 Excel 使用相同狀態篩選及統計量。
- 反例驗收：只有「行动赋权」為 3、其餘為 0，focus 為「行动赋权」，三路皆約 **0.743119**。同一案例三輪總分 `[0,0,3]`，cell 總分兩種報表皆 **1**，維度 median 為 **0**。
- 有效案例數與有效輪次數是不同分母。不要將僅部分輪次可觀測的維度中位數，解讀為整個 episode 已完成。

## 3. 人工覆核、裁決與版本遷移

Schema 2.1 的 `01_Cases` 新增品質狀態、品質結論、門檻、最終動態權重、執行狀態、oracle 批准狀態。原自動分、人評分與最終來源繼續分欄保存。

自動逐輪分、人評與裁決均使用 workbook 保存的動態權重；覆核後依 final score 重新判斷品質結論。覆核一個案例不能重算其他案例；合法零分不能因真假值判斷變成缺失。裁決若選擇紅線成立來源，案例仍為 0／FAIL；執行 ERROR 不可由人工填分消除。

舊 2.0 workbook 仍可驗證及讀取，但缺少原動態權重時不能進行新的人工重評，需從原始案例、rubric 與評分證據重新產生。不能只補上當前基礎權重。跨 schema／scoring contract 的 baseline 品質比較會拒絕；相同契約下任一側品質缺失，對應 delta 為 null、標記 UNAVAILABLE，整體比较標記非完整可比。不要把版本修正前後的數字直接當成模型改善。

新 matrix checkpoint 的 hash 包含 v2 評分契約。不要用 legacy override 混用舊公式產生的 cell；本次沒有修改任何既有私有 run。

## 4. 指標分母與 memory lifecycle

- 空 route／safety 可接受集合代表沒有該 oracle，不算失敗，也不进入 accuracy 分母。
- `unsupported_claim_rate = (被檢查 claims 數 − supported claims 數) / 被檢查 claims 數`。是否命中 required claim 是另一個軸；一條 required 但 unsupported 的 claim 仍必須算 unsupported。沒有被檢查 claim 時不可用。
- 普通與 matrix 共用 memory observer；`remember`、`retrieve`、`use`、`not_use`、`update`、`isolation`、`stale`、`unsafe` 分別判斷。
- `not_use` 的成功是沒有使用禁止 facts，不要求正向 used=true。
- 缺欄位、錯誤欄位型別與 unknown 是 SKIP/UNAVAILABLE；明確的空 retrieved facts 才是已觀测但未命中。不能把缺 retrieval telemetry 加入 recall 分母。
- `memory_used_facts` 是逐 fact 的使用證據；兼容的 `memory_used` 布林值只屬較弱遙測。`use` 在只有 generic flag 時還需 retention 證據。
- isolation 出現非空 contamination candidates 即失敗；沒有任何 isolation 證據不可判成功。
- flags／fact IDs 的正確性依賴產品遙測；這些觀察本身不構成對最終回答的因果使用證明。

## 5. 跨 Judge 統計

預設隔離同 provider/model 自評；保留自評列供診斷，不進主要矩陣。若明確使用 `--no-isolate-self-judging`，主要矩陣才納入；agreement 仍維持 non-self 描述統計。分母分別保存 self_judging 與實際 self_excluded 數。

缺失 rank 不再插補。Kendall W 只有足夠、完整且非退化的同 case/turn panel 才可用；缺失或常數排名顯示 UNAVAILABLE。Ordinal/nominal alpha 的 expected disagreement=0 時是未定義，不再回傳 1。Excel 保存 alpha reason 和 Kendall stratum 的缺失原因。

相關與一致性只標記 `DESCRIPTIVE_ONLY`；本次 run 不宣稱已完成效度校準。隔離自評／provider failure 後，不同 subject 可能有不同 Judge panel，分數比較仍屬探索性；正式模型排名需相同獨立 Judge panel、人工錨點及足夠重複樣本。本次沒有假造共識金標或自動完成 Judge 校準。

## 6. 案例覆蓋與仍需人工作業

預設正式集仍為原有 74 案、217 輪；新增 `test-cases/proposed/` 九份草案，預設不遞迴載入：

- TC-17、TC-52：提出 response_oracle 必要／禁止行為，等待領域審閱後合併。
- TC-75–81：remember、retrieve、not_use、update、isolation、stale、unsafe 的合成候選；原案例已有 use checkpoints。

九份皆保持 PROVISIONAL_DESCRIPTIVE，沒有 reviewer 批准。普通報告與 matrix 增加 authored/reviewed 覆蓋數；reviewed=0 顯示 UNAVAILABLE。寫出 YAML 只能證明 schema 可解析，不等於 agent 已通過該能力測試。

需要審閱者確認必要行為、允許替代、禁止行為與證據；memory cases 還需接通 fact IDs 與 trace，多 session isolation 需可控制 session 的 harness。工具結果、goal oracle、更多 response 情境仍須依真實產品能力補充。不能將本次草案或測試通過數當作覆蓋已完成。

## 7. 離線驗證

測試涵蓋運行失敗不進品質平均、有效零分、threshold、動態權重、人工覆核與裁決、Markdown/Excel 一致、完整案例 macro 聚合、空 oracle、unsupported 分母、memory 缺遙測、退化 agreement、草案批准狀態及 baseline 缺失。

本次最終完整測試：`evaluation` **248 passed**；`evaluation_multimodels` **292 passed**。13 個本次修改的共用核心檔案已確認兩套位元組一致。

在各自 package 根目錄執行：

```bash
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q
```

另外用修改前 writer 產生純合成 2.0 workbook，驗證新版 reader 及 digest 可讀、缺原權重時拒絕重評。本次不呼叫外部模型，不代表真實 Judge 的可靠性／閾值／記憶能力已驗證。
