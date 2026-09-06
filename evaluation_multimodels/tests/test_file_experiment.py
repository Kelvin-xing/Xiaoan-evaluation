import json

import pytest

from xiaoan_eval.file_experiment import apply_capsule_ground_proposal


def test_capsule_ground_executor_changes_only_declared_entity_field(tmp_path) -> None:
    path = tmp_path / "tech/chatflow/poc/capsules.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([
        {"id": "n2a", "ground": {"nodes": ["a", "b"]}, "title": "keep"},
        {"id": "n3", "ground": {"nodes": ["c"]}},
    ]))
    change = apply_capsule_ground_proposal(tmp_path, {
        "experiment_type": "capsule_ground_nodes",
        "target": {"file": "tech/chatflow/poc/capsules.json", "entity_id": "n2a", "field": "ground.nodes"},
        "operation": "replace", "before": ["a", "b"], "after": ["b"],
    })
    result = json.loads(path.read_text())
    assert result[0] == {"id": "n2a", "ground": {"nodes": ["b"]}, "title": "keep"}
    assert result[1]["ground"]["nodes"] == ["c"]
    assert change["before_sha256"] != change["after_sha256"]


def test_capsule_ground_executor_rejects_stale_before_value(tmp_path) -> None:
    path = tmp_path / "tech/chatflow/poc/capsules.json"
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps([{"id": "n2a", "ground": {"nodes": ["actual"]}}]))
    with pytest.raises(ValueError, match="before value"):
        apply_capsule_ground_proposal(tmp_path, {
            "experiment_type": "capsule_ground_nodes",
            "target": {"file": "tech/chatflow/poc/capsules.json", "entity_id": "n2a", "field": "ground.nodes"},
            "operation": "replace", "before": ["stale"], "after": ["new"],
        })
