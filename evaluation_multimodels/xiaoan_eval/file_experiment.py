"""Field-level, allowlisted file experiments for XiaoAn snapshots."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import shutil
from typing import Any, Mapping


CAPSULES_PATH = Path("tech/chatflow/poc/capsules.json")
SNAPSHOT_EXCLUDES = frozenset({".git", ".venv", "runs", "__pycache__", ".pytest_cache"})


def validate_capsule_ground_proposal(proposal: Mapping[str, Any]) -> dict[str, Any]:
    if proposal.get("experiment_type") != "capsule_ground_nodes":
        raise ValueError("only capsule_ground_nodes experiments are approved")
    target = proposal.get("target")
    if not isinstance(target, Mapping):
        raise ValueError("proposal target must be an object")
    expected = {"file": str(CAPSULES_PATH), "field": "ground.nodes"}
    for key, value in expected.items():
        if target.get(key) != value:
            raise ValueError(f"proposal target {key} must be {value!r}")
    capsule_id = target.get("entity_id")
    if not isinstance(capsule_id, str) or not capsule_id:
        raise ValueError("proposal target entity_id must be a non-empty string")
    if proposal.get("operation") != "replace":
        raise ValueError("capsule ground proposal operation must be replace")
    before = _node_list(proposal.get("before"), "before")
    after = _node_list(proposal.get("after"), "after")
    if before == after:
        raise ValueError("proposal must change ground.nodes")
    return {"capsule_id": capsule_id, "before": before, "after": after}


def apply_capsule_ground_proposal(snapshot_root: Path, proposal: Mapping[str, Any]) -> dict[str, Any]:
    validated = validate_capsule_ground_proposal(proposal)
    path = snapshot_root / CAPSULES_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    capsule = next((item for item in document if item.get("id") == validated["capsule_id"]), None)
    if not isinstance(capsule, dict):
        raise ValueError(f"capsule not found: {validated['capsule_id']}")
    ground = capsule.get("ground")
    if not isinstance(ground, dict):
        raise ValueError("capsule ground must be an object")
    actual = ground.get("nodes", [])
    if actual != validated["before"]:
        raise ValueError("proposal before value does not match snapshot ground.nodes")
    before_hash = _sha256(path)
    ground["nodes"] = validated["after"]
    path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "experiment_type": "capsule_ground_nodes",
        "file": str(CAPSULES_PATH),
        "entity_id": validated["capsule_id"],
        "field": "ground.nodes",
        "before": validated["before"],
        "after": validated["after"],
        "before_sha256": before_hash,
        "after_sha256": _sha256(path),
    }


def snapshot_workspace(source: Path, destination: Path) -> None:
    if destination.exists():
        raise ValueError(f"snapshot destination already exists: {destination}")

    def ignore(_directory: str, names: list[str]) -> set[str]:
        return {name for name in names if name in SNAPSHOT_EXCLUDES or name == ".DS_Store"}

    shutil.copytree(source, destination, ignore=ignore, symlinks=False)


def _node_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) and item for item in value):
        raise ValueError(f"proposal {field} must be an array of non-empty node IDs")
    if len(value) != len(set(value)):
        raise ValueError(f"proposal {field} contains duplicate node IDs")
    return list(value)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
