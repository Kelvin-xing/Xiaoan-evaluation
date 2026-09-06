import pytest

from xiaoan_eval.parameter_contract import ParameterResolutionFact, control_digest


def _fact(boundary="COMPOSER", **overrides):
    values = {
        "fact_id": "p1", "case_id": "TC-01", "turn": 1,
        "invocation_id": "i1", "boundary": boundary, "parameter_id": "temperature",
        "canonical_name": "temperature", "value": 0.2, "value_type": "number",
        "source": "RUN_CONFIG", "precedence": 10, "scope": "invocation",
        "request_state": "REQUESTED", "application_state": "SENT",
        "acceptance": "UNVERIFIED", "acceptance_evidence_ref": None,
        "snapshot_invocation_ref": "snapshot:1:composer", "treatment": False,
    }
    values.update(overrides)
    return ParameterResolutionFact(**values)


def test_evaluation_controls_never_enter_generation_digest():
    product = _fact()
    judge = _fact(boundary="ATTRIBUTION_JUDGE", fact_id="j1", invocation_id="j1")

    assert control_digest([product], product_generation=True) == control_digest(
        [product, judge], product_generation=True
    )
    assert control_digest([judge], product_generation=False) != control_digest(
        [], product_generation=False
    )


def test_confirmed_acceptance_requires_boundary_evidence():
    with pytest.raises(ValueError, match="requires boundary evidence"):
        _fact(acceptance="CONFIRMED")
