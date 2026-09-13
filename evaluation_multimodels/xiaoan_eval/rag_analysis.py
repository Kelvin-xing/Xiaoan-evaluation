from __future__ import annotations

from typing import Any, Mapping, Sequence

from .measurement import retrieval_batch
from .trace_observations import iter_trace_observations


ATTRIBUTION_CATEGORIES = (
    "grounded_capsule",
    "capsule_only",
    "grounded_baseline",
    "baseline_no_resolved_refs",
)


def summarize_rag(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate reviewed RAG metrics and trace-based response attribution."""
    metric_sources = {
        "route_acceptance": "route",
        "route_preference": "route_preference",
    }
    metric_scores: dict[str, list[float]] = {
        "route_acceptance": [],
        "route_preference": [],
    }
    counts = {name: 0 for name in ATTRIBUTION_CATEGORIES}
    turns: list[dict[str, Any]] = []
    route_confusion: dict[str, dict[str, int]] = {}
    capsule_units = 0

    for record in records:
        case_id = str(record.get("case_id", "unknown"))
        pipeline = record.get("pipeline")
        if not isinstance(pipeline, Mapping):
            continue
        metric_turns = pipeline.get("turns", ())
        if isinstance(metric_turns, Sequence) and not isinstance(metric_turns, (str, bytes)):
            for metric_turn in metric_turns:
                if not isinstance(metric_turn, Mapping):
                    continue
                for name, source_name in metric_sources.items():
                    metric = metric_turn.get(source_name)
                    if not isinstance(metric, Mapping):
                        continue
                    score = metric.get("score")
                    if (
                        metric.get("status") in {"pass", "fail"}
                        and isinstance(score, (int, float))
                        and not isinstance(score, bool)
                    ):
                        metric_scores[name].append(float(score))
        observations = pipeline.get("observations", ())
        if isinstance(observations, Sequence) and not isinstance(observations, (str, bytes)):
            for observation in observations:
                if not isinstance(observation, Mapping) or observation.get("oracle_approved") is not True:
                    continue
                actual = observation.get("actual")
                expected = observation.get("expected")
                if not isinstance(expected, Mapping) or not isinstance(actual, Mapping):
                    continue
                pair = _route_pair(expected, actual)
                if pair is not None:
                    expected_route, actual_route = pair
                    row = route_confusion.setdefault(expected_route, {})
                    row[actual_route] = row.get(actual_route, 0) + 1
                units = actual.get("capsule_units")
                if isinstance(units, Sequence) and not isinstance(units, (str, bytes)):
                    capsule_units += sum(1 for item in units if isinstance(item, Mapping))

    for observation in iter_trace_observations(records):
        category = _attribution(observation.route_id, observation.resolved_refs)
        counts[category] += 1
        turns.append(
            {
                "case_id": observation.case_id,
                "turn": observation.turn,
                "route_id": observation.route_id,
                "resolved_ref_count": len(observation.resolved_refs),
                "attribution": category,
            }
        )

    return {
        "metrics": {
            name: {
                "evaluated_turns": len(scores),
                "mean": sum(scores) / len(scores) if scores else None,
            }
            for name, scores in metric_scores.items()
        },
        "attribution": {
            "method": (
                "Trace-based operational attribution. baseline_no_resolved_refs means "
                "only that the captured trace has no capsule route or resolved ground "
                "refs; it does not prove model-only provenance or hallucination."
            ),
            "counts": counts,
            "turns": sorted(turns, key=lambda item: (item["case_id"], item["turn"] or 0)),
        },
        "capsule_usage": (
            {
                "status": "available",
                "injected_units": capsule_units,
                "reason": "trace exposes the capsule units injected into composition; claim-level alignment is in v3 metrics",
            }
            if capsule_units
            else {
                "status": "unavailable",
                "reason": "current Chatflow traces do not expose verifiable capsule content units",
            }
        ),
        "retrieval": _ranked_measurements(records),
        "route_confusion": route_confusion,
    }


def _route_pair(
    expected: Mapping[str, Any], actual: Mapping[str, Any]
) -> tuple[str, str] | None:
    expected_route = expected.get("preferred_route_id")
    if expected_route is None:
        accepted = expected.get("route_ids")
        if isinstance(accepted, Sequence) and not isinstance(accepted, (str, bytes)) and len(accepted) == 1:
            expected_route = accepted[0]
    actual_route = actual.get("route_id")
    if expected_route is None or actual_route is None:
        return None
    return str(expected_route), str(actual_route)


def render_rag_markdown(summary: Mapping[str, Any]) -> str:
    metrics = summary["metrics"]
    attribution = summary["attribution"]
    lines = [
        "# Routing and RAG metrics",
        "",
        "| Metric | Evaluated turns | Mean |",
        "| --- | ---: | ---: |",
    ]
    for name in ("route_acceptance", "route_preference"):
        item = metrics[name]
        mean = item["mean"]
        lines.append(
            f"| {name} | {item['evaluated_turns']} | "
            f"{mean:.3f} |" if isinstance(mean, (int, float)) else
            f"| {name} | {item['evaluated_turns']} | n/a |"
        )
    lines.extend(
        [
            "",
            "Capsule content attribution: "
            + ("available from injected unit trace." if summary["capsule_usage"]["status"] == "available" else
               "unavailable. Current Chatflow traces do not expose verifiable capsule content units."),
            "",
            "## Retrieval ranking",
            "",
            f"MRR: {_format_optional(summary.get('retrieval', {}).get('mrr'))}",
            f"nDCG: {_format_optional(summary.get('retrieval', {}).get('ndcg'))}",
        ]
    )
    lines.extend(
        [
            "",
            "## Trace attribution",
            "",
            attribution["method"],
            "",
            "| Category | Turns |",
            "| --- | ---: |",
        ]
    )
    lines.extend(
        f"| {name} | {attribution['counts'][name]} |"
        for name in ATTRIBUTION_CATEGORIES
    )
    return "\n".join(lines) + "\n"


def _format_optional(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"


def _retrieval_rates(counts: Mapping[str, int]) -> dict[str, float | None]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall else None
    )
    return {"precision": precision, "recall": recall, "f1": f1}


def _attribution(route_id: str, refs: frozenset[str]) -> str:
    capsule = route_id not in {"baseline", "unknown"}
    if capsule and refs:
        return "grounded_capsule"
    if capsule:
        return "capsule_only"
    if refs:
        return "grounded_baseline"
    return "baseline_no_resolved_refs"


def _ranked_measurements(records):
    rows = []
    missing = 0
    for record in records:
        for observation in record.get("pipeline", {}).get("observations", []):
            oracle = observation.get("expected", {}).get("retrieval_oracle")
            if observation.get("oracle_approved") is not True or not isinstance(oracle, dict):
                continue
            actual = observation.get("actual", {})
            versions = actual.get("retrieval_versions")
            keys = ("corpus_version", "chunk_version", "retriever_version", "reranker_version")
            matching = isinstance(versions, dict) and all(versions.get(k) == oracle[k] for k in keys)
            if actual.get("ranked_refs") is None or not matching:
                missing += 1
                continue
            rows.append({**oracle, "ranked_ids": actual["ranked_refs"]})
    result = retrieval_batch(rows)
    # Keep legacy flat fields only for a single comparable stratum.
    metrics = result["strata"][0]["metrics"] if len(result["strata"]) == 1 else {}
    return {"mrr": metrics.get("reciprocal_rank_at_k", {}).get("mean"),
            "ndcg": metrics.get("ndcg_at_k", {}).get("mean"),
            "evaluated_turns": sum(r["status"] == "AVAILABLE" for r in result["queries"]),
            "missing_trace_turns": missing, "ranked_evaluation": result}
