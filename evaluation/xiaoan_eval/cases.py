from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
import re
from typing import Any, Callable, Mapping, Sequence

import yaml

from .rules import RatingRule


SUPPORTED_SCHEMA_VERSION = "2.0"
_CASE_ID = re.compile(r"TC-\d+")
CASE_MATURITIES = frozenset(
    {"PROVISIONAL_DESCRIPTIVE", "REVIEWED", "APPROVED_AGGREGATE"}
)


class CaseValidationError(ValueError):
    """Raised when a case cannot safely be used as an evaluation manifest."""


@dataclass(frozen=True)
class ToolExpectation:
    name: str
    arguments: Mapping[str, Any]


@dataclass(frozen=True)
class ResponseOracle:
    required_claims: tuple[str, ...] = ()
    forbidden_claims: tuple[str, ...] = ()
    must_cite: tuple[str, ...] = ()
    should_abstain: bool | None = None
    max_chars: int | None = None
    expected_tools: tuple[ToolExpectation, ...] = ()
    goal_completed: bool | None = None
    max_steps: int | None = None
    reference_answer: str | None = None


@dataclass(frozen=True)
class ExpectedOutcome:
    safety_levels: tuple[str, ...] = ()
    route_ids: tuple[str, ...] = ()
    preferred_route_id: str | None = None
    must_include: tuple[str, ...] = ()
    forbidden_behaviors: tuple[str, ...] = ()
    # Optional evidence/answer oracles.  These are intentionally additive so
    # legacy v2 cases (which only declare route/safety expectations) continue
    # to load unchanged.
    source_refs: tuple[str, ...] = ()
    wiki_refs: tuple[str, ...] = ()
    capsule_ids: tuple[str, ...] = ()
    response_oracle: ResponseOracle | None = None


@dataclass(frozen=True)
class TestTurn:
    turn: int
    user: str
    expected: ExpectedOutcome | None = None


@dataclass(frozen=True)
class MemoryCheckpoint:
    after_turn: int
    facts: tuple[str, ...]
    usage: str
    check_type: str = "use"


@dataclass(frozen=True)
class OracleProvenance:
    source: str
    status: str
    reviewed_by: str | None = None
    reviewed_at: str | None = None
    legal_effective_date: str | None = None


@dataclass(frozen=True)
class TestCase:
    schema_version: str
    id: str
    test_objective: str
    quality_focus: tuple[str, ...]
    turns: tuple[TestTurn, ...]
    oracle_provenance: OracleProvenance
    category: str | None = None
    tags: Mapping[str, Any] = field(default_factory=dict)
    memory_checkpoints: tuple[MemoryCheckpoint, ...] = ()
    user_variable: str | None = None
    scenario_id: str = "unclassified"
    coverage_axes: Mapping[str, tuple[str, ...]] = field(default_factory=dict)
    comparability_group: str = "default"
    maturity: str = "PROVISIONAL_DESCRIPTIVE"

    @property
    def oracle_gate_eligible(self) -> bool:
        return self.oracle_provenance.status in {"reviewed", "approved"}

    @property
    def aggregate_eligible(self) -> bool:
        return self.maturity == "APPROVED_AGGREGATE"


@dataclass(frozen=True)
class PreflightIssue:
    issue_type: str
    field: str
    reason: str


@dataclass(frozen=True)
class CaseRemediation:
    issue_type: str
    original: Any
    reason: str
    evidence: str
    suggested_patch: Mapping[str, Any]
    affects_historical_baseline: bool
    confidence: str
    required_reviewer: str


@dataclass(frozen=True)
class CasePreflight:
    status: str
    issues: tuple[PreflightIssue, ...] = ()
    remediations: tuple[CaseRemediation, ...] = ()


@dataclass(frozen=True)
class CaseLoadResult:
    case_id: str
    source: Path
    case: TestCase | None
    preflight: CasePreflight


def load_case(
    path: str | Path,
    rating_rule: RatingRule,
    pii_validator: Callable[[Mapping[str, Any]], bool] | None = None,
) -> CaseLoadResult:
    """Load one versioned v2 evaluation case."""
    source = Path(path)
    raw = _read_yaml(source)
    if "schema_version" not in raw:
        raise CaseValidationError(
            "schema_version is required; migrate legacy v1 cases to schema v2"
        )
    case = _parse_v2(raw, source, rating_rule)
    issues = _preflight_issues(case, pii_validator=pii_validator)
    remediations = tuple(_remediation_for(issue, raw) for issue in issues)
    status = "needs_remediation" if issues else "ready"
    return CaseLoadResult(
        case_id=case.id,
        source=source,
        case=case,
        preflight=CasePreflight(status, issues, remediations),
    )


def load_cases(
    path: str | Path,
    rating_rule: RatingRule,
    pii_validator: Callable[[Mapping[str, Any]], bool] | None = None,
) -> tuple[CaseLoadResult, ...]:
    """Load all YAML cases, retaining an invalid preflight result per bad file."""
    root = Path(path)
    paths = sorted(root.glob("*.yaml")) if root.is_dir() else [root]
    results: list[CaseLoadResult] = []
    for source in paths:
        try:
            results.append(load_case(source, rating_rule, pii_validator))
        except CaseValidationError as exc:
            issue = PreflightIssue("schema_validation", "$", str(exc))
            remediation = CaseRemediation(
                issue_type="schema_validation",
                original=None,
                reason=str(exc),
                evidence=str(source),
                suggested_patch={},
                affects_historical_baseline=True,
                confidence="high",
                required_reviewer="test_case_owner",
            )
            results.append(
                CaseLoadResult(
                    case_id=_case_id_from_path(source),
                    source=source,
                    case=None,
                    preflight=CasePreflight("invalid", (issue,), (remediation,)),
                )
            )
    return tuple(results)


def _read_yaml(source: Path) -> Mapping[str, Any]:
    try:
        value = yaml.safe_load(source.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise CaseValidationError(f"cannot parse YAML: {exc}") from exc
    if not isinstance(value, Mapping):
        raise CaseValidationError("case root must be a mapping")
    return value


def _parse_v2(
    raw: Mapping[str, Any], source: Path, rating_rule: RatingRule
) -> TestCase:
    version = _required_string(raw, "schema_version")
    if version != SUPPORTED_SCHEMA_VERSION:
        raise CaseValidationError(f"unsupported schema_version: {version!r}")

    case_id = _required_string(raw, "id")
    if not _CASE_ID.fullmatch(case_id):
        raise CaseValidationError("id must use the TC-<number> form")
    if source.stem != case_id:
        raise CaseValidationError(
            f"case id {case_id!r} does not match filename {source.name!r}"
        )

    objective = _required_string(raw, "test_objective")
    focus = _string_tuple(raw.get("quality_focus"), "quality_focus", allow_empty=False)
    unknown_focus = set(focus) - {module.name for module in rating_rule.modules}
    if unknown_focus:
        raise CaseValidationError(
            f"quality_focus contains unknown modules: {sorted(unknown_focus)!r}"
        )

    turns_raw = _mapping_sequence(raw.get("turns"), "turns")
    turns = tuple(_parse_turn(item) for item in turns_raw)
    if [item.turn for item in turns] != list(range(1, len(turns) + 1)):
        raise CaseValidationError("turn numbers must be consecutive and start at 1")

    provenance_raw = _required_mapping(raw, "oracle_provenance")
    provenance = OracleProvenance(
        source=_required_string(provenance_raw, "source", "oracle_provenance"),
        status=_required_string(provenance_raw, "status", "oracle_provenance"),
        reviewed_by=_optional_string(provenance_raw.get("reviewed_by")),
        reviewed_at=_optional_string(provenance_raw.get("reviewed_at")),
        legal_effective_date=_optional_string(provenance_raw.get("legal_effective_date")),
    )
    if provenance.status not in {"provisional", "reviewed", "approved"}:
        raise CaseValidationError("oracle_provenance.status must be provisional, reviewed, or approved")
    if provenance.status in {"reviewed", "approved"} and (
        provenance.reviewed_by is None or provenance.reviewed_at is None
    ):
        raise CaseValidationError(
            "reviewed/approved oracle_provenance requires reviewed_by and reviewed_at"
        )

    # Legacy approval means the oracle was reviewed.  Aggregate inclusion is a
    # separate suite-owner decision and is therefore never inferred here.
    maturity = raw.get("maturity")
    if maturity is None:
        maturity = "REVIEWED" if provenance.status in {"reviewed", "approved"} else "PROVISIONAL_DESCRIPTIVE"
    if maturity not in CASE_MATURITIES:
        raise CaseValidationError(
            "maturity must be PROVISIONAL_DESCRIPTIVE, REVIEWED, or APPROVED_AGGREGATE"
        )
    if maturity == "APPROVED_AGGREGATE" and provenance.status not in {"reviewed", "approved"}:
        raise CaseValidationError("APPROVED_AGGREGATE requires a reviewed oracle")

    scenario_id = _optional_string(raw.get("scenario_id")) or "unclassified"
    comparability_group = _optional_string(raw.get("comparability_group")) or "default"
    coverage_axes = _parse_coverage_axes(raw.get("coverage_axes", {}))

    checkpoints_raw = raw.get("memory_checkpoints", [])
    checkpoints = tuple(
        _parse_checkpoint(item)
        for item in _mapping_sequence(checkpoints_raw, "memory_checkpoints", allow_empty=True)
    )
    if any(item.after_turn > len(turns) for item in checkpoints):
        raise CaseValidationError("memory checkpoint references a missing turn")

    tags = raw.get("tags", {})
    if not isinstance(tags, Mapping):
        raise CaseValidationError("tags must be a mapping")
    return TestCase(
        schema_version=version,
        id=case_id,
        category=_optional_string(raw.get("category")),
        tags=dict(tags),
        user_variable=_optional_string(raw.get("user_variable")),
        test_objective=objective,
        quality_focus=focus,
        turns=turns,
        memory_checkpoints=checkpoints,
        oracle_provenance=provenance,
        scenario_id=scenario_id,
        coverage_axes=coverage_axes,
        comparability_group=comparability_group,
        maturity=maturity,
    )


def _parse_coverage_axes(value: Any) -> Mapping[str, tuple[str, ...]]:
    if not isinstance(value, Mapping):
        raise CaseValidationError("coverage_axes must be a mapping")
    parsed: dict[str, tuple[str, ...]] = {}
    for key, raw in value.items():
        if not isinstance(key, str) or not key.strip():
            raise CaseValidationError("coverage_axes keys must be non-empty strings")
        if isinstance(raw, str):
            values = (raw.strip(),) if raw.strip() else ()
        elif isinstance(raw, Sequence) and not isinstance(raw, (str, bytes)):
            values = tuple(
                item.strip() for item in raw if isinstance(item, str) and item.strip()
            )
            if len(values) != len(raw):
                raise CaseValidationError("coverage_axes values must be non-empty strings")
        else:
            raise CaseValidationError("coverage_axes values must be strings or string lists")
        if not values:
            raise CaseValidationError("coverage_axes values cannot be empty")
        parsed[key.strip()] = values
    return parsed


def _parse_turn(raw: Mapping[str, Any]) -> TestTurn:
    number = raw.get("turn")
    if not isinstance(number, int) or isinstance(number, bool):
        raise CaseValidationError("each turn.turn must be an integer")
    user = _required_string(raw, "user", f"turn {number}")
    expected_raw = raw.get("expected")
    expected = None
    if expected_raw is not None:
        if not isinstance(expected_raw, Mapping):
            raise CaseValidationError(f"turn {number}.expected must be a mapping")
        route_ids = _string_tuple(expected_raw.get("route_ids", []), "route_ids")
        preferred_route_id = _optional_string(expected_raw.get("preferred_route_id"))
        if preferred_route_id is not None and preferred_route_id not in route_ids:
            raise CaseValidationError(
                f"turn {number}.expected.preferred_route_id must be included in route_ids"
            )
        expected = ExpectedOutcome(
            safety_levels=_string_tuple(expected_raw.get("safety_levels", []), "safety_levels"),
            route_ids=route_ids,
            preferred_route_id=preferred_route_id,
            must_include=_string_tuple(expected_raw.get("must_include", []), "must_include"),
            forbidden_behaviors=_string_tuple(
                expected_raw.get("forbidden_behaviors", []), "forbidden_behaviors"
            ),
            source_refs=_optional_string_tuple(
                expected_raw,
                "source_refs",
                aliases=("sources", "expected_source_refs", "source_oracle"),
            ),
            wiki_refs=_optional_string_tuple(
                expected_raw,
                "wiki_refs",
                aliases=("wiki", "expected_wiki_refs", "wiki_oracle"),
            ),
            capsule_ids=_optional_string_tuple(
                expected_raw,
                "capsule_ids",
                aliases=("capsules", "allowed_capsule_ids", "capsule_oracle"),
            ),
            response_oracle=_parse_response_oracle(expected_raw),
        )
    return TestTurn(number, user, expected)


def _parse_checkpoint(raw: Mapping[str, Any]) -> MemoryCheckpoint:
    after_turn = raw.get("after_turn")
    if not isinstance(after_turn, int) or isinstance(after_turn, bool) or after_turn < 1:
        raise CaseValidationError("memory_checkpoints.after_turn must be a positive integer")
    check_type = raw.get("type", "use")
    allowed_types = {"remember", "retrieve", "use", "not_use", "update", "isolation", "stale", "unsafe"}
    if check_type not in allowed_types:
        raise CaseValidationError(f"memory_checkpoints.type must be one of {sorted(allowed_types)}")
    return MemoryCheckpoint(
        after_turn=after_turn,
        facts=_string_tuple(raw.get("facts"), "memory_checkpoints.facts", allow_empty=False),
        usage=_required_string(raw, "usage", "memory_checkpoint"),
        check_type=str(check_type),
    )


def _preflight_issues(
    case: TestCase,
    *,
    pii_validator: Callable[[Mapping[str, Any]], bool] | None,
) -> tuple[PreflightIssue, ...]:
    issues: list[PreflightIssue] = []
    missing = [str(turn.turn) for turn in case.turns if turn.expected is None]
    if missing:
        issues.append(
            PreflightIssue(
                "missing_turn_oracle",
                "turns.expected",
                f"turns {', '.join(missing)} have no reviewed safety/route/ground oracle",
            )
        )
    if case.oracle_provenance.status == "provisional":
        issues.append(
            PreflightIssue(
                "provisional_oracle",
                "oracle_provenance.status",
                "provisional oracle cannot be used as a formal hard gate",
            )
        )
    if "法律维权" in case.quality_focus and case.oracle_provenance.legal_effective_date is None:
        issues.append(
            PreflightIssue(
                "missing_legal_effective_date",
                "oracle_provenance.legal_effective_date",
                "legal expectations require an authoritative source effective date",
            )
        )
    adversarial = case.category == "adversarial" or case.tags.get("adversarial") is True
    if adversarial and not case.tags.get("rl_ids"):
        issues.append(
            PreflightIssue(
                "missing_red_line_linkage",
                "tags.rl_ids",
                "adversarial cases must identify the red-line rule they exercise",
            )
        )
    if pii_validator is not None and not pii_validator({"case": asdict(case)}):
        issues.append(
            PreflightIssue(
                "case_pii_detected",
                "turns.user",
                "case content failed approved PII validation",
            )
        )
    return tuple(issues)


def _remediation_for(issue: PreflightIssue, raw: Mapping[str, Any]) -> CaseRemediation:
    patches: dict[str, Mapping[str, Any]] = {
        "missing_turn_oracle": {"op": "add", "path": "/turns/*/expected", "value": {}},
        "provisional_oracle": {
            "op": "replace", "path": "/oracle_provenance/status", "value": "approved"
        },
        "missing_legal_effective_date": {"op": "add", "path": "/oracle_provenance/legal_effective_date", "value": "YYYY-MM-DD"},
        "missing_red_line_linkage": {"op": "add", "path": "/tags/rl_ids", "value": []},
        "case_pii_detected": {"op": "replace", "path": "/turns/*/user", "value": "synthetic non-identifying text"},
    }
    return CaseRemediation(
        issue_type=issue.issue_type,
        original=raw.get(issue.field),
        reason=issue.reason,
        evidence=issue.field,
        suggested_patch=patches[issue.issue_type],
        affects_historical_baseline=True,
        confidence="medium",
        required_reviewer="domain_reviewer",
    )


def _required_mapping(raw: Mapping[str, Any], field_name: str) -> Mapping[str, Any]:
    value = raw.get(field_name)
    if not isinstance(value, Mapping):
        raise CaseValidationError(f"{field_name} must be a mapping")
    return value


def _mapping_sequence(
    value: Any, field_name: str, *, allow_empty: bool = False
) -> Sequence[Mapping[str, Any]]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise CaseValidationError(f"{field_name} must be a non-empty list")
    if not all(isinstance(item, Mapping) for item in value):
        raise CaseValidationError(f"every {field_name} item must be a mapping")
    return value


def _string_tuple(value: Any, field_name: str, *, allow_empty: bool = True) -> tuple[str, ...]:
    if not isinstance(value, list) or (not value and not allow_empty):
        raise CaseValidationError(f"{field_name} must be a list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise CaseValidationError(f"{field_name} must be a list of non-empty strings")
    return tuple(item.strip() for item in value)


def _optional_string_tuple(
    raw: Mapping[str, Any], name: str, *, aliases: tuple[str, ...] = ()
) -> tuple[str, ...]:
    """Read an optional list oracle, accepting established importer aliases."""
    present = [key for key in (name, *aliases) if key in raw]
    if len(present) > 1:
        raise CaseValidationError(
            f"{name} has conflicting aliases: {present!r}"
        )
    value = raw[present[0]] if present else None
    if value is None:
        return ()
    return _string_tuple(value, name)


def _parse_response_oracle(raw: Mapping[str, Any]) -> ResponseOracle | None:
    present = [key for key in ("response_oracle", "response") if key in raw]
    if len(present) > 1:
        raise CaseValidationError("response_oracle and response cannot both be present")
    value = raw[present[0]] if present else None
    if value is None:
        return None
    if isinstance(value, str):
        if not value.strip():
            raise CaseValidationError("response_oracle must not be empty")
        return ResponseOracle(reference_answer=value.strip())
    if not isinstance(value, Mapping):
        raise CaseValidationError("response_oracle must be a string or mapping")
    allowed = {
        "required_claims", "forbidden_claims", "must_cite", "should_abstain",
        "max_chars", "expected_tools", "goal_completed", "max_steps",
        "reference_answer",
    }
    unknown = set(value) - allowed
    if unknown:
        raise CaseValidationError(
            f"response_oracle contains unknown fields: {sorted(unknown)!r}"
        )
    should_abstain = _optional_bool(value, "should_abstain")
    goal_completed = _optional_bool(value, "goal_completed")
    max_chars = _optional_positive_int(value, "max_chars")
    max_steps = _optional_positive_int(value, "max_steps")
    reference_answer = value.get("reference_answer")
    if reference_answer is not None and (
        not isinstance(reference_answer, str) or not reference_answer.strip()
    ):
        raise CaseValidationError("response_oracle.reference_answer must be non-empty string")
    return ResponseOracle(
        required_claims=_string_tuple(
            value.get("required_claims", []), "response_oracle.required_claims"
        ),
        forbidden_claims=_string_tuple(
            value.get("forbidden_claims", []), "response_oracle.forbidden_claims"
        ),
        must_cite=_string_tuple(
            value.get("must_cite", []), "response_oracle.must_cite"
        ),
        should_abstain=should_abstain,
        max_chars=max_chars,
        expected_tools=_parse_tool_expectations(value.get("expected_tools", [])),
        goal_completed=goal_completed,
        max_steps=max_steps,
        reference_answer=reference_answer.strip() if isinstance(reference_answer, str) else None,
    )


def _parse_tool_expectations(value: Any) -> tuple[ToolExpectation, ...]:
    if not isinstance(value, list):
        raise CaseValidationError("response_oracle.expected_tools must be an array")
    tools: list[ToolExpectation] = []
    for index, item in enumerate(value):
        if not isinstance(item, Mapping) or set(item) - {"name", "arguments"}:
            raise CaseValidationError(
                f"response_oracle.expected_tools[{index}] must contain name and optional arguments"
            )
        name = item.get("name")
        arguments = item.get("arguments", {})
        if not isinstance(name, str) or not name.strip():
            raise CaseValidationError(
                f"response_oracle.expected_tools[{index}].name must be non-empty string"
            )
        if not isinstance(arguments, Mapping):
            raise CaseValidationError(
                f"response_oracle.expected_tools[{index}].arguments must be an object"
            )
        tools.append(ToolExpectation(name.strip(), dict(arguments)))
    return tuple(tools)


def _optional_bool(value: Mapping[str, Any], name: str) -> bool | None:
    item = value.get(name)
    if item is not None and not isinstance(item, bool):
        raise CaseValidationError(f"response_oracle.{name} must be boolean")
    return item


def _optional_positive_int(value: Mapping[str, Any], name: str) -> int | None:
    item = value.get(name)
    if item is not None and (
        isinstance(item, bool) or not isinstance(item, int) or item < 1
    ):
        raise CaseValidationError(f"response_oracle.{name} must be a positive integer")
    return item


def _required_string(
    raw: Mapping[str, Any], field_name: str, context: str = "case"
) -> str:
    value = raw.get(field_name)
    if not isinstance(value, str) or not value.strip():
        raise CaseValidationError(f"{context}.{field_name} must be a non-empty string")
    return value.strip()


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str) and value.strip():
        return value.strip()
    # PyYAML parses unquoted ISO dates as date objects; preserve their stable text form.
    if value.__class__.__module__ == "datetime":
        return str(value)
    raise CaseValidationError("optional metadata values must be strings or null")


def _case_id_from_path(source: Path) -> str:
    return source.stem if _CASE_ID.fullmatch(source.stem) else source.name
