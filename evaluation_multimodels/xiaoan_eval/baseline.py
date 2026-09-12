"""Comparable case, cohort, and global baseline deltas."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

from .report_model import ReportModel
from .workbook import read_workbook


@dataclass(frozen=True)
class MetricDelta:
    weighted_total_delta: float | None
    pass_rate_delta: float | None


@dataclass(frozen=True)
class BaselineDiff:
    comparable: bool
    cases: Mapping[str, MetricDelta]
    cohorts: Mapping[str, MetricDelta]
    global_delta: MetricDelta
    missing_in_variant: tuple[str, ...] = ()
    new_in_variant: tuple[str, ...] = ()
    unavailable_cases: tuple[str, ...] = ()


def compare_baseline(
    baseline: Sequence[Mapping[str, object]],
    variant: Sequence[Mapping[str, object]],
) -> BaselineDiff:
    before = _by_id(baseline)
    after = _by_id(variant)
    shared = sorted(before.keys() & after.keys())
    case_deltas = {case_id: _delta([before[case_id]], [after[case_id]]) for case_id in shared}
    cohort_names = sorted(
        {c for record in baseline for c in _cohort_names(record)}
        | {c for record in variant for c in _cohort_names(record)}
    )
    cohort_deltas = {
        cohort: _delta(
            [before[case_id] for case_id in shared if cohort in _cohort_names(before[case_id])],
            [after[case_id] for case_id in shared if cohort in _cohort_names(after[case_id])],
        )
        for cohort in cohort_names
    }
    missing = tuple(sorted(before.keys() - after.keys()))
    new = tuple(sorted(after.keys() - before.keys()))
    unavailable = tuple(case_id for case_id in shared if _weighted_total(before[case_id]) is None or _weighted_total(after[case_id]) is None)
    return BaselineDiff(
        comparable=bool(shared) and not missing and not new and not unavailable,
        cases=case_deltas,
        cohorts=cohort_deltas,
        global_delta=_delta([before[i] for i in shared], [after[i] for i in shared]),
        missing_in_variant=missing,
        new_in_variant=new,
        unavailable_cases=unavailable,
    )


def compare_workbook_baseline(path: Path, candidate: ReportModel) -> tuple[BaselineDiff, tuple[Mapping[str, object], ...]]:
    """Admit a final workbook and return human-readable comparison rows."""
    baseline = read_workbook(path)
    if baseline.artifact_state != "FINAL":
        raise ValueError(f"baseline workbook must be FINAL, got {baseline.artifact_state}")
    if baseline.schema_version != candidate.schema_version:
        raise ValueError("baseline quality domain is incompatible: workbook schema / scoring contract; regenerate from original evidence")
    required_manifest_keys = ("rating_rule_hash", "rating_rule_schema_version", "judge_prompt_version", "scoring_contract_version")
    drift = [key for key in required_manifest_keys if baseline.manifest.get(key) != candidate.manifest.get(key)]
    if drift:
        raise ValueError("baseline quality domain is incompatible: " + ", ".join(drift))
    diff = compare_baseline(baseline.cases, candidate.cases)
    rows: list[Mapping[str, object]] = []
    for case_id, delta in sorted(diff.cases.items()):
        rows.append({
            "domain": "quality", "grain": "case", "key": case_id,
            "metric": "final_score", "baseline_value": _case_score(baseline.cases, case_id),
            "candidate_value": _case_score(candidate.cases, case_id),
            "delta": delta.weighted_total_delta, "status": "COMPARABLE" if delta.weighted_total_delta is not None else "UNAVAILABLE",
            "reason": "matched case_id and measurement contract" if delta.weighted_total_delta is not None else "quality unavailable on at least one side; no zero imputation",
        })
    rows.append({
        "domain": "quality", "grain": "run", "key": "subject", "metric": "final_score",
        "baseline_value": None, "candidate_value": None,
        "delta": diff.global_delta.weighted_total_delta if diff.comparable else None,
        "status": "COMPARABLE" if diff.comparable else "PARTIAL",
        "reason": "complete matched case set" if diff.comparable else f"missing={diff.missing_in_variant}; new={diff.new_in_variant}; unavailable={diff.unavailable_cases}",
    })
    return diff, tuple(rows)


def _by_id(records: Sequence[Mapping[str, object]]) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for record in records:
        case_id = str(record["case_id"])
        if case_id in result:
            raise ValueError(f"duplicate case_id: {case_id}")
        result[case_id] = record
    return result


def _delta(before: Sequence[Mapping[str, object]], after: Sequence[Mapping[str, object]]) -> MetricDelta:
    if not before or not after or any(_weighted_total(row) is None for row in (*before, *after)):
        return MetricDelta(None, None)
    before_score = sum(_weighted_total(r) for r in before) / len(before)
    after_score = sum(_weighted_total(r) for r in after) / len(after)
    before_pass = sum(str(r["status"]).upper() == "PASS" for r in before) / len(before)
    after_pass = sum(str(r["status"]).upper() == "PASS" for r in after) / len(after)
    return MetricDelta(round(after_score - before_score, 12), round(after_pass - before_pass, 12))


def _weighted_total(record: Mapping[str, object]) -> float | None:
    if str(record.get("status", "")).upper() in {"ERROR", "UNAVAILABLE"} or record.get("quality_status") == "UNAVAILABLE":
        return None
    quality = record.get("quality")
    if isinstance(quality, Mapping):
        value = None if quality.get("status") == "UNAVAILABLE" else quality.get("weighted_total")
    else:
        value = record.get("final_score") if "final_score" in record else record.get("weighted_total")
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _cohort_names(record: Mapping[str, object]) -> set[str]:
    raw = record.get("cohorts", ())
    if isinstance(raw, Mapping):
        return {
            f"{kind}:{value}"
            for kind, values in raw.items()
            for value in (values if isinstance(values, (list, tuple)) else (values,))
        }
    if isinstance(raw, str):
        return {item.strip() for item in raw.split(";") if item.strip()}
    if raw is None:
        return set()
    return {str(value) for value in raw}


def _case_score(records: Sequence[Mapping[str, object]], case_id: str) -> float | None:
    for record in records:
        if str(record.get("case_id")) == case_id:
            value = record.get("final_score")
            return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None
    return None
