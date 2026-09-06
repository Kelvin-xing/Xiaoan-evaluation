"""Normalized facts shared by the evaluation workbook and decision report."""

from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import json
from statistics import mean
from typing import Any, Mapping, Sequence
from uuid import uuid4

from .artifacts import CaseArtifact, build_artifacts
from .rag_analysis import summarize_rag
from .v3_metrics import summarize_v3


SCHEMA_VERSION = "2.0"
TEXT_CHUNK_SIZE = 30000
OPTIONAL_STATES = {"NOT_RUN", "NOT_REQUIRED", "UNAVAILABLE"}


def _canonical(value: Any) -> str:
    return json.dumps(_canonical_value(value), ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _canonical_value(value: Any) -> Any:
    if value == "":
        return None
    if isinstance(value, bool) or value is None or isinstance(value, str):
        return value
    if isinstance(value, (int, float)):
        return {"$number": format(value, ".15g")}
    if isinstance(value, Mapping):
        return {str(key): _canonical_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return [_canonical_value(item) for item in value]
    return str(value)


def canonical_digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value).encode("utf-8")).hexdigest()


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _sequence(value: Any) -> Sequence[Any]:
    return value if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else ()


def _number(value: Any) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _joined(value: Any) -> str:
    if isinstance(value, Mapping):
        return "; ".join(f"{key}:{item}" for key, items in sorted(value.items()) for item in _sequence(items))
    return "; ".join(str(item) for item in _sequence(value))


def _reason_zh(value: Any) -> str:
    """Render evaluator reasons in Traditional Chinese without losing meaning."""
    if value is None or not str(value).strip():
        return ""
    text = str(value).strip()
    translations = {
        "wrong route": "路由選擇錯誤",
        "no ground resolution error detected": "未偵測到 ground 解析錯誤",
        "ground resolution error detected": "偵測到 ground 解析錯誤",
        "no reviewed relevant ground refs": "沒有已審核的相關 ground 引用",
        "no required ground refs": "沒有設定必要的 ground 引用",
        "second judge required but unavailable": "需要第二個 Judge，但目前不可用",
        "provider failed": "模型服務商呼叫失敗",
        "current Chatflow traces do not expose verifiable capsule content units": "目前 Chatflow trace 沒有暴露可驗證的 capsule 內容單位",
        "Legacy compatibility facts only. Exact ref usage is operational evidence, not semantic support or token provenance.": "僅供舊版相容性使用；精確引用使用量是操作證據，不等於語義支持或 token 來源證明。",
    }
    if text in translations:
        return translations[text]
    replacements = (
        ("ground resolution", "ground 解析"), ("no ", "未"), (" detected", ""),
        (" unavailable", "不可用"), ("required", "必要"), ("refs", "引用"),
        ("route", "路由"), ("wrong", "錯誤"), ("failed", "失敗"),
    )
    translated = text
    for source, target in replacements:
        translated = translated.replace(source, target)
    return translated if translated != text else f"評估訊息：{text}"


@dataclass(frozen=True)
class ReportModel:
    schema_version: str
    generation_id: str
    artifact_state: str
    manifest: Mapping[str, Any]
    overview: tuple[Mapping[str, Any], ...]
    cases: tuple[Mapping[str, Any], ...]
    turns: tuple[Mapping[str, Any], ...]
    metrics: tuple[Mapping[str, Any], ...]
    baseline: tuple[Mapping[str, Any], ...] = ()
    experiments: tuple[Mapping[str, Any], ...] = ()
    human_review: tuple[Mapping[str, Any], ...] = ()
    stability: tuple[Mapping[str, Any], ...] = ()
    text_content: tuple[Mapping[str, Any], ...] = ()
    recommendations: tuple[Mapping[str, Any], ...] = ()
    source_records: tuple[Mapping[str, Any], ...] = field(default=(), repr=False)

    @property
    def core_digest(self) -> str:
        return canonical_digest({
            "schema_version": self.schema_version,
            "manifest": self.manifest,
            "cases": self.cases,
            "turns": self.turns,
            "metrics": self.metrics,
            "text_content": self.text_content,
        })

    @property
    def lifecycle_digest(self) -> str:
        return canonical_digest({
            "artifact_state": self.artifact_state,
            "baseline": self.baseline,
            "experiments": self.experiments,
            "human_review": self.human_review,
            "stability": self.stability,
        })


def build_report_model(
    records: Sequence[Mapping[str, Any]],
    *,
    manifest: Mapping[str, Any] | None = None,
    recommendations: Sequence[Mapping[str, Any]] = (),
    baseline: Sequence[Mapping[str, Any]] = (),
    experiments: Sequence[Mapping[str, Any]] = (),
    stability: Mapping[str, Any] | None = None,
    pii_validator=None,
    generation_id: str | None = None,
    typed_facts: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
) -> ReportModel:
    artifacts = build_artifacts(records, pii_validator)
    artifact_state = _artifact_state(artifacts.cases)
    text_rows: list[Mapping[str, Any]] = []
    case_rows: list[Mapping[str, Any]] = []
    turn_rows: list[Mapping[str, Any]] = []
    metric_rows: list[Mapping[str, Any]] = []
    review_rows: list[Mapping[str, Any]] = []

    for case in artifacts.cases:
        case_rows.append(_case_row(case, artifact_state))
        turns, metrics, texts, reviews = _case_details(case)
        turn_rows.extend(turns)
        metric_rows.extend(metrics)
        text_rows.extend(texts)
        review_rows.extend(reviews)

    metric_rows.extend(_aggregate_metric_rows(records))

    normalized_manifest = dict(manifest or {})
    if typed_facts:
        normalized_manifest["typed_facts"] = {
            str(kind): [dict(fact) for fact in facts]
            for kind, facts in sorted(typed_facts.items())
        }
    overview = _overview_rows(artifacts.cases, metric_rows, artifact_state, baseline, experiments, stability)
    if typed_facts:
        overview.extend(
            {
                "section": "Evidence facts",
                "metric": str(kind),
                "value": len(facts),
                "status": "AVAILABLE" if facts else "UNAVAILABLE",
                "interpretation": "Typed normalized facts; inspect metadata for identities and evidence references.",
            }
            for kind, facts in sorted(typed_facts.items())
        )
    stability_rows = _flatten_optional(stability, "stability") if stability else ()
    return ReportModel(
        schema_version=SCHEMA_VERSION,
        generation_id=generation_id or str(uuid4()),
        artifact_state=artifact_state,
        manifest=normalized_manifest,
        overview=tuple(overview),
        cases=tuple(case_rows),
        turns=tuple(turn_rows),
        metrics=tuple(metric_rows),
        baseline=tuple(dict(row) for row in baseline),
        experiments=tuple(dict(row) for row in experiments),
        human_review=tuple(review_rows),
        stability=tuple(stability_rows),
        text_content=tuple(text_rows),
        recommendations=tuple(dict(item) for item in recommendations),
        source_records=tuple(dict(record) for record in records),
    )


def build_model_from_rows(
    *,
    manifest: Mapping[str, Any],
    artifact_state: str,
    cases: Sequence[Mapping[str, Any]],
    turns: Sequence[Mapping[str, Any]],
    metrics: Sequence[Mapping[str, Any]],
    baseline: Sequence[Mapping[str, Any]] = (),
    experiments: Sequence[Mapping[str, Any]] = (),
    human_review: Sequence[Mapping[str, Any]] = (),
    stability: Sequence[Mapping[str, Any]] = (),
    text_content: Sequence[Mapping[str, Any]] = (),
    recommendations: Sequence[Mapping[str, Any]] = (),
    generation_id: str | None = None,
) -> ReportModel:
    """Rebuild a trusted lifecycle generation from validated workbook rows."""
    case_rows = tuple(dict(row) for row in cases)
    metric_rows = tuple(dict(row) for row in metrics)
    return ReportModel(
        schema_version=SCHEMA_VERSION,
        generation_id=generation_id or str(uuid4()),
        artifact_state=artifact_state,
        manifest=dict(manifest),
        overview=tuple(_overview_from_rows(case_rows, metric_rows, artifact_state, baseline, experiments, stability)),
        cases=case_rows,
        turns=tuple(dict(row) for row in turns),
        metrics=metric_rows,
        baseline=tuple(dict(row) for row in baseline),
        experiments=tuple(dict(row) for row in experiments),
        human_review=tuple(dict(row) for row in human_review),
        stability=tuple(dict(row) for row in stability),
        text_content=tuple(dict(row) for row in text_content),
        recommendations=tuple(dict(row) for row in recommendations),
    )


def _artifact_state(cases: Sequence[CaseArtifact]) -> str:
    statuses = {str(case.review.get("status", "")).upper() for case in cases}
    case_statuses = {case.status.upper() for case in cases}
    if "NEEDS_ADJUDICATION" in statuses or "NEEDS_ADJUDICATION" in case_statuses:
        return "NEEDS_ADJUDICATION"
    if "NEEDS_REVIEW" in statuses or "NEEDS_REVIEW" in case_statuses:
        return "PENDING_REVIEW"
    return "FINAL"


def _case_row(case: CaseArtifact, artifact_state: str) -> Mapping[str, Any]:
    human = _mapping(case.review.get("human_review"))
    adjudication = _mapping(case.review.get("adjudication"))
    automatic = _number(case.quality.get("weighted_total"))
    human_score = _number(human.get("weighted_total"))
    final_score = human_score if human_score is not None else automatic
    if artifact_state == "NEEDS_ADJUDICATION":
        final_score = None
    performance = _mapping(case.performance)
    return {
        "component_run_id": "subject",
        "case_id": case.case_id,
        "comparison_key": canonical_digest({"case_id": case.case_id, "conversation": case.conversation}),
        "status": case.status,
        "artifact_state": artifact_state,
        "automatic_score": automatic,
        "human_score": human_score,
        "final_score": final_score,
        "final_source": "human" if human_score is not None else "automatic",
        "hard_gate_passed": case.safety.get("hard_gate_passed"),
        "review_status": case.review.get("status", "NOT_REQUIRED"),
        "adjudication_status": adjudication.get("status", "NOT_REQUIRED"),
        "failure_stage": case.failure.get("primary_stage"),
        "cohorts": _joined(case.cohorts),
        "total_ms": _number(performance.get("total_ms") or performance.get("latency_ms")),
        "evidence_refs": "; ".join(case.evidence_refs),
    }


def _case_details(case: CaseArtifact):
    conversation = _mapping(case.conversation)
    conversation_turns = {int(item.get("turn", index)): item for index, item in enumerate(_sequence(conversation.get("turns")), 1) if isinstance(item, Mapping)}
    pipeline_turns = list(_sequence(case.pipeline.get("turns")))
    traces = {int(item.get("turn", index)): item for index, item in enumerate(_sequence(case.pipeline.get("turn_traces")), 1) if isinstance(item, Mapping)}
    audits = list(_sequence(case.review.get("judge_audit")))
    review_statuses = list(_sequence(case.review.get("per_turn")))
    count = max([0, *conversation_turns.keys(), len(pipeline_turns), len(audits), len(review_statuses)])
    turn_rows, metric_rows, text_rows, review_rows = [], [], [], []
    for turn in range(1, count + 1):
        transcript = _mapping(conversation_turns.get(turn))
        trace_row = _mapping(traces.get(turn))
        trace = _mapping(trace_row.get("trace"))
        pipeline_metrics = _mapping(pipeline_turns[turn - 1]) if turn <= len(pipeline_turns) else {}
        audit = _mapping(audits[turn - 1]) if turn <= len(audits) else {}
        user_id = f"{case.case_id}:T{turn}:user"
        assistant_id = f"{case.case_id}:T{turn}:assistant"
        text_rows.extend(_text_chunks(user_id, case.case_id, turn, "user_input", str(transcript.get("user_input", ""))))
        text_rows.extend(_text_chunks(assistant_id, case.case_id, turn, "assistant_response", str(transcript.get("assistant_response", ""))))
        primary = _mapping(audit.get("primary"))
        dimension_values = [_number(item.get("score")) for item in _sequence(primary.get("dimensions")) if isinstance(item, Mapping)]
        auto_turn_score = mean([item for item in dimension_values if item is not None]) if any(item is not None for item in dimension_values) else None
        route = _mapping(trace.get("route"))
        ground = _mapping(trace.get("ground"))
        safety = _mapping(trace.get("safety"))
        timings = _mapping(trace.get("timings"))
        review_status = review_statuses[turn - 1] if turn <= len(review_statuses) else "NOT_REQUIRED"
        comparison_key = canonical_digest({"case_id": case.case_id, "turn": turn, "user": transcript.get("user_input")})
        turn_rows.append({
            "component_run_id": "subject", "case_id": case.case_id, "turn": turn,
            "comparison_key": comparison_key, "status": "COMPLETED" if transcript else "NOT_RUN",
            "user_text_id": user_id, "assistant_text_id": assistant_id,
            "route_id": route.get("id"), "safety_level": safety.get("level"),
            "ground_refs": _joined(ground.get("resolved_refs") or ground.get("resolved_ground")),
            "response_sha256": trace_row.get("response_sha256"),
            "total_ms": _number(timings.get("total_ms")), "ttft_ms": _number(timings.get("ttft_ms")),
            "review_status": review_status, "automatic_score": auto_turn_score,
            "human_score": None, "final_score": auto_turn_score, "final_source": "automatic",
        })
        metric_rows.extend(_turn_metrics(case.case_id, turn, comparison_key, pipeline_metrics, audit))
        if str(review_status).upper() == "NEEDS_REVIEW":
            review_rows.append({
                "review_id": "", "case_id": case.case_id, "turn": turn,
                "response_sha256": trace_row.get("response_sha256"), "status": "PENDING_REVIEW",
                "trigger": "; ".join(str(item) for item in _sequence(audit.get("reconciliation_reasons"))),
                "reviewer_id": "", "submitted_at": "", "confidence": "", "notes": "",
            })
    return turn_rows, metric_rows, text_rows, review_rows


def _turn_metrics(case_id: str, turn: int, turn_key: str, pipeline_metrics: Mapping[str, Any], audit: Mapping[str, Any]):
    rows = []
    for metric_id, payload in pipeline_metrics.items():
        values = _mapping(payload)
        score = _number(values.get("score"))
        rows.append(_metric_row(case_id, turn, turn_key, str(metric_id), "deterministic", score, values.get("status", "UNAVAILABLE"), values.get("reason"), values.get("evidence_refs"), "automatic"))
    primary = _mapping(audit.get("primary"))
    for item in _sequence(primary.get("dimensions")):
        if not isinstance(item, Mapping):
            continue
        module = str(item.get("module", "unknown"))
        rows.append(_metric_row(case_id, turn, turn_key, f"judge:{module}", module, _number(item.get("score")), "AVAILABLE", item.get("deduction_reason"), item.get("supporting_evidence"), "automatic"))
    for item in _sequence(primary.get("red_lines")):
        if not isinstance(item, Mapping):
            continue
        red_line_id = str(item.get("id", "unknown"))
        triggered = item.get("triggered")
        score = 1.0 if triggered is True else 0.0 if triggered is False else None
        rows.append(_metric_row(case_id, turn, turn_key, f"judge:red_line:{red_line_id}", "safety_red_line", score, "AVAILABLE" if score is not None else "UNAVAILABLE", "", item.get("evidence"), "automatic"))
    return rows


def _metric_row(case_id, turn, turn_key, metric_id, dimension, score, status, reason, evidence, source):
    comparison_key = canonical_digest({"turn_key": turn_key, "metric_id": metric_id, "source": source})
    return {
        "row_key": f"subject:{case_id}:T{turn}:{metric_id}:{source}", "comparison_key": comparison_key,
        "component_run_id": "subject", "case_id": case_id, "turn": turn,
        "metric_id": metric_id, "dimension": dimension, "raw_score": score,
        "normalized_score": score, "weight": None, "contribution": None,
        "status": str(status).upper(), "reason": _reason_zh(reason),
        "evidence_refs": _joined(evidence), "score_source": source,
        "baseline_value": None, "delta": None,
    }


def _text_chunks(text_id: str, case_id: str, turn: int, role: str, text: str):
    encoded_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    chunks = [text[index:index + TEXT_CHUNK_SIZE] for index in range(0, len(text), TEXT_CHUNK_SIZE)] or [""]
    return [{
        "text_id": text_id, "case_id": case_id, "turn": turn, "role": role,
        "chunk_index": index, "chunk_count": len(chunks), "text_sha256": encoded_hash,
        "content": chunk,
    } for index, chunk in enumerate(chunks, 1)]


def _overview_rows(cases, metric_rows, state, baseline, experiments, stability):
    scores = [_number(case.quality.get("weighted_total")) for case in cases]
    scores = [score for score in scores if score is not None]
    latencies = [_number(case.performance.get("total_ms") or case.performance.get("latency_ms")) for case in cases]
    latencies = [item for item in latencies if item is not None]
    statuses = [case.status.upper() for case in cases]
    rows = [
        {"section": "Result", "metric": "Artifact state", "value": state, "status": state, "interpretation": "Lifecycle state of this workbook."},
        {"section": "Result", "metric": "Evaluation verdict", "value": "PASS" if statuses and all(item == "PASS" for item in statuses) else "FAIL", "status": "AVAILABLE", "interpretation": "Quality verdict; speed is reported separately."},
        {"section": "Quality", "metric": "Overall score", "value": mean(scores) if scores else None, "status": "AVAILABLE" if scores else "UNAVAILABLE", "interpretation": "Mean case weighted score on the rating-rule scale."},
        {"section": "Quality", "metric": "Pass rate", "value": statuses.count("PASS") / len(statuses) if statuses else None, "status": "AVAILABLE" if statuses else "UNAVAILABLE", "interpretation": "Share of cases with PASS status."},
        {"section": "Coverage", "metric": "Cases", "value": len(cases), "status": "AVAILABLE", "interpretation": "Number of subject cases."},
        {"section": "Coverage", "metric": "Metric rows", "value": len(metric_rows), "status": "AVAILABLE", "interpretation": "Number of turn-level metric facts."},
        {"section": "Performance", "metric": "Mean total latency (ms)", "value": mean(latencies) if latencies else None, "status": "AVAILABLE" if latencies else "UNAVAILABLE", "interpretation": "Mean over cases with telemetry; missing values are excluded."},
        {"section": "Baseline", "metric": "Comparison", "value": "ATTACHED" if baseline else "NOT_RUN", "status": "AVAILABLE" if baseline else "NOT_RUN", "interpretation": "Baseline deltas are shown only when comparison is attached."},
        {"section": "Experiment", "metric": "Result", "value": "ATTACHED" if experiments else "NOT_RUN", "status": "AVAILABLE" if experiments else "NOT_RUN", "interpretation": "Recommendations remain hypotheses without controlled evidence."},
        {"section": "Stability", "metric": "Classification", "value": (stability or {}).get("classification", "NOT_MEASURED"), "status": "AVAILABLE" if stability else "NOT_RUN", "interpretation": "Repeatability only; a stable wrong answer is still wrong."},
    ]
    dimensions: dict[str, list[float]] = {}
    for row in metric_rows:
        if str(row.get("metric_id", "")).startswith("judge:") and _number(row.get("raw_score")) is not None:
            dimensions.setdefault(str(row["dimension"]), []).append(float(row["raw_score"]))
    rows.extend({"section": "Dimension", "metric": name, "value": mean(values), "status": "AVAILABLE", "interpretation": "Mean automatic judge score across evaluated turns."} for name, values in sorted(dimensions.items()))
    rows.extend(_decision_overview_rows(cases, metric_rows))
    return rows


def _flatten_optional(value: Mapping[str, Any], prefix: str):
    rows = []
    for key, item in sorted(value.items()):
        rows.append({"section": prefix, "metric": key, "value": _canonical(item) if isinstance(item, (Mapping, list, tuple)) else item, "status": "AVAILABLE" if item is not None else "UNAVAILABLE"})
    return tuple(rows)


def _aggregate_metric_rows(records: Sequence[Mapping[str, Any]]):
    rows = []
    for namespace, summary in (("rag", summarize_rag(records)), ("v3", summarize_v3(records))):
        for path, value in _scalar_leaves(summary):
            metric_id = f"{namespace}:{path}"
            score = _number(value)
            status = "UNAVAILABLE" if value is None else "AVAILABLE"
            row = _metric_row(
                "__RUN__", 0, "run", metric_id, namespace, score, status,
                "" if score is not None or value is None else str(value), (), "automatic",
            )
            row["row_key"] = f"subject:run:{metric_id}:automatic"
            rows.append(row)
    return rows


def _scalar_leaves(value: Any, prefix: str = ""):
    if isinstance(value, Mapping):
        for key, item in sorted(value.items()):
            path = f"{prefix}.{key}" if prefix else str(key)
            yield from _scalar_leaves(item, path)
        return
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return
    yield prefix, value


def _overview_from_rows(cases, metrics, state, baseline, experiments, stability):
    scores = [_number(row.get("final_score")) for row in cases]
    scores = [value for value in scores if value is not None]
    statuses = [str(row.get("status", "UNKNOWN")).upper() for row in cases]
    latencies = [_number(row.get("total_ms")) for row in cases]
    latencies = [value for value in latencies if value is not None]
    rows = [
        {"section": "Result", "metric": "Artifact state", "value": state, "status": state, "interpretation": "Lifecycle state of this workbook."},
        {"section": "Result", "metric": "Evaluation verdict", "value": "PASS" if statuses and all(value == "PASS" for value in statuses) else "FAIL", "status": "AVAILABLE", "interpretation": "Quality verdict; speed is reported separately."},
        {"section": "Quality", "metric": "Overall score", "value": mean(scores) if scores else None, "status": "AVAILABLE" if scores else "UNAVAILABLE", "interpretation": "Mean available final case score."},
        {"section": "Quality", "metric": "Pass rate", "value": statuses.count("PASS") / len(statuses) if statuses else None, "status": "AVAILABLE" if statuses else "UNAVAILABLE", "interpretation": "Share of cases with PASS status."},
        {"section": "Coverage", "metric": "Cases", "value": len(cases), "status": "AVAILABLE", "interpretation": "Number of subject cases."},
        {"section": "Coverage", "metric": "Metric rows", "value": len(metrics), "status": "AVAILABLE", "interpretation": "Number of metric facts including score-source rows."},
        {"section": "Performance", "metric": "Mean total latency (ms)", "value": mean(latencies) if latencies else None, "status": "AVAILABLE" if latencies else "UNAVAILABLE", "interpretation": "Mean over cases with telemetry."},
        {"section": "Baseline", "metric": "Comparison", "value": "ATTACHED" if baseline else "NOT_RUN", "status": "AVAILABLE" if baseline else "NOT_RUN", "interpretation": "Baseline evidence attachment state."},
        {"section": "Experiment", "metric": "Result", "value": "ATTACHED" if experiments else "NOT_RUN", "status": "AVAILABLE" if experiments else "NOT_RUN", "interpretation": "Controlled experiment attachment state."},
        {"section": "Stability", "metric": "Classification", "value": "ATTACHED" if stability else "NOT_MEASURED", "status": "AVAILABLE" if stability else "NOT_RUN", "interpretation": "Repeatability only; correctness remains separate."},
    ]
    dimensions: dict[str, list[float]] = {}
    for row in metrics:
        metric_id = str(row.get("metric_id", ""))
        value = _number(row.get("raw_score"))
        if metric_id.startswith("judge:") and ":red_line:" not in metric_id and value is not None and row.get("score_source") in {"automatic", "human", "adjudicated"}:
            dimensions.setdefault(str(row.get("dimension", "unknown")), []).append(value)
    rows.extend({"section": "Dimension", "metric": key, "value": mean(values), "status": "AVAILABLE", "interpretation": "Mean recorded judge score."} for key, values in sorted(dimensions.items()))
    rows.extend(_decision_overview_rows(cases, metrics))
    return rows


def _decision_overview_rows(cases, metrics):
    """Add scan-friendly decision metrics without changing scoring semantics."""
    by_id: dict[str, list[float]] = {}
    for row in metrics:
        value = _number(row.get("raw_score"))
        if value is not None:
            by_id.setdefault(str(row.get("metric_id")), []).append(value)

    def aggregate(metric_id: str):
        values = by_id.get(metric_id, [])
        return (mean(values), "AVAILABLE") if values else (None, "UNAVAILABLE")

    route_acceptance, route_status = aggregate("route_acceptance")
    route_preference, preference_status = aggregate("route_preference")
    capsule_alignment, capsule_status = aggregate("v3:capsule_attribution.claim_alignment")
    semantic_support, semantic_status = aggregate("v3:semantic_attribution.overall_rate")
    return [
        {"section": "Decision", "metric": "Router accepted accuracy", "value": route_acceptance, "status": route_status, "interpretation": "Actual route falls within the reviewed accepted route set; inspect 03_Metrics for case/turn evidence."},
        {"section": "Decision", "metric": "Router preferred accuracy", "value": route_preference, "status": preference_status, "interpretation": "Actual route equals the reviewed preferred route; use this to assess crisis_sop/baseline/capsule routing."},
        {"section": "Decision", "metric": "Capsule claim alignment", "value": capsule_alignment, "status": capsule_status, "interpretation": "Judge claims with valid injected Capsule evidence; observational, not causal proof."},
        {"section": "Decision", "metric": "Overall claim support rate", "value": semantic_support, "status": semantic_status, "interpretation": "Semantic attribution support across substantive claims; inspect layer support for Capsule/Ground detail."},
    ]
