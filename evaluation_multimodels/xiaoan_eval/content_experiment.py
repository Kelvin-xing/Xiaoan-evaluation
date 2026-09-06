"""Single-treatment proposal and paired eligibility contracts."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


ARTIFACT_KINDS = frozenset({"PROMPT", "CAPSULE", "WIKI", "PARAMETER"})
OPERATIONS = frozenset({"replace"})


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


@dataclass(frozen=True)
class TreatmentProposal:
    proposal_id: str
    artifact_kind: str
    entity_id: str
    canonical_field_path: str
    source_path: str
    operation: str
    before_value: Any
    before_digest: str
    candidate_value: Any
    routing_mode: str
    confirmation_required: bool = False

    def __post_init__(self) -> None:
        if self.artifact_kind not in ARTIFACT_KINDS:
            raise ValueError("unsupported experiment artifact kind")
        if self.operation not in OPERATIONS:
            raise ValueError("only exact replacement experiments are supported")
        if canonical_digest(self.before_value) != self.before_digest:
            raise ValueError("proposal before digest does not match before value")
        path = PurePosixPath(self.source_path)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError("proposal source path must be workspace-relative")
        allowed = {
            "PROMPT": ("knowledge/sops/",),
            "CAPSULE": ("knowledge/capsules/",),
            "WIKI": ("knowledge/wiki/nodes/",),
            "PARAMETER": ("parameter://",),
        }
        if not any(self.source_path.startswith(prefix) for prefix in allowed[self.artifact_kind]):
            raise ValueError("proposal source is outside the artifact allowlist")
        expected_mode = "NATURAL_ROUTE" if (
            self.artifact_kind == "CAPSULE"
            and self.canonical_field_path in {"triggers", "use_when", "do_not_use_when"}
        ) else "FIXED_ROUTE"
        if self.artifact_kind != "PARAMETER" and self.routing_mode != expected_mode:
            raise ValueError(f"treatment requires {expected_mode}")
        if self.before_value == self.candidate_value:
            raise ValueError("candidate must differ from control")

    @property
    def digest(self) -> str:
        return canonical_digest(asdict(self))


@dataclass(frozen=True)
class PairObservation:
    case_id: str
    turn: int
    repeat_id: str
    arm: str
    succeeded: bool
    snapshot_digest: str
    control_digest: str
    case_digest: str
    treatment_exposed: bool
    treatment_applied: bool
    provider_acceptance: str
    hard_gate_passed: bool
    metric_value: float | None


@dataclass(frozen=True)
class PairEligibility:
    case_id: str
    turn: int
    repeat_id: str
    status: str
    reasons: tuple[str, ...]
    effect: float | None


def pair_observations(observations: Sequence[PairObservation]) -> tuple[PairEligibility, ...]:
    grouped: dict[tuple[str, int, str], dict[str, PairObservation]] = {}
    for observation in observations:
        if observation.arm not in {"CONTROL", "CANDIDATE"}:
            raise ValueError("pair arm must be CONTROL or CANDIDATE")
        key = (observation.case_id, observation.turn, observation.repeat_id)
        if observation.arm in grouped.setdefault(key, {}):
            raise ValueError("duplicate paired arm observation")
        grouped[key][observation.arm] = observation
    results = []
    for (case_id, turn, repeat_id), arms in sorted(grouped.items()):
        reasons = []
        if set(arms) != {"CONTROL", "CANDIDATE"}:
            reasons.append("INCOMPLETE_PAIR")
        else:
            control, candidate = arms["CONTROL"], arms["CANDIDATE"]
            if not control.succeeded or not candidate.succeeded:
                reasons.append("ARM_FAILURE")
            if control.case_digest != candidate.case_digest or control.control_digest != candidate.control_digest:
                reasons.append("CONTROL_DRIFT")
            if not candidate.treatment_applied:
                reasons.append("NOT_APPLIED")
            if not candidate.treatment_exposed:
                reasons.append("NOT_EXPOSED")
            if candidate.provider_acceptance == "REJECTED":
                reasons.append("PROVIDER_REJECTED")
            if control.metric_value is None or candidate.metric_value is None:
                reasons.append("METRIC_UNAVAILABLE")
            if not control.hard_gate_passed or not candidate.hard_gate_passed:
                reasons.append("HARD_GATE_FAILURE")
        effect = None
        if not reasons:
            effect = arms["CANDIDATE"].metric_value - arms["CONTROL"].metric_value  # type: ignore[operator]
        results.append(PairEligibility(
            case_id=case_id, turn=turn, repeat_id=repeat_id,
            status="ELIGIBLE" if not reasons else "INELIGIBLE",
            reasons=tuple(reasons), effect=effect,
        ))
    return tuple(results)
