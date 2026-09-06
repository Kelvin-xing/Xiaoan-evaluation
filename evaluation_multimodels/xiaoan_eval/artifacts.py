"""Stable evaluation artifacts and human-readable views."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass
import json
from typing import Any, Callable, Mapping, Sequence


class ArtifactSafetyError(ValueError):
    """Raised when an optional artifact safety validator rejects content."""


@dataclass(frozen=True)
class CaseArtifact:
    case_id: str
    status: str
    conversation: Mapping[str, Any]
    safety: Mapping[str, Any]
    pipeline: Mapping[str, Any]
    quality: Mapping[str, Any]
    performance: Mapping[str, Any]
    review: Mapping[str, Any]
    failure: Mapping[str, Any]
    cohorts: Mapping[str, tuple[str, ...]]
    evidence_refs: tuple[str, ...]
    remediation: Mapping[str, Any]


@dataclass(frozen=True)
class ReportArtifacts:
    cases: tuple[CaseArtifact, ...]
    markdown: Mapping[str, str]

    def to_jsonl(self) -> str:
        return "".join(
            json.dumps(asdict(case), ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            + "\n"
            for case in self.cases
        )


def build_artifacts(
    records: Sequence[Mapping[str, Any]],
    pii_validator: Callable[[Mapping[str, Any]], bool] | None = None,
) -> ReportArtifacts:
    """Normalize records once, then render case/cohort/global views."""
    if pii_validator is not None and any(not pii_validator(record) for record in records):
        raise ArtifactSafetyError("artifact record failed PII validation")
    cases = tuple(sorted((_normalize(record) for record in records), key=lambda x: x.case_id))
    return ReportArtifacts(
        cases=cases,
        markdown={
            "case": _case_markdown(cases),
            "cohort": _cohort_markdown(cases),
            "global": _global_markdown(cases),
        },
    )


def _normalize(record: Mapping[str, Any]) -> CaseArtifact:
    required = {"case_id", "status", "safety", "pipeline", "quality", "performance", "review", "failure"}
    missing = required - set(record)
    if missing:
        raise ValueError(f"case artifact missing fields: {', '.join(sorted(missing))}")
    _validate_anchored_judge_scores(record["review"])
    cohorts = {
        str(kind): tuple(sorted(str(value) for value in values))
        for kind, values in dict(record.get("cohorts", {})).items()
    }
    return CaseArtifact(
        case_id=str(record["case_id"]),
        status=str(record["status"]),
        conversation=deepcopy(dict(record.get("conversation", {"conversation_id": "", "turns": []}))),
        safety=deepcopy(dict(record["safety"])),
        pipeline=deepcopy(dict(record["pipeline"])),
        quality=deepcopy(dict(record["quality"])),
        performance=deepcopy(dict(record["performance"])),
        review=deepcopy(dict(record["review"])),
        failure=deepcopy(dict(record["failure"])),
        cohorts=cohorts,
        evidence_refs=tuple(sorted(str(ref) for ref in record.get("evidence_refs", ()))),
        remediation=deepcopy(dict(record.get("remediation", {}))),
    )


def _validate_anchored_judge_scores(review: Any) -> None:
    if not isinstance(review, Mapping):
        return
    audits = review.get("judge_audit", [])
    if not isinstance(audits, Sequence) or isinstance(audits, (str, bytes)):
        return
    for audit in audits:
        if not isinstance(audit, Mapping):
            continue
        for judge_name in ("primary", "secondary"):
            judgement = audit.get(judge_name)
            dimensions = (
                judgement.get("dimensions", [])
                if isinstance(judgement, Mapping)
                else []
            )
            if not isinstance(dimensions, Sequence) or isinstance(
                dimensions, (str, bytes)
            ):
                continue
            for dimension in dimensions:
                if not isinstance(dimension, Mapping):
                    continue
                score = dimension.get("score")
                if (
                    isinstance(score, bool)
                    or not isinstance(score, (int, float))
                    or not float(score).is_integer()
                    or int(score) not in {0, 1, 2, 3}
                ):
                    raise ValueError(
                        f"{judge_name} judge score {score!r} is not an anchored rating-rule score"
                    )


def _case_markdown(cases: Sequence[CaseArtifact]) -> str:
    lines = [
        "# Case view",
        "",
        "| Case | Status | Score | Failure stage | Review |",
        "| --- | --- | ---: | --- | --- |",
    ]
    for case in cases:
        lines.append(
            f"| {case.case_id} | {case.status} | {_score_display(case.quality.get('weighted_total'))} "
            f"| {case.failure.get('primary_stage', '-')} | {case.review.get('status', '-')} |"
        )
    for case in cases:
        lines.extend(_case_quality_markdown(case))
    return "\n".join(lines) + "\n"


def _case_quality_markdown(case: CaseArtifact) -> list[str]:
    lines = ["", f"## {case.case_id}", "", f"Overall quality score: {_score_display(case.quality.get('weighted_total'))}"]
    dimensions = case.quality.get("dimensions", {})
    if isinstance(dimensions, Mapping) and dimensions:
        lines.extend(["", "### Dimension scores", "", "| Dimension | Score (0-3) |", "| --- | ---: |"])
        for module, score in dimensions.items():
            lines.append(
                f"| {_markdown_cell(module)} | {_score_display(score)} |"
            )

    audits = case.review.get("judge_audit", [])
    if not isinstance(audits, Sequence) or isinstance(audits, (str, bytes)):
        return lines
    for turn_number, audit in enumerate(audits, 1):
        if not isinstance(audit, Mapping):
            continue
        turn_statuses = case.review.get("per_turn", [])
        turn_status = (
            turn_statuses[turn_number - 1]
            if isinstance(turn_statuses, Sequence) and turn_number <= len(turn_statuses)
            else "-"
        )
        lines.extend(["", f"### Turn {turn_number}", "", f"Review status: {_markdown_cell(turn_status)}"])
        reasons = audit.get("reconciliation_reasons", [])
        if isinstance(reasons, Sequence) and not isinstance(reasons, (str, bytes)) and reasons:
            lines.append("Reconciliation: " + "; ".join(_markdown_cell(reason) for reason in reasons))
        primary = audit.get("primary", {})
        judge_dimensions = primary.get("dimensions", []) if isinstance(primary, Mapping) else []
        if not isinstance(judge_dimensions, Sequence) or isinstance(judge_dimensions, (str, bytes)):
            continue
        lines.extend(["", "| Dimension | Score | Supporting evidence | Deduction evidence |", "| --- | ---: | --- | --- |"])
        for dimension in judge_dimensions:
            if not isinstance(dimension, Mapping):
                continue
            lines.append(
                f"| {_markdown_cell(dimension.get('module', '-'))} "
                f"| {_raw_score(dimension.get('score'))} "
                f"| {_evidence_cell(dimension.get('supporting_evidence'))} "
                f"| {_evidence_cell(dimension.get('deduction_evidence'))} |"
            )
    return lines


def _raw_score(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, (int, float)) and not isinstance(value, bool) else "n/a"


def _score_display(value: Any) -> str:
    return f"{value:.4f}/3" if isinstance(value, (int, float)) and not isinstance(value, bool) else "n/a"


def _markdown_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _evidence_cell(value: Any) -> str:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return "-"
    items = [_markdown_cell(item) for item in value if str(item).strip()]
    return "<br>".join(items) if items else "-"


def _cohort_markdown(cases: Sequence[CaseArtifact]) -> str:
    groups: dict[str, list[CaseArtifact]] = {}
    for case in cases:
        for kind, values in case.cohorts.items():
            for value in values:
                groups.setdefault(f"{kind}:{value}", []).append(case)
        stage = case.failure.get("primary_stage")
        if stage:
            groups.setdefault(f"stage:{stage}", []).append(case)
    lines = ["# Cohort view", "", "| Cohort | Cases | Pass rate |", "| --- | ---: | ---: |"]
    for name, members in sorted(groups.items()):
        passed = sum(case.status.upper() == "PASS" for case in members)
        lines.append(f"| {name} | {len(members)} | {passed / len(members):.3f} |")
    return "\n".join(lines) + "\n"


def _global_markdown(cases: Sequence[CaseArtifact]) -> str:
    passed = sum(case.status.upper() == "PASS" for case in cases)
    stages: dict[str, int] = {}
    for case in cases:
        stage = str(case.failure.get("primary_stage", "none"))
        stages[stage] = stages.get(stage, 0) + 1
    lines = ["# Global view", "", f"Cases: {len(cases)}", f"Pass rate: {passed / len(cases):.3f}" if cases else "Pass rate: n/a", "", "## Failure stages"]
    lines.extend(f"- {stage}: {count}" for stage, count in sorted(stages.items()))
    return "\n".join(lines) + "\n"
