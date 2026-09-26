# 凍結答案評估：新流程

正式入口為 `measure frozen-answer-evaluation`；`unified`、`staged`、舊 workbook 報告入口已從 CLI 移除。兩個 evaluation 目錄共用 canonical package／core。以下從 repository root 執行；模型與密鑰沿用 `evaluation_multimodels/.env`。

本專案所有 test cases 至指定 KaroAPI／Google embedding 的持續外送授權見 [授權紀錄](../../docs/implementation/evaluation-api-authorization.zh-HK.md)，同範圍試跑與重試可沿用。

## 建立計劃與執行

```bash
PYTHONPATH=evaluation python -m xiaoan_eval run --cases TC-35 --output evaluation/runs/example
```

預設只建立計劃，不呼叫 API。加 `--execute` 後實際生成與評估；加 `--report` 後独立生成報告。`--subject-mode chatflow` 使用本機程式內的完整 Chatflow，`http --base-url URL` 使用部署服務，`direct` 只測直接模型回應，沒有 Chatflow snapshot，不應用來證明路由或 RAG 表現。

`matrix --subjects MODEL_A MODEL_B --judges JUDGE_A JUDGE_B` 使用同一流程；模型 ID 必須已在共用配置中。每個 case 的輪次順序執行，跨 case 和 evaluator 受 `--max-workers` 與 workflow 限制。

```bash
PYTHONPATH=evaluation python -m xiaoan_eval measure frozen-answer-evaluation \
  evaluation/runs/example/frozen-input.json --output evaluation/runs/reassessment \
  --checkpoint-dir evaluation/runs/example/checkpoint --execute
```

補評重用 frozen answers。相同 output 已有完整 results.json 時只重建 downstream；需要重試失敗評估時使用新的 output，指定既有 checkpoint。Subject checkpoint 保留 case lane 和逐輪 state；中斷時外部呼叫結果未知會停止自動重放，需明確建立新生成版本。HTTP session 無法安全重建時同樣不自動重放。

## 選擇性重跑

相同 evaluator 配置和 provider 傳輸選項下，可按回答 ID、Judge 和階段只補不可用格位。先不加 `--execute` 查看本次選取的呼叫數；再加 `--execute` 寫入全新的 output，來源 `results.json` 保持不變：

```bash
PYTHONPATH=evaluation python -m xiaoan_eval retry-evaluation \
  --from-results evaluation/runs/example/results.json \
  --output evaluation/runs/example-rubric-retry \
  --stages rubric --answer-ids ANSWER_ID --judges JUDGE_ID
```

階段為 `extraction`、`rubric`、`assessment`、`relevancy`。省略選取條件時，掃描所有現有可用回答的不可用或 `PARTIAL` 格位。assessment 缺 inventory 時會先重抽 claim；明確重抽 claim 會使該回答所有 Judge assessment 失效並補評。完整成功的格位保留原始內容，request hash 相同的成功回應從來源或新 checkpoint 復用。`PARTIAL` 不作成功快取；同一請求已驗證的維度可在補評時保留，衝突仍標記為 `PARTIAL`。未經確認的中斷呼叫可以明確重試，但先前用量保持未知；新的 provider 呼叫可能再次計費。結果的 `provenance` 和 `retry-selection.json` 記錄 parent generation 與選取範圍。已有人工作出的 Human Review 結果不能直接自動補評，須先另行處理人工審核綁定。

配置已變更時，不得把舊成功格位和新評分混合。`--new-evaluator-cohort` 保留凍結回答、用現行 evaluator/schema/傳輸選項對**全部現有可用回答**重做評估；不接受階段、回答或 Judge 子集：

```bash
PYTHONPATH=evaluation python -m xiaoan_eval retry-evaluation \
  --from-results evaluation/runs/example/results.json \
  --output evaluation/runs/example-new-evaluator \
  --new-evaluator-cohort
```

subject 失敗按 `SUBJECT:CASE` 選完整多輪 lane；後續 turn 依新前文重新生成，新的回答 ID 使該 lane 舊評估失效，其他 lane 原樣帶入。此命令只支援 `chatflow`／`direct` 模式；HTTP session 沒有可驗證的狀態重建。執行前要求現行 provider 選項與原 plan 相同：

```bash
PYTHONPATH=evaluation python -m xiaoan_eval retry-subject-lanes \
  --from-results evaluation/runs/example/results.json \
  --output evaluation/runs/example-subject-retry \
  --lanes MODEL_ID:TC-35
```

上述兩個命令預設只作離線驗證與選取預覽；加 `--execute` 才呼叫供應商。重啟同一次重跑須使用完全相同的來源與選取範圍；已封存 `results.json` 的目錄不可覆寫。每次執行後以新 `results.json` 的可用率判斷是否仍需補評，失敗不填零。

## 產物

- `plan.json`／`frozen-input.json`：批准的計劃與凍結答案。
- `results.json`：完整評估、證據、聚合、用量及來源。
- `results.xlsx`：Overview、Spec、Answers、Scores、Claims、Requirements、Rating Details、Human Review。
- `report/`：獨立 report.md、findings、查詢與驗證紀錄。
- `subject-checkpoint/`、`checkpoint/`、`provider-artifacts/`：恢復與原始證據；不當公開資料。

各 Judge 分開展示，不計跨 Judge 平均。Rubric／claims 按完整案例等權；紅線不強制歸零，gate 獨立。未知、不適用與執行失敗分開，附覆蓋矩陣。

## 人工審閱

在 Human Review 填 decision（APPROVE／REJECT／NEEDS_INFO）、notes、reviewer、reviewed_at。APPROVE 是認可 Judge 判定，不表示回答通過。原文／評分欄不可改寫；修訂以 revisions_json 明確記錄，REJECT 不自動重跑。

```bash
PYTHONPATH=evaluation python -m xiaoan_eval import-human-review \
  evaluation/runs/example/results.json evaluation/runs/example/results.xlsx \
  --output evaluation/runs/reviewed --confirmed-by user
```

匯入建立新 generation，原自動結果不覆寫；有人工填寫的 workbook 不可直接重建覆蓋。

## 配置、校準與報告

`evaluation/evaluator-config/` 的 prompt、rating-rule、workflow 和 schemas 是實際載入檔案。候選評估用 `measure frozen-answer-evaluation ... --evaluator-config PATH`，保持 frozen row 不變、另綁 evaluator configuration。不要直接修改已凍結的 run 配置。

`python -m xiaoan_eval frozen-calibration --help` 列出 split、benchmark、snapshot、compare、inputs、mark-holdout-used、adopt。按 case 分 22／11，保留驗證集不能進 prompt 修改；使用者最終確認人工修訂及是否採用候選。Adopt 只保存決策，不自動切換生效配置。

```bash
PYTHONPATH=evaluation python -m xiaoan_eval report \
  evaluation/runs/example/results.json --output evaluation/runs/example/report --execute
```

不加 `--execute` 只建立報告 catalog。報告失敗可單獨恢復，不重新生成回答／分數。獨立事實證據須具備核准 scope、版本與來源 hash；目前案例只有要求／來源標註而沒有独立 factual gold 時，correctness 保持 UNKNOWN，不自動升級為批准真值。

完整政策與驗收見 [重構規格](../../docs/research/2026-09-24-evaluation-workflow-refactor-spec.zh-HK.md)。

## 路由模式混淆矩陣

新結果的 `aggregates.routing` 按被測 subject、case、turn 計數，不按 Judge 複製。Overview 顯示預期模式（列）× trace 實際模式（欄），分為危機、baseline、capsule、安全澄清，另保留未知及缺失欄；Answers 有預期／實際路由、模式、允許路由是否命中及排除原因。

預期採已核准 preferred_route_id；沒有首選且只有一個核准允許路由時使用該唯一值。多個允許路由但沒有唯一預期者不進矩陣，另記原因；仍可計允許路由命中率。合法替代路由可能在非對角格，不能將所有非對角格當作違反。未知／缺失另報；允許路由命中率只對有核准集合與實際路由的輪次計算。

```bash
PYTHONPATH=evaluation python -m xiaoan_eval route-analysis \
  evaluation/runs/example/results.json --output evaluation/runs/example-routing
```

此命令只從凍結 trace 重算新 JSON／Excel，沒有 API 呼叫，原產物不覆寫。新生成計劃凍結核准路由 ID 清單，未識別 ID 不猜成 capsule。

## 回答模型成本

新結果在 `aggregates.answer_costs` 保存逐輪輸入／輸出成本、合計、公式、費率來源及計價覆蓋；Answers 表增加成本欄，Overview 按 subject 彙總。Report Agent 的人類版報告顯示逐輪成本及注意事項。

普通公式為 `(input_tokens × input_rate + output_tokens × output_rate) / 1,000,000`。若有快取分類，先從總輸入扣除 cache read／write，再按各自費率計算；長上下文按模型門檻套用全請求倍率。金額以 USD 保存，不在逐項計算前四捨五入。

費率唯一來源為 `evaluation/evaluator-config/official-prices.json`，包含精確 provider／model／服務層、官方網址、核對日期和版本。這是官方標準價格估算，不是 KaroAPI 帳單；只計回答模型，不混入 Router／Safety、Judge、embedding、報告或未記錄重試。其他費用須另行核算。Google 儲存／工具費不含於文字 token 估算。

缺 token、價格、DeepSeek 峰谷時段，或 Anthropic cache write 時長時保留不可計算原因；缺失不填零。沒有任何回答模型呼叫、且已有明確 runtime 紀錄時可記零成本。部分可計價時提供已知小計，完整總計留空並列覆蓋。

```bash
PYTHONPATH=evaluation python -m xiaoan_eval cost \
  evaluation/runs/example/results.json --output evaluation/runs/example-priced
```

可加 `--pricing-catalog PATH` 指定核實後的價目表。指令完全離線，生成新 JSON／Excel，不修改原回答或分數。模型別名不模糊匹配；價格更新應建立新目錄版本。原資料未記錄 usage 時無法事後由文字還原，本機 Chatflow 的新紀錄已補上 Composer usage 捕獲。
