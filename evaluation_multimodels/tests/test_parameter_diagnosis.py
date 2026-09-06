import pytest

from xiaoan_eval.parameter_diagnosis import RecommendationFact, diagnose


def test_attribution_only_difference_is_observational():
    fact = diagnose(
        diagnosis_id="d1", subject_scope="TC-01", observed_outcomes=("capsule support low",),
        changed_factors=("capsule",), source_fact_ids=("a1",),
    )
    assert fact.evidence_state == "OBSERVATIONAL_HYPOTHESIS"
    assert fact.causal_experiment_id is None


def test_requested_but_unconfirmed_parameter_is_not_causal():
    fact = diagnose(
        diagnosis_id="d1", subject_scope="TC-01", observed_outcomes=("score changed",),
        changed_factors=("composer.temperature",), source_fact_ids=("p1",),
        experiment_id="e1", treatment_applied=True, confirmation_required=True,
        acceptance="UNVERIFIED", exposed=True, controls_match=True, complete_pairs=True,
    )
    assert fact.evidence_state == "INCONCLUSIVE"


def test_one_applied_confirmed_isolated_factor_can_be_causal():
    fact = diagnose(
        diagnosis_id="d1", subject_scope="TC-01", observed_outcomes=("score changed",),
        changed_factors=("composer.temperature",), source_fact_ids=("p1",),
        experiment_id="e1", treatment_applied=True, confirmation_required=True,
        acceptance="CONFIRMED", exposed=True, controls_match=True, complete_pairs=True,
    )
    assert fact.evidence_state == "CAUSAL_EVIDENCE"
    assert fact.causal_experiment_id == "e1"


def test_adoption_cannot_override_non_target_regression():
    with pytest.raises(ValueError, match="complete sealed decision rule"):
        RecommendationFact(
            recommendation_id="r1", experiment_id="e1", proposal_id="p1",
            estimand="delta", decision_rule_digest="rule", analysis_version="1",
            target_result="IMPROVED", non_target_result="REGRESSED",
            equivalence_result="NOT_TESTED", multiplicity_result="PASS",
            gate_result="PASS", eligible_pairs=4, attrited_pairs=0,
            acceptance="CONFIRMED", exposure="EXPOSED", source_fact_ids=("e1",),
            outcome="ADOPT_CANDIDATE",
        )
