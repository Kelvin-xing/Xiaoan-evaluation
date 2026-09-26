# evaluation｜單一 XiaoAn Chatflow 的端到端評估

> **2026-09-22 新增：** `measure unified` 共用一次抽取的 claim 清單，分開支持／正確性／安全任務 gate；`measure capsule-ablation` 提供固定 Composer context 對照。新版本不改寫舊分數。完整合約、命令、人工校準與 live 驗證邊界見 [evaluation-unified-v1](../../docs/implementation/evaluation-unified-v1.md)。

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
| 凍結答案的雙序 pairwise CLI | `measure pairwise` 提供独立入口；ordinary run 尚非整批先凍結的調度模式 |

## 2. 安裝與環境

```bash
cd evaluation
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 PYTHONPATH=. python -m pytest -q
```

兩個 project 都使用 `xiaoan_eval` 與 `xiaoan-eval` 名稱，請分開 virtualenv。
三个评估项目统一从 `evaluation_multimodels/.env` 读取模型、GlobalAI 地址和三家 key。
源码使用时保持两个 evaluation 目录相邻；内置插件不再读取旧项目的模型配置。
Google embedding 的模型、API 地址、key、任务类型和维度均从共享文件读取；保留原有 Google 官方连接，不走 GlobalAI。
完整配置规则见本页“共享模型配置”。Credentials 不进入 Git、report 或 workbook。

## 3. 案例與版本準備

`test-cases/*.yaml` 預設74案217輪；檔案標記均為REVIEWED，但沒有APPROVED_AGGREGATE。正式集只有4輪route、24輪safety oracle、6個memory-use checkpoints，response_oracle已覆蓋217輪，並由mat於2026-09-13全部核准。這些是已撰寫標籤的覆蓋，不是agent通過結果。

`test-cases/proposed/` 的九份草案不自動載入；TC-17／52內容已合併正式案；TC-75–81共14輪response oracle已核准，memory harness與遙測仍待完善。不要把proposed直接混入同ID正式案例或自動改成approved。

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

v2本機完整測試248 passed；發布前亦於standalone clone驗證。全部為離線合成／mock測試，不代表真實case通過率。v3 已補語意 oracle、observer task outcome、工具檢查及 case-cluster 方法入口；待完成真實資料校準、observer/harness 接線、逐情境 rubric、人類 benchmark 與核心去重；詳見 Shared Guide 第15節及 v3 方法文件。

## Response oracle 已核准（2026-09-13）

[審核紀錄與Excel](../../docs/response-oracle-review/2026-09-13/README.md)：使用者mat已全部核准81案231輪。既有74案217輪已回寫正式來源；另7案14輪memory提案保留proposed，尚未納入預設suite。全部內容標记REVIEWED，APPROVED_AGGREGATE仍為0。核准內容不等同agent已通過評估。

## 評估方法 v3

### Oracle 引文定位（2026-09-13）

Judge 提供逐字原文 `quote` 與 Unicode 字符位置 `start/end`（從0開始，end不含）。位置精確匹配則接受；位置不符時，僅在 quote 非空且在回答中**唯一精確出現**時由程式定位，不模糊匹配、不修改引文。找不到、存在多個候選（含重疊）、非法欄位仍拒絕；重複引文若原始位置正確仍可接受。

標準化結果中的 `span_resolution` 記錄 `exact-quote-location/v1`、oracle ID、span index、原始與修正位置；私有 checkpoint 另記 `<judge_event>_span_resolution`，原始 Judge JSON 保持不變。`<judge_event>_validation=OK` 現在代表 JSON、claim refs 與 oracle 全部校驗完成。這只修正證據位置，不修改語義判定；仍無效的結果維持 UNAVAILABLE，後续可重試，單次 JudgeClient 不自動發起額外付費請求。

此變更適用於本 `evaluation` project。已通過287項離線測試，並以既有10個引文定位失敗評審離線驗證；原有run的Excel與判定不會因此被覆寫。

[完整操作與資料契約](measurement-methods-v3.zh-HK.md)：新增`measure`的answer/retrieval/oracle/pairwise/cluster/outcome/perturbation/calibration/online入口。主Judge已接semantic oracle，排序報告可讀已reviewed retrieval oracle及匹配trace版本。真實gold、harness與線上資料仍由團隊提供，不把合成範例當產品能力驗證。


### Test case 引用 oracle（2026-09-13）

正式 74 案 217 轮已增加按当前 content 快照绑定的分流、安全与引用标签。新增标签单独待审核，原回答 oracle 审核不被撤销，也不会被继承到新标签。详情与 217 轮审核表见 [引用更新说明](../oracles/README.zh-CN.md)。仍需区分来源缺口、运行证据缺失与不适用指标。

## 輸出盤點

完整的交付文件、工作表、指標及可用條件見 [Evaluation 輸出盤點](output-inventory.zh-HK.md)。


## LLM Report Agent

正式 CLI 的最終 `report.md` 已改由 LLM Report Agent 讀取 `results.xlsx` 後生成，舊 Markdown 模板不再作預設或失敗備援。設定、定義表載入、離線報告重試與失敗恢復見 [Report Agent 使用說明](report-agent.zh-HK.md)。

## 共享模型配置（2026-09-23）

`evaluation`、`evaluation_multimodels`、`evaluation_report_agent` 的内置 live 调用
统一读取仓库的 `evaluation_multimodels/.env`。模型字段以文件为准，进程环境变量、
旧项目 `.env` 和写死默认值不再决定模型；必需字段缺失时在调用前报错。

- 矩阵 answer：`XIAOAN_{CLAUDE,GPT,GEMINI}_{LATEST,SECOND}_MODEL`。
- 矩阵 judge：`XIAOAN_{CLAUDE,GPT,GEMINI}_JUDGE_MODEL`。
- 普通评估：`XIAOAN_JUDGE_MODEL`、`XIAOAN_SECONDARY_JUDGE_MODEL`。
- 建议与报告：`XIAOAN_RECOMMENDATION_MODEL`、`XIAOAN_REPORT_MODEL`。
- Unified：`XIAOAN_CLAIM_EXTRACTOR_MODEL`、`XIAOAN_CLAIM_ASSESSOR_MODEL`。
- 被测服务：`XIAOAN_SAFETY_MODEL`、`XIAOAN_ROUTER_MODEL`、`XIAOAN_RESPONSE_MODEL`；
  多模型服务可选列表为 `XIAOAN_ROUTER_MODELS`、`XIAOAN_RESPONSE_MODELS`。

API key 分别为 `XIAOAN_CLAUDE_API_KEY`、`XIAOAN_OPENAI_API_KEY`、
`XIAOAN_GEMINI_API_KEY`，统一使用 `GLOBALAI_API_BASE`。
矩阵自定义清单只能选文件中配置的相应模型；Report Agent 的 `--model` 若与文件冲突会报错。
Unified 输入中的模型身份必须与对应字段相同，避免篡改冻结证据和检查点身份。

新运行 manifest 的模型字段从共享配置生成，旧 manifest／结果／检查点不重写。
普通评估会显式传入 Router／回答模型，并核对服务的 Safety 配置及返回 trace；
服务不匹配时需先配置并重启。远端服务仍须由部署者加载对应配置；评估器不会修改远端部署。
自定义第三方插件应自行遵守同一契约，其内部请求不受内置配置模块控制。
修改配置后重启服务与评估进程。配置与离线测试通过不等于供应商已确认模型可用。

反向问题生成示例使用 `XIAOAN_RELEVANCY_MODEL`；旧 Google embedding 示例的型号使用
`GOOGLE_EMBEDDING_MODEL`。旧实验的固定端点和证据授权检查仍保留，不会自动扩大历史数据发送范围。

Embedding 配置同样位于 `evaluation_multimodels/.env`：`GOOGLE_EMBEDDING_MODEL`、
`GOOGLE_EMBEDDING_BASE_URL`、`GOOGLE_EMBEDDING_API_KEY`、`GOOGLE_EMBEDDING_TASK_TYPE`、
`GOOGLE_EMBEDDING_DIMENSIONS`。继续使用 `gemini-embedding-001`、Google 官方 `v1beta` 地址、
原有专用 key、`SEMANTIC_SIMILARITY` 和 3072 维；缓存／输入／输出路径保持不变。
