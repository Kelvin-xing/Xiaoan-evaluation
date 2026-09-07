# DeepEval 閱讀研究：XiaoAn evaluation 與 multimodels 方法論深化建議

日期：2026-09-07  
範圍：只閱讀下列 DeepEval 公開文章；本文件不使用 DeepEval API，也不建議把 DeepEval 加入 XiaoAn runtime。

## 摘要判斷

這批文章最值得吸收的是方法論詞彙，而不是框架實作：

1. 把 eval harness 定義成「資料集、執行、trace、metrics、比較與產物」的完整驗證層，並把離線 eval 與線上 safety guardrail 分開。
2. LLM-as-a-judge 應按問題形狀選 single-output、pairwise、trajectory/component 評估；主觀標準要寫成明確 evaluation steps，硬性條件則拆成 deterministic branches。
3. EDD 應由少量高品質 golden、少量與人類判斷有關聯的 metrics、受控迭代組成，而不是追求大量模糊測試或單一總分。
4. multi-turn、RAG、memory 不能只評 final answer；必須保存 history/state、retrieval/context、工具或軌跡，並以 correctness、coverage、faithfulness、stability 分開觀察。

現有 XiaoAn 設計已超過文章中的入門模型：已有 versioned case/oracle、safety/route/ground/guard/state 分層 trace、0–3 rubric、red-line short circuit、claim/evidence contract、human calibration、單 deployment runner、5×10 subject/judge matrix、checkpoint 與 telemetry。因此修正方向不是引入 DeepEval，而是把目前已存在的規則收斂成更嚴格的「測量契約」，並補足 matrix 的比較統計與 judge validity。

## 文章觀察與適用邊界

| 文章 | 可採納的原則 | 不能直接照搬 |
| --- | --- | --- |
| [LLM-as-a-Judge](https://deepeval.com/blog/llm-as-a-judge) | single-output 適合絕對品質，pairwise 適合 prompt/model 版本比較；criteria 可先探索，重要指標改用明確 steps；judge 要用人類標註校準。 | 0–1 continuous score 不應取代 XiaoAn 的 0–3 錨點與 red-line gate；RAG faithfulness 不能只依賴 retrieved context，必須驗證真實 injected evidence。 |
| [Eval harness](https://deepeval.com/blog/what-is-an-eval-harness) | harness 包括 dataset、invoke、trace、metrics；offline eval 與 runtime guardrail 是不同職責。 | 文章以 pytest/API 整合為例，不能證明第三方框架適合本專案；XiaoAn 的安全 guard 不應被稱為 eval 分數。 |
| [Eval-driven development](https://deepeval.com/blog/eval-driven-development) | 先定義品質標準，再建 agent；少量高品質 goldens、3–5 個高關聯 metrics、反覆迭代。 | 「約 100 goldens」是一般經驗值，不是 XiaoAn 的 release gate；反家暴案例要按風險與 coverage 分層，不能用數量取代 critical recall。 |
| [Medical multi-turn chatbot](https://deepeval.com/blog/medical-chatbot-deepeval-guide) | full history 可能造成 context overload；應測 history window、summary、memory 與多輪一致性。 | 範例把 temperature/模型切換當主要旋鈕，未提供安全失誤成本、記憶錯誤分類或人類 calibration；不能直接套用於高風險反家暴場景。 |
| [RAG contract assistant](https://deepeval.com/blog/rag-contract-assistant-deepeval-guide) | generator 可能在 retriever 正確時仍產生合規錯誤；應分評 retrieval、faithfulness、relevancy、tone、citation。 | XiaoAn 已決定不把未經人工審核的 `required_ground_refs` / `relevant_ground_refs` 當一般 ground oracle；文章的 retrieval metrics 只適合有可信 finite universe/relevance labels 的專項實驗。 |
| [G-Eval use cases](https://deepeval.com/blog/top-5-geval-use-cases) | criteria 要具體、處理 partial correctness、允許語義等價並說明 ambiguity；硬要求宜用分支式檢查。 | G-Eval 本身不是 validity 證明；不能把 judge 的自我解釋當 evidence，也不能讓 judge 自行產生 release recommendation。 |
| [Cognee memory case](https://deepeval.com/blog/use-case-cognee-ai-memory) | memory 要同時看 QA correctness、context relevance/coverage、F1/EM 與跨 run consistency，且跨多資料集。 | 案例是供應商敘述，不是獨立 benchmark；F1/EM 不能覆蓋記憶污染、錯誤持久化、越權使用等 XiaoAn 特有風險。 |

## 對現有 implementation 的審核

### 已經正確且應保留

- `evaluation/README_SHARED.md` 已清楚區分單 deployment 與 `evaluation_multimodels/`，並把 provider failure / timeout / `UNAVAILABLE` 排除於品質零分之外。
- `evaluation/ratings rule.yml` 的 red-line-first 與 0–3 anchor 適合高風險產品；judge 不計算 `Weighted_Total`，避免把政策和模型混在一起。
- `evaluation/xiaoan_eval/judge.py` 要求 supported claim 有且只能引用 evidence catalog ref，這比只把 retrieval context 傳給 judge 更可稽核。
- `evaluation_multimodels/xiaoan_eval/multimodel.py` 的 `build_judge_evidence()` 使用 allowlist、trace hash、injected context units 與 unresolved-ref fail-closed，且不把 provider request、prompt、timing/token 傳給 judge。
- matrix 已保留 subject/judge cell、first-character latency、token/cache telemetry、checkpoint contract hash 與 concurrency guard；這些是可重現性基礎。
- calibration 模組已能比較 human/judge 的 dimensions、red-lines、claim relations、policy applicability/compliance 及 evidence spans；應把它升格為 judge release qualification，而非事後描述。

### 必須深化或修正

#### 1. 把「分數」改成三層測量契約

每個 case/turn 應固定輸出三類結果：

1. **Safety/operational gate**：red line、PII、未知 route、ground resolution、guard、provider/trace completeness。
2. **Task outcome**：approved oracle 的 route/safety/required claims/tools/memory checkpoint 是否達成。
3. **Quality judgement**：七個 0–3 維度、atomic claims、faithfulness、語氣與包容性。

`Weighted_Total` 只能是第三層的摘要，不能取代前兩層。報告要同時顯示 critical recall、coverage、available denominator 和品質平均，避免「高平均分掩蓋一個危機漏接」。

#### 2. 將 broad rubric 拆成可校準的 judge steps

保留七個產品維度，但每個維度增加：`decision_questions`、`positive_examples`、`negative_examples`、`not_applicable` 規則與最低 evidence 要求。Judge prompt 應先逐題判斷，再映射到 0/1/2/3；不要讓模型直接憑印象選分。red-line、安全路由、必要 claim、禁用行為仍由 deterministic gate 優先。

#### 3. 對 multimodels 同時使用 absolute 與 pairwise，但不混成一個排名

- **Absolute track**：固定 rating rule、approved oracle、固定 evidence catalog，產生每個 subject×judge cell 的分數。
- **Pairwise track**：同一 case/turn、同一 trace context，隨機化 A/B 顯示順序，讓 judge 選 preferred / tie，並記錄 position。這回答「哪個版本較好」，不回答「是否安全合格」。
- **Release decision**：先套 safety/operational hard gate，再看 absolute quality；pairwise 只作相容版本的改善證據。

不要把五個 judge 的平均分當真實 ground truth，也不要直接把不同 judge model 的分數排成單一 leaderboard。應報告 subject×judge 矩陣、judge 間 dispersion、與人類 anchor 的 agreement，並對 case strata 做 macro aggregation。

#### 4. 加入 judge validity 與 drift gate

在 frozen human benchmark 上，按 red-line、criticality、route、language/accessibility strata 抽樣，定期計算：

- red-line sensitivity/recall（false negative 是高風險）；
- 每維 exact agreement、允許 ±1 的 agreement、ordinal correlation；
- supported/unsupported claim precision，以及 evidence-span match；
- judge model/prompt/rating-rule 改變前後的 score drift。

若 validity 未達門檻，該 judge 只能作 exploratory，不可作 release gate 或 baseline comparison。這延伸現有 `calibration.py`，不需要引入外部平台。

#### 5. 對 memory 建立獨立測試，不只看多輪 final answer

每個 memory checkpoint 應分成：`remember`（是否保留）、`retrieve`（是否在需要時使用）、`not_use`（是否避免不相關使用）、`update`（新資訊覆蓋規則）、`isolation`（跨 conversation 不洩漏）、`stale/unsafe`（過期或高風險資訊處置）。

報告至少按 case/turn 顯示 memory precision、recall、污染/越權數與跨重跑一致性；memory 錯誤不應被一般 helpfulness 分數稀釋。

#### 6. 對 EDD 迴圈增加「失敗 → 假設 → 單變量實驗 → guardrail」鏈

每個 recommendation 必須綁定：失敗 observation、stage、可改 lever、before/after、target metric、non-target guardrails、重複次數、停止規則。未經 controlled variant 的 root cause 仍標 `hypothesis`。對 critical safety case，任何 hard-gate regression 都應使實驗失敗；不能因平均分上升而接受。

#### 7. 修正 matrix 的公平性與可解讀性

目前 matrix runner 已有 concurrency 與 telemetry，但下一版應：

- 固定同一 case/turn 的輸入與 evidence snapshot；禁止不同 subject 因 provider 封裝而收到不同 rubric；
- 明確記錄 provider/model/version、reasoning、sampling、system prompt hash、knowledge snapshot 與 judge prompt hash；
- 對每一 subject 使用相同 judge 集合，對每一 judge 使用相同 cell subset；
- 計算 paired case-level delta、bootstrap confidence interval 或至少 strata-level uncertainty，不只平均分；
- 對 `UNAVAILABLE` 報 coverage 與缺失模式，不能因某 provider 失敗較多而錯誤地視為低品質；
- cache telemetry 只有 provider 回傳 hit/read/write 數值時才宣稱有效，wall-clock speedup 與 token/API cost 分開報告。

## 建議的下一版最小 schema

不破壞現有 v2/v3，可在 private audit / workbook 新增：

```yaml
measurement_contract:
  track: absolute | pairwise
  evaluator_version: "..."
  judge_validity_status: qualified | exploratory | invalid
  denominator_policy: approved_available_only
  strata: [risk, route, language, accessibility]

turn_measurement:
  gates: [{id: RL-04, status: PASS, evidence_refs: [...]}]
  outcome: {status: PASS, required_claim_recall: 1.0}
  quality: {dimensions: {法律維權: 2}, weighted_total: 2.31}
  memory: {remember: PASS, retrieve: SKIP, isolation: PASS}
  operational: {status: PASS, provider: ...}
```

對 pairwise cell 另加：`pair_id`、`left/right_subject_id`、`display_order`、`winner`、`tie`、`judge_id`、`validity_status`。這些欄位是比較設計，不應回填到 absolute score。

## 分階段落地

**P0：契約與可信度**：把 judge validity gate、measurement contract、case strata、provider model registry/hash 補進 manifest；確認所有公開報告明確顯示 denominator 與 unavailable。

**P1：judge 校準**：用已 adjudicated benchmark 跑每個 judge profile；建立 red-line recall、dimension agreement、claim/evidence agreement 門檻，未達標的 judge 降級為 exploratory。

**P2：matrix 比較**：新增 paired pairwise track 與 case-level delta；保留現有 absolute 5×10 matrix，兩者分開寫入 workbook sheets。

**P3：memory/EDD**：新增 memory 五類 checkpoint 與 recommendation ledger 的 target/guardrail/stop rule 驗證；只對通過 validity 與 hard gates 的實驗產生改善結論。

## 結論

DeepEval 文章支持 XiaoAn 目前「trace-first、分層 metrics、human calibration、EDD」的方向，但不足以替代本專案的 domain safety contract。最重要的修正不是增加更多通用 metrics，而是：把 judge 從「可呼叫的評分器」提升為「有資格門檻的測量儀器」；把 multimodels 從「5×10 分數矩陣」提升為「公平、配對、可解釋、保留 unavailable 的比較實驗」；把 memory 與 critical safety 從平均品質分中拆出來。

