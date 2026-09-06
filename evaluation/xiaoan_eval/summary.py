"""Human-first evaluation summary with explicit evidence and interpretation."""

from __future__ import annotations

from typing import Any, Mapping, Sequence


_INTERPRETATIONS = {
    "safety": (
        "安全風險判斷或危機處置未符合 oracle；優先檢查 safety policy、危機 prompt 和風險分級。",
        "這是 product-stage evidence，不等於已證明某一個 prompt 參數是唯一根因。",
    ),
    "router": (
        "route/capsule 選擇未符合 accepted oracle；優先檢查 router prompt、threshold、context turns 和 capsule eligibility。",
        "confusion matrix 能定位到 routing stage，但需要 controlled experiment 才能證明應改哪個參數。",
    ),
    "ground": (
        "必要 evidence 未解析或 retrieval precision/recall 不足；優先檢查 chunking、embedding、top-k、reranker 和 ground mapping。",
        "FN 偏高表示漏取回，FP 偏高表示取回雜訊；這是調優方向，不是單次 run 的因果證明。",
    ),
    "composer": (
        "retrieval 已提供 evidence，但回答 claims 未充分 grounded；優先檢查 composer prompt、context ordering 和 citation policy。",
        "高 retrieval recall 加低 faithfulness 才支持 generation-side hypothesis。",
    ),
    "memory": (
        "跨輪 state/memory checkpoint 未滿足；優先檢查 memory window、state handoff 和 continuation process。",
        "需要確認 trace 完整，避免把 unavailable telemetry 誤判成 memory failure。",
    ),
    "output_guard": (
        "output guard 或 PII/safety gate 未通過；優先檢查 guard rules、response schema 和拒答策略。",
        "hard-gate failure 不可由平均 quality score 抵銷。",
    ),
    "performance": (
        "timing/token/latency 指標超出要求或 trace 不可用；優先檢查 model、context size、reranker 和 streaming policy。",
        "先區分真實 latency regression 與 evaluator/provider telemetry error。",
    ),
}


def build_summary(
    records: Sequence[Mapping[str, Any]],
    v3_summary: Mapping[str, Any],
    recommendations: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    statuses = [str(record.get("status", "UNKNOWN")).upper() for record in records]
    issues: list[dict[str, Any]] = []
    pending_review: list[str] = []
    for record in records:
        record_status = str(record.get("status", "")).upper()
        if record_status == "NEEDS_REVIEW":
            pending_review.append(str(record.get("case_id", "unknown")))
            continue
        if record_status == "PASS":
            continue
        failure = record.get("failure")
        raw_stage = failure.get("primary_stage") if isinstance(failure, Mapping) else None
        stage = raw_stage if isinstance(raw_stage, str) and raw_stage else "unknown"
        interpretation, rationale = _INTERPRETATIONS.get(
            stage,
            ("這個 case 未通過，但目前沒有足夠的 stage mapping 證據。", "先檢查原始 case artifact 與 trace，再形成 hypothesis。"),
        )
        details = _record_evidence(record)
        issues.append({
            "case_id": str(record.get("case_id", "unknown")),
            "stage": stage,
            "evidence": [str(item) for item in record.get("evidence_refs", ())],
            "evidence_details": details,
            "interpretation": interpretation,
            "rationale": rationale,
            "status": "hypothesis",
        })
    issues.extend(_aggregate_issues(v3_summary))
    return {
        "overview": {
            "total_cases": len(records),
            "passed_cases": statuses.count("PASS"),
            "failed_cases": sum(item in {"FAIL", "ERROR"} for item in statuses),
            "needs_review_cases": statuses.count("NEEDS_REVIEW"),
        },
        "issues": issues,
        "pending_review": pending_review,
        "v3_metrics": dict(v3_summary),
        "recommendations": [dict(item) for item in recommendations],
        "reading_policy": {
            "human_entrypoint": "0-evaluation-summary.md",
            "audit_artifacts": ["4.2-case-results.jsonl", "6.2-rag-metrics.json", "6.4-v3-evaluation.json"],
            "causal_claim_policy": "A metric identifies a problem area; a parameter change is only validated after controlled repeated experiments.",
        },
    }


def render_summary(summary: Mapping[str, Any]) -> str:
    overview = summary.get("overview", {})
    lines = [
        "# Evaluation Summary",
        "",
        "> 人類入口：先看本文件；需要審計時再打開 4.2、6.2、6.4 詳細 artifact。",
        "",
        "## Outcome",
        "",
        f"- Cases: `{overview.get('total_cases', 0)}`",
        f"- Passed: `{overview.get('passed_cases', 0)}`",
        f"- Failed/Error: `{overview.get('failed_cases', 0)}`",
        f"- Needs review: `{overview.get('needs_review_cases', 0)}`",
        "",
        "## Issues and interpretation",
        "",
    ]
    issues = summary.get("issues", [])
    if not isinstance(issues, Sequence) or isinstance(issues, (str, bytes)) or not issues:
        lines.append("No product issue was identified in failed case records.")
    else:
        for issue in issues:
            if not isinstance(issue, Mapping):
                continue
            lines.extend([
                f"### {issue.get('case_id', 'unknown')} · `{issue.get('stage', 'unknown')}`",
                "",
                f"- Status: `{issue.get('status', 'hypothesis')}`",
                f"- Evidence: {', '.join(f'`{item}`' for item in issue.get('evidence', [])) or 'none recorded'}",
                *[f"- Evidence detail: `{detail.get('metric', 'metric')}` status=`{detail.get('status')}` score=`{detail.get('score', 'n/a')}` counts=`{detail.get('counts', {})}` reason={detail.get('reason', '')}" for detail in issue.get('evidence_details', []) if isinstance(detail, Mapping)],
                f"- Interpretation: {issue.get('interpretation', '')}",
                f"- Rationale / limitation: {issue.get('rationale', '')}",
                "",
            ])
    lines += ["## Recommended next actions", ""]
    recommendations = summary.get("recommendations", [])
    if isinstance(recommendations, Sequence) and not isinstance(recommendations, (str, bytes)) and recommendations:
        for item in recommendations:
            if isinstance(item, Mapping):
                lines.append(
                    f"- `{item.get('recommendation_id', 'recommendation')}` — {item.get('action_label', 'review')} — {item.get('target', 'unspecified target')}"
                )
    else:
        lines.append("No recommendation was generated.")
    pending = summary.get("pending_review", [])
    if isinstance(pending, Sequence) and pending:
        lines += ["", "## Pending human review", "", "- " + ", ".join(f"`{item}`" for item in pending)]
    lines += ["", "## Metric snapshot", ""]
    metrics = summary.get("v3_metrics", {})
    if isinstance(metrics, Mapping):
        for section in ("claims", "answer", "citations", "route", "safety", "refusal", "tools", "agent"):
            values = metrics.get(section)
            if not isinstance(values, Mapping):
                continue
            scalar_values = [
                f"{key}={_display(value)}"
                for key, value in values.items()
                if not isinstance(value, Mapping) and value is not None
            ]
            if scalar_values:
                lines.append(f"- `{section}`: " + ", ".join(scalar_values))
    if not isinstance(metrics, Mapping) or not metrics:
        lines.append("No v3 metric snapshot was available.")
    lines += [
        "",
        "## How to read this result",
        "",
        "1. This report identifies evidence-backed problem areas.",
        "2. `hypothesis` means the stage is implicated, not that a specific parameter is proven causal.",
        "3. Validate changes with a controlled repeated experiment before modifying production.",
    ]
    return "\n".join(lines) + "\n"


def _display(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.3f}"
    return str(value)


def _record_evidence(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    pipeline = record.get("pipeline")
    turns = pipeline.get("turns", ()) if isinstance(pipeline, Mapping) else ()
    details: list[dict[str, Any]] = []
    if isinstance(turns, Sequence) and not isinstance(turns, (str, bytes)):
        for turn_number, turn in enumerate(turns, 1):
            if not isinstance(turn, Mapping):
                continue
            for metric, payload in turn.items():
                if isinstance(payload, Mapping) and payload.get("status") in {"fail", "error"}:
                    details.append({"turn": turn_number, "metric": metric,
                                    "status": payload.get("status"), "score": payload.get("score"),
                                    "counts": payload.get("counts", {}), "reason": payload.get("reason", "")})
    return details


def _aggregate_issues(v3: Mapping[str, Any]) -> list[dict[str, Any]]:
    candidates = (
        ("ground", "retrieval", "recall", "retrieval recall is below 1.0"),
        ("composer", "answer", "faithfulness", "answer faithfulness is below 1.0"),
        ("composer", "citations", "recall", "citation recall is below 1.0"),
        ("router", "route", "accepted_accuracy", "accepted route accuracy is below 1.0"),
        ("safety", "safety", "accepted_accuracy", "accepted safety accuracy is below 1.0"),
        ("agent", "tools", "argument_accuracy", "tool argument accuracy is below 1.0"),
    )
    issues: list[dict[str, Any]] = []
    for stage, section, metric, message in candidates:
        values = v3.get(section)
        value = values.get(metric) if isinstance(values, Mapping) else None
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value >= 1.0:
            continue
        issues.append({
            "case_id": "cohort",
            "stage": stage,
            "evidence": ["6.4-v3-evaluation.json"],
            "evidence_details": [{"metric": f"{section}.{metric}", "status": "observed", "score": value}],
            "interpretation": message,
            "rationale": "Aggregate signal identifies a stage to investigate; controlled repeated experiment is still required.",
            "status": "hypothesis",
        })
    return issues
