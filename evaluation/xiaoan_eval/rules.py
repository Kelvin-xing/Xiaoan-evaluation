from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Mapping

import yaml


class RatingRuleError(ValueError):
    """The authoritative rating policy cannot be used safely."""


class MetricStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    ERROR = "error"
    SKIP = "skip"


@dataclass(frozen=True)
class MetricResult:
    status: MetricStatus
    score: float | None
    reason: str
    evidence: tuple[str, ...] = ()
    counts: Mapping[str, int] | None = None


@dataclass(frozen=True)
class RedLineRule:
    id: str
    name: str
    description: str


@dataclass(frozen=True)
class RubricModule:
    name: str
    weight: float
    positive: tuple[str, ...]
    negative: tuple[str, ...]


@dataclass(frozen=True)
class ScoreAnchor:
    score: int
    description: str


@dataclass(frozen=True)
class RatingRule:
    schema_version: str
    score_scale: tuple[ScoreAnchor, ...]
    red_lines: tuple[RedLineRule, ...]
    modules: tuple[RubricModule, ...]
    dynamic_weight_multiplier: float


def load_rating_rule(path: str | Path) -> RatingRule:
    rule_path = Path(path)
    try:
        document = yaml.safe_load(rule_path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError) as exc:
        raise RatingRuleError(f"cannot read rating rule: {rule_path}") from exc
    except yaml.YAMLError as exc:
        raise RatingRuleError(f"cannot parse rating rule: {rule_path}") from exc

    if not isinstance(document, Mapping):
        raise RatingRuleError("rating rule must be a mapping")

    schema_version = document.get("schema_version")
    if schema_version != "1.1":
        raise RatingRuleError(f"unsupported schema_version: {schema_version!r}")

    score_scale = _parse_score_scale(document.get("score_scale"))
    red_lines = _parse_red_lines(document.get("red_lines"))
    modules = _parse_modules(document.get("quality_rubric"))
    multiplier = _positive_number(
        document.get("dynamic_weight_multiplier"),
        "dynamic_weight_multiplier",
    )

    total_weight = sum(module.weight for module in modules)
    if abs(total_weight - 1.0) > 1e-9:
        raise RatingRuleError(
            f"quality_rubric weights must sum to 1, got {total_weight}"
        )

    return RatingRule(schema_version, score_scale, red_lines, modules, multiplier)


def _parse_score_scale(value: Any) -> tuple[ScoreAnchor, ...]:
    rows = _nonempty_list(value, "score_scale")
    anchors: list[ScoreAnchor] = []
    for index, row in enumerate(rows):
        mapping = _mapping(row, f"score_scale[{index}]")
        score = mapping.get("score")
        if isinstance(score, bool) or not isinstance(score, int):
            raise RatingRuleError(f"score_scale[{index}].score must be an integer")
        anchors.append(
            ScoreAnchor(
                score=score,
                description=_text(
                    mapping.get("description"), f"score_scale[{index}].description"
                ),
            )
        )
    if [anchor.score for anchor in anchors] != [0, 1, 2, 3]:
        raise RatingRuleError("score_scale must contain exactly the scores 0, 1, 2, and 3")
    return tuple(anchors)


def _parse_red_lines(value: Any) -> tuple[RedLineRule, ...]:
    rows = _nonempty_list(value, "red_lines")
    rules: list[RedLineRule] = []
    for index, row in enumerate(rows):
        mapping = _mapping(row, f"red_lines[{index}]")
        rules.append(
            RedLineRule(
                id=_text(mapping.get("id"), f"red_lines[{index}].id"),
                name=_text(mapping.get("name"), f"red_lines[{index}].name"),
                description=_text(
                    mapping.get("description"), f"red_lines[{index}].description"
                ),
            )
        )
    ids = [rule.id for rule in rules]
    if len(ids) != len(set(ids)):
        raise RatingRuleError("red_lines ids must be unique")
    return tuple(rules)


def _parse_modules(value: Any) -> tuple[RubricModule, ...]:
    rows = _nonempty_list(value, "quality_rubric")
    modules: list[RubricModule] = []
    for index, row in enumerate(rows):
        mapping = _mapping(row, f"quality_rubric[{index}]")
        prefix = f"quality_rubric[{index}]"
        modules.append(
            RubricModule(
                name=_text(mapping.get("module"), f"{prefix}.module"),
                weight=_positive_number(mapping.get("weight"), f"{prefix}.weight"),
                positive=_text_list(mapping.get("positive"), f"{prefix}.positive"),
                negative=_text_list(mapping.get("negative"), f"{prefix}.negative"),
            )
        )
    names = [module.name for module in modules]
    if len(names) != len(set(names)):
        raise RatingRuleError("quality_rubric module names must be unique")
    return tuple(modules)


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise RatingRuleError(f"{field} must be a mapping")
    return value


def _nonempty_list(value: Any, field: str) -> list[Any]:
    if not isinstance(value, list) or not value:
        raise RatingRuleError(f"{field} must be a non-empty list")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise RatingRuleError(f"{field} must be non-empty text")
    return value.strip()


def _text_list(value: Any, field: str) -> tuple[str, ...]:
    rows = _nonempty_list(value, field)
    return tuple(_text(item, f"{field}[]") for item in rows)


def _positive_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or value <= 0:
        raise RatingRuleError(f"{field} must be a positive number")
    return float(value)
