# evaluation｜單一 XiaoAn Chatflow 的端到端評估

**2026-09-13 · scoring `response-effectiveness/v2` · workbook `2.1`**

本 project 用實際部署的 Chatflow 執行多輪案例，保存 trace，判定安全／oracle／品質，產生可覆核的 Excel 與 Markdown。適合產品回歸、定位失敗階段、比較受控修改；多 subject×Judge 矩陣請用 [evaluation_multimodels](../../evaluation_multimodels/README/README.md)。

完整共同設計請讀 [Shared Guide](../README_SHARED.md)，包括 metrics 公式、記憶與歸因、Judge 校準、分母與所有限制。遷移細節見 [v2 修復紀錄](measurement-contract-v2.zh-HK.md)。

## 1. 本 project 能做什麼

| 能力 | 狀態與邊界 |
| --- | --- |
| Case→HTTP→trace→Judge→report | 已實作；同 case turns 順序執行，獨立 cases 預設並行2 |
| 0–3 rubric／動態權重／紅線 | 已實作；v2 同 suite／matrix公式，缺失不當零分 |
| route／safety／response oracle | 按已批准且非空oracle判定；沒有oracle不當答錯 |
| Memory | 八種類型共用observer；缺遙測SKIP，完整summary在ordinary報表仍有限 |
| Attribution | 可選插件，需要snapshot及span/ref驗證，不是trace路由推論 |
| 人工覆核／裁決 | blinded XLSX、immutable binding、原權重、重算final verdict |
| Baseline／experiment／stability | 已有流程；固定版本、可比資料、單變量，不等於自動因果證明 |
| 整批答案先凍結再任意重評／pairwise CLI | 尚未在ordinary run提供完整流程 |

## 2. 安裝與環境

```bash
cd evaluation
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q
```

兩個 project 都使用 `xiaoan_eval` 與 `xiaoan-eval` 名稱，請分開virtualenv。Standalone repo包含evaluator，不包含完整Chatflow服務與知識庫，實際run需已有endpoint及context provider。提供的 `company_eval_plugins.py` 優先使用monorepo settings；standalone fallback讀project-local環境設定。Credentials不進Git、report或workbook。

## 3. 案例與版本準備

`test-cases/*.yaml` 預設74案217輪；檔案標記均為REVIEWED，但沒有APPROVED_AGGREGATE。正式集只有4輪route、24輪safety oracle、6個memory-use checkpoints，response_oracle為0。這些是已撰寫標籤的覆蓋，不是agent通過結果。

`test-cases/proposed/` 的九份草案不自動載入；TC-17／52 response提案及TC-75–81 memory提案均待審閱與遙測。不要把proposed直接混入同ID正式案例或自動改成approved。

更新 `manifest.json`：本次deployment、policy、Prompt hashes、knowledge versions、model IDs、rule hash、Judge prompt、seed、retry及hyperparameters。Repo歷史manifest值不能直接充當新run的真實版本。

設定 `run_config.quality_threshold` 才會有品質合格判斷。`null` 表示NOT_CONFIGURED；例如2.0只是配置例子，不是已校準門檻。

## 4. 執行

```bash
xiaoan-eval preflight test-cases --rating-rule 'ratings rule.yml'
xiaoan-eval run test-cases \
  --base-url http://127.0.0.1:8000 \
  --judge-plugin company_eval_plugins:judge \
  --context-provider company_eval_plugins:authoritative_context \
  --manifest manifest.json --config evaluator-config.yml \
  --rating-rule 'ratings rule.yml' --case-concurrency 2 \
  --output runs/team-demo
```

Primary與context provider必填。可選 `--secondary-judge-plugin company_eval_plugins:second_judge`、`--attribution-judge-plugin module:callable`（需自行提供符合契約的插件）、`--baseline previous/results.xlsx`、`--release-review`。Secondary未配置或provider不可用，不丟棄可用primary；記錄原因。雙Judge有分歧可轉人工覆核。

Ordinary transport使用POST `/v1/conversations`、POST `/v1/conversations/{id}/responses/stream`；必需debug包含safety、route、ground、output_guard、state、timings。缺欄位是接口錯誤，不能靠Judge猜測。

輸出目錄必須空白或已含可驗證的正式pair；不會默默刪除未知檔案。私有suite ledger/checkpoint在正式目錄外；`--suite-ledger`可指定位置。

## 5. 如何讀分數與狀態

先讀 execution／quality eligible／oracle coverage，再看安全、品質與證據。timeout、缺輪、必要evidence或Judge錯誤使quality UNAVAILABLE/null，不加入Overall。真實0分仍保留為數字0。

七維度base weights為0.22、0.18、0.18、0.13、0.09、0.09、0.11；focus乘1.5後全部歸一化。每輪是七維度加權和，完整case跨預期turns取平均；完整可評case命中紅線則0。Scenario只聚合APPROVED_AGGREGATE。

`execution_status`和`quality_verdict`分開：全部維度1、閾值2，可能execution PASS但quality FAIL；未配置閾值NOT_CONFIGURED；未批准oracle NOT_APPROVED。`Execution gate pass rate`不是品質通過率。

## 6. 正式輸出

每run只有 `results.xlsx` 與 `report.md`。Workbook schema2.1：

| Sheet | 用途 |
| --- | --- |
| 00_Overview | verdict、有效分母、Overall、coverage、baseline/experiments |
| 01_Cases | automatic/human/final、動態權重、閾值、品質/執行/批准狀態 |
| 02_Turns | 輪次與全文chunks，`row_kind=text` |
| 03_Metrics | 逐case/turn/metric/source、值與evidence |
| 04_Baseline／05_Experiments | 比較與受控修改 |
| 06_Human_Review／07_Stability | 人評來源與重複穩定性 |
| 08_Metadata／09_Data_Dictionary | 版本、digest、facts與欄位定義 |

從finding回到case/turn、evidence ref、snapshot，定位最早可證明出錯的階段。route正確不代表內容已注入；ref存在不代表語義支持；語義支持不等於因果使用。完整定義見Shared Guide。

## 7. 人工覆核與裁決

```bash
xiaoan-eval export-human-review runs/team-demo \
  --rating-rule 'ratings rule.yml' --output private-review/team-review.xlsx
# 人工完成必填評分、紅線與證據後
xiaoan-eval import-human-review private-review/team-review.xlsx \
  --rating-rule 'ratings rule.yml' --output runs/team-demo
```

有紅線分歧時使用 `adjudicate --case ... --turn ... --decision automatic|human --adjudicator ... --rationale ...`。原動態權重、threshold和execution status保存於workbook；重算final verdict，未覆核案例不被改分。reviewer ID是操作標記，不是身份認證。Original API error不能透過人工填分消除。

## 8. Baseline、實驗與遷移

`run --baseline previous/results.xlsx` 要求普通FINAL workbook且schema、scoring、rule與Judge prompt可比。任一側quality缺失，delta=null；不補零。Matrix workbook不能當ordinary baseline。

`experiment`、`auto-experiment`、`auto-file-experiment` 分別聚合已跑變體、執行受控變體、執行allowlisted檔案變體。現有預設seeds101/202/303，門檻與註冊變量以 `evaluator-config.yml` 為準。先固定控制，再改一項變量；推薦仍是待驗證假設。

2.0 workbook可讀及驗digest，缺原動態權重不能新做人評。需從原case/rule/evidence重新生成；不要直接拿v1/v2分差當能力提升。

## 9. 驗證與待辦

v2本機完整測試248 passed；發布前亦於standalone clone驗證。全部為離線合成／mock測試，不代表真實case通過率。Known gaps包括response/task oracle覆蓋、真正工具結果與goal outcome、逐情境rubric、人類benchmark、case-cluster不確定性、核心去重；詳見Shared Guide第15節。
