import pytest

from xiaoan_eval.diagnosis import DiagnosisError, attribute_failure


@pytest.mark.parametrize(
    ("trace", "stage", "lever_type", "target"),
    [
        (
            {"safety": {"correct": False}},
            "safety",
            "prompt",
            "safety rules/prompt/process",
        ),
        (
            {"safety": {"correct": True}, "route": {"correct": False}},
            "router",
            "prompt",
            "router prompt/model/context turns",
        ),
        (
            {
                "safety": {"correct": True},
                "route": {"correct": True},
                "ground": {"loaded": False, "refs_complete": False},
            },
            "ground",
            "process",
            "load policy/capsule-node mapping/knowledge",
        ),
        (
            {
                "safety": {"correct": True},
                "route": {"correct": True},
                "ground": {"loaded": True, "refs_complete": True},
                "answer": {"faithful": False},
            },
            "composer",
            "prompt",
            "composer prompt/model/verbosity",
        ),
        (
            {"memory": {"fact_available": True, "used_correctly": False}},
            "memory",
            "hyperparameter",
            "context turns/state/continuation process",
        ),
        (
            {"output_guard": {"unsafe_input": True, "blocked": False}},
            "output_guard",
            "process",
            "output guard rules/process",
        ),
        (
            {"test_case": {"oracle_determinable": False}},
            "test_case",
            "test_case",
            "test case remediation",
        ),
    ],
)
def test_attribute_failure_maps_trace_pattern_to_primary_stage_and_candidate_lever(
    trace: dict, stage: str, lever_type: str, target: str
) -> None:
    attribution = attribute_failure(trace)

    assert attribution.primary_stage == stage
    assert attribution.candidate_lever.type == lever_type
    assert attribution.candidate_lever.target == target
    assert attribution.status == "hypothesis"


def test_attribute_failure_prioritizes_invalid_test_oracle_over_product_changes() -> None:
    attribution = attribute_failure(
        {
            "test_case": {"oracle_determinable": False},
            "safety": {"correct": False},
        }
    )

    assert attribution.primary_stage == "test_case"
    assert attribution.secondary_stages == ("safety",)


def test_attribute_failure_rejects_trace_without_a_registered_failure_pattern() -> None:
    with pytest.raises(DiagnosisError, match="registered failure pattern"):
        attribute_failure({"route": {"correct": True}})
