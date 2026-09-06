import hashlib
import json

import pytest

from xiaoan_eval.evidence import (
    SnapshotValidationError,
    build_evidence_catalog,
    validate_effective_context_snapshot,
)


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def _snapshot() -> dict:
    return {
        "schema_version": "effective-context-snapshot/v1",
        "snapshot_id": "snap-TC-01-T2",
        "turn": 2,
        "context_kind": "ordinary",
        "router": {"status": "NOT_APPLICABLE", "units": []},
        "composer": {
            "status": "INVOKED",
            "units": [
                {
                    "occurrence_id": "prompt:main-agent:T2:1",
                    "unit_id": "prompt:main-agent",
                    "layer": "PROMPT",
                    "source_turn": 2,
                    "content": "Follow the response policy.",
                    "content_sha256": _digest("Follow the response policy."),
                    "policy_ids": ["policy:warn-risk"],
                },
                {
                    "occurrence_id": "capsule:n1:act:0:T2:1",
                    "unit_id": "capsule:n1:act:0",
                    "layer": "CAPSULE",
                    "source_turn": 2,
                    "content": "Ask what happened and what help is wanted.",
                    "content_sha256": _digest(
                        "Ask what happened and what help is wanted."
                    ),
                    "policy_ids": [],
                },
                {
                    "occurrence_id": "history:user:T1",
                    "unit_id": "history:user",
                    "layer": "PRIOR_USER",
                    "source_turn": 1,
                    "content": "Earlier message",
                    "content_sha256": _digest("Earlier message"),
                    "policy_ids": [],
                },
            ],
        },
    }


def test_canonical_catalog_uses_only_composer_visible_occurrences() -> None:
    snapshot = _snapshot()
    snapshot["router"] = {
        "status": "INVOKED",
        "units": [
            {
                "occurrence_id": "router:card:n1:T2",
                "unit_id": "router:card:n1",
                "layer": "CAPSULE",
                "source_turn": 2,
                "content": "Router-only card",
                "content_sha256": _digest("Router-only card"),
                "policy_ids": [],
            }
        ],
    }

    validated = validate_effective_context_snapshot(snapshot)
    catalog = build_evidence_catalog(validated)

    assert [item["ref"] for item in catalog] == [
        "prompt:prompt:main-agent:T2:1",
        "capsule:capsule:n1:act:0:T2:1",
        "prior-user:history:user:T1",
    ]
    assert all(item["snapshot_id"] == "snap-TC-01-T2" for item in catalog)
    assert all(item["invocation"] == "composer" for item in catalog)
    assert catalog[0]["policy_ids"] == ["policy:warn-risk"]


def test_snapshot_rejects_hash_drift_duplicate_occurrences_and_bad_turn_lineage() -> None:
    bad_hash = _snapshot()
    bad_hash["composer"]["units"][0]["content_sha256"] = "sha256:" + "0" * 64
    with pytest.raises(SnapshotValidationError, match="content_sha256"):
        validate_effective_context_snapshot(bad_hash)

    duplicate = _snapshot()
    duplicate["composer"]["units"][1]["occurrence_id"] = (
        duplicate["composer"]["units"][0]["occurrence_id"]
    )
    with pytest.raises(SnapshotValidationError, match="duplicate occurrence_id"):
        validate_effective_context_snapshot(duplicate)

    future_history = _snapshot()
    future_history["composer"]["units"][2]["source_turn"] = 2
    with pytest.raises(SnapshotValidationError, match="PRIOR_USER.*earlier"):
        validate_effective_context_snapshot(future_history)


def test_non_invoked_invocation_cannot_claim_model_visible_units() -> None:
    snapshot = _snapshot()
    snapshot["composer"]["status"] = "UNAVAILABLE"
    with pytest.raises(SnapshotValidationError, match="UNAVAILABLE.*units"):
        validate_effective_context_snapshot(snapshot)


def test_chatflow_runtime_v1_envelope_is_losslessly_adapted() -> None:
    content = {"rules": [{"id": "capsule-rule-1", "instruction": "ask once"}]}
    runtime_hash = "sha256:" + hashlib.sha256(
        json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    runtime = {
        "schema_version": "effective-context-snapshot/v1",
        "version": "effective-context-snapshot/v1",
        "snapshot_id": "snapshot-1", "turn": 1, "context_kind": "ORDINARY_CAPSULE",
        "invocations": {
            "router": {"status": "NOT_APPLICABLE", "context_units": [], "reason": "offline"},
            "composer": {"status": "INVOKED", "context_units": [{
                "ref": "capsule/N1/response_policy", "layer": "CAPSULE",
                "entity_id": "N1", "field_path": "response_policy", "item_id": "response_policy",
                "content": content, "content_hash": runtime_hash,
                "inclusion_state": "EXPOSED", "version": "2.0", "parent_ref": None,
            }]},
        },
    }

    snapshot = validate_effective_context_snapshot(runtime)
    catalog = build_evidence_catalog(snapshot)

    assert catalog[0]["policy_ids"] == ["capsule-rule-1"]
    assert catalog[0]["content"] == json.dumps(content, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
