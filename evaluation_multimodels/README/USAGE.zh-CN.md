# XiaoAn Evaluation 使用指南

本指南描述目前可執行的評估流程、兩個公開交付物的讀法、人工審核與 Judge 校準。命令和欄位以 `evaluation/xiaoan_eval` 的現行程式為準。

## 1. 先決條件

- Python 3.11 或以上。
- 在 `evaluation/` 安裝套件：

  ```bash
  python -m pip install -e '.[test]'
  ```

- XiaoAn Chatflow 已啟動，且 `--base-url` 可連線。
- 準備相容的 `manifest.json`、`ratings rule.yml` 和測試案例目錄。
- 固定並記錄模型、prompt、knowledge snapshot、rating rule 和 manifest。

## 2. 執行評估

先做不呼叫 Chatflow 的案例檢查：

```bash
cd evaluation
xiaoan-eval preflight test-cases \
  --rating-rule 'ratings rule.yml' \
  --output runs/<run-id>-preflight
```

再執行正式評估：

```bash
cd evaluation
xiaoan-eval run test-cases \
  --base-url http://localhost:8000 \
  --judge-plugin company_eval_plugins:judge \
  --context-provider company_eval_plugins:authoritative_context \
  --manifest manifest.json \
  --rating-rule 'ratings rule.yml' \
  --config evaluator-config.yml \
  --output runs/<run-id>
```

`--judge-plugin`、`--context-provider` 是必要參數。可按需加入 `--secondary-judge-plugin`、`--attribution-judge-plugin`。與正式基準比較時加入 `--baseline runs/<baseline-id>/results.xlsx`。

輸出目錄只允許 `results.xlsx` 和 `report.md`（可保留系統產生的隱藏檔）。私有重試 ledger 預設放在公開目錄旁，不是公開交付物。

## 3. 閱讀 `report.md`

1. **執行結果**：看產物狀態、整體分數和通過率。整體分數是可用 case final score 的平均；`UNAVAILABLE`、`NOT_RUN`、`NOT_REQUIRED`、`NOT_APPLICABLE` 都不是零分。
2. **維度分數**：看 Judge 各維度平均和評分來源。
3. **案例結果**：看每個 case 的狀態、final score、失敗階段和審核狀態。`NEEDS_REVIEW`／`NEEDS_ADJUDICATION` 不等於產品品質零分。
4. **指標發現／改善建議**：以 case、turn、metric 和 evidence refs 回到工作簿核查；沒有受控實驗時，建議只能是 `hypothesis`。
5. **基準、實驗、穩定性、人工複核**：沒有執行時會明確寫出未執行或未測量。

## 4. 閱讀 `results.xlsx`

| 工作表 | 用途 |
| --- | --- |
| `00_Overview` | 整體分數、通過率、維度平均、資料覆蓋率、基準／實驗／穩定性狀態。 |
| `01_Cases` | 每個 case 的自動／人工／final 分數來源、hard gate、失敗階段、審核狀態和延遲。 |
| `02_Turns` | 每個 turn 的輸入、回答、route、ground、安全和 latency；`row_kind=text` 是長文字分塊。 |
| `03_Metrics` | case/turn/metric/source 的分數、狀態、中文 reason、evidence refs 和 score source；也有 run-level aggregates。 |
| `04_Baseline` | 相容正式 baseline 的差異和不可比原因。 |
| `05_Experiments` | 假設、對照／候選、重複、目標結果、guardrails、結論和下一步。 |
| `06_Human_Review` | 人工審核生命週期和 provenance。 |
| `07_Stability` | 固定控制條件下的重複性，不是正確性分數。 |
| `08_Metadata` | schema、generation、manifest、版本和 digest。 |
| `09_Data_Dictionary` | 欄位和狀態語義。 |

### 4.1 Router 分流

在 `02_Turns` 看實際 `route_id`，在 `03_Metrics` 看 route 指標：

- `route_acceptance`：實際 route 是否在可接受集合內。
- `route_preference`：實際 route 是否等於 preferred route。
- `route_confusion`：只有 expected route 唯一時才建立 expected→actual 矩陣。

逐案核查 `crisis_sop`、`baseline` 和 capsule route 是否符合 `expected.route_ids`／`preferred_route_id`。路由命中不證明回答語義上使用了內容。

### 4.2 Crisis SOP、baseline 與失敗原因

- crisis：先看 safety hard gate、red line、拒答／轉介和 `route_acceptance`；再依 `03_Metrics` 的 reason／evidence 判斷是 router、composer、ground 解析還是 provider 問題。
- baseline：看 route、required/forbidden claims、faithfulness 和 Judge 維度；一次偶發低分不足以證明 prompt 需要修改。
- `ERROR`、`ReadTimeout`、provider failure 和 `UNAVAILABLE` 是操作證據不可用，不是產品品質零分；應先重跑或修復環境。

### 4.3 Capsule／Ground 支持程度

1. **Capsule 是否注入**：看 `02_Turns` trace 和 `03_Metrics` 的 capsule attribution aggregate（injected units、valid capsule evidence、claim alignment、content coverage）。
2. **回答是否有 Capsule 支持**：看 Judge atomic claims、`evidence_refs` 和 capsule claim alignment；這是語義支持的近似證據，仍受 trace 可見性限制。
3. **Ground 是否解析**：看 `02_Turns` 的 `ground_status`、`ground_refs`／resolved refs 和 deterministic ground resolution gate。

本版本已移除對 `required_ground_refs`／`relevant_ground_refs` 的判斷。若 `ground_recall`／`ground_precision` 出現在相容欄位中，狀態應是 `SKIP`，不能當成零分或 Ground quality score。resolved ref 數量是操作證據，不等於回答語義支持。每個 case/turn 要以同一 `case_id:T<turn>` 交叉核查 `02_Turns`、`03_Metrics` 和 report evidence refs。

## 5. 何時使用 baseline、experiment、stability

- **Baseline**：已有通過 schema、digest、`FINAL` 狀態且 measurement contract 相容的正式 workbook，要比較新版本時使用。規則、Judge prompt 或案例契約不相容時，不宣稱全局改善。
- **Experiment**：metrics 已定位具體假設，且只改一個註冊變數時使用；其他條件、輸入和版本固定，按 `evaluator-config.yml` 的 repeats/seeds 執行。
- **Stability**：相同 deployment、model、prompt、knowledge、hyperparameters 和 case/turn 集合需要測重複性時使用；至少兩個 run。穩定地答錯仍是錯。

受控實驗聚合：

```bash
xiaoan-eval experiment \
  --baseline private/<baseline>.jsonl \
  --variants private/<variant-1>.jsonl private/<variant-2>.jsonl \
  --baseline-manifest private/<baseline-manifest>.json \
  --variant-manifests private/<manifest-1>.json private/<manifest-2>.json \
  --target-cohort <cohort> --lever-type <registered-variable> \
  --target <metric> --output runs/<run-id>
```

穩定性聚合：

```bash
xiaoan-eval stability \
  --runs private/<run-1>.jsonl private/<run-2>.jsonl private/<run-3>.jsonl \
  --manifests private/<manifest-1>.json private/<manifest-2>.json private/<manifest-3>.json \
  --output runs/<final-run-id>
```

## 6. 人工審核

人工審核是 exception-triggered。對 `PENDING_REVIEW` pair 匯出 blinded packet：

```bash
xiaoan-eval export-human-review runs/<run-id> \
  --rating-rule 'ratings rule.yml' \
  --output private-review/<run-id>-review.xlsx
```

Reviewer 只填藍色欄位：每個 red line 填 TRUE/FALSE，每個 dimension 填有錨點的 `0/1/2/3`，低於 3 分寫扣分原因，只引用 `03_Evidence` 列出的 refs。`reviewer_id` 是作業標籤，不是身分驗證。

匯回原 packet：

```bash
xiaoan-eval import-human-review private-review/<run-id>-review.xlsx \
  --rating-rule 'ratings rule.yml' \
  --output runs/<run-id>
```

匯入會驗證 response、rubric、evidence 和 generation binding，保留 automatic、human、final 三種來源。AI 與人工 red-line 不一致時，狀態為 `NEEDS_ADJUDICATION`，final score 留空；完成決定後：

```bash
xiaoan-eval adjudicate runs/<run-id> \
  --case TC-01 --turn 1 --decision human \
  --adjudicator <作業標籤> \
  --rationale '依據 evidence refs 複核後接受人工判斷。'
```

## 7. 回傳 baseline 和人工結果做 Judge 校準

校準是比較 Judge 與已審核人工基準，不是用 Judge 產生 oracle：

1. 完成代表性 cases 的人工審核和必要 adjudication，凍結 benchmark version、case/turn、response、authoritative context、rubric 和 evidence digest。
2. 保存原始 `results.xlsx`、blinded packet、匯入後的 human/final rows 和 manifest；不要只保留平均分。
3. 在 `03_Metrics` 按 metric/dimension 比較 automatic Judge 與 human/adjudicated score；在 `06_Human_Review` 查看 disagreement、unavailable denominator 和 provenance。
4. `xiaoan_eval.calibration` 有 frozen benchmark、annotation、agreement report 和 judge-run schema/API；目前 CLI 沒有獨立的 `calibrate` 子命令，不可臆造不存在的命令。校準資料應透過既有 review workbook 和 calibration API 管理。
5. Judge model、prompt、rating rule 或 schema 變更後，記錄 configuration drift；影響可比性時重建 baseline 和 benchmark。

校準結果只衡量 Judge 的測量品質，不會自動批准 testcase oracle、實驗候選或 release gate；reviewer／adjudicator 身分與簽核需在流程外確認。

## 8. 常見誤讀

- 平均分不代表每個 case 都通過；同時看 case 分布、pass rate 和 hard gate。
- `route_acceptance` 高不代表回答有足夠 Capsule 支持；還要看 claims、evidence refs 和 alignment。
- resolved Ground refs 多不代表回答引用正確；本版本不對 `required_ground_refs`／`relevant_ground_refs` 做 precision/recall 判斷。
- 不把 provider error、timeout、Judge unavailable 或缺少 telemetry 轉成品質零分。
- 沒有單變量、重複且控制條件一致的 experiment，報告建議仍是待驗證假設。
