"""Evaluation-owned validation for boundary-resolved parameter facts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping


BOUNDARIES = frozenset(
    {"ROUTER", "COMPOSER", "GROUND_RUNTIME", "EVALUATOR", "ATTRIBUTION_JUDGE", "QUALITY_JUDGE"}
)
SOURCES = frozenset(
    {"DEFAULT", "RUN_CONFIG", "CLI", "EXPERIMENT_OVERRIDE", "PROVIDER_DEFAULT", "DERIVED_RUNTIME"}
)
ACCEPTANCE = frozenset({"CONFIRMED", "REJECTED", "UNVERIFIED", "NOT_APPLICABLE"})
PRODUCT_BOUNDARIES = frozenset({"ROUTER", "COMPOSER", "GROUND_RUNTIME"})


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class ParameterResolutionFact:
    fact_id: str
    case_id: str
    turn: int
    invocation_id: str
    boundary: str
    parameter_id: str
    canonical_name: str
    value: Any
    value_type: str
    source: str
    precedence: int
    scope: str
    request_state: str
    application_state: str
    acceptance: str
    acceptance_evidence_ref: str | None
    snapshot_invocation_ref: str | None
    treatment: bool = False

    def __post_init__(self) -> None:
        if self.boundary not in BOUNDARIES:
            raise ValueError("unsupported parameter boundary")
        if self.source not in SOURCES:
            raise ValueError("unsupported parameter source")
        if self.acceptance not in ACCEPTANCE:
            raise ValueError("unsupported provider acceptance state")
        if self.acceptance in {"CONFIRMED", "REJECTED"} and not self.acceptance_evidence_ref:
            raise ValueError("confirmed/rejected acceptance requires boundary evidence")
        if self.acceptance == "NOT_APPLICABLE" and self.boundary in {"ROUTER", "COMPOSER"} and self.request_state == "REQUESTED":
            raise ValueError("requested provider parameters cannot be NOT_APPLICABLE")
        if self.value == "UNRESOLVED_PROVIDER_DEFAULT" and self.source != "PROVIDER_DEFAULT":
            raise ValueError("unresolved provider default must use PROVIDER_DEFAULT source")

    @property
    def record_digest(self) -> str:
        return _digest(asdict(self))


def control_digest(
    facts: list[ParameterResolutionFact], *, product_generation: bool
) -> str:
    selected = [
        fact
        for fact in facts
        if (fact.boundary in PRODUCT_BOUNDARIES) is product_generation
    ]
    payload = [
        {
            "boundary": fact.boundary,
            "parameter_id": fact.parameter_id,
            "name": fact.canonical_name,
            "value": fact.value,
            "type": fact.value_type,
            "source": fact.source,
            "scope": fact.scope,
            "application_state": fact.application_state,
            "acceptance": fact.acceptance,
        }
        for fact in sorted(selected, key=lambda item: (item.boundary, item.parameter_id))
    ]
    return _digest(payload)


def parse_parameter_fact(raw: Mapping[str, Any]) -> ParameterResolutionFact:
    return ParameterResolutionFact(**dict(raw))
