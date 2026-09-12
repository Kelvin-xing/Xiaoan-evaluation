"""Versioned, reproducible turn-to-case-to-scenario scoring facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable, Mapping, Sequence

from .rules import RatingRule, RatingRuleError


SCORING_CONTRACT_VERSION = "response-effectiveness/v2"


@dataclass(frozen=True)
class TurnQuality:
    dimension_scores: Mapping[str, float]
    triggered_red_lines: tuple[str, ...] = ()


@dataclass(frozen=True)
class CaseScore:
    case_status: str
    red_line_triggered: bool
    triggered_red_lines: tuple[str, ...]
    dimension_scores: Mapping[str, float]
    final_weights: Mapping[str, float]
    weighted_total: float | None


def calculate_dynamic_weights(
    rule: RatingRule, quality_focus: Iterable[str] = ()
) -> dict[str, float]:
    return normalized_weights(
        {module.name: module.weight for module in rule.modules},
        quality_focus, rule.dynamic_weight_multiplier,
    )


def normalized_weights(base: Mapping[str, float], focus: Iterable[str], multiplier: float = 1.5) -> dict[str, float]:
    selected = set(focus)
    if selected - set(base):
        raise RatingRuleError(f"quality_focus contains unknown modules: {sorted(selected - set(base))!r}")
    adjusted = {name: weight * (multiplier if name in selected else 1.0) for name, weight in base.items()}
    total = sum(adjusted.values())
    if total <= 0:
        raise ValueError("dimension weights must sum to a positive number")
    return {name: weight / total for name, weight in adjusted.items()}


def score_case(
    rule: RatingRule,
    turns: Sequence[TurnQuality],
    quality_focus: Iterable[str] = (),
) -> CaseScore:
    if not turns:
        raise ValueError("a case must contain at least one turn")
    final_weights = calculate_dynamic_weights(rule, quality_focus)
    triggered = _ordered_unique(
        red_line for turn in turns for red_line in turn.triggered_red_lines
    )
    if triggered:
        known = {red_line.id for red_line in rule.red_lines}
        unknown = set(triggered) - known
        if unknown:
            raise ValueError(f"unknown triggered red lines: {sorted(unknown)!r}")
        return CaseScore(
            "FAIL", True, triggered,
            {module.name: 0.0 for module in rule.modules}, final_weights, 0.0,
        )
    expected = {module.name for module in rule.modules}
    totals = {module.name: 0.0 for module in rule.modules}
    for index, turn in enumerate(turns):
        actual = set(turn.dimension_scores)
        if actual != expected:
            raise ValueError(
                f"turn {index + 1} dimension scores mismatch; "
                f"missing={sorted(expected - actual)!r}, extra={sorted(actual - expected)!r}"
            )
        for name, raw in turn.dimension_scores.items():
            totals[name] += _quality_score(raw, name, index)
    scores = {name: total / len(turns) for name, total in totals.items()}
    weighted = sum(scores[name] * final_weights[name] for name in scores)
    return CaseScore("PASS", False, (), scores, final_weights, weighted)


@dataclass(frozen=True)
class TurnDimensionFact:
    case_id: str
    turn: int
    dimension: str
    status: str
    value: float | None
    reason: str = ""

    def __post_init__(self) -> None:
        if self.status == "AVAILABLE":
            if self.value is None or not 0 <= self.value <= 3:
                raise ValueError("available rating values must be within 0..3")
        elif self.value is not None:
            raise ValueError("unavailable rating facts cannot carry a numeric value")


@dataclass(frozen=True)
class CaseScoreFact:
    case_id: str
    status: str
    value: float | None
    expected_turns: tuple[int, ...]
    dimension_means: Mapping[str, float]
    dimension_weights: Mapping[str, float]
    exclusions: tuple[str, ...]
    formula: str = "mean all dimensions across expected turns, then dynamic-focus weighted mean"
    scoring_contract_version: str = SCORING_CONTRACT_VERSION


@dataclass(frozen=True)
class ScenarioScoreFact:
    scenario_id: str
    comparability_group: str
    status: str
    value: float | None
    expected_cases: int
    completed_cases: int
    eligible_cases: int
    excluded_cases: int
    included_case_ids: tuple[str, ...]
    exclusions: Mapping[str, str]
    formula: str = "unweighted mean of eligible APPROVED_AGGREGATE case scores"
    scoring_contract_version: str = SCORING_CONTRACT_VERSION


def score_case_fact(
    *,
    case_id: str,
    expected_turns: Sequence[int],
    quality_focus: Sequence[str],
    dimension_weights: Mapping[str, float],
    turn_facts: Sequence[TurnDimensionFact],
    dynamic_weight_multiplier: float = 1.5,
) -> CaseScoreFact:
    expected = tuple(expected_turns)
    if not expected or len(set(expected)) != len(expected):
        raise ValueError("expected_turns must be non-empty and unique")
    focus = tuple(quality_focus)
    exclusions: list[str] = []
    means: dict[str, float] = {}
    for dimension in dimension_weights:
        values: list[float] = []
        for turn in expected:
            matches = [
                fact
                for fact in turn_facts
                if fact.case_id == case_id
                and fact.turn == turn
                and fact.dimension == dimension
                and fact.status == "AVAILABLE"
            ]
            if len(matches) != 1 or matches[0].value is None:
                exclusions.append(f"{dimension}:TURN_{turn}_UNAVAILABLE")
                continue
            values.append(matches[0].value)
        if len(values) == len(expected):
            means[dimension] = sum(values) / len(values)
    if exclusions or set(means) != set(dimension_weights):
        return CaseScoreFact(
            case_id=case_id,
            status="UNAVAILABLE",
            value=None,
            expected_turns=expected,
            dimension_means=means,
            dimension_weights={},
            exclusions=tuple(exclusions),
        )
    weights = normalized_weights(dimension_weights, focus, dynamic_weight_multiplier)
    value = sum(means[key] * weights[key] for key in dimension_weights)
    return CaseScoreFact(
        case_id=case_id,
        status="AVAILABLE",
        value=value,
        expected_turns=expected,
        dimension_means=means,
        dimension_weights=weights,
        exclusions=(),
    )


def score_scenario(
    *,
    scenario_id: str,
    comparability_group: str,
    cases: Sequence[Mapping[str, object]],
    case_scores: Mapping[str, CaseScoreFact],
) -> ScenarioScoreFact:
    matching = [
        case
        for case in cases
        if case.get("scenario_id") == scenario_id
        and case.get("comparability_group") == comparability_group
    ]
    included: list[str] = []
    values: list[float] = []
    exclusions: dict[str, str] = {}
    completed = 0
    for case in matching:
        case_id = str(case["case_id"])
        score = case_scores.get(case_id)
        if score is not None and score.status == "AVAILABLE":
            completed += 1
        if case.get("maturity") != "APPROVED_AGGREGATE":
            exclusions[case_id] = "MATURITY_INELIGIBLE"
        elif score is None or score.status != "AVAILABLE" or score.value is None:
            exclusions[case_id] = "SCORE_UNAVAILABLE"
        else:
            included.append(case_id)
            values.append(score.value)
    return ScenarioScoreFact(
        scenario_id=scenario_id,
        comparability_group=comparability_group,
        status="AVAILABLE" if values else "NOT_APPLICABLE",
        value=sum(values) / len(values) if values else None,
        expected_cases=len(matching),
        completed_cases=completed,
        eligible_cases=len(values),
        excluded_cases=len(exclusions),
        included_case_ids=tuple(included),
        exclusions=exclusions,
    )


def fact_dict(fact: object) -> dict[str, object]:
    return asdict(fact)  # type: ignore[arg-type]


def _quality_score(value: object, module: str, turn_index: int) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not float(value).is_integer()
    ):
        raise ValueError(
            f"turn {turn_index + 1} score for {module!r} must be an anchored integer"
        )
    score = float(value)
    if not 0 <= score <= 3:
        raise ValueError(
            f"turn {turn_index + 1} score for {module!r} must be between 0 and 3"
        )
    return score


def _ordered_unique(values: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(values))
