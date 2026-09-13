"""Validation boundary for structured semantic judge responses."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence

from .rules import RatingRule


UNCERTAINTY_LEVELS = frozenset({"low", "medium", "high"})


class JudgeValidationError(ValueError):
    """Raised when a provider response does not satisfy the judge contract."""


@dataclass(frozen=True)
class RedLineJudgement:
    id: str
    triggered: bool
    evidence: tuple[str, ...]
    uncertainty: str


@dataclass(frozen=True)
class DimensionJudgement:
    module: str
    score: float
    supporting_evidence: tuple[str, ...]
    deduction_evidence: tuple[str, ...]
    uncertainty: str


@dataclass(frozen=True)
class ClaimJudgement:
    claim: str
    supported: bool
    evidence_refs: tuple[str, ...]
    uncertainty: str


@dataclass(frozen=True)
class JudgeResult:
    red_lines: tuple[RedLineJudgement, ...]
    dimensions: tuple[DimensionJudgement, ...]
    legal_claims: tuple[ClaimJudgement, ...] = ()
    faithfulness_claims: tuple[ClaimJudgement, ...] = ()
    oracle_assessment: Mapping[str, Any] | None = None


def validate_claim_evidence(
    result: JudgeResult, evidence_catalog: Sequence[Mapping[str, Any]]
) -> None:
    """Require every supported claim to cite evidence supplied for this turn."""
    valid_refs = {
        item.get("ref")
        for item in evidence_catalog
        if isinstance(item.get("ref"), str) and item["ref"].strip()
    }
    for field, claims in (
        ("legal_claims", result.legal_claims),
        ("faithfulness_claims", result.faithfulness_claims),
    ):
        for index, claim in enumerate(claims):
            location = f"{field}[{index}]"
            if claim.supported and not claim.evidence_refs:
                raise JudgeValidationError(
                    f"{location}.supported=true requires at least one evidence_ref"
                )
            if not claim.supported and claim.evidence_refs:
                raise JudgeValidationError(
                    f"{location}.supported=false requires empty evidence_refs"
                )
            unknown = set(claim.evidence_refs) - valid_refs
            if unknown:
                raise JudgeValidationError(
                    f"{location}.evidence_refs contains unknown refs: {sorted(unknown)}"
                )


def parse_judge_response(raw_json: str, rating_rule: RatingRule) -> JudgeResult:
    """Parse and validate untrusted JSON returned by a judge provider."""
    if not isinstance(raw_json, str):
        raise JudgeValidationError("judge response must be a JSON string")
    try:
        payload = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise JudgeValidationError("judge response must be valid JSON") from exc

    root = _mapping(payload, "judge response")
    red_line_items = _list_field(root, "red_lines")
    dimension_items = _list_field(root, "dimensions")
    legal_claim_items = _list_field(root, "legal_claims")
    faithfulness_items = _list_field(root, "faithfulness_claims")

    red_lines = tuple(_parse_red_line(item, index) for index, item in enumerate(red_line_items))
    red_line_ids = {item.id for item in red_lines}
    expected_red_line_ids = {item.id for item in rating_rule.red_lines}
    if len(red_lines) != len(expected_red_line_ids) or red_line_ids != expected_red_line_ids:
        raise JudgeValidationError(
            "red_lines must contain exactly the unique IDs from the rating rule"
        )

    dimensions = tuple(
        _parse_dimension(item, index, rating_rule)
        for index, item in enumerate(dimension_items)
    )
    modules = {item.module for item in dimensions}
    expected_modules = {item.name for item in rating_rule.modules}
    if len(dimensions) != len(expected_modules) or modules != expected_modules:
        raise JudgeValidationError(
            "dimensions must contain exactly the unique modules from the rating rule"
        )

    return JudgeResult(
        oracle_assessment=root.get("oracle_assessment"),
        red_lines=red_lines,
        dimensions=dimensions,
        legal_claims=tuple(
            _parse_claim(item, index, "legal_claims")
            for index, item in enumerate(legal_claim_items)
        ),
        faithfulness_claims=tuple(
            _parse_claim(item, index, "faithfulness_claims")
            for index, item in enumerate(faithfulness_items)
        ),
    )


def _parse_red_line(value: Any, index: int) -> RedLineJudgement:
    item = _mapping(value, f"red_lines[{index}]")
    identifier = _non_empty_string(item, "id", f"red_lines[{index}]")
    triggered = item.get("triggered")
    if not isinstance(triggered, bool):
        raise JudgeValidationError(f"red_lines[{index}].triggered must be boolean")
    return RedLineJudgement(
        id=identifier,
        triggered=triggered,
        evidence=_string_list(item, "evidence", f"red_lines[{index}]"),
        uncertainty=_uncertainty(item, f"red_lines[{index}]"),
    )


def _parse_dimension(
    value: Any, index: int, rating_rule: RatingRule
) -> DimensionJudgement:
    item = _mapping(value, f"dimensions[{index}]")
    score = item.get("score")
    allowed_scores = {anchor.score for anchor in rating_rule.score_scale}
    if isinstance(score, bool) or not isinstance(score, int) or score not in allowed_scores:
        raise JudgeValidationError(
            f"dimensions[{index}].score must be an anchored integer from {sorted(allowed_scores)}"
        )
    return DimensionJudgement(
        module=_non_empty_string(item, "module", f"dimensions[{index}]"),
        score=float(score),
        supporting_evidence=_string_list(
            item, "supporting_evidence", f"dimensions[{index}]"
        ),
        deduction_evidence=_string_list(
            item, "deduction_evidence", f"dimensions[{index}]"
        ),
        uncertainty=_uncertainty(item, f"dimensions[{index}]"),
    )


def _parse_claim(value: Any, index: int, field: str) -> ClaimJudgement:
    item = _mapping(value, f"{field}[{index}]")
    supported = item.get("supported")
    if not isinstance(supported, bool):
        raise JudgeValidationError(f"{field}[{index}].supported must be boolean")
    return ClaimJudgement(
        claim=_non_empty_string(item, "claim", f"{field}[{index}]"),
        supported=supported,
        evidence_refs=_string_list(item, "evidence_refs", f"{field}[{index}]"),
        uncertainty=_uncertainty(item, f"{field}[{index}]"),
    )


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise JudgeValidationError(f"{location} must be an object")
    return value


def _list_field(item: Mapping[str, Any], field: str) -> Sequence[Any]:
    value = item.get(field)
    if not isinstance(value, list):
        raise JudgeValidationError(f"judge response.{field} must be an array")
    return value


def _non_empty_string(item: Mapping[str, Any], field: str, location: str) -> str:
    value = item.get(field)
    if not isinstance(value, str) or not value.strip():
        raise JudgeValidationError(f"{location}.{field} must be a non-empty string")
    return value


def _string_list(item: Mapping[str, Any], field: str, location: str) -> tuple[str, ...]:
    value = item.get(field)
    if not isinstance(value, list) or any(
        not isinstance(entry, str) or not entry.strip() for entry in value
    ):
        raise JudgeValidationError(f"{location}.{field} must be an array of strings")
    return tuple(value)


def _uncertainty(item: Mapping[str, Any], location: str) -> str:
    value = item.get("uncertainty")
    if value not in UNCERTAINTY_LEVELS:
        raise JudgeValidationError(
            f"{location}.uncertainty must be low, medium, or high"
        )
    return value
