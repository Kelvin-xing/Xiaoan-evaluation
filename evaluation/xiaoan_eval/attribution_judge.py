"""Strict structured-output boundary for the dedicated attribution judge."""

from __future__ import annotations

from dataclasses import dataclass
import json
from typing import Any, Mapping, Sequence


ATTRIBUTION_CONTRACT_VERSION = "attribution/v1"
CLAIM_KINDS = frozenset(
    {"FACTUAL", "INTERPRETIVE", "RECOMMENDATION", "ACTION", "SUPPORTIVE"}
)
RELATIONS = frozenset(
    {"ENTAILS", "PARTIAL", "CONTEXT_ONLY", "CONTRADICTS", "UNSUPPORTED"}
)
UNCERTAINTY_LEVELS = frozenset({"LOW", "MEDIUM", "HIGH"})
UNSUPPORTED_CATEGORIES = frozenset(
    {"UNVERIFIABLE_UNSUPPORTED", "PERMITTED_INFERENCE", "NON_FACTUAL_SUPPORTIVE"}
)
APPLICABILITY = frozenset({"APPLICABLE", "NOT_APPLICABLE", "UNCERTAIN"})
COMPLIANCE = frozenset(
    {"COMPLIANT", "PARTIAL", "NON_COMPLIANT", "NOT_APPLICABLE", "UNCERTAIN"}
)


class AttributionValidationError(ValueError):
    """Raised when untrusted attribution output is not locally authentic."""


@dataclass(frozen=True)
class TextSpan:
    start: int
    end: int
    text: str


@dataclass(frozen=True)
class SupportRelation:
    relation: str
    evidence_ref: str | None
    evidence_span: TextSpan | None
    layer: str | None
    occurrence_id: str | None


@dataclass(frozen=True)
class ClaimAttribution:
    claim_id: str
    kind: str
    answer_span: TextSpan
    relations: tuple[SupportRelation, ...]
    unsupported_category: str | None
    uncertainty: str


@dataclass(frozen=True)
class PolicyAttribution:
    policy_id: str
    evidence_ref: str
    applicability: str
    compliance: str
    answer_spans: tuple[TextSpan, ...]
    uncertainty: str


@dataclass(frozen=True)
class AttributionResult:
    contract_version: str
    claims: tuple[ClaimAttribution, ...]
    policies: tuple[PolicyAttribution, ...]
    abstention_status: str
    abstention_reason: str | None
    judge_version: str | None = None


def parse_attribution_response(
    raw_json: str,
    assistant_answer: str,
    evidence_catalog: Sequence[Mapping[str, Any]],
    *,
    judge_version: str | None = None,
) -> AttributionResult:
    if not isinstance(raw_json, str):
        raise AttributionValidationError("attribution response must be a JSON string")
    try:
        payload = json.loads(raw_json)
    except (json.JSONDecodeError, TypeError) as exc:
        raise AttributionValidationError("attribution response must be valid JSON") from exc
    root = _mapping(payload, "attribution response")
    if root.get("contract_version") != ATTRIBUTION_CONTRACT_VERSION:
        raise AttributionValidationError(
            f"contract_version must be {ATTRIBUTION_CONTRACT_VERSION}"
        )
    catalog = _catalog_index(evidence_catalog)
    claims_raw = _array(root.get("claims"), "claims")
    claims = tuple(
        _claim(item, index, assistant_answer, catalog)
        for index, item in enumerate(claims_raw)
    )
    claim_ids = [claim.claim_id for claim in claims]
    if len(set(claim_ids)) != len(claim_ids):
        raise AttributionValidationError("claims must have unique claim_id values")
    policies_raw = _array(root.get("policies"), "policies")
    policies = tuple(
        _policy(item, index, assistant_answer, catalog)
        for index, item in enumerate(policies_raw)
    )
    policy_keys = [(item.policy_id, item.evidence_ref) for item in policies]
    if len(set(policy_keys)) != len(policy_keys):
        raise AttributionValidationError("policies must be unique per policy occurrence")
    abstention = _mapping(root.get("abstention"), "abstention")
    status = abstention.get("status")
    if status not in {"ANSWERED", "ABSTAINED"}:
        raise AttributionValidationError("abstention.status must be ANSWERED or ABSTAINED")
    reason = abstention.get("reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise AttributionValidationError("abstention.reason must be null or non-empty text")
    if status == "ABSTAINED" and claims:
        raise AttributionValidationError("ABSTAINED responses cannot contain claims")
    return AttributionResult(
        contract_version=ATTRIBUTION_CONTRACT_VERSION,
        claims=claims,
        policies=policies,
        abstention_status=status,
        abstention_reason=reason,
        judge_version=judge_version,
    )


def _claim(
    value: Any,
    index: int,
    answer: str,
    catalog: Mapping[str, Mapping[str, Any]],
) -> ClaimAttribution:
    location = f"claims[{index}]"
    item = _mapping(value, location)
    claim_id = _text(item.get("claim_id"), f"{location}.claim_id")
    kind = item.get("kind")
    if kind not in CLAIM_KINDS:
        raise AttributionValidationError(f"{location}.kind is invalid")
    answer_span = _span(item.get("answer_span"), answer, f"{location}.answer_span")
    relations_raw = _array(item.get("relations"), f"{location}.relations")
    if not relations_raw:
        raise AttributionValidationError(f"{location}.relations must not be empty")
    relations = tuple(
        _relation(relation, relation_index, location, catalog)
        for relation_index, relation in enumerate(relations_raw)
    )
    relation_names = {relation.relation for relation in relations}
    unsupported_category = item.get("unsupported_category")
    if "UNSUPPORTED" in relation_names:
        if len(relations) != 1:
            raise AttributionValidationError(
                f"{location} UNSUPPORTED cannot be combined with other relations"
            )
        if unsupported_category not in UNSUPPORTED_CATEGORIES:
            raise AttributionValidationError(
                f"{location}.unsupported_category is required for UNSUPPORTED"
            )
    elif unsupported_category is not None:
        raise AttributionValidationError(
            f"{location}.unsupported_category is only valid for UNSUPPORTED"
        )
    if "CONTRADICTS" in relation_names and relation_names & {"ENTAILS", "PARTIAL"}:
        raise AttributionValidationError(
            f"{location} cannot combine CONTRADICTS with support relations"
        )
    uncertainty = item.get("uncertainty")
    if uncertainty not in UNCERTAINTY_LEVELS:
        raise AttributionValidationError(f"{location}.uncertainty is invalid")
    return ClaimAttribution(
        claim_id=claim_id,
        kind=kind,
        answer_span=answer_span,
        relations=relations,
        unsupported_category=unsupported_category,
        uncertainty=uncertainty,
    )


def _relation(
    value: Any,
    index: int,
    claim_location: str,
    catalog: Mapping[str, Mapping[str, Any]],
) -> SupportRelation:
    location = f"{claim_location}.relations[{index}]"
    item = _mapping(value, location)
    relation = item.get("relation")
    if relation not in RELATIONS:
        raise AttributionValidationError(f"{location}.relation is invalid")
    evidence_ref = item.get("evidence_ref")
    evidence_span_raw = item.get("evidence_span")
    if relation == "UNSUPPORTED":
        if evidence_ref is not None or evidence_span_raw is not None:
            raise AttributionValidationError(
                f"{claim_location} UNSUPPORTED requires no evidence"
            )
        return SupportRelation(relation, None, None, None, None)
    if not isinstance(evidence_ref, str) or evidence_ref not in catalog:
        raise AttributionValidationError(f"{location} has unknown evidence_ref")
    evidence = catalog[evidence_ref]
    content = evidence.get("content")
    if not isinstance(content, str):
        raise AttributionValidationError(
            f"catalog entry {evidence_ref} has no captured string content"
        )
    evidence_span = _span(evidence_span_raw, content, f"{location}.evidence_span")
    return SupportRelation(
        relation=relation,
        evidence_ref=evidence_ref,
        evidence_span=evidence_span,
        layer=str(evidence.get("layer")),
        occurrence_id=str(evidence.get("occurrence_id")),
    )


def _policy(
    value: Any,
    index: int,
    answer: str,
    catalog: Mapping[str, Mapping[str, Any]],
) -> PolicyAttribution:
    location = f"policies[{index}]"
    item = _mapping(value, location)
    policy_id = _text(item.get("policy_id"), f"{location}.policy_id")
    evidence_ref = _text(item.get("evidence_ref"), f"{location}.evidence_ref")
    evidence = catalog.get(evidence_ref)
    if evidence is None:
        raise AttributionValidationError(f"{location} has unknown evidence_ref")
    policy_ids = evidence.get("policy_ids")
    if not isinstance(policy_ids, Sequence) or policy_id not in policy_ids:
        raise AttributionValidationError(
            f"{location}.policy_id is not bound to the captured evidence occurrence"
        )
    applicability = item.get("applicability")
    compliance = item.get("compliance")
    if applicability not in APPLICABILITY:
        raise AttributionValidationError(f"{location}.applicability is invalid")
    if compliance not in COMPLIANCE:
        raise AttributionValidationError(f"{location}.compliance is invalid")
    if applicability == "NOT_APPLICABLE" and compliance != "NOT_APPLICABLE":
        raise AttributionValidationError(
            f"{location} NOT_APPLICABLE policy requires NOT_APPLICABLE compliance"
        )
    if applicability == "UNCERTAIN" and compliance != "UNCERTAIN":
        raise AttributionValidationError(
            f"{location} UNCERTAIN applicability requires UNCERTAIN compliance"
        )
    if applicability == "APPLICABLE" and compliance in {"NOT_APPLICABLE", "UNCERTAIN"}:
        raise AttributionValidationError(
            f"{location} APPLICABLE policy requires an evaluated compliance label"
        )
    spans = tuple(
        _span(span, answer, f"{location}.answer_spans[{span_index}]")
        for span_index, span in enumerate(_array(item.get("answer_spans"), f"{location}.answer_spans"))
    )
    uncertainty = item.get("uncertainty")
    if uncertainty not in UNCERTAINTY_LEVELS:
        raise AttributionValidationError(f"{location}.uncertainty is invalid")
    return PolicyAttribution(
        policy_id=policy_id,
        evidence_ref=evidence_ref,
        applicability=applicability,
        compliance=compliance,
        answer_spans=spans,
        uncertainty=uncertainty,
    )


def _span(value: Any, content: str, location: str) -> TextSpan:
    item = _mapping(value, location)
    start = item.get("start")
    end = item.get("end")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(content)
    ):
        raise AttributionValidationError(
            f"{location} must be a valid half-open Unicode-code-point span"
        )
    text = item.get("text")
    if not isinstance(text, str) or text != content[start:end]:
        raise AttributionValidationError(f"{location}.text does not match bound content")
    return TextSpan(start=start, end=end, text=text)


def _catalog_index(
    evidence_catalog: Sequence[Mapping[str, Any]],
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(evidence_catalog, Sequence) or isinstance(
        evidence_catalog, (str, bytes)
    ):
        raise AttributionValidationError("evidence_catalog must be an array")
    result: dict[str, Mapping[str, Any]] = {}
    for index, value in enumerate(evidence_catalog):
        item = _mapping(value, f"evidence_catalog[{index}]")
        ref = _text(item.get("ref"), f"evidence_catalog[{index}].ref")
        if ref in result:
            raise AttributionValidationError(f"duplicate evidence ref {ref}")
        result[ref] = item
    return result


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise AttributionValidationError(f"{location} must be an object")
    return value


def _array(value: Any, location: str) -> Sequence[Any]:
    if not isinstance(value, list):
        raise AttributionValidationError(f"{location} must be an array")
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AttributionValidationError(f"{location} must be non-empty text")
    return value.strip()
