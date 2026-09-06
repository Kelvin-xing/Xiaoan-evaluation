from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

import yaml

from .experiments import ExperimentValidationError, VariableSpec


class ConfigError(ValueError):
    pass


@dataclass(frozen=True)
class ExperimentConfig:
    repeats: int
    seeds: tuple[int, ...]
    min_target_cohort_pass_rate_delta: float
    min_weighted_total_delta: float
    max_non_target_weighted_regression: float
    critical_hard_gate_regression_tolerance: float


@dataclass(frozen=True)
class ReviewConfig:
    uncertainty_levels: tuple[str, ...]
    quality_threshold_margin: float
    judge_score_disagreement: float


@dataclass(frozen=True)
class EvaluatorConfig:
    schema_version: str
    experiment: ExperimentConfig
    review: ReviewConfig
    parameters: Mapping[str, VariableSpec]


def load_evaluator_config(path: str | Path) -> EvaluatorConfig:
    source = Path(path)
    try:
        document = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ConfigError(f"cannot load evaluator config: {source}") from exc
    root = _mapping(document, "config")
    version = root.get("schema_version")
    if version != "1.0":
        raise ConfigError(f"unsupported schema_version: {version!r}")

    experiment_raw = _mapping(root.get("experiment"), "experiment")
    review_raw = _mapping(root.get("review"), "review")
    parameters_raw = _mapping(root.get("parameters"), "parameters")

    repeats = _positive_int(experiment_raw.get("repeats"), "experiment.repeats")
    seeds_raw = experiment_raw.get("seeds")
    if not isinstance(seeds_raw, list) or len(seeds_raw) != repeats or any(
        isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds_raw
    ):
        raise ConfigError("experiment.seeds must contain one integer per repeat")

    uncertainty_raw = review_raw.get("uncertainty_levels")
    if not isinstance(uncertainty_raw, list) or not uncertainty_raw or any(
        item not in {"low", "medium", "high"} for item in uncertainty_raw
    ):
        raise ConfigError("review.uncertainty_levels contains unsupported values")

    registry: dict[str, VariableSpec] = {}
    for path_name, value in parameters_raw.items():
        if not isinstance(path_name, str) or not path_name:
            raise ConfigError("parameter paths must be non-empty strings")
        item = _mapping(value, f"parameters.{path_name}")
        candidates = item.get("candidates")
        if not isinstance(candidates, list) or not candidates:
            raise ConfigError(f"parameters.{path_name}.candidates must be non-empty")
        minimum = _optional_number(item.get("min"), f"parameters.{path_name}.min")
        maximum = _optional_number(item.get("max"), f"parameters.{path_name}.max")
        try:
            registry[path_name] = VariableSpec(
                path=path_name,
                candidates=tuple(candidates),
                minimum=minimum,
                maximum=maximum,
            )
        except ExperimentValidationError as exc:
            raise ConfigError(
                f"parameters.{path_name} candidates must be within min/max"
            ) from exc
        if item.get("current") not in candidates:
            raise ConfigError(
                f"parameters.{path_name}.current must be an explicit candidate"
            )

    return EvaluatorConfig(
        schema_version=version,
        experiment=ExperimentConfig(
            repeats=repeats,
            seeds=tuple(seeds_raw),
            min_target_cohort_pass_rate_delta=_number(
                experiment_raw.get("min_target_cohort_pass_rate_delta"),
                "experiment.min_target_cohort_pass_rate_delta",
            ),
            min_weighted_total_delta=_number(
                experiment_raw.get("min_weighted_total_delta"),
                "experiment.min_weighted_total_delta",
            ),
            max_non_target_weighted_regression=_number(
                experiment_raw.get("max_non_target_weighted_regression"),
                "experiment.max_non_target_weighted_regression",
            ),
            critical_hard_gate_regression_tolerance=_number(
                experiment_raw.get("critical_hard_gate_regression_tolerance"),
                "experiment.critical_hard_gate_regression_tolerance",
            ),
        ),
        review=ReviewConfig(
            uncertainty_levels=tuple(uncertainty_raw),
            quality_threshold_margin=_number(
                review_raw.get("quality_threshold_margin"),
                "review.quality_threshold_margin",
            ),
            judge_score_disagreement=_number(
                review_raw.get("judge_score_disagreement"),
                "review.judge_score_disagreement",
            ),
        ),
        parameters=registry,
    )


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ConfigError(f"{field} must be a mapping")
    return value


def _number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ConfigError(f"{field} must be numeric")
    return float(value)


def _optional_number(value: Any, field: str) -> float | None:
    if value is None:
        return None
    return _number(value, field)


def _positive_int(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise ConfigError(f"{field} must be a positive integer")
    return value
