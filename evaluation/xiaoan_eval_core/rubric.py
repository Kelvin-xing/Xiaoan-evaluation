"""Deterministic rubric-stage contract for the shared evaluation runner.

The provider is responsible for judging the dimensions and red lines.  This
module is responsible for validating that payload and applying the frozen
ratings rule.  It deliberately does not call a provider or infer a missing
observation: a missing/failed judge is represented as ``UNAVAILABLE``.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any


class RubricContractError(ValueError):
    """A supplied rubric payload cannot be safely scored."""


def evaluate_rubric(
    answer: Mapping[str, Any],
    judge_payload: Any,
    rating_rule: Any,
    *,
    status: str = "AVAILABLE",
    reason: str | None = None,
) -> dict[str, Any]:
    """Validate and score one answer against the existing ratings rule.

    ``rating_rule`` is intentionally duck-typed so both the parsed
    ``RatingRule`` and serialized rule adapters can use this stage.  A
    provider failure should call this function with ``judge_payload=None`` or
    ``status="UNAVAILABLE"``.  Invalid non-empty payloads raise
    :class:`RubricContractError`; callers should record that as an unavailable
    stage with the validation reason rather than assigning a zero score.
    """
    if status != "AVAILABLE" or judge_payload is None:
        why = reason or "rubric judge result was not available"
        return _unavailable(why)

    dimensions = _field(judge_payload, "dimensions")
    red_lines = _field(judge_payload, "red_lines")
    expected_modules = tuple(_name(module) for module in rating_rule.modules)
    expected_red_lines = tuple(_id(item) for item in rating_rule.red_lines)

    parsed_dimensions = _parse_dimensions(dimensions, expected_modules, rating_rule)
    parsed_red_lines = _parse_red_lines(red_lines, expected_red_lines)
    triggered = tuple(item["id"] for item in parsed_red_lines if item["triggered"])

    focus = _quality_focus(answer)
    weights = _dynamic_weights(rating_rule, expected_modules, focus)
    scores = {item["module"]: item["score"] for item in parsed_dimensions}
    weighted_total = sum(scores[name] * weights[name] for name in expected_modules)
    reasons = [f"red line triggered: {identifier}" for identifier in triggered]

    result: dict[str, Any] = {
        "status": "AVAILABLE",
        "scores": scores,
        "dimension_details": parsed_dimensions,
        "gate": "FAIL" if triggered else "PASS",
        "weighted_total": weighted_total,
        "final_weights": weights,
        "red_lines": parsed_red_lines,
        "triggered_red_lines": list(triggered),
        "red_line_triggered": bool(triggered),
        "reasons": reasons,
        # Compatibility names used by the legacy pipeline/exporters.
        "dimensions": scores,
        "weighted_score": weighted_total,
    }
    return result


def _unavailable(reason: str) -> dict[str, Any]:
    """Return a stable no-score result; missing observations are never zeroes."""
    result: dict[str, Any] = {
        "status": "UNAVAILABLE",
        "scores": {},
        "weighted_total": None,
        "final_weights": {},
        "red_lines": [],
        "triggered_red_lines": [],
        "red_line_triggered": False,
        "reasons": [reason],
        "dimensions": {},
        "weighted_score": None,
    }
    return result


def _field(value: Any, name: str) -> Any:
    if isinstance(value, Mapping):
        result = value.get(name)
    else:
        result = getattr(value, name, None)
    if not isinstance(result, (list, tuple)):
        raise RubricContractError(f"judge payload.{name} must be an array")
    return result


def _parse_dimensions(rows: Iterable[Any], expected: tuple[str, ...], rule: Any) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    allowed = {int(_field_value(anchor, "score")) for anchor in rule.score_scale}
    for index, row in enumerate(rows):
        module = _required(row, "module", f"dimensions[{index}]")
        score = _field_value(row, "score")
        if (isinstance(score, bool) or not isinstance(score, (int, float))
                or int(score) != score or int(score) not in allowed):
            raise RubricContractError(
                f"dimensions[{index}].score must be an anchored integer from {sorted(allowed)}"
            )
        score = int(score)
        parsed.append({
            "module": module,
            "score": score,
            "reason": _required(row, "reason", f"dimensions[{index}]"),
            "supporting_evidence": list(_string_list(row, "supporting_evidence", f"dimensions[{index}")),
            "deduction_evidence": list(_string_list(row, "deduction_evidence", f"dimensions[{index}")),
            "uncertainty": _field_value(row, "uncertainty", default=None),
        })
    actual = tuple(item["module"] for item in parsed)
    if len(parsed) != len(expected) or set(actual) != set(expected) or len(set(actual)) != len(actual):
        raise RubricContractError(
            "dimensions must contain exactly the unique modules from the rating rule"
        )
    return parsed


def _parse_red_lines(rows: Iterable[Any], expected: tuple[str, ...]) -> list[dict[str, Any]]:
    parsed: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        identifier = _required(row, "id", f"red_lines[{index}]")
        triggered = _field_value(row, "triggered")
        if type(triggered) is not bool:
            raise RubricContractError(f"red_lines[{index}].triggered must be boolean")
        evidence = _string_list(row, "evidence", f"red_lines[{index}", default=())
        if not evidence:
            evidence = _string_list(row, "evidence_refs", f"red_lines[{index}", default=())
        parsed.append({"id": identifier, "triggered": triggered, "evidence": list(evidence),
                       "reason": _required(row, "reason", f"red_lines[{index}]"),
                       "uncertainty": _field_value(row, "uncertainty", default=None)})
    actual = tuple(item["id"] for item in parsed)
    if len(parsed) != len(expected) or set(actual) != set(expected) or len(set(actual)) != len(actual):
        raise RubricContractError(
            "red_lines must contain exactly the unique IDs from the rating rule"
        )
    return parsed


def _dynamic_weights(rule: Any, modules: tuple[str, ...], focus: tuple[str, ...]) -> dict[str, float]:
    selected = set(focus)
    unknown = selected - set(modules)
    if unknown:
        raise RubricContractError(f"quality_focus contains unknown modules: {sorted(unknown)!r}")
    multiplier = float(getattr(rule, "dynamic_weight_multiplier", 1.5))
    raw = {
        _name(module): float(getattr(module, "weight", _field_value(module, "weight")))
        for module in rule.modules
    }
    adjusted = {name: weight * (multiplier if name in selected else 1.0)
                for name, weight in raw.items()}
    total = sum(adjusted.values())
    if total <= 0:
        raise RubricContractError("dimension weights must sum to a positive number")
    return {name: value / total for name, value in adjusted.items()}


def _quality_focus(answer: Mapping[str, Any]) -> tuple[str, ...]:
    value = answer.get("quality_focus", ())
    if value is None:
        return ()
    if isinstance(value, str) or not isinstance(value, (list, tuple, set)):
        raise RubricContractError("quality_focus must be an array")
    return tuple(str(item) for item in value)


def _name(value: Any) -> str:
    return str(getattr(value, "name", _field_value(value, "name")))


def _id(value: Any) -> str:
    return str(getattr(value, "id", _field_value(value, "id")))


def _field_value(value: Any, name: str, default: Any = ...):
    if isinstance(value, Mapping):
        if name in value:
            return value[name]
    elif hasattr(value, name):
        return getattr(value, name)
    if default is not ...:
        return default
    raise RubricContractError(f"missing required field: {name}")


def _required(value: Any, name: str, location: str) -> str:
    field = _field_value(value, name, default=None)
    if not isinstance(field, str) or not field.strip():
        raise RubricContractError(f"{location}.{name} must be a non-empty string")
    return field


def _string_list(value: Any, name: str, location: str, default: tuple[str, ...] | None = None) -> tuple[str, ...]:
    field = _field_value(value, name, default=default)
    if field is None:
        return ()
    if not isinstance(field, (list, tuple)) or any(not isinstance(item, str) or not item.strip() for item in field):
        raise RubricContractError(f"{location}.{name} must be an array of strings")
    return tuple(field)
