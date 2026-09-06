# Evaluation Output Contract

版本：v2.0
更新：2026-09-03

## Public deliverables

每個 evaluation lifecycle 的公開目錄只能包含 `results.xlsx` 和 `report.md`。兩者必須具有相同 `generation_id`，並由同一 normalized report model 產生。v2.0 將完整文字分段併入 `02_Turns`，移除 `10_Text_Content`。

## Natural row grains

| Sheet | Row grain | Required identity |
| --- | --- | --- |
| `01_Cases` | component run × case | `component_run_id`, `case_id`, `comparison_key` |
| `02_Turns` | component run × case × turn，另含文字分段列 | `row_kind`, `component_run_id`, `case_id`, `turn`, `comparison_key` |
| `03_Metrics` | component run × case/turn × metric × score source | `row_key`, `comparison_key`, `metric_id`, `score_source` |
| `04_Baseline` | comparison domain × grain × key × metric | `domain`, `grain`, `key`, `metric` |
| `05_Experiments` | controlled experiment | `experiment_id` |
| `06_Human_Review` | review item lifecycle | `review_id`, `case_id`, `turn`, `response_sha256` |
| `07_Stability` | stability scope × metric | `section`, `metric` |
| `02_Turns`（`row_kind=text`） | text × ordered chunk | `text_id`, `chunk_index`, `chunk_count`, `text_sha256` |

## Score and status rules

- Judge dimension scores are anchored integers 0, 1, 2, or 3 at turn/source level; aggregates may be decimals.
- Numeric zero is a measured value. `UNAVAILABLE`, `NOT_RUN`, `NOT_REQUIRED`, `NOT_APPLICABLE`, `SKIPPED`, and `ERROR` are distinct states.
- Automatic, human, and adjudicated/final facts must be separate rows or columns with explicit `score_source`; human values never overwrite automatic facts.
- A disputed red line makes affected final turn/case/run values unavailable until adjudication.
- `03_Metrics.reason` is rendered in Traditional Chinese; internal metric IDs and status enums remain canonical for machine comparison.
- Quality, safety/hard gates, coverage, performance, experiment verdict, and stability classification must not be collapsed into one opaque score.

## Baseline rules

The formal baseline source is a validated `FINAL` workbook. Schema, logical digests, rating rule, judge measurement configuration, and case/turn comparison keys determine domain comparability. Partial overlap may produce scoped row deltas but not a global improvement claim.

## Text and privacy

Full conversations are sensitive. Formula-leading text must remain inert literal content. Text that exceeds a cell is split into ordered chunks and reconstructed by `text_id`, `chunk_index`, `chunk_count`, and `text_sha256`. Public workbooks, reports, and review packets must pass the configured PII/safety validation gates before publication or transport.

## Version changes

Adding a backward-compatible optional display column requires a minor schema version. Changing sheet names, identity keys, score/status semantics, types, required columns, comparison keys, or digest canonicalization is a breaking change and requires a new baseline contract.
