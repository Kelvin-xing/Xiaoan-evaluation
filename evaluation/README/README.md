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

Independent cases run concurrently (`--case-concurrency 2` by default); turns inside one case remain sequential. Raise this only after checking Chatflow capacity and provider rate limits. Judge requests place the stable instructions/rating rule before dynamic case data so eligible providers can reuse the prefix. Set `XIAOAN_PROMPT_CACHE_MODE=explicit` only for direct OpenAI Responses calls on a model that supports explicit caching; `prefix_only` is the compatibility-safe default and `off` restores the legacy single payload.

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
