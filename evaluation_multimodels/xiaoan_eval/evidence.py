"""Validation and canonicalization for captured Effective Context Snapshots."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any, Mapping, Sequence


SNAPSHOT_SCHEMA_VERSION = "effective-context-snapshot/v1"
INVOCATION_STATUSES = frozenset({"INVOKED", "NOT_APPLICABLE", "UNAVAILABLE"})
EVIDENCE_LAYERS = frozenset(
    {
        "PROMPT",
        "CAPSULE",
        "WIKI",
        "SOURCE",
        "CURRENT_INPUT",
        "PRIOR_USER",
        "PRIOR_ASSISTANT",
    }
)
PRIOR_LAYERS = frozenset({"PRIOR_USER", "PRIOR_ASSISTANT"})


class SnapshotValidationError(ValueError):
    """Raised when captured context cannot be trusted as model-visible evidence."""


@dataclass(frozen=True)
class EvidenceUnit:
    occurrence_id: str
    unit_id: str
    layer: str
    source_turn: int
    content: str
    content_sha256: str
    policy_ids: tuple[str, ...]


@dataclass(frozen=True)
class InvocationSnapshot:
    status: str
    units: tuple[EvidenceUnit, ...]
    reason: str | None = None


@dataclass(frozen=True)
class EffectiveContextSnapshot:
    schema_version: str
    snapshot_id: str
    turn: int
    context_kind: str
    router: InvocationSnapshot
    composer: InvocationSnapshot


def validate_effective_context_snapshot(value: Mapping[str, Any]) -> EffectiveContextSnapshot:
    """Fail closed unless a v1 snapshot binds every captured unit to exact text."""
    root = _mapping(value, "snapshot")
    if "invocations" in root:
        root = _normalize_runtime_snapshot(root)
    if root.get("schema_version") != SNAPSHOT_SCHEMA_VERSION:
        raise SnapshotValidationError(
            f"snapshot.schema_version must be {SNAPSHOT_SCHEMA_VERSION}"
        )
    snapshot_id = _text(root.get("snapshot_id"), "snapshot.snapshot_id")
    turn = _positive_int(root.get("turn"), "snapshot.turn")
    context_kind = _text(root.get("context_kind"), "snapshot.context_kind")
    seen: set[str] = set()
    router = _invocation(root.get("router"), "router", turn, seen)
    composer = _invocation(root.get("composer"), "composer", turn, seen)
    return EffectiveContextSnapshot(
        schema_version=SNAPSHOT_SCHEMA_VERSION,
        snapshot_id=snapshot_id,
        turn=turn,
        context_kind=context_kind,
        router=router,
        composer=composer,
    )


def _normalize_runtime_snapshot(root: Mapping[str, Any]) -> Mapping[str, Any]:
    """Losslessly adapt the Chatflow-owned v1 envelope at evaluator ingress."""
    version = root.get("schema_version", root.get("version"))
    if version not in {SNAPSHOT_SCHEMA_VERSION, "1.0"}:
        raise SnapshotValidationError("unsupported runtime snapshot version")
    turn = _positive_int(root.get("turn"), "snapshot.turn")
    invocations = _mapping(root.get("invocations"), "snapshot.invocations")
    return {
        "schema_version": SNAPSHOT_SCHEMA_VERSION,
        "snapshot_id": root.get("snapshot_id"),
        "turn": turn,
        "context_kind": root.get("context_kind"),
        "router": _normalize_runtime_invocation(invocations.get("router"), "router", turn),
        "composer": _normalize_runtime_invocation(invocations.get("composer"), "composer", turn),
    }


def _normalize_runtime_invocation(value: Any, name: str, turn: int) -> Mapping[str, Any]:
    invocation = _mapping(value, f"snapshot.invocations.{name}")
    raw_status = invocation.get("status")
    status = {
        "PREPARED": "UNAVAILABLE",
        "INVOKED": "INVOKED",
        "FAILED": "UNAVAILABLE",
        "NOT_APPLICABLE": "NOT_APPLICABLE",
        "UNAVAILABLE": "UNAVAILABLE",
    }.get(raw_status)
    if status is None:
        raise SnapshotValidationError(f"unsupported runtime invocation status: {raw_status}")
    units = []
    if status == "INVOKED":
        for index, raw in enumerate(invocation.get("context_units", ())):
            item = _mapping(raw, f"snapshot.invocations.{name}.context_units[{index}]")
            if item.get("inclusion_state") != "EXPOSED":
                continue
            content_value = item.get("content")
            content = (
                content_value
                if isinstance(content_value, str)
                else json.dumps(content_value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            )
            supplied = item.get("content_hash")
            expected_runtime = "sha256:" + hashlib.sha256(
                json.dumps(content_value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
            ).hexdigest()
            if supplied != expected_runtime:
                raise SnapshotValidationError("runtime context unit content_hash mismatch")
            policy_ids = []
            if item.get("field_path") == "response_policy" and isinstance(content_value, Mapping):
                rules = content_value.get("rules", ())
                if isinstance(rules, Sequence) and not isinstance(rules, (str, bytes)):
                    policy_ids = [
                        str(rule["id"])
                        for rule in rules
                        if isinstance(rule, Mapping) and isinstance(rule.get("id"), str)
                    ]
            units.append({
                "occurrence_id": str(item.get("ref")),
                "unit_id": str(item.get("item_id") or item.get("field_path")),
                "layer": item.get("layer"),
                "source_turn": turn,
                "content": content,
                "content_sha256": "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest(),
                "policy_ids": policy_ids,
            })
    return {"status": status, "units": units, "reason": invocation.get("reason") or None}


def build_evidence_catalog(
    snapshot: EffectiveContextSnapshot | Mapping[str, Any],
) -> list[dict[str, Any]]:
    """Build answer-support refs only from units visible to the Composer."""
    validated = (
        snapshot
        if isinstance(snapshot, EffectiveContextSnapshot)
        else validate_effective_context_snapshot(snapshot)
    )
    if validated.composer.status != "INVOKED":
        return []
    return [
        {
            "ref": canonical_evidence_ref(unit),
            "layer": unit.layer,
            "occurrence_id": unit.occurrence_id,
            "unit_id": unit.unit_id,
            "source_turn": unit.source_turn,
            "content": unit.content,
            "content_sha256": unit.content_sha256,
            "policy_ids": list(unit.policy_ids),
            "snapshot_id": validated.snapshot_id,
            "invocation": "composer",
        }
        for unit in validated.composer.units
    ]


def canonical_evidence_ref(unit: EvidenceUnit) -> str:
    return f"{unit.layer.lower().replace('_', '-')}:{unit.occurrence_id}"


def _invocation(
    value: Any,
    name: str,
    snapshot_turn: int,
    seen: set[str],
) -> InvocationSnapshot:
    item = _mapping(value, f"snapshot.{name}")
    status = item.get("status")
    if status not in INVOCATION_STATUSES:
        raise SnapshotValidationError(
            f"snapshot.{name}.status must be one of {sorted(INVOCATION_STATUSES)}"
        )
    raw_units = item.get("units")
    if not _sequence(raw_units):
        raise SnapshotValidationError(f"snapshot.{name}.units must be an array")
    if status != "INVOKED" and raw_units:
        raise SnapshotValidationError(
            f"snapshot.{name} status {status} requires empty units"
        )
    units: list[EvidenceUnit] = []
    for index, raw_unit in enumerate(raw_units):
        unit = _unit(raw_unit, f"snapshot.{name}.units[{index}]", snapshot_turn)
        if unit.occurrence_id in seen:
            raise SnapshotValidationError(
                f"snapshot contains duplicate occurrence_id {unit.occurrence_id}"
            )
        seen.add(unit.occurrence_id)
        units.append(unit)
    reason = item.get("reason")
    if reason is not None and (not isinstance(reason, str) or not reason.strip()):
        raise SnapshotValidationError(f"snapshot.{name}.reason must be non-empty text")
    return InvocationSnapshot(status=status, units=tuple(units), reason=reason)


def _unit(value: Any, location: str, snapshot_turn: int) -> EvidenceUnit:
    item = _mapping(value, location)
    occurrence_id = _text(item.get("occurrence_id"), f"{location}.occurrence_id")
    unit_id = _text(item.get("unit_id"), f"{location}.unit_id")
    layer = item.get("layer")
    if layer not in EVIDENCE_LAYERS:
        raise SnapshotValidationError(
            f"{location}.layer must be one of {sorted(EVIDENCE_LAYERS)}"
        )
    source_turn = _positive_int(item.get("source_turn"), f"{location}.source_turn")
    if layer in PRIOR_LAYERS and source_turn >= snapshot_turn:
        raise SnapshotValidationError(
            f"{location} {layer} source_turn must be earlier than snapshot.turn"
        )
    if layer not in PRIOR_LAYERS and source_turn != snapshot_turn:
        raise SnapshotValidationError(
            f"{location} {layer} source_turn must equal snapshot.turn"
        )
    content = _text(item.get("content"), f"{location}.content", strip=False)
    supplied_digest = _text(
        item.get("content_sha256"), f"{location}.content_sha256"
    )
    expected_digest = "sha256:" + hashlib.sha256(content.encode("utf-8")).hexdigest()
    if supplied_digest != expected_digest:
        raise SnapshotValidationError(
            f"{location}.content_sha256 does not match captured content"
        )
    policy_ids = item.get("policy_ids", [])
    if not isinstance(policy_ids, list) or any(
        not isinstance(policy_id, str) or not policy_id.strip()
        for policy_id in policy_ids
    ):
        raise SnapshotValidationError(f"{location}.policy_ids must be an array of strings")
    if len(set(policy_ids)) != len(policy_ids):
        raise SnapshotValidationError(f"{location}.policy_ids must be unique")
    return EvidenceUnit(
        occurrence_id=occurrence_id,
        unit_id=unit_id,
        layer=layer,
        source_turn=source_turn,
        content=content,
        content_sha256=supplied_digest,
        policy_ids=tuple(policy_ids),
    )


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SnapshotValidationError(f"{location} must be an object")
    return value


def _text(value: Any, location: str, *, strip: bool = True) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SnapshotValidationError(f"{location} must be non-empty text")
    return value.strip() if strip else value


def _positive_int(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise SnapshotValidationError(f"{location} must be a positive integer")
    return value


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
