import pytest

from xiaoan_eval.content_experiment import (
    PairObservation, TreatmentProposal, canonical_digest, pair_observations,
)


def test_route_fields_require_natural_routing():
    before = ["old"]
    with pytest.raises(ValueError, match="NATURAL_ROUTE"):
        TreatmentProposal(
            proposal_id="p1", artifact_kind="CAPSULE", entity_id="N1",
            canonical_field_path="triggers", source_path="knowledge/capsules/N1.md",
            operation="replace", before_value=before, before_digest=canonical_digest(before),
            candidate_value=["new"], routing_mode="FIXED_ROUTE",
        )


def _observation(arm, **overrides):
    values = {
        "case_id": "TC-01", "turn": 1, "repeat_id": "r1", "arm": arm,
        "succeeded": True, "snapshot_digest": arm.lower(), "control_digest": "same",
        "case_digest": "case", "treatment_exposed": True,
        "treatment_applied": True, "provider_acceptance": "CONFIRMED",
        "hard_gate_passed": True, "metric_value": 2 if arm == "CONTROL" else 3,
    }
    values.update(overrides)
    return PairObservation(**values)


def test_pair_effect_requires_complete_exposed_matching_controls():
    result = pair_observations([_observation("CONTROL"), _observation("CANDIDATE")])[0]
    assert result.status == "ELIGIBLE"
    assert result.effect == 1


def test_unexposed_candidate_is_not_zero_effect():
    result = pair_observations([
        _observation("CONTROL"), _observation("CANDIDATE", treatment_exposed=False)
    ])[0]
    assert result.status == "INELIGIBLE"
    assert result.effect is None
    assert "NOT_EXPOSED" in result.reasons
