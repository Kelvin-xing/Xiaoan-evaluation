# XiaoAn Evaluation

中文运行、报告阅读、人工审核与 Judge 校准指南：[`USAGE.zh-CN.md`](USAGE.zh-CN.md)。

The current public evaluation contract is deliberately small: every ordinary run publishes exactly two files.

- `results.xlsx` is the formal, human-readable evidence and baseline source.
- `report.md` is the detailed decision, optimization, experiment, and limitation report.

JSON or JSONL may still be accepted as a bounded legacy input for `report`, experiment component runs, and stability repeats. They are not public deliverables and must not be treated as a second official result.

## Run

```bash
xiaoan-eval run test-cases \
  --base-url http://localhost:8000 \
  --judge-plugin company_eval_plugins:judge \
  --context-provider company_eval_plugins:authoritative_context \
  --manifest manifest.json \
  --output runs/<run-id>
```

The output directory must be empty or contain a valid existing pair. Unknown files are refused and never deleted implicitly. Full `preflight` remains a separate command; an ordinary run performs only the parsing, schema, PII/input-integrity, and output-target guards required for that operation.

## Workbook map

| Sheet | Grain and purpose |
| --- | --- |
| `00_Overview` | Decision dashboard: artifact state, verdict, overall/dimension scores, coverage, speed, baseline, experiment, and stability state. |
| `01_Cases` | One row per subject case with automatic/human/final score provenance, hard gates, failure stage, review status, cohorts, and latency. |
| `02_Turns` | One row per turn with transcript links, route/ground/safety context, performance, review state, and automatic/human/final turn scores. |
| `03_Metrics` | One row per case/turn/metric/source plus run-level RAG/V3 aggregates. Zero is numeric zero; missing states remain explicit. |
| `04_Baseline` | Domain/grain/key deltas and comparability reasons. |
| `05_Experiments` | Hypothesis, control, candidate, repetitions, target/non-target results, guardrails, verdict, and next action. |
| `06_Human_Review` | Review lifecycle and provenance. Reviewer ID is an operational label, not authenticated identity. |
| `07_Stability` | Optional repeatability facts and classification; never a correctness score. |
| `08_Metadata` | Schema, generation, lifecycle, manifest, and logical digests. |
| `09_Data_Dictionary` | Column meanings and status semantics. |
| `02_Turns` (`row_kind=text`) | Lossless ordered chunks for full user and assistant text. |

## Formal baseline

Pass a prior final workbook to a new run:

```bash
xiaoan-eval run test-cases ... \
  --baseline runs/<baseline-id>/results.xlsx \
  --output runs/<candidate-id>
```

The loader verifies OOXML safety, fixed schema, logical digests, `FINAL` state, and the quality measurement contract. A changed rating rule, rule schema, or judge prompt suppresses the quality comparison instead of producing a misleading global delta. Partial case overlap is reported as partial and does not produce a global improvement claim.

## Human review

Review is exception-driven. A pending run remains a complete official pair with artifact state `PENDING_REVIEW`.

Export one blinded transport workbook outside the deliverable directory:

```bash
xiaoan-eval export-human-review runs/<run-id> \
  --rating-rule "ratings rule.yml" \
  --output private-review/<run-id>-review.xlsx
```

The packet contains:

- `00_Instructions`: purpose, anchored scoring, privacy, completion, and escalation rules.
- `01_Review_Queue`: the bound case/turn/response and editable reviewer metadata.
- `02_Review_Items`: every red line and rubric dimension; only blue cells are editable.
- `03_Evidence`: packet-bound evidence references and relevant conversation content.

It contains no automatic scores. The reviewer fills every anchored score/red-line judgment, cites only listed evidence refs, records a timezone timestamp, and returns the same XLSX. `reviewer_id` is a self-declared operational label; this workflow intentionally does not authenticate the person filling the workbook.

Import and regenerate the same official pair:

```bash
xiaoan-eval import-human-review private-review/<run-id>-review.xlsx \
  --rating-rule "ratings rule.yml" \
  --output runs/<run-id>
```

Import is all-or-nothing. It rejects formulas, unsafe OOXML, stale generations, changed response/rubric/evidence bindings, changed immutable cells, incomplete judgments, non-anchored scores, and unknown evidence refs. Automatic, human, and final rows remain separate. AI/human red-line disagreement produces `NEEDS_ADJUDICATION` and leaves the affected final score empty.

Resolve each disputed turn by explicitly selecting the accepted fact source and recording a rationale:

```bash
xiaoan-eval adjudicate runs/<run-id> \
  --case TC-01 --turn 1 --decision human \
  --adjudicator adjudicator-label \
  --rationale "Human red-line evidence is accepted after evidence review."
```

The adjudicator label is also self-declared and unauthenticated. The command appends adjudicated metric provenance and regenerates the same pair; it does not erase either original source.

## Stability

Stability means repeatability under fixed deployment, model, prompt, knowledge, hyperparameter, and case/turn controls. It does not mean correctness. A consistently wrong answer can be highly stable.

```bash
xiaoan-eval stability \
  --runs private-repeats/run-101.jsonl private-repeats/run-202.jsonl private-repeats/run-303.jsonl \
  --manifests private-repeats/manifest-101.json private-repeats/manifest-202.json private-repeats/manifest-303.json \
  --output runs/<final-run-id>
```

The command attaches route modal agreement, ground Jaccard, response-hash agreement, score variance, pass/fail flips, hard-gate consistency, latency variance, retry variance, and timeout rate to the existing final pair. Without configured thresholds the classification is `DESCRIPTIVE_ONLY`; if not run, the workbook says `NOT_MEASURED`.

## Controlled experiment

Experiment component runs are private inputs. `experiment`, `auto-experiment`, and `auto-file-experiment` attach a controlled conclusion to the existing final pair rather than creating a third public file. Recommendations in `report.md` remain hypotheses until such evidence is attached.

## Legacy conversion

```bash
xiaoan-eval report private-legacy/case-results.jsonl --output runs/<converted-id>
```

This produces the same two-file pair. If the legacy input lacks manifest and case/oracle contract metadata, it is useful for reading but is not a trustworthy formal baseline.
# 多模型矩陣評估

`xiaoan_eval matrix` 會以相同用例建立 XiaoAn subject × judge 矩陣。預設為五家供應商各兩個 subject 配置（最新模型/medium、次新模型/high）乘五個 judge（均為 medium），即 10×5。每個 answer 在 `All_Answers` 只保留一次，Judge JSON、分數與遙測則在 `All_Judgements` 以 `answer_id` 關聯；服務商或 Judge 失敗記為 `UNAVAILABLE`，不進入分母。完整 Chatflow trace 只寫入私有 checkpoint。輸出包含總 `results.xlsx`、總 `report.md`，以及 `pairs/` 下每個 subject × judge 的獨立 Excel。

```bash
# Terminal 1: start the XiaoAn subject chatflow. It reads
# evaluation_multimodels/.env directly.
.venv/bin/uvicorn server:create_app \
  --factory --app-dir ../tech_multimodels/chatflow/poc \
  --host 127.0.0.1 --port 8000

# Terminal 2: run the 10x5 matrix.
PYTHONPATH=. python -m xiaoan_eval matrix test-cases \
  --subject-transport company_eval_plugins:xiaoan_chatflow_transport \
  --judge-transport company_eval_plugins:multimodel_transport \
  --output runs/matrix-$(date +%Y%m%d%H%M%S)
```

GlobalAI 使用統一的 OpenAI-compatible endpoint `https://globalai.vip/v1/chat/completions`。請把 key 填入 `evaluation_multimodels/.env` 的 `GLOBALAI_API_KEY=...`；Judge 與 `tech_multimodels` chatflow 會讀取同一個檔案。程式使用 `Authorization: Bearer <key>`，並對 HTTP 429、暫時性 5xx、空 Judge 回覆與不符合 rubric schema 的 Judge 回覆做 bounded retry；可用 `GLOBALAI_API_BASE`、`GLOBALAI_MAX_RETRIES`、`XIAOAN_PROVIDER_TIMEOUT` 覆寫單次 provider 請求。若某個模型家族需要獨立供應商，可設定 `XIAOAN_<PROVIDER>_API_KEY` 與 `XIAOAN_<PROVIDER>_ENDPOINT`；provider-specific 設定優先於 GlobalAI 共用設定，endpoint 可填 base URL 或完整 API 路徑。外層 Chatflow 請求另用 `XIAOAN_CHATFLOW_TIMEOUT`，預設 600 秒，避免慢模型在內部重試完成前被呼叫端中止。供本機 HTTP 評估使用的 `XIAOAN_ENABLE_DEBUG=true` 與 `XIAOAN_COOKIE_SECURE=false` 也應保留。模型可用 `LATEST_MODEL`、`SECOND_MODEL` 環境變數覆寫；需要第三種 subject 設定時，使用 `--subjects` 傳入 `ModelSpec` JSON 陣列，judge 可用 `--judges` 覆寫。不要把真實 key 寫進 Git、測試、XLSX 或 report。

Matrix 預設啟用 2 條獨立 subject×case lane、3 個 Judge，且同一 provider 同時最多 1 個請求；可用 `--subject-concurrency`、`--judge-concurrency`、`--max-in-flight` 與 `--per-provider-concurrency` 調整。每條 lane 內的多輪對話仍嚴格依序執行，Chatflow conversation/cookie 狀態按 thread 隔離。每次 subject 或 Judge provider call 完成後都會立即 `fsync` 到輸出目錄旁的私有 `.matrix-audit/<run>/matrix-checkpoint.jsonl`（權限 `0600`）；可用 `--checkpoint` 指定其他私有路徑，中斷後以相同輸出目錄加 `--resume` 續跑。新版 checkpoint 绑定 cases/models/rating rule hash，配置变化时拒绝复用；旧版没有 hash 的 checkpoint 必须额外明确传入 `--allow-legacy-checkpoint`，不能静默信任。若 stateful chatflow case 只完成部分 turn，程式會拒絕從不完整 conversation state 靜默續跑。

一般 `--resume` 會重用所有已落盤結果，包括 `UNAVAILABLE`，以維持相同 checkpoint 的可重現性。使用 `--resume --retry-unavailable` 時，成功的 subject answers 仍保持 frozen 並只重試不可用 Judge cells；若 subject lane 內任何 answer 失敗，則從該 case 的 turn 1 重建整條 stateful lane，並重新執行該 lane 的 Judges 與 attribution。Judge evidence 建立失敗的 cell 不會被誤送至 provider。

Judge 不再接收完整 `chatflow_trace`。runner 以固定 allowlist 產生 `judge-evidence/v1`：保留 route/safety/capsule/state/output-guard 摘要、Composer 實際可見的 capsule/wiki/source 內容與完整 trace SHA-256；排除 router candidate catalog、provider request、系統 prompt、retry、timing、token 與 response ID。任何 `resolved_ground` 找不到對應正文時會停止該答案的 Judge 評分並記為 `UNAVAILABLE`。公開 `results.xlsx` 的 `All_Answers` 每個答案只保存一次且不含完整 trace，`All_Judgements` 以 `answer_id` 關聯；完整 trace 只保留在私有 checkpoint。兩張明細表與 report 都保留 queue、error class、cache hit/write token（provider 有回傳時）。

Judge prompt 固定把評分規則與 schema 放在前綴，case、history、answer 與 evidence 放在後綴。`XIAOAN_PROMPT_CACHE_MODE=prefix_only`（預設）只利用供應商自動快取；確認 relay 相容後才設 `explicit`，也可用 `XIAOAN_<PROVIDER>_PROMPT_CACHE_MODE` 逐家啟用。`off` 只代表不发送显式 cache control，无法保证上游供应商关闭自动 prefix cache。OpenAI-compatible explicit 模式发送固定 `prompt_cache_key`，Anthropic-compatible explicit 模式在 system block 发送 `cache_control`；是否生效以 GlobalAI 实际返回的 cached/write token 为准。快取不降低 TPM 佔用，首次 cache write 可能比普通 input 更貴，因此必須用 workbook 的 cached/write tokens 驗證。

調參時先用同一組 2 cases 跑 serial baseline（四個 concurrency 都設 1）與預設配置，比較 wall time、PASS/UNAVAILABLE 分布、輸出列數、答案/評分摘要及 cache tokens。只有結果等價、429/5xx 沒有上升且 p95 queue/latency 可接受時才逐步增加 `--max-in-flight`。通常最先遇到的卡點是 Chatflow worker 數、單 provider RPM/TPM、relay 連線穩定性與 Judge 長尾，而不是本機 CPU。

兩次 run 完成後可執行 `python tools/compare_matrix_runs.py runs/serial/results.xlsx runs/parallel/results.xlsx --serial-seconds <秒> --parallel-seconds <秒>`；只有答案與評分等價且 rate-limit failure 沒有增加才回傳成功，JSON 同時列出 speedup、queue p95、cache tokens 與總 attempts。

目前 `evaluation_multimodels/.env` 啟用的十個 subject model 為：Claude `claude-opus-5` / `claude-sonnet-5`、GPT `gpt-5.6-sol` / `o4-mini-2025-04-16`、Gemini `gemini-3-pro-preview-thinking` / `gemini-3.8-flash`、Qwen `qwen3.8-max` / `qwen3.7-max`、Kimi `kimi-k3` / `kimi-k2.6`。每家的第一個模型使用 medium effort，第二個模型使用 high effort。這些 ID 必須存在於目前 GlobalAI 帳戶；若 provider 回傳模型不存在，該 observation 會保留為 `UNAVAILABLE`，不納入品質平均分。
