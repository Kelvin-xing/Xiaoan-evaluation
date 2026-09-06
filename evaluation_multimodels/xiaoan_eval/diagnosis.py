"""Rule-based failure attribution from an evaluator turn trace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping


class DiagnosisError(ValueError):
    """Raised when a trace cannot be attributed using a registered pattern."""


@dataclass(frozen=True)
class CandidateLever:
    type: str
    target: str


@dataclass(frozen=True)
class FailureAttribution:
    primary_stage: str
    secondary_stages: tuple[str, ...]
    candidate_lever: CandidateLever
    status: str = "hypothesis"


@dataclass(frozen=True)
class _Pattern:
    stage: str
    lever_type: str
    target: str
    matches: Callable[[Mapping[str, Any]], bool]


def _is(trace: Mapping[str, Any], section: str, field: str, value: Any) -> bool:
    data = trace.get(section)
    return isinstance(data, Mapping) and data.get(field) is value


_PATTERNS = (
    _Pattern(
        "test_case",
        "test_case",
        "test case remediation",
        lambda trace: _is(trace, "test_case", "oracle_determinable", False),
    ),
    _Pattern(
        "output_guard",
        "process",
        "output guard rules/process",
        lambda trace: _is(trace, "output_guard", "unsafe_input", True)
        and _is(trace, "output_guard", "blocked", False),
    ),
    _Pattern(
        "safety",
        "prompt",
        "safety rules/prompt/process",
        lambda trace: _is(trace, "safety", "correct", False),
    ),
    _Pattern(
        "router",
        "prompt",
        "router prompt/model/context turns",
        lambda trace: _is(trace, "safety", "correct", True)
        and _is(trace, "route", "correct", False),
    ),
    _Pattern(
        "ground",
        "process",
        "load policy/capsule-node mapping/knowledge",
        lambda trace: _is(trace, "route", "correct", True)
        and (
            _is(trace, "ground", "loaded", False)
            or _is(trace, "ground", "refs_complete", False)
        ),
    ),
    _Pattern(
        "memory",
        "hyperparameter",
        "context turns/state/continuation process",
        lambda trace: _is(trace, "memory", "fact_available", True)
        and _is(trace, "memory", "used_correctly", False),
    ),
    _Pattern(
        "composer",
        "prompt",
        "composer prompt/model/verbosity",
        lambda trace: _is(trace, "route", "correct", True)
        and _is(trace, "ground", "loaded", True)
        and _is(trace, "ground", "refs_complete", True)
        and _is(trace, "answer", "faithful", False),
    ),
    _Pattern(
        "performance",
        "hyperparameter",
        "model/context/ground size/stream policy",
        lambda trace: _is(trace, "performance", "within_budget", False),
    ),
)


def attribute_failure(trace: Mapping[str, Any]) -> FailureAttribution:
    """Return the highest-priority failure stage and its candidate lever."""
    if not isinstance(trace, Mapping):
        raise DiagnosisError("trace must be a mapping")
    matched = tuple(pattern for pattern in _PATTERNS if pattern.matches(trace))
    if not matched:
        raise DiagnosisError("trace does not match a registered failure pattern")
    primary = matched[0]
    return FailureAttribution(
        primary_stage=primary.stage,
        secondary_stages=tuple(pattern.stage for pattern in matched[1:]),
        candidate_lever=CandidateLever(primary.lever_type, primary.target),
    )
