from xiaoan_eval.cases import ExpectedOutcome, MemoryCheckpoint
from xiaoan_eval.metrics import (
    evaluate_hard_gates,
    evaluate_memory_checkpoint,
    evaluate_turn_metrics,
    retrieval_confusion,
)
from xiaoan_eval.rules import MetricStatus
import pytest


def test_expected_trace_values_and_reviewed_ground_are_scored() -> None:
    expected = ExpectedOutcome(
        safety_levels=("high",), route_ids=("crisis",),
        preferred_route_id="crisis",
    )
    trace = {
        "safety": {"level": "high"}, "route": {"id": "crisis"},
        "ground": {"resolved_refs": ["sop-1", "extra"]},
        "timings": {"total_ms": 12, "ttft_ms": 3, "first_guarded_delta_ms": 4,
                    "router_ms": 1, "ground_ms": 2, "generation_ms": 8},
        "tokens": {"input": 4, "output": 5},
    }
    metrics = evaluate_turn_metrics(expected, trace, oracle_approved=True)
    assert metrics["safety"].status is MetricStatus.PASS
    assert metrics["route"].status is MetricStatus.PASS
    assert metrics["route_preference"].status is MetricStatus.PASS
    assert metrics["ground_recall"].status is MetricStatus.SKIP
    assert metrics["ground_precision"].status is MetricStatus.SKIP
    assert metrics["timings"].status is MetricStatus.PASS


def test_retrieval_confusion_reports_tn_only_for_explicit_universe() -> None:
    counts = retrieval_confusion(["a", "b"], ["b", "x"], universe=["a", "b", "x", "y"])
    assert (counts.tp, counts.fp, counts.fn, counts.tn) == (1, 1, 1, 1)
    assert counts.f1 == 0.5
    assert retrieval_confusion(["a"], ["x"]).tn is None


def test_retrieval_confusion_rejects_labels_outside_explicit_universe() -> None:
    with pytest.raises(ValueError, match="outside explicit universe"):
        retrieval_confusion(["a"], ["x"], universe=["a", "b"])


def test_unreviewed_or_absent_oracles_skip_instead_of_guessing() -> None:
    expected = ExpectedOutcome(
        safety_levels=("low",),
        route_ids=("baseline", "n3"),
        preferred_route_id="n3",
    )
    metrics = evaluate_turn_metrics(expected, {}, oracle_approved=False)
    assert metrics["safety"].status is MetricStatus.SKIP
    assert metrics["route"].status is MetricStatus.SKIP
    assert metrics["route_preference"].status is MetricStatus.SKIP
    assert metrics["ground_precision"].status is MetricStatus.SKIP
    assert metrics["trace"].status is MetricStatus.ERROR


def test_accepted_non_preferred_route_is_reported_separately() -> None:
    expected = ExpectedOutcome(
        route_ids=("baseline", "n3"),
        preferred_route_id="n3",
    )
    trace = {
        "safety": {},
        "route": {"id": "baseline"},
        "ground": {"resolved_refs": []},
        "guard": {},
        "state": {},
        "timings": {},
        "tokens": {},
    }

    metrics = evaluate_turn_metrics(expected, trace, oracle_approved=True)

    assert metrics["route"].status is MetricStatus.PASS
    assert metrics["route_preference"].status is MetricStatus.FAIL
    assert metrics["route_preference"].evidence == (
        "actual=baseline",
        "preferred=n3",
    )


def test_unavailable_debug_telemetry_is_skipped_instead_of_reported_as_performance_error() -> None:
    expected = ExpectedOutcome()
    trace = {
        "safety": {"level": "normal"},
        "route": {"id": "baseline"},
        "ground": {"resolved_refs": []},
        "guard": {"passed": True},
        "state": {},
        "timings": {
            "ttft_ms": None,
            "first_guarded_delta_ms": None,
            "router_ms": 2.0,
            "ground_ms": 0.0,
            "generation_ms": 10.0,
            "total_ms": 12.0,
        },
        "tokens": {},
    }

    metrics = evaluate_turn_metrics(expected, trace, oracle_approved=False)

    assert metrics["timings"].status is MetricStatus.SKIP
    assert "non-streaming" in metrics["timings"].reason
    assert metrics["tokens"].status is MetricStatus.SKIP
    assert "not reported" in metrics["tokens"].reason


def test_unavailable_ttft_aliases_do_not_create_timing_error() -> None:
    trace = {
        "timings": {
            "ttft_ms": None,
            "response_ttft_ms": None,
            "first_guarded_delta_ms": None,
            "router_ms": 1.0,
            "ground_ms": 0.0,
            "generation_ms": 2.0,
            "response_generation_ms": 2.0,
            "total_ms": 3.0,
        },
        "tokens": {},
    }
    metrics = evaluate_turn_metrics(ExpectedOutcome(), trace, oracle_approved=False)
    assert metrics["timings"].status is MetricStatus.SKIP


def test_missing_memory_telemetry_is_unavailable_not_schema_error() -> None:
    result = evaluate_memory_checkpoint(
        MemoryCheckpoint(1, ("fact",), "use fact"),
        {"state": {"active_capsule_id": "n1"}},
    )
    assert result.status is MetricStatus.SKIP


def test_memory_checkpoint_uses_structured_memory_evidence() -> None:
    checkpoint = MemoryCheckpoint(2, ("has-child",), "use when proposing a plan")
    result = evaluate_memory_checkpoint(
        checkpoint, {"state": {"memory_facts": ["has-child"], "memory_used": True}}
    )
    assert result.status is MetricStatus.PASS


def test_oracle_independent_hard_gates_fail_unknown_route_pii_and_resolution_error():
    metrics = evaluate_hard_gates(
        {
            "route": {"id": "invented"},
            "guard": {"passed": True},
            "ground": {"warnings": ["node not found"]},
        },
        response_is_pii_safe=False,
        known_route_ids=frozenset({"baseline", "crisis_sop"}),
    )

    assert metrics["pii_leakage"].status is MetricStatus.FAIL
    assert metrics["route_validity"].status is MetricStatus.FAIL
    assert metrics["ground_resolution"].status is MetricStatus.FAIL
