from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


SUITE_MATURITIES = frozenset(
    {"PROVISIONAL_DESCRIPTIVE", "REVIEWED", "APPROVED_AGGREGATE"}
)


def canonical_digest(value: Any) -> str:
    canonical = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


@dataclass(frozen=True)
class SuiteCaseBinding:
    case_id: str
    case_digest: str
    expected_turns: tuple[int, ...]
    scenario_id: str
    coverage_axes: Mapping[str, tuple[str, ...]]
    comparability_group: str
    maturity: str
    quality_focus: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not self.case_id or not self.case_digest:
            raise ValueError("suite case identity and digest are required")
        if self.expected_turns != tuple(range(1, len(self.expected_turns) + 1)):
            raise ValueError("expected_turns must be consecutive and start at 1")
        if self.maturity not in SUITE_MATURITIES:
            raise ValueError("unsupported suite case maturity")
        if not self.scenario_id or not self.comparability_group:
            raise ValueError("scenario and comparability group are required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SuiteManifest:
    suite_id: str
    suite_version: str
    taxonomy_version: str
    scoring_contract_version: str
    cases: tuple[SuiteCaseBinding, ...]
    retry_policy: Mapping[str, Any]
    rollup: Mapping[str, Any] | None = None

    def __post_init__(self) -> None:
        if not self.suite_id or not self.suite_version:
            raise ValueError("suite identity is required")
        if not self.taxonomy_version or not self.scoring_contract_version:
            raise ValueError("taxonomy and scoring versions are required")
        if not self.cases:
            raise ValueError("suite must bind at least one case")
        ids = [case.case_id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("suite case ids must be unique")
        maximum = self.retry_policy.get("max_attempts", 1)
        if isinstance(maximum, bool) or not isinstance(maximum, int) or maximum < 1:
            raise ValueError("retry_policy.max_attempts must be a positive integer")

    def to_dict(self) -> dict[str, Any]:
        return {
            "suite_id": self.suite_id,
            "suite_version": self.suite_version,
            "taxonomy_version": self.taxonomy_version,
            "scoring_contract_version": self.scoring_contract_version,
            "cases": [case.to_dict() for case in self.cases],
            "retry_policy": dict(self.retry_policy),
            "rollup": dict(self.rollup) if self.rollup is not None else None,
        }

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self.to_dict())

    @classmethod
    def from_cases(
        cls,
        *,
        suite_id: str,
        suite_version: str,
        taxonomy_version: str,
        scoring_contract_version: str,
        cases: Sequence[Any],
        case_digests: Mapping[str, str],
        retry_policy: Mapping[str, Any],
        rollup: Mapping[str, Any] | None = None,
    ) -> "SuiteManifest":
        bindings = tuple(
            SuiteCaseBinding(
                case_id=case.id,
                case_digest=case_digests[case.id],
                expected_turns=tuple(turn.turn for turn in case.turns),
                scenario_id=case.scenario_id,
                coverage_axes=case.coverage_axes,
                comparability_group=case.comparability_group,
                maturity=case.maturity,
                quality_focus=case.quality_focus,
            )
            for case in cases
        )
        return cls(
            suite_id=suite_id,
            suite_version=suite_version,
            taxonomy_version=taxonomy_version,
            scoring_contract_version=scoring_contract_version,
            cases=bindings,
            retry_policy=dict(retry_policy),
            rollup=rollup,
        )


@dataclass(frozen=True)
class RunManifest:
    run_started_at: str
    product_version: str
    safety_policy_version: str
    output_guard_version: str
    prompt_hashes: Mapping[str, str]
    knowledge_versions: Mapping[str, str]
    model_ids: Mapping[str, str]
    provider_versions: Mapping[str, str]
    hyperparameters: Mapping[str, Any]
    run_config: Mapping[str, Any]
    evaluator_version: str
    rating_rule_hash: str
    rating_rule_schema_version: str
    judge_prompt_version: str
    seed: int
    retry_policy: Mapping[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def fingerprint(self) -> str:
        return canonical_digest(self.to_dict())
