# XiaoAn RAG Agent Evaluation 方法論

更新：2026-09-04

## 1. 目的

XiaoAn 不是單一的 vector search + generation chain，而是：

```text
user input
  → PII/safety
  → route/capsule
  → source/wiki/ground resolution
  → response composition
  → output guard
  → state/memory update
```

Evaluation 的目的不是只產生一個總分，而是回答三個問題：

1. 回答是否安全、正確、可追溯？
2. 若失敗，失敗位於哪一個 stage？
3. 哪一個變更值得以實驗驗證？

## 2. 評估流程

### 2.1 Case 與 oracle

每個 case 是 versioned YAML。`expected` 是人工可審核的 acceptable-outcome contract，不是固定答案文字。

Oracle 至少可包含：

- `safety_levels`：可接受安全等級；
- `route_ids` / `preferred_route_id`：可接受與最佳 route；
- `source_refs`、`wiki_refs`、`capsule_ids`：分層證據預期；
- `response_oracle`：required/forbidden claims、must-cite、abstention、tool、goal 與長度預期；
- `memory_checkpoints`：多輪應保留且在適當時使用的 facts。

正式 release gate 只使用 `oracle_provenance.status=approved`。`provisional` 只用於診斷，避免模型或 evaluator 自己產生的 oracle 反過來定義正確答案。

### 2.2 執行與 trace

每個 case 建立獨立 conversation，按 YAML turns 串行呼叫 Chatflow。Transport adapter 將不同版本 debug response 正規化為：

```text
safety, route, ground, source, wiki, capsule,
answer, guard, tools, agent, state, timings, tokens
```

Pipeline 為每個 approved turn 建立 `pipeline.observations`，保存：

```text
expected oracle + actual trace + ranked refs + citations
+ tool calls + goal/steps + primary judge claims
```

這個 observation 是 v3 metrics、報告和 diagnosis 的共同資料來源。為保持 v2 artifact 相容，
`summarize_rag()` 仍會從 `pipeline.turns` 讀取既有 deterministic route 指標與 Ground
解析狀態；Ground ref ranking 不再計分，route confusion 與 v3 aggregate 則只讀 approved
observations。兩者的分工會在後續 schema
major version 合併，避免把 legacy score 與 v3 observation 混成不同分母。

### 2.3 評分順序

1. schema/trace completeness；
2. PII、unknown route、output guard、ground resolution hard gates；
3. deterministic route/safety/ground/memory/performance metrics；
4. approved turn 的 retrieval、claim、citation、refusal、tool metrics；
5. primary/secondary judge；
6. quality rubric aggregation、human review 與 recommendation。

Evaluator error、provider error 和 unavailable telemetry 不當成產品 0 分；它們應是 `error` 或 `skip`，並從產品 pass-rate 分母中明確區分。

## 3. Metrics 定義

### 3.1 Retrieval

本節的 precision/recall/F1 只適用於存在人工審核 retrieval oracle 的獨立檢索實驗。現行
XiaoAn 主流程沒有使用 `required_ground_refs` / `relevant_ground_refs` 作為 Ground oracle，
因此這些公式不會自動套用到一般 evaluation run；沒有 oracle 時必須輸出 `SKIP` 或
`UNAVAILABLE`。

對 reviewed ref 集合：

```text
TP = retrieved ∩ relevant
FP = retrieved - relevant
FN = required - retrieved
```

```text
precision = TP / (TP + FP)
recall    = TP / (TP + FN)
F1        = 2 × precision × recall / (precision + recall)
```

`required` 與 `relevant` 可不同，因此報告中的 counts 是「required recall + relevant precision」的 canonical counts，不把 optional relevant ref 誤算成 FP。

TN 只有在存在有限且完整的 `universe` 時才計算：

```text
TN = universe - relevant - retrieved
```

沒有 universe 時，TN 必須是 null/不可評估，而不是猜測整個 corpus。

若 trace 提供明確的 ranked refs，才計算：

```text
MRR  = 1 / rank(first relevant ref)
nDCG = DCG(ranked refs) / ideal DCG
```

重複 ref 先按首次出現去重，避免同一 evidence 重複灌高分。

### 3.2 Route 與 safety

- accepted accuracy：actual 是否落在 accepted set；
- preferred accuracy：actual 是否等於 preferred route；
- confusion matrix：只有單一 canonical expected class 才納入；
- macro-F1：各 class F1 的平均；
- micro precision/recall/F1：全體 instance 的 aggregate；
- multi-accepted oracle：保留 accepted accuracy，但不捏造唯一 class。

Safety 的 high-risk recall 應由 class-level recall 讀取，不能用 overall accuracy 取代。

### 3.3 Answer、claim 與 citation

對 judge 回傳的 atomic claims：

```text
claim TP = required claim 被 supported claim 覆蓋
claim FN = required claim 沒有被覆蓋
claim FP = 額外且 unsupported 的 claim
```

另行報告：

```text
faithfulness = supported claims / all judged claims
unsupported claim rate = unsupported claims / all judged claims
```

這樣「漏答 required claim」不會與「講了 context 不支持的額外 claim」混成同一種失敗。

Citation 使用 `must_cite` 與實際 `citations` 計算 precision/recall。沒有 citation oracle 時標記 skipped，不把未知當成失敗。

### 3.4 Capsule／Ground 依循與歸因

「選中了哪個 Capsule」、「載入了哪些 Ground」與「回答實際依照哪些內容」是三種不同事實，不可用單一 route 或 ref count 互相代替。

#### 3.4.1 Ground 解析（不做 ref oracle 評分）

Chatflow 透過 `ground.resolved_refs` 報告實際解析的 Ground refs。現行評估**不再使用**
`required_ground_refs` 或 `relevant_ground_refs` 判斷 Ground precision/recall；這兩個欄位不是
可信的產品品質 oracle，保留在舊 YAML 時也只會被忽略。Ground 目前只回答兩個可驗證問題：

1. trace 是否存在 Ground 欄位；
2. resolver 是否回報 `resolution_errors`、明確 `resolution_error` 或 warning。

因此 `ground_resolution` 是 hard gate/操作健康度指標；`ground_recall` 與
`ground_precision` 只以 `SKIP`（原因為「不評估 Ground citation oracle」）輸出，不能進入
平均分，也不能被解讀為引用品質。`resolved_refs` 數量及 `rag.attribution` 分類
（`grounded_capsule`、`grounded_baseline` 等）只代表 trace 中發生的操作事實，不代表回答在語義上
使用了 Ground。

#### 3.4.2 Capsule claim alignment

Evaluator 從 trace 取得實際注入 Composer 的 Capsule units，並建立：

```text
capsule:<capsule_id>:<unit_id>
```

Primary Judge 必須把回答拆成 substantive claims，並只可引用 evaluator 提供的 `evidence_catalog`。Claim 引用了當輪實際注入的 Capsule unit，才算 Capsule-aligned。

```text
Capsule claim alignment
= 有至少一個有效 Capsule ref 的 claims
  / 有 evidence_refs 的 claims

Capsule content coverage
= 被至少一個 claim 引用的 Capsule units
  / 所有注入的 Capsule units

Capsule citation precision
= 有效 Capsule refs
  / Judge 回傳的所有 Capsule refs
```

`report.md` 的 Capsule 引用分數目前使用 `Capsule claim alignment`。這組指標標記為
`LEGACY_OBSERVATIONAL_ONLY`：它是受 schema 約束的 Judge 歸因，不是 token-level 因果證明。
若 trace 沒有可驗證的 injected units，分數為 `UNAVAILABLE`，不能補成 0。

#### 3.4.3 Semantic attribution

若執行時配置獨立 Attribution Judge，Evaluator 會使用 `effective_context_snapshot`。Evidence catalog 只包含當輪真正暴露給 Composer 的 context units，並保留 layer、occurrence、原文 span 與 hash。

Attribution Judge 對每個 substantive claim 標記其與證據的關係：

```text
ENTAILS      = 1.0
PARTIAL      = 0.5
CONTEXT_ONLY = 0.0
CONTRADICTS  = 0.0
UNSUPPORTED  = 0.0
```

Substantive claims 包含 `FACTUAL`、`INTERPRETIVE`、`RECOMMENDATION` 與 `ACTION`；純支持性語句不進入此分母。

```text
overall claim support rate
= 每個 substantive claim 的最高支持權重總和
  / substantive claims 數量

layer support rate
= 某 layer 對各 substantive claim 的最高支持權重總和
  / substantive claims 數量
```

Layer 可分為 `CAPSULE`、`WIKI`、`SOURCE`、`PROMPT`、`CURRENT_INPUT`、`PRIOR_USER` 與 `PRIOR_ASSISTANT`。因此可分開觀察回答在多大程度受 Capsule、Ground source/wiki 或對話內容支持。

另行計算 exposed-unit utilization：被任一 `ENTAILS/PARTIAL` relation 使用的 context occurrences，除以暴露給 Composer 的 occurrences。它衡量 context 使用範圍，不代表所有暴露內容都必須被使用。

Attribution 結果必須通過本地驗證：answer/evidence span 必須與原文完全相符、ref 必須存在於 snapshot-bound catalog、`UNSUPPORTED` 不得附帶虛構證據。驗證失敗時標記 `UNAVAILABLE`，不得補零。

#### 3.4.4 判讀層級

| 指標 | 可以證明 | 不可以證明 |
| --- | --- | --- |
| route/capsule ID | 系統選中了哪個 Capsule | 回答使用了 Capsule 內容 |
| `resolved_refs` | 系統解析了哪些 Ground | 回答依照了 Ground |
| Ground precision/recall | 檢索結果符合 reviewed oracle 的程度 | Claim 的語義忠實度 |
| Capsule claim alignment | Judge 將多少 claims 歸因到有效 Capsule refs | token-level 因果來源 |
| Semantic attribution by layer | Claim 與當輪可見證據的語義支持程度 | 沒有校準誤差的真實因果關係 |

正式結論應同時呈現檢索品質與 answer attribution。只有 route 或 Ground trace 時，結論必須限定為 operational attribution；不能寫成「回答已依照 Capsule／Ground」。

### 3.5 Refusal

以 `should_abstain` 作 gold，以 trace `abstained` 作 prediction：

```text
TP = 應拒答且已拒答
FP = 不應拒答但拒答
FN = 應拒答但未拒答
TN = 不應拒答且未拒答
```

這可分別觀察 safety 漏攔截與過度拒答。

### 3.6 Agent/tool/state

- tool precision/recall/F1：expected tool names 與 actual calls；
- argument accuracy：名稱匹配後，arguments exact match 的比例；
- exact sequence rate：每個 turn 的工具序列是否完全一致；
- goal completion：expected goal 與 actual agent outcome 是否一致；
- step efficiency：在 `max_steps` 內完成則為 1，超出則按比例下降；
- invalid calls、retries、timeouts：直接由 trace 計數；
- memory checkpoint：required facts 是否保留及正確使用。

Tool metrics 必須以 turn 為單位計算後再 aggregate，避免不同 turn 的 call 互相抵銷。

### 3.7 Quality、成本與可靠性

`ratings rule.yml` 的 0–3 dimensions 用於 quality reward，但不能掩蓋 hard-gate failure。另記錄：

- p50/p95 latency、TTFT、generation time；
- input/output tokens、cost/query；
- timeout/error rate、cache hit rate；
- repeated judge mean absolute delta、pass/fail flips；
- human exact agreement、Cohen's kappa；
- cohort slices（risk、language、intent、difficulty）。

## 4. 如何定位問題

診斷採用「最早失敗 stage」原則：

```text
safety fail              → safety policy/prompt/process
route fail               → router/capsule selection
    ground resolution fail  → resolver、ground mapping 或 context 上限
faithfulness fail        → composer/context assembly/generation
memory fail              → state handoff/context window
guard/refusal fail       → output guard/refusal policy
latency/tool timeout     → model/context/orchestration parameters
```

`report.md` 對每個 failed case 輸出：

1. 問題位置（stage/case）；
2. evidence refs；
3. 指標的解讀；
4. 仍未證明的部分；
5. 下一步 recommendation。

這是 evidence-backed localization，不是自動宣稱唯一 root cause。

## 5. 如何設計調優實驗

### 5.1 固定控制項

固定：

- golden query set 與 approved oracle；
- product/build、prompt hash、knowledge/source version；
- model、temperature/top-p、retry policy；
- evaluator/judge model、judge prompt 與 rating rule；
- random seed、timeout 與 context policy。

### 5.2 單變因矩陣

一次只改一個主要變因，例如：

```text
chunk_size: 256 / 512 / heading-aware
overlap: 0 / 10% / 20%
top_k: 3 / 5 / 10
reranker: off / cross-encoder
hybrid_weight: 0 / .25 / .5 / .75 / 1
```

每個 variant 同時記錄 retrieval、answer、safety、tool、latency、cost metrics。不要只優化 weighted_total，因為它可能掩蓋 high-risk recall 或 hard-gate regression。

### 5.3 統計與決策

至少重跑 3 次；比較相同 query 的 paired outcomes。使用 paired bootstrap 或 randomization test，並報告 95% CI。小樣本 CI 只作 exploratory evidence，不能假裝成穩定 production estimate。

候選改動只有在以下條件同時成立時才可標記 `validated`：

```text
target metric 穩定改善
AND critical hard-gate regressions = 0
AND non-target regression 在門檻內
AND latency/cost side effects 可接受
AND 高風險 disagreement 已人工抽查
```

否則 recommendation 保持 `hypothesis`，並明確寫出要驗證的變因與 rollback condition。

## 6. 報告層次

人類只需要先讀：

```text
report.md
```

它是跨 case 的 executive/diagnosis view。只有在需要追查時才讀：

```text
results.xlsx / 01_Cases      # case 結論與 auto/human/final provenance
results.xlsx / 02_Turns      # turn、trace、對話 linkage
results.xlsx / 03_Metrics    # deterministic、judge、route/retrieval、answer/agent aggregate
results.xlsx / 05_Experiments # 實驗結果與 guardrails
```

`report.md` 的 Capsule／Ground 摘要是快速定位入口。需要判斷 answer adherence 時，應在
`03_Metrics` 分開查看：

```text
rag:metrics.route_acceptance.mean
rag:metrics.route_preference.mean
rag:attribution.counts.*
v3:capsule_attribution.claim_alignment
v3:capsule_attribution.content_coverage
v3:capsule_attribution.citation_precision
v3:semantic_attribution.claim_support.*
v3:semantic_attribution.exposed_unit_utilization.*
```

平均分的來源是 `00_Overview` 的 `Overall score`（可用 case final score 平均），維度平均則位於
同一張表的 `Dimension` rows。Router 是否正確分流，先看 `route_acceptance`（落在 accepted
route 集合的比例）及 `route_preference`（是否命中 preferred route），再看
`rag.route_confusion`。這能分開回答 crisis SOP、baseline 與一般 Capsule 三類分流是否正確：
前提是 testcase 的 accepted/preferred route oracle 已人工審核。

判斷 crisis SOP 是否合理，不能只看 route 命中：還要把 crisis case 的安全/拒答/必要行動
維度、`red_line`、`output_guard` 與人工 review 一起看。baseline 是否合理，則需檢查 baseline
case 的 route、無 Capsule 時的回答完整性，以及 `04_Baseline` 的 matched delta；沒有附加
baseline 時只能標示 `NOT_RUN`，不宣稱改善或退化。若 semantic attribution 為 `UNAVAILABLE`，
只能報告 trace 操作事實與 Capsule claim alignment，不能把缺失的語義歸因推定為通過或失敗。

這種分層同時滿足可讀性與可重現性：Markdown 方便決策，workbook facts 方便審計與 baseline 比較。
