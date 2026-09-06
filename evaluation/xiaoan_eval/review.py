"""Policy-driven second-judge selection and disagreement handling."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping

from .judge import JudgeResult


class ReviewStatus(str, Enum):
    NOT_REQUESTED = "not_requested"
    AGREED = "agreed"
    NEEDS_REVIEW = "NEEDS_REVIEW"


@dataclass(frozen=True)
class ReviewDecision:
    status: ReviewStatus
    reasons: tuple[str, ...] = ()


def should_request_second_judge(
    primary: JudgeResult,
    config: Mapping[str, Any],
    *,
    critical: bool = False,
    quality_threshold: float | None = None,
    contradiction: bool | None = None,
    release_requested: bool = False,
) -> bool:
    config = _review_config(config)
    uncertainty_levels = set(config.get("uncertainty_levels", ()))
    uncertain = any(item.uncertainty in uncertainty_levels for item in primary.red_lines) or any(
        item.uncertainty in uncertainty_levels for item in primary.dimensions
    )
    margin = _number(config, "quality_threshold_margin")
    near_gate = critical and quality_threshold is not None and abs(
        _mean_score(primary) - quality_threshold
    ) <= margin
    contradictory = has_structured_contradiction(primary) if contradiction is None else contradiction
    return uncertain or near_gate or contradictory or release_requested


def reconcile_judges(primary: JudgeResult, secondary: JudgeResult,
                     config: Mapping[str, Any]) -> ReviewDecision:
    config = _review_config(config)
    reasons: list[str] = []
    first_safety = {item.id: item.triggered for item in primary.red_lines}
    second_safety = {item.id: item.triggered for item in secondary.red_lines}
    if first_safety != second_safety:
        reasons.append("safety judgements disagree")
    threshold = _number(config, "judge_score_disagreement")
    first_scores = {item.module: item.score for item in primary.dimensions}
    second_scores = {item.module: item.score for item in secondary.dimensions}
    if first_scores.keys() != second_scores.keys() or any(
        abs(first_scores[module] - second_scores[module]) > threshold
        for module in first_scores.keys() & second_scores.keys()
    ):
        reasons.append("quality scores exceed disagreement threshold")
    status = ReviewStatus.NEEDS_REVIEW if reasons else ReviewStatus.AGREED
    return ReviewDecision(status, tuple(reasons))


def has_structured_contradiction(result: JudgeResult) -> bool:
    """Detect claims whose evidence fields contradict the structured decision."""
    return any(item.triggered and not item.evidence for item in result.red_lines) or any(
        (item.score == 3 and item.deduction_evidence)
        or (item.score == 0 and item.supporting_evidence)
        for item in result.dimensions
    )


def _mean_score(result: JudgeResult) -> float:
    if not result.dimensions:
        return 0.0
    return sum(item.score for item in result.dimensions) / len(result.dimensions)


def _number(config: Mapping[str, Any], key: str) -> float:
    value = config.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
        raise ValueError(f"review.{key} must be a non-negative number")
    return float(value)


def _review_config(config: Mapping[str, Any]) -> Mapping[str, Any]:
    nested = config.get("review")
    return nested if isinstance(nested, Mapping) else config
