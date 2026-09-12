"""Optional second-pass runtime over immutable answer artifacts."""

from __future__ import annotations

from dataclasses import asdict
import json
from typing import Any, Callable, Mapping, Sequence

from .attribution_client import AttributionClient
from .methodology_metrics import agreement_report, red_line_agreement_report, robust_dimension_summary, summarize_memory_metrics


def run_attribution_pass(answers: Sequence[Mapping[str, Any]], provider: Callable[[Mapping[str, Any]], str], *, judge_version: str) -> list[dict[str, Any]]:
    client = AttributionClient(provider, judge_version=judge_version)
    output = []
    for artifact in answers:
        answer_id = str(artifact.get("answer_id", ""))
        answer = artifact.get("answer") if isinstance(artifact.get("answer"), Mapping) else artifact
        text = answer.get("text", answer.get("answer", ""))
        trace = answer.get("trace")
        snapshot = trace.get("effective_context_snapshot") if isinstance(trace, Mapping) else None
        if str(answer.get("status", "PASS")) != "PASS" or not isinstance(snapshot, Mapping):
            output.append({"answer_id": answer_id, "status": "UNAVAILABLE", "result": None, "error_type": "ANSWER_OR_SNAPSHOT_UNAVAILABLE", "dag_node_id": f"attribution:{answer_id}", "parent_node_ids": [f"answer:{answer_id}"]})
            continue
        try:
            result = client.judge(str(text), snapshot)
            normalized = json.loads(json.dumps(asdict(result), ensure_ascii=False))
            output.append({"answer_id": answer_id, "status": "AVAILABLE", "result": normalized, "error_type": None, "dag_node_id": f"attribution:{answer_id}", "parent_node_ids": [f"answer:{answer_id}"]})
        except Exception as exc:
            output.append({"answer_id": answer_id, "status": "UNAVAILABLE", "result": None, "error_type": type(exc).__name__, "error": str(exc), "dag_node_id": f"attribution:{answer_id}", "parent_node_ids": [f"answer:{answer_id}"]})
    return output


def build_matrix_summaries(rows: Sequence[Mapping[str, Any]], *, memory_results: Sequence[Mapping[str, Any]] = (), attribution_results: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    dimensions = sorted({str(name) for row in rows for name in row.get("scores", {})})
    red_line_ids = sorted({str(identifier) for row in rows for identifier in (*row.get("expected_red_line_ids", ()), *row.get("red_line_evidence", {}))})
    attribution_available = sum(item.get("status") == "AVAILABLE" for item in attribution_results)
    attribution_status = "NOT_RUN" if not attribution_results else "AVAILABLE" if attribution_available else "UNAVAILABLE"
    return {
        "primary_denominator": {
            "eligible_n": sum(row.get("status") == "PASS" and row.get("primary_eligible", True) for row in rows),
            "self_judging_n": sum(bool(row.get("self_judging")) for row in rows),
            "self_excluded_n": sum(bool(row.get("self_judging")) and not row.get("primary_eligible", True) for row in rows),
            "operationally_unavailable_n": sum(row.get("status") != "PASS" for row in rows),
        },
        "validity_status": "NOT_CALIBRATED_BY_THIS_RUN",
        "agreement": {dimension: agreement_report(rows, dimension) for dimension in dimensions},
        "dimensions": {dimension: robust_dimension_summary(rows, dimension) for dimension in dimensions},
        "red_line_agreement": {identifier: red_line_agreement_report(rows, identifier) for identifier in red_line_ids},
        "memory": summarize_memory_metrics(memory_results),
        "attribution": {"status": attribution_status, "attempted_n": len(attribution_results), "eligible_n": attribution_available, "missing_n": len(attribution_results) - attribution_available},
    }
