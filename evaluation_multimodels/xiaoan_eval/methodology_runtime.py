"""Optional second-pass runtime over immutable answer artifacts."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Mapping, Sequence

from .attribution_client import AttributionClient
from .methodology_metrics import agreement_report, summarize_memory_metrics


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
            output.append({"answer_id": answer_id, "status": "UNAVAILABLE", "result": None, "error_type": "ANSWER_OR_SNAPSHOT_UNAVAILABLE"})
            continue
        try:
            result = client.judge(str(text), snapshot)
            output.append({"answer_id": answer_id, "status": "AVAILABLE", "result": asdict(result), "error_type": None})
        except Exception as exc:
            output.append({"answer_id": answer_id, "status": "UNAVAILABLE", "result": None, "error_type": type(exc).__name__, "error": str(exc)})
    return output


def build_matrix_summaries(rows: Sequence[Mapping[str, Any]], *, memory_results: Sequence[Mapping[str, Any]] = (), attribution_results: Sequence[Mapping[str, Any]] = ()) -> dict[str, Any]:
    dimensions = sorted({str(name) for row in rows for name in row.get("scores", {})})
    attribution_available = sum(item.get("status") == "AVAILABLE" for item in attribution_results)
    return {
        "primary_denominator": {
            "eligible_n": sum(row.get("status") == "PASS" and row.get("primary_eligible", True) for row in rows),
            "self_judging_n": sum(bool(row.get("self_judging")) for row in rows),
            "operationally_unavailable_n": sum(row.get("status") != "PASS" for row in rows),
        },
        "agreement": {dimension: agreement_report(rows, dimension) for dimension in dimensions},
        "memory": summarize_memory_metrics(memory_results),
        "attribution": {"status": "AVAILABLE" if attribution_available else "UNAVAILABLE", "eligible_n": attribution_available, "missing_n": len(attribution_results) - attribution_available},
    }
