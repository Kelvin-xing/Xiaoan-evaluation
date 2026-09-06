"""Constraints for controlled, one-variable evaluator experiments."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


class ExperimentValidationError(ValueError):
    """Raised when a variant is not a registered one-variable experiment."""


@dataclass(frozen=True)
class VariableSpec:
    path: str
    candidates: tuple[Any, ...]
    minimum: float | None = None
    maximum: float | None = None

    def __post_init__(self) -> None:
        if not self.path:
            raise ExperimentValidationError("variable path must not be empty")
        if not self.candidates:
            raise ExperimentValidationError("variable must have explicit candidates")
        if (self.minimum is None) != (self.maximum is None):
            raise ExperimentValidationError("minimum and maximum must be provided together")
        if self.minimum is not None:
            if self.minimum > self.maximum:  # type: ignore[operator]
                raise ExperimentValidationError("minimum must not exceed maximum")
            for candidate in self.candidates:
                if (
                    isinstance(candidate, bool)
                    or not isinstance(candidate, (int, float))
                    or not self.minimum <= candidate <= self.maximum  # type: ignore[operator]
                ):
                    raise ExperimentValidationError(
                        "all candidates must be numeric and within the registered range"
                    )


@dataclass(frozen=True)
class VariantChange:
    path: str
    baseline_value: Any
    variant_value: Any


def enforce_single_variable(
    baseline: Mapping[str, Any],
    variant: Mapping[str, Any],
    registry: Mapping[str, VariableSpec],
) -> VariantChange:
    """Validate that a variant changes exactly one registered variable."""
    unregistered = (set(baseline) | set(variant)) - set(registry)
    if unregistered:
        names = ", ".join(sorted(unregistered))
        raise ExperimentValidationError(f"variant contains unregistered variable: {names}")

    if set(baseline) != set(variant):
        raise ExperimentValidationError(
            "baseline and variant must contain the same registered variables"
        )

    changed = [path for path in baseline if baseline[path] != variant[path]]
    if len(changed) != 1:
        raise ExperimentValidationError(
            "variant must change exactly one registered variable"
        )

    path = changed[0]
    spec = registry[path]
    if spec.path != path:
        raise ExperimentValidationError(
            f"registry key {path!r} does not match VariableSpec.path {spec.path!r}"
        )
    candidate = variant[path]
    if candidate not in spec.candidates:
        raise ExperimentValidationError(
            f"variant value for {path} must be an explicit candidate"
        )
    return VariantChange(path, baseline[path], candidate)
