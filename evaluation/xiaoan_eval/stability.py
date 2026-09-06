from __future__ import annotations

from collections import Counter
from itertools import combinations
from statistics import mean, pvariance
from typing import Any, Mapping, Sequence

from .trace_observations import TraceObservation, iter_trace_observations


def summarize_stability(
    runs: Sequence[Sequence[Mapping[str, Any]]],
) -> dict[str, Any]:
    """Compare repeated runs of the same case/turn set."""
    if len(runs) < 2:
        raise ValueError("stability analysis requires at least two runs")
    indexed = [_index_run(run) for run in runs]
    expected_keys = set(indexed[0])
    if any(set(run) != expected_keys for run in indexed[1:]):
        raise ValueError("stability runs must contain the same case and turn set")

    turns = []
    for case_id, turn in sorted(expected_keys):
        observations = [run[(case_id, turn)] for run in indexed]
        routes = [item.route_id for item in observations]
        refs = [item.resolved_refs for item in observations]
        hashes = [
            item.response_sha256
            for item in observations
            if item.response_sha256 is not None
        ]
        raw_rows = [_raw_turn(run, case_id, turn) for run in runs]
        scores = [value for row in raw_rows if (value := _turn_score(row, turn)) is not None]
        latencies = [value for row in raw_rows if (value := _turn_latency(row, turn)) is not None]
        statuses = [str(row.get("status", "UNKNOWN")).upper() for row in raw_rows]
        hard_gates = [_hard_gate(row) for row in raw_rows]
        hard_gates = [value for value in hard_gates if value is not None]
        retries = [_trace_count(row, turn, "retries") for row in raw_rows]
        timeouts = [_trace_count(row, turn, "timeouts") for row in raw_rows]
        turns.append(
            {
                "case_id": case_id,
                "turn": turn,
                "capsule_modal_agreement": _modal_agreement(routes),
                "ground_pairwise_jaccard": _mean_pairwise_jaccard(refs),
                "response_exact_modal_agreement": (
                    _modal_agreement(hashes) if hashes else None
                ),
                "observed_route_ids": sorted(set(routes)),
                "observed_ground_ref_sets": len({tuple(sorted(item)) for item in refs}),
                "observed_response_hashes": len(set(hashes)),
                "score_mean": mean(scores) if scores else None,
                "score_variance": pvariance(scores) if len(scores) > 1 else 0.0 if scores else None,
                "score_range": max(scores) - min(scores) if scores else None,
                "pass_fail_flips": len(set(statuses) & {"PASS", "FAIL", "ERROR"}) > 1,
                "hard_gate_consistency": _modal_agreement(hard_gates) if hard_gates else None,
                "latency_mean_ms": mean(latencies) if latencies else None,
                "latency_variance_ms2": pvariance(latencies) if len(latencies) > 1 else 0.0 if latencies else None,
                "retry_mean": mean(retries),
                "retry_variance": pvariance(retries) if len(retries) > 1 else 0.0,
                "timeout_rate": sum(value > 0 for value in timeouts) / len(timeouts),
            }
        )

    summary = {
        "run_count": len(runs),
        "turns": turns,
        "global": {
            "capsule_modal_agreement": _mean(
                item["capsule_modal_agreement"] for item in turns
            ),
            "ground_pairwise_jaccard": _mean(
                item["ground_pairwise_jaccard"] for item in turns
            ),
            "response_exact_modal_agreement": _mean(
                item["response_exact_modal_agreement"]
                for item in turns
                if item["response_exact_modal_agreement"] is not None
            ),
            "response_semantic_agreement": None,
            "claim_stability": None,
            "score_variance": _mean_optional(item["score_variance"] for item in turns),
            "pass_fail_flip_turns": sum(bool(item["pass_fail_flips"]) for item in turns),
            "hard_gate_consistency": _mean_optional(item["hard_gate_consistency"] for item in turns),
            "latency_variance_ms2": _mean_optional(item["latency_variance_ms2"] for item in turns),
            "retry_variance": _mean_optional(item["retry_variance"] for item in turns),
            "timeout_rate": _mean_optional(item["timeout_rate"] for item in turns),
        },
    }
    summary["classification"] = "DESCRIPTIVE_ONLY"
    summary["limitation"] = "Repeatability is not correctness; a stable wrong answer remains wrong."
    return summary


def render_stability_markdown(summary: Mapping[str, Any]) -> str:
    global_metrics = summary["global"]
    lines = [
        "# Stability report",
        "",
        f"Runs: {summary['run_count']}",
        "",
        f"- Capsule modal agreement: {_format(global_metrics['capsule_modal_agreement'])}",
        f"- Ground refs pairwise Jaccard: {_format(global_metrics['ground_pairwise_jaccard'])}",
        f"- Response exact modal agreement: {_format(global_metrics['response_exact_modal_agreement'])}",
        f"- Score variance: {_format(global_metrics['score_variance'])}",
        f"- Pass/fail flip turns: {global_metrics['pass_fail_flip_turns']}",
        f"- Hard-gate consistency: {_format(global_metrics['hard_gate_consistency'])}",
        f"- Latency variance (ms^2): {_format(global_metrics['latency_variance_ms2'])}",
        f"- Retry variance: {_format(global_metrics['retry_variance'])}",
        f"- Timeout rate: {_format(global_metrics['timeout_rate'])}",
        "- Response semantic agreement: unavailable (responses are not stored in artifacts)",
        "- Claim stability: unavailable (claim-level provenance is not instrumented)",
        "",
        "| Case | Turn | Capsule agreement | Ground Jaccard | Response agreement |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for item in summary["turns"]:
        lines.append(
            f"| {item['case_id']} | {item['turn']} | "
            f"{_format(item['capsule_modal_agreement'])} | "
            f"{_format(item['ground_pairwise_jaccard'])} | "
            f"{_format(item['response_exact_modal_agreement'])} |"
        )
    return "\n".join(lines) + "\n"


def _index_run(
    records: Sequence[Mapping[str, Any]],
) -> dict[tuple[str, int], TraceObservation]:
    indexed: dict[tuple[str, int], TraceObservation] = {}
    for observation in iter_trace_observations(records):
        key = (observation.case_id, observation.turn)
        if key in indexed:
            raise ValueError(
                f"duplicate stability observation: {observation.case_id} "
                f"turn {observation.turn}"
            )
        indexed[key] = observation
    return indexed


def _raw_turn(run: Sequence[Mapping[str, Any]], case_id: str, turn: int) -> Mapping[str, Any]:
    return next(record for record in run if str(record.get("case_id")) == case_id)


def _turn_score(record: Mapping[str, Any], turn: int) -> float | None:
    review = record.get("review")
    audits = review.get("judge_audit", ()) if isinstance(review, Mapping) else ()
    if isinstance(audits, Sequence) and not isinstance(audits, (str, bytes)) and turn <= len(audits):
        audit = audits[turn - 1]
        primary = audit.get("primary") if isinstance(audit, Mapping) else None
        dimensions = primary.get("dimensions", ()) if isinstance(primary, Mapping) else ()
        scores = [float(item["score"]) for item in dimensions if isinstance(item, Mapping) and isinstance(item.get("score"), (int, float)) and not isinstance(item.get("score"), bool)]
        if scores:
            return mean(scores)
    quality = record.get("quality")
    value = quality.get("weighted_total") if isinstance(quality, Mapping) else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _turn_latency(record: Mapping[str, Any], turn: int) -> float | None:
    trace = _trace(record, turn)
    timings = trace.get("timings") if isinstance(trace, Mapping) else None
    value = timings.get("total_ms") if isinstance(timings, Mapping) else None
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _hard_gate(record: Mapping[str, Any]) -> bool | None:
    safety = record.get("safety")
    value = safety.get("hard_gate_passed") if isinstance(safety, Mapping) else None
    return value if isinstance(value, bool) else None


def _trace_count(record: Mapping[str, Any], turn: int, key: str) -> int:
    trace = _trace(record, turn)
    value = trace.get(key) if isinstance(trace, Mapping) else None
    return int(value) if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def _trace(record: Mapping[str, Any], turn: int) -> Mapping[str, Any]:
    pipeline = record.get("pipeline")
    traces = pipeline.get("turn_traces", ()) if isinstance(pipeline, Mapping) else ()
    for index, row in enumerate(traces, 1):
        if isinstance(row, Mapping) and int(row.get("turn", index)) == turn:
            value = row.get("trace")
            return value if isinstance(value, Mapping) else {}
    return {}


def _modal_agreement(values: Sequence[str]) -> float:
    return max(Counter(values).values()) / len(values)


def _mean_optional(values) -> float | None:
    items = [value for value in values if isinstance(value, (int, float)) and not isinstance(value, bool)]
    return mean(items) if items else None


def _mean_pairwise_jaccard(values: Sequence[frozenset[str]]) -> float:
    scores = []
    for left, right in combinations(values, 2):
        union = left | right
        scores.append(len(left & right) / len(union) if union else 1.0)
    return _mean(scores)


def _mean(values) -> float:
    items = list(values)
    return sum(items) / len(items) if items else 1.0


def _format(value: Any) -> str:
    return f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"
