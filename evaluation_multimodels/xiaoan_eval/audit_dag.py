"""Small auditable DAG contract shared by rubric, attribution and pairwise passes."""

from __future__ import annotations

from typing import Any, Mapping


DAG_SCHEMA_VERSION = "evaluation-dag/v1"


def dag_node(node_id: str, node_type: str, *, parents: tuple[str, ...] = (), **payload: Any) -> dict[str, Any]:
    if not node_id.strip() or not node_type.strip():
        raise ValueError("DAG node id and type must be non-empty")
    return {
        "dag_schema_version": DAG_SCHEMA_VERSION,
        "node_id": node_id,
        "node_type": node_type,
        "parent_node_ids": list(parents),
        **payload,
    }


def validate_dag_node(value: Mapping[str, Any]) -> None:
    if value.get("dag_schema_version") != DAG_SCHEMA_VERSION:
        raise ValueError("invalid evaluation DAG schema")
    if not isinstance(value.get("node_id"), str) or not value["node_id"].strip():
        raise ValueError("DAG node_id must be non-empty")
    if not isinstance(value.get("parent_node_ids"), list):
        raise ValueError("DAG parent_node_ids must be an array")
