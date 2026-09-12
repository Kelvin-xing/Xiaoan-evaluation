"""Pure deterministic metrics over a reviewed case oracle and structured trace."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from .cases import ExpectedOutcome, MemoryCheckpoint
from .rules import MetricResult, MetricStatus


REQUIRED_TRACE_SECTIONS = frozenset(
    {"safety", "route", "ground", "guard", "state", "timings", "tokens"}
)
REQUIRED_TIMING_FIELDS = frozenset(
    {"ttft_ms", "first_guarded_delta_ms", "router_ms", "ground_ms", "generation_ms", "total_ms"}
)
REQUIRED_TOKEN_FIELDS = frozenset({"input", "output"})


@dataclass(frozen=True)
class RetrievalConfusion:
    """Auditable set confusion counts; TN is absent without a finite universe."""

    tp: int
    fp: int
    fn: int
    tn: int | None = None

    @property
    def precision(self) -> float | None:
        denominator = self.tp + self.fp
        return self.tp / denominator if denominator else None

    @property
    def recall(self) -> float | None:
        denominator = self.tp + self.fn
        return self.tp / denominator if denominator else None

    @property
    def f1(self) -> float | None:
        precision, recall = self.precision, self.recall
        return 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None


def retrieval_confusion(
    gold_refs: Sequence[str], retrieved_refs: Sequence[str],
    *, universe: Sequence[str] | None = None,
) -> RetrievalConfusion:
    """Compute retrieval TP/FP/FN and only compute TN for an explicit corpus universe."""
    gold, retrieved = set(map(str, gold_refs)), set(map(str, retrieved_refs))
    tp = len(gold & retrieved)
    fp = len(retrieved - gold)
    fn = len(gold - retrieved)
    tn = None
    if universe is not None:
        candidates = set(map(str, universe))
        outside = (gold | retrieved) - candidates
        if outside:
            raise ValueError(
                f"retrieval labels outside explicit universe: {sorted(outside)!r}"
            )
        tn = len(candidates - gold - retrieved)
    return RetrievalConfusion(tp, fp, fn, tn)


def evaluate_hard_gates(
    trace: Mapping[str, Any],
    *,
    response_is_pii_safe: bool | None,
    known_route_ids: frozenset[str],
) -> dict[str, MetricResult]:
    """Evaluate oracle-independent Stage 1 validity and privacy gates."""
    results: dict[str, MetricResult] = {}
    if response_is_pii_safe is not None:
        results["pii_leakage"] = (
            _pass("assistant response passed PII validation")
            if response_is_pii_safe
            else _fail("assistant response contains PII", (), 0.0)
        )
    route = trace.get("route")
    route_id = None
    if isinstance(route, Mapping):
        route_id = route.get("id", route.get("route_id"))
    if not isinstance(route_id, str) or not route_id:
        results["route_validity"] = _error("route trace has no route ID")
    elif known_route_ids and route_id not in known_route_ids:
        results["route_validity"] = _fail(
            "route/capsule ID is not registered", (route_id,), 0.0
        )
    else:
        results["route_validity"] = _pass("route/capsule ID is registered", (route_id,))

    guard = trace.get("guard")
    if not isinstance(guard, Mapping) or not isinstance(guard.get("passed"), bool):
        results["output_guard"] = _error("output guard result is missing")
    elif guard["passed"]:
        results["output_guard"] = _pass("output guard passed")
    else:
        results["output_guard"] = _fail("output guard rejected the answer", (), 0.0)

    ground = trace.get("ground")
    if not isinstance(ground, Mapping):
        results["ground_resolution"] = _error("ground trace is missing")
    else:
        errors = ground.get("resolution_errors", ())
        explicit_error = ground.get("resolution_error") is True
        warnings = ground.get("warnings", ())
        error_warnings = (
            [str(item) for item in warnings if _looks_like_resolution_error(str(item))]
            if isinstance(warnings, Sequence) and not isinstance(warnings, (str, bytes))
            else []
        )
        if explicit_error or (isinstance(errors, Sequence) and len(errors) > 0) or error_warnings:
            evidence = tuple(str(item) for item in errors) if isinstance(errors, Sequence) else ()
            results["ground_resolution"] = _fail(
                "ground resolution error detected", evidence + tuple(error_warnings), 0.0
            )
        else:
            results["ground_resolution"] = _pass("no ground resolution error detected")
    return results


def _looks_like_resolution_error(warning: str) -> bool:
    lowered = warning.lower()
    return any(token in lowered for token in ("error", "unresolved", "not found", "missing"))


def evaluate_turn_metrics(
    expected: ExpectedOutcome,
    trace: Mapping[str, Any],
    *,
    oracle_approved: bool,
) -> dict[str, MetricResult]:
    """Evaluate facts that can be decided without semantic model judgement."""
    results = {"trace": evaluate_trace_completeness(trace)}
    results["timings"] = _numeric_section(trace, "timings", REQUIRED_TIMING_FIELDS)
    results["tokens"] = _numeric_section(trace, "tokens", REQUIRED_TOKEN_FIELDS)

    if not oracle_approved:
        reason = "oracle is not approved for formal gates"
        for name in (
            "safety",
            "route",
            "route_preference",
            "ground_recall",
            "ground_precision",
        ):
            results[name] = _skip(reason)
        return results

    results["safety"] = _expected_value(
        expected.safety_levels, trace, "safety", ("level", "risk_level"), "safety"
    )
    results["route"] = _expected_value(
        expected.route_ids, trace, "route", ("id", "route_id"), "route"
    )
    results["route_preference"] = _preferred_route(
        expected.preferred_route_id, trace
    )
    # Ground citation oracles are retained only for legacy case-file parsing.
    # Citation quality is not judged from required/relevant ref lists.
    results["ground_recall"] = _skip("ground citation oracle is not evaluated")
    results["ground_precision"] = _skip("ground citation oracle is not evaluated")
    return results


def evaluate_trace_completeness(trace: Mapping[str, Any]) -> MetricResult:
    if not isinstance(trace, Mapping):
        return _error("trace must be an object")
    missing = REQUIRED_TRACE_SECTIONS - set(trace)
    if missing:
        return _error(f"missing trace sections: {', '.join(sorted(missing))}")
    return _pass("all required trace sections are present")


def evaluate_memory_checkpoint(
    checkpoint: MemoryCheckpoint, trace: Mapping[str, Any]
) -> MetricResult:
    from .memory_metrics import memory_observation

    observation = memory_observation(checkpoint, trace)
    if observation["status"] == "skip":
        return _skip(observation["reason"])
    if observation["status"] == "fail":
        return _fail(observation["reason"], checkpoint.facts, 0.0)
    return _pass(observation["reason"], checkpoint.facts)


def _expected_value(expected: tuple[str, ...], trace: Mapping[str, Any], section: str,
                    keys: tuple[str, ...], label: str) -> MetricResult:
    if not expected:
        return _skip(f"no reviewed expected {label}")
    actual = _trace_string(trace, section, keys)
    if actual is None and not isinstance(trace.get(section), Mapping):
        return _error(f"{section} trace is missing")
    if not isinstance(actual, str):
        return _error(f"{section} trace has no comparable value")
    if actual in expected:
        return _pass(f"actual {label} is accepted", (actual,))
    return _fail(f"actual {label} is not accepted", (f"actual={actual}", *expected), 0.0)


def _preferred_route(
    preferred_route_id: str | None, trace: Mapping[str, Any]
) -> MetricResult:
    if preferred_route_id is None:
        return _skip("no reviewed preferred route")
    actual = _trace_string(trace, "route", ("id", "route_id"))
    if actual is None and not isinstance(trace.get("route"), Mapping):
        return _error("route trace is missing")
    if not isinstance(actual, str):
        return _error("route trace has no comparable value")
    if actual == preferred_route_id:
        return _pass("actual route is preferred", (actual,))
    return _fail(
        "actual route is not the reviewed preferred route",
        (f"actual={actual}", f"preferred={preferred_route_id}"),
        0.0,
    )


def _trace_string(
    trace: Mapping[str, Any], section: str, keys: tuple[str, ...]
) -> str | None:
    value = trace.get(section)
    if not isinstance(value, Mapping):
        return None
    actual = next((value[key] for key in keys if key in value), None)
    return actual if isinstance(actual, str) else None


def _resolved_refs(trace: Mapping[str, Any]) -> tuple[str, ...] | None:
    ground = trace.get("ground")
    if not isinstance(ground, Mapping):
        return None
    refs = ground.get("resolved_refs")
    if not isinstance(refs, Sequence) or isinstance(refs, (str, bytes)):
        return None
    return tuple(str(ref) for ref in refs)


def _set_metric(oracle: tuple[str, ...], actual: tuple[str, ...] | None,
                label: str, *, precision: bool,
                counts: Mapping[str, int] | None = None) -> MetricResult:
    if not oracle:
        return _skip(f"no {label}")
    if actual is None:
        return _error("ground.resolved_refs must be an array")
    expected_set, actual_set = set(oracle), set(actual)
    confusion = retrieval_confusion(tuple(expected_set), tuple(actual_set))
    denominator = len(actual_set) if precision else len(expected_set)
    score = len(expected_set & actual_set) / denominator if denominator else 1.0
    status = MetricStatus.PASS if score == 1.0 else MetricStatus.FAIL
    return MetricResult(
        status, score, f"{label} score is {score:.3f}", tuple(actual),
        counts=counts or {"tp": confusion.tp, "fp": confusion.fp, "fn": confusion.fn},
    )


def _numeric_section(trace: Mapping[str, Any], section: str,
                     required: frozenset[str]) -> MetricResult:
    value = trace.get(section)
    if not isinstance(value, Mapping):
        return _error(f"{section} trace must be an object")
    if not value:
        return _skip(f"{section} telemetry was not reported by chatflow debug")
    missing = required - set(value)
    if missing:
        return _error(f"missing {section} fields: {', '.join(sorted(missing))}")
    if section == "timings":
        unavailable = [
            key
            for key in ("ttft_ms", "first_guarded_delta_ms")
            if value.get(key) is None
        ]
        if unavailable:
            remaining = {
                key: item
                for key, item in value.items()
                if key not in unavailable
                and not (key == "response_ttft_ms" and "ttft_ms" in unavailable)
            }
            invalid_remaining = [
                key
                for key, item in remaining.items()
                if isinstance(item, bool)
                or not isinstance(item, (int, float))
                or item < 0
            ]
            if invalid_remaining:
                return _error(
                    f"{section} values must be non-negative numbers",
                    tuple(invalid_remaining),
                )
            return _skip(
                "non-streaming chatflow response does not expose TTFT telemetry"
            )
    invalid = [key for key, item in value.items() if isinstance(item, bool) or not isinstance(item, (int, float)) or item < 0]
    if invalid:
        return _error(f"{section} values must be non-negative numbers", tuple(invalid))
    return _pass(f"{section} values are complete", tuple(str(k) for k in value))


def _pass(reason: str, evidence: tuple[str, ...] = ()) -> MetricResult:
    return MetricResult(MetricStatus.PASS, 1.0, reason, evidence)


def _fail(reason: str, evidence: tuple[str, ...], score: float) -> MetricResult:
    return MetricResult(MetricStatus.FAIL, score, reason, evidence)


def _error(reason: str, evidence: tuple[str, ...] = ()) -> MetricResult:
    return MetricResult(MetricStatus.ERROR, None, reason, evidence)


def _skip(reason: str) -> MetricResult:
    return MetricResult(MetricStatus.SKIP, None, reason)
