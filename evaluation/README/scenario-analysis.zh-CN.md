# 情境標籤、Faithfulness 與 Answer Relevancy 分析

兩套 evaluator 的 `run` / `report`，以及 `evaluation_multimodels` 的 `matrix` 入口均支援以下可選旗標：

- `--scenario-analysis`：產生離線診斷，即使沒有標籤或 AR 也列出缺失。
- `--scenario-annotations PATH`：匯入依使用者歷史標註的情境；會同時啟用分析。
- `--answer-analysis PATH`：匯入已計算的 Answer Relevancy；會同時啟用分析。
- `--analysis-subject-id ID`：單模型身份。通常從 run manifest 的 `model_ids.response` 或已凍結 trace 的 `models.response` 取得；無法核實時為 UNKNOWN，不能接受 AR sidecar。

這些旗標不呼叫 LLM、embedding 或外部 API。原本 run/matrix 的 subject/Judge 呼叫仍由原有配置決定。沒有反向問題及 embedding 結果時，AR 是 UNAVAILABLE，不自動付費生成。

## 本批 32 案的完整離線重建

在倉庫根目錄：

```bash
python evaluation/examples/build_minimal32_scenario_analysis.py
python evaluation/examples/export_minimal32_answer_analysis.py
```

進入 `evaluation` 後執行：

```bash
python -m xiaoan_eval report \
  runs/2026-09-21-minimal32-scenario-analysis/diagnostic-case-results.jsonl \
  --output runs/2026-09-21-minimal32-integrated-report \
  --scenario-analysis \
  --scenario-annotations oracles/minimal32-remediation/scenario-analysis/turn-annotations.json \
  --answer-analysis runs/2026-09-21-minimal32-scenario-analysis/answer-analysis.json
```

使用已凍結的 89 回答、267 反向問題及原 Google embeddings；沒有新增 API 呼叫。適配器驗證原任務、回答與 snapshot 綁定後匯入，7 個未回答／未執行輪仍保留在 96 輪執行分母。

## 新的 run / matrix

在原本可執行的 `python -m xiaoan_eval run ...` 或多模型 `python -m xiaoan_eval matrix ...` 命令後，加上 `--scenario-analysis`，或加 `--scenario-annotations /absolute/path/turn-annotations.json`。單模型 run 自動記錄完整 planned_turns 與 manifest subject 身份，未執行輪不消失。

現有 primary Judge、獨立 attribution、semantic oracle、route/ground/history 指標直接從本次結果分析，不需要搬到另一份 JSON。若 attribution provider 未啟用、Judge 失敗或語義資料尚未產生，對應項目為 UNAVAILABLE。matrix 的原有 primary/self-judging eligibility 不變；AR 另按每個 subject 回答去重，不按 Judge 數量加權。

新 run 的 AR 不能借用本批 89 輪分数：需對新凍結回答生成 N 個反向問題，使用固定向量模型計算原問題與反向問題餘弦，再輸出下述 sidecar。當前接入只接受已有本地結果；不提供通用自動付費 AR 執行器。當前問題的 raw-query AR 與使用歷史改寫的 contextual AR 必須分開，不應取較高者。

## 標籤格式與綁定

JSON 根節點：`{"schema_version":"scenario-annotations/v1","annotations":[...]}`。每條包含：

```json
{
  "case_id": "TC-01", "turn": 1,
  "user_history_sha256": "sha256 of canonical user prefix",
  "annotation_status": "PROVISIONAL",
  "task_family": ["安全處置"], "task": ["立即避險"],
  "topic": ["急性危險"], "constraints": [], "dialogue": ["首輪"], "risk": ["必須crisis"],
  "need_summary": "本輪必要需求", "rationale": "使用者內容依據"
}
```

hash 是 UTF-8 SHA256，輸入 `[{"turn":1,"user":"原始用戶文字"}, ...]` 截至本輪，JSON 使用 `ensure_ascii=False, sort_keys=True, separators=(',', ':')`。標註不能讀模型本輪回答或實際 route 倒推。不同模型共用同一用戶前綴標籤。缺失或 hash 不匹配為 UNLABELED；PROVISIONAL 不等於人工 REVIEWED。多選標籤不可相加當總量。

## AR sidecar

根節點：`{"schema_version":"answer-analysis/v1","results":[...]}`。每條同時有 case_id、turn、subject_id，及 `binding`：

```json
{
  "case_id": "TC-01", "turn": 1, "subject_id": "model-id",
  "binding": {
    "case_id": "TC-01", "turn": 1, "subject_id": "model-id",
    "answer_sha256": "raw answer UTF-8 SHA256",
    "context_sha256": "canonical complete effective_context_snapshot SHA256"
  },
  "answer_relevancy": {
    "status": "AVAILABLE", "n": 3, "query_mode": "raw_current_user",
    "questions": ["反向問題1", "反向問題2", "反向問題3"],
    "similarities": [0.8, 0.9, 0.7],
    "embedding_model": "fixed-model", "embedding_revision": "fixed-config-and-revision",
    "generator_model": "fixed-generator", "prompt_version": "reverse-question-prompt/v1"
  }
}
```

`xiaoan_eval.scenario_analysis.binding(...)` 提供生成 binding 的純函數。context hash 採上述 canonical JSON；完整 snapshot 缺失、模型未知、模型／回答／上下文不一致均不採用分數。query_mode 必須為 raw_current_user，禁止混入 contextual 分數。N、問題數與餘弦數必須相等；NaN、無限值、超出 [-1,1] 都拒絕。重算均值，不信任外部 score。這是本地計算產物的身份契約，不是重新驗證向量服務或 Judge 的正確性。

## 報告位置與口徑

普通 run/report 仍只發佈 `results.xlsx` 與 `report.md`；可讀表結構已在2026-09-22擴充，詳見文末。`03_Metrics` 的 `scenario.groups`、`scenario.answer_groups`、`scenario.turns`、`scenario.claims`、`scenario.claim_groups` 保存完整 JSON 明細，可依 metric_id 篩選；核心 digest 覆蓋這些明細，round-trip 會驗證。matrix 與 pair 工作簿都產生 Claims、Evidence、Relevancy、Requirements、Groups，並擴充原 All_Answers 表。

- primary binary：原主 Judge 聲明清單，文字去重，同文有分歧時採 AND，保留原口徑。
- strict entailment proxy：獨立聲明清單，PARTIAL 不计完整支持；不等同已聯合裁決的原子 claim Faithfulness v2。
- 原有 0.5 PARTIAL-weighted attribution 指標完全不改，與 strict proxy 分欄解讀。
- claim.kind、support category、unsupported category 分開統計。layer 分組依該層關係判定：CAPSULE ENTAILS 不會把 SOURCE PARTIAL 算成 SOURCE ENTAILS；同 claim 可跨層，但整體只計一次。
- claim facts 來源是原管線已驗證的 attribution，這個分析器另外核對回答 span；不另外呼叫 Judge 或重新進行全上下文聯合裁決。
- 必要需求覆蓋由 existing required oracle 項目计算：SATISFIED／(SATISFIED+VIOLATED)，另列 UNCERTAIN；不是 ground 文字復述率。
- AR 分組含 case/turn 數、有效與缺失數、均值／中位數／最小最大值；是語義對齊代理，不是正確率、完整性、安全或簡潔度。
- claim 與需求的語義相關性、冗餘比例尚未標註時顯示 UNAVAILABLE，不從其他指標推算。
- 診斷表將需求標籤、actual route、oracle／route／注入／history 指標、claim 支持和 AR 放在同輪；`HYPOTHESIS` 指明需核對的 stage 和 next_check。不能僅憑低分宣布 Router/Composer 有因果缺陷。

表內 `quality_focus` 是原案例輔助維度，不代替本輪任務標籤。未回答輪不按零分計入品質均值，但留在執行與可用率分母。未審標籤、樣本量小、跨模型不同有效面板，均只能描述性比較。

## 2026-09-22：可讀 Excel 明細

正常 run/report 現在預設產生明細，不必額外啟用 --scenario-analysis。情境標籤與AR仍由可選參數匯入；沒有資料保持UNAVAILABLE。

- `02_Turns`：原有對話表新增情境、需求、指標及診斷欄位；缺失計畫輪以diagnostic列保留。
- `Claims`：每個Judge的聲明原文、類型與支持判定。
- `Evidence`：每條claim與引文的關係，含證據原文與位置。
- `Relevancy`：每個回答的反向問題及餘弦，跨Judge去重；不可用回答有狀態列。
- `Requirements`：必要和禁止要求、判定、理由、回答引文及oracle狀態。
- `Groups`：情境分組分母及統計；AR使用answer-level去重面板。

不新增Review_Turns。matrix沿用All_Answers並擴充摘要，主工作簿與pair工作簿都包含上述五個明細表；Judge相關的摘要不冒充回答層級單一判定。

工作簿核心schema不改寫歷史評分；新增独立版號`readable-details/v1`。讀取器相容原10表格式，並將新表與核心scenario facts重算比對；篡改可讀表會校驗失敗。重新匯出也會重建明細。超長claim／證據／要求按part、parts分段，同鍵按part重組；機讀facts同步分段，不靜默截斷。

03_Metrics保留機讀facts供審計，使用者直接閱讀上述明細表。這不是新增語義Judge，亦沒有新增API費用。
