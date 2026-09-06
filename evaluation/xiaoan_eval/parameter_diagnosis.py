"""Evidence-bounded diagnosis and sealed recommendation decisions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence


DIAGNOSES = frozenset(
    {"OBSERVATIONAL_HYPOTHESIS", "CAUSAL_EVIDENCE", "MULTI_FACTOR", "INCONCLUSIVE"}
)
RECOMMENDATIONS = frozenset(
    {"ADOPT_CANDIDATE", "KEEP_CONTROL", "EQUIVALENT_NO_CHANGE", "NO_RECOMMENDATION"}
)


@dataclass(frozen=True)
class DiagnosisFact:
    diagnosis_id: str
    subject_scope: str
    observed_outcomes: tuple[str, ...]
    candidate_factors: tuple[str, ...]
    competing_factors: tuple[str, ...]
    evidence_state: str
    reason_codes: tuple[str, ...]
    source_fact_ids: tuple[str, ...]
    causal_experiment_id: str | None = None
    next_experiment: str | None = None

    def __post_init__(self) -> None:
        if self.evidence_state not in DIAGNOSES:
            raise ValueError("unsupported diagnosis state")
        if self.evidence_state == "CAUSAL_EVIDENCE" and not self.causal_experiment_id:
            raise ValueError("causal diagnosis requires causal_experiment_id")
        if self.evidence_state != "CAUSAL_EVIDENCE" and self.causal_experiment_id:
            raise ValueError("non-causal diagnosis cannot cite a causal experiment")


@dataclass(frozen=True)
class RecommendationFact:
    recommendation_id: str
    experiment_id: str
    proposal_id: str
    estimand: str
    decision_rule_digest: str
    analysis_version: str
    target_result: str
    non_target_result: str
    equivalence_result: str
    multiplicity_result: str
    gate_result: str
    eligible_pairs: int
    attrited_pairs: int
    acceptance: str
    exposure: str
    source_fact_ids: tuple[str, ...]
    outcome: str

    def __post_init__(self) -> None:
        if self.outcome not in RECOMMENDATIONS:
            raise ValueError("unsupported recommendation outcome")
        if self.outcome == "ADOPT_CANDIDATE" and (
            self.gate_result != "PASS"
            or self.target_result != "IMPROVED"
            or self.non_target_result != "NO_REGRESSION"
            or self.acceptance != "CONFIRMED"
            or self.exposure != "EXPOSED"
            or self.eligible_pairs < 1
        ):
            raise ValueError("adoption requires the complete sealed decision rule")


def diagnose(
    *,
    diagnosis_id: str,
    subject_scope: str,
    observed_outcomes: Sequence[str],
    changed_factors: Sequence[str],
    source_fact_ids: Sequence[str],
    experiment_id: str | None = None,
    treatment_applied: bool = False,
    confirmation_required: bool = False,
    acceptance: str = "UNVERIFIED",
    exposed: bool = False,
    controls_match: bool = False,
    complete_pairs: bool = False,
    effects_consistent: bool = True,
) -> DiagnosisFact:
    factors = tuple(changed_factors)
    causal_eligible = (
        len(factors) == 1
        and bool(experiment_id)
        and treatment_applied
        and (not confirmation_required or acceptance == "CONFIRMED")
        and exposed
        and controls_match
        and complete_pairs
        and effects_consistent
    )
    if causal_eligible:
        state, reasons = "CAUSAL_EVIDENCE", ("ISOLATED_ELIGIBLE_PAIR",)
    elif len(factors) > 1:
        state, reasons = "MULTI_FACTOR", ("MULTIPLE_MATERIAL_FACTORS",)
    elif experiment_id and not causal_eligible:
        state, reasons = "INCONCLUSIVE", ("CAUSAL_ELIGIBILITY_FAILED",)
    else:
        state, reasons = "OBSERVATIONAL_HYPOTHESIS", ("NO_ISOLATED_EXPERIMENT",)
    return DiagnosisFact(
        diagnosis_id=diagnosis_id,
        subject_scope=subject_scope,
        observed_outcomes=tuple(observed_outcomes),
        candidate_factors=factors,
        competing_factors=() if len(factors) <= 1 else factors[1:],
        evidence_state=state,
        reason_codes=reasons,
        source_fact_ids=tuple(source_fact_ids),
        causal_experiment_id=experiment_id if state == "CAUSAL_EVIDENCE" else None,
        next_experiment=None if state == "CAUSAL_EVIDENCE" else "isolate one bounded factor",
    )
