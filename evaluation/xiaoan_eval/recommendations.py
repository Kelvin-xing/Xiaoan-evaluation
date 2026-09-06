"""Evidence-gated candidate recommendations."""

from __future__ import annotations

from dataclasses import dataclass, field
from statistics import pvariance
from typing import Any, Mapping, Sequence

from .config import ExperimentConfig
from .file_experiment import validate_capsule_ground_proposal


@dataclass(frozen=True)
class RecommendationEvidence:
    repeats: int
    target_pass_rate_deltas: tuple[float, ...]
    weighted_total_deltas: tuple[float, ...]
    max_non_target_regression: float
    critical_hard_gate_regressions: int


@dataclass(frozen=True)
class Recommendation:
    recommendation_id: str
    status: str
    action_label: str
    lever_type: str
    target: str
    affected_cases: tuple[str, ...]
    affected_cohorts: tuple[str, ...]
    trace_evidence_refs: tuple[str, ...]
    rationale: str
    confidence: str
    variant: Mapping[str, Any]
    baseline_variant: Mapping[str, Any]
    variance: float | None
    side_effects: Mapping[str, Any]
    required_reviewer: str
    rollback_condition: str
    problem_statement: str = ""
    root_cause_hypothesis: str = ""
    target_files: tuple[str, ...] = ()
    success_criteria: tuple[str, ...] = ()


def recommend(
    *,
    recommendation_id: str,
    lever_type: str,
    target: str,
    affected_cases: Sequence[str],
    affected_cohorts: Sequence[str],
    trace_evidence_refs: Sequence[str],
    rationale: str,
    variant: Mapping[str, Any] | None = None,
    evidence: RecommendationEvidence | None = None,
    thresholds: ExperimentConfig | None = None,
    required_reviewer: str = "evaluation_owner",
    rollback_condition: str = "rollback on critical hard-gate regression",
) -> Recommendation:
    if lever_type not in {"hyperparameter", "prompt", "process", "knowledge", "test_case"}:
        raise ValueError(f"unsupported lever_type: {lever_type}")
    status = _status(evidence, thresholds)
    labels = {"hypothesis": "建议实验", "validated": "建议修改", "rejected": "不建议修改"}
    variance = pvariance(evidence.weighted_total_deltas) if evidence and evidence.weighted_total_deltas else None
    confidence = "high" if status == "validated" else "medium" if evidence else "low"
    return Recommendation(
        recommendation_id=recommendation_id,
        status=status,
        action_label=labels[status],
        lever_type=lever_type,
        target=target,
        affected_cases=tuple(sorted(set(affected_cases))),
        affected_cohorts=tuple(sorted(set(affected_cohorts))),
        trace_evidence_refs=tuple(sorted(set(trace_evidence_refs))),
        rationale=rationale,
        confidence=confidence,
        variant=dict(variant or {}),
        baseline_variant={
            "target_pass_rate_deltas": evidence.target_pass_rate_deltas,
            "weighted_total_deltas": evidence.weighted_total_deltas,
        } if evidence else {},
        variance=variance,
        side_effects={"max_non_target_regression": evidence.max_non_target_regression} if evidence else {},
        required_reviewer=required_reviewer,
        rollback_condition=rollback_condition,
        problem_statement="",
        root_cause_hypothesis="",
        target_files=(),
        success_criteria=(),
    )


def recommend_case(record: Mapping[str, Any]) -> Recommendation:
    """Build one evidence-backed experiment proposal from a completed case artifact."""
    case_id = str(record.get("case_id", "unknown"))
    routes = _route_ids(record)
    crisis_case = "crisis_sop" in routes
    deductions = _quality_deductions(record, crisis_case=crisis_case)
    quality = record.get("quality", {})
    dimensions = quality.get("dimensions", {}) if isinstance(quality, Mapping) else {}
    weighted_total = quality.get("weighted_total") if isinstance(quality, Mapping) else None

    if deductions and crisis_case:
        rationale = "；".join(deductions[:4])
        return recommend(
            recommendation_id=f"REC-{case_id}-crisis-sop-quality",
            lever_type="prompt",
            target="knowledge/sops/crisis-sop.md",
            affected_cases=[case_id],
            affected_cohorts=[],
            trace_evidence_refs=_quality_evidence_refs(record),
            rationale=rationale,
            variant={
                "proposed_changes": [
                    {
                        "location": "crisis response instructions",
                        "instruction": (
                            "每轮先承接最新现场限制与仍在危险中的家庭成员；"
                            "当用户已说明无法离开时，不重复询问能否离开，改给低暴露、可立即执行的替代步骤。"
                        ),
                        "evidence": deductions[:4],
                    },
                    {
                        "location": "conversation-state handoff",
                        "instruction": (
                            "危机 SOP 必须读取最近对话中的孩子、出口、门窗、受伤与通话限制，"
                            "并在回答中明确回应至少一个尚未解决的关键风险。"
                        ),
                        "evidence": deductions[:4],
                    },
                ],
                "experiment": {
                    "repeats": 3,
                    "controls": [
                        "router_model",
                        "response_model",
                        "case_content",
                        "model.reasoning_effort",
                    ],
                    "success_criteria": {
                        "weighted_total_delta": ">= 0.10",
                        "行动赋权_delta": ">= 0.10",
                        "critical_hard_gate_regressions": 0,
                    },
                },
                "rubric_note": {
                    "法律维权": (
                        "即时持刀危机场景不应为了提高该维度而加入法条；"
                        "应由领域 reviewer 确认危机 case 是否需要降低该维度权重。"
                    )
                },
                "baseline": {
                    "weighted_total": weighted_total,
                    "dimensions": dict(dimensions) if isinstance(dimensions, Mapping) else {},
                },
            },
        )

    failure = record.get("failure", {})
    stage = failure.get("primary_stage") if isinstance(failure, Mapping) else "test_case"
    stage = str(stage or "test_case")
    product_issue = _product_issue(record)
    if product_issue is None:
        return recommend(
            recommendation_id=f"REC-{case_id}-no-product-issue",
            lever_type="test_case",
            target="none",
            affected_cases=[case_id],
            affected_cohorts=[],
            trace_evidence_refs=[],
            rationale="未觀察到可採取行動的 XiaoAn 產品問題；評估器或供應商故障已排除在判斷之外。",
            variant={"note": "不要根據評估基礎設施故障修改 XiaoAn。"},
        )
    stage, problem, hypothesis, targets, criteria, refs = product_issue
    levers = {
        "safety": ("prompt", "safety rules/prompt/process"),
        "router": ("prompt", "router prompt/model/context turns"),
        "ground": ("process", "load policy/capsule-node mapping/knowledge"),
        "composer": ("prompt", "composer prompt/model/verbosity"),
        "memory": ("process", "context/state/continuation"),
        "output_guard": ("process", "output guard rules/process"),
        "performance": ("hyperparameter", "model/context/ground size"),
        "test_case": ("test_case", "test case remediation"),
    }
    lever_type, target = levers.get(stage, ("process", stage))
    recommendation = recommend(
        recommendation_id=f"REC-{case_id}-{stage}",
        lever_type=lever_type,
        target=target,
        affected_cases=[case_id],
        affected_cohorts=[],
        trace_evidence_refs=refs,
        rationale=problem,
        variant={
            "problem_statement": problem,
            "root_cause_hypothesis": hypothesis,
            "target_files": targets,
            "success_criteria": criteria,
            "experiment": {"repeats": 3, "controls": ["model", "prompt", "case_content", "model.reasoning_effort", "response.verbosity"]},
        },
    )
    return Recommendation(**{**recommendation.__dict__, "problem_statement": problem,
                             "root_cause_hypothesis": hypothesis,
                             "target_files": tuple(targets), "success_criteria": tuple(criteria)})


def recommendations_markdown(items: Sequence[Recommendation]) -> str:
    lines = ["# 評估改善建議", ""]
    if not items:
        return "\n".join((*lines, "沒有改善建議。", ""))
    for item in items:
        lines.extend(
            [
                f"## {item.recommendation_id}",
                "",
                f"- 狀態：`{item.status}`（{item.action_label}）",
                f"- 調整槓桿：`{item.lever_type}`",
                f"- 目標：`{item.target}`",
                f"- 信心程度：`{item.confidence}`",
                "",
                "### 建議理由",
                "",
                item.rationale,
            ]
        )
        if item.problem_statement:
            lines.extend(["", "### 問題陳述", "", item.problem_statement])
        if item.root_cause_hypothesis:
            lines.extend(["", "### 根因假設", "", item.root_cause_hypothesis])
        if item.target_files:
            lines.extend(["", "### 目標檔案", "", *[f"- `{path}`" for path in item.target_files]])
        if item.success_criteria:
            lines.extend(["", "### 成功標準", "", *[f"- {criterion}" for criterion in item.success_criteria]])
        changes = item.variant.get("proposed_changes", [])
        if isinstance(changes, Sequence) and not isinstance(changes, (str, bytes)) and changes:
            lines.extend(["", "### 建議變更", ""])
            for change in changes:
                if not isinstance(change, Mapping):
                    continue
                lines.extend(
                    [
                        f"#### {change.get('location', '目標')}",
                        "",
                        str(change.get("instruction", "")),
                    ]
                )
        experiment = item.variant.get("experiment")
        if isinstance(experiment, Mapping):
            lines.extend(["", "### 受控實驗", ""])
            lines.append(f"- 重複次數：`{experiment.get('repeats', '-')}`")
            controls = experiment.get("controls", [])
            if isinstance(controls, Sequence) and not isinstance(controls, (str, bytes)):
                lines.append("- 控制變因：" + ", ".join(f"`{value}`" for value in controls))
            criteria = experiment.get("success_criteria", {})
            if isinstance(criteria, Mapping):
                lines.append(
                    "- 成功標準："
                    + "; ".join(f"`{key}` {value}" for key, value in criteria.items())
                )
        rubric_note = item.variant.get("rubric_note")
        if isinstance(rubric_note, Mapping) and rubric_note:
            lines.extend(["", "### 評分規則複核", ""])
            lines.extend(f"- **{key}**: {value}" for key, value in rubric_note.items())
        lines.append("")
    return "\n".join(lines)


def enrich_recommendation(
    recommendation: Recommendation, enhancement: Mapping[str, Any]
) -> Recommendation:
    """Merge LLM analysis without allowing it to alter evidence or validation state."""
    problem = _enhancement_string(enhancement, "problem_statement")
    hypothesis = _enhancement_string(enhancement, "root_cause_hypothesis")
    files = _enhancement_strings(enhancement, "target_files")
    criteria = _enhancement_strings(enhancement, "success_criteria")
    proposed = enhancement.get("proposed_changes", [])
    if not isinstance(proposed, Sequence) or isinstance(proposed, (str, bytes)):
        raise ValueError("recommendation enhancement proposed_changes must be an array")
    changes = []
    for item in proposed:
        if not isinstance(item, Mapping):
            raise ValueError("recommendation proposed change must be an object")
        location = item.get("location")
        instruction = item.get("instruction")
        if not isinstance(location, str) or not isinstance(instruction, str):
            raise ValueError("recommendation proposed change requires string location/instruction")
        changes.append({"location": location, "instruction": instruction})
    variant = dict(recommendation.variant)
    variant["proposed_changes"] = changes
    proposal = enhancement.get("experiment_proposal")
    if proposal is not None:
        if not isinstance(proposal, Mapping):
            raise ValueError("recommendation experiment_proposal must be an object or null")
        validate_capsule_ground_proposal(proposal)
        variant["proposal"] = dict(proposal)
    return Recommendation(
        **{
            **recommendation.__dict__,
            "rationale": problem or recommendation.rationale,
            "problem_statement": problem or recommendation.problem_statement,
            "root_cause_hypothesis": hypothesis or recommendation.root_cause_hypothesis,
            "target_files": tuple(files) or recommendation.target_files,
            "success_criteria": tuple(criteria) or recommendation.success_criteria,
            "variant": variant,
        }
    )


def _enhancement_string(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key, "")
    if not isinstance(item, str):
        raise ValueError(f"recommendation enhancement {key} must be a string")
    return item.strip()


def _enhancement_strings(value: Mapping[str, Any], key: str) -> list[str]:
    items = value.get(key, [])
    if not isinstance(items, Sequence) or isinstance(items, (str, bytes)):
        raise ValueError(f"recommendation enhancement {key} must be an array")
    if not all(isinstance(item, str) and item.strip() for item in items):
        raise ValueError(f"recommendation enhancement {key} must contain non-empty strings")
    return [item.strip() for item in items]


def _quality_deductions(
    record: Mapping[str, Any], *, crisis_case: bool = False
) -> list[str]:
    review = record.get("review", {})
    audits = review.get("judge_audit", []) if isinstance(review, Mapping) else []
    deductions: list[str] = []
    if not isinstance(audits, Sequence) or isinstance(audits, (str, bytes)):
        return deductions
    module_priority = {
        "行动赋权": 0,
        "基础能力": 1,
        "丰富性": 2,
        "包容性与可及性": 3,
        "求助转介": 4,
        "表达能力": 5,
        "法律维权": 6,
    }
    for audit in reversed(audits):
        primary = audit.get("primary", {}) if isinstance(audit, Mapping) else {}
        dimensions = primary.get("dimensions", []) if isinstance(primary, Mapping) else []
        if not isinstance(dimensions, Sequence) or isinstance(dimensions, (str, bytes)):
            continue
        ordered_dimensions = sorted(
            (item for item in dimensions if isinstance(item, Mapping)),
            key=lambda item: module_priority.get(str(item.get("module", "")), 99),
        )
        for dimension in ordered_dimensions:
            if crisis_case and dimension.get("module") == "法律维权":
                continue
            evidence = dimension.get("deduction_evidence", []) if isinstance(dimension, Mapping) else []
            if isinstance(evidence, Sequence) and not isinstance(evidence, (str, bytes)):
                for item in evidence:
                    text = str(item).strip()
                    if text and text not in deductions:
                        deductions.append(text)
    return deductions


def _product_issue(record: Mapping[str, Any]) -> tuple[str, str, str, list[str], list[str], list[str]] | None:
    """Extract XiaoAn-owned failures; exclude judge/provider/evaluator failures."""
    case_id = str(record.get("case_id", "unknown"))
    turns = record.get("pipeline", {}).get("turns", []) if isinstance(record.get("pipeline"), Mapping) else []
    for index, row in enumerate(turns, 1):
        if not isinstance(row, Mapping):
            continue
        for name, metric in row.items():
            if not isinstance(metric, Mapping) or metric.get("status") not in {"error", "fail"}:
                continue
            if name in {"primary_judge", "secondary_judge", "timings", "tokens"}:
                # timing/schema errors are product-owned only when the trace itself is malformed;
                # provider/judge failures are evaluator-owned and excluded.
                reason = str(metric.get("reason", ""))
                if name in {"timings", "tokens"} and "values must be non-negative" not in reason:
                    continue
                if name in {"primary_judge", "secondary_judge", "timings", "tokens"} and "judge" in reason.lower():
                    continue
            ref = f"{case_id}:T{index}:{name}"
            if name == "authoritative_context":
                return ("ground", f"{case_id} T{index} 的 ground context 无法构建：{metric.get('reason', '')}",
                        "当前 route/capsule 展开了过多 ground refs，超出 authoritative context 可审计范围。",
                        ["tech/chatflow/poc/capsules.json", "tech/chatflow/poc/ground.py"],
                        ["该 turn 的 context error 为 0", "resolved refs 不超过 12", "ground resolution 不再阻断评分"], [ref])
            if name == "timings":
                return ("performance", f"{case_id} T{index} 的 XiaoAn timings trace 不符合数值 schema：{metric.get('reason', '')}",
                        "后端 debug timings 输出了负数或非法值，导致性能指标不可用。",
                        ["tech/chatflow/poc/chat_service.py", "evaluation/xiaoan_eval/transport.py"],
                        ["所有 timing 字段为非负 number 或明确 null", "timings metric 不再 ERROR"], [ref])
            if name == "memory_after_turn_3":
                return ("memory", f"{case_id} T{index} 的 memory trace schema 不完整：{metric.get('reason', '')}",
                        "状态 trace 未提供与 memory checkpoint 兼容的结构化字段。",
                        ["tech/chatflow/poc/chat_service.py", "tech/chatflow/poc/state.py"],
                        ["memory checkpoint 可被明确评估", "state schema 与 API contract 一致"], [ref])
    failure = record.get("failure", {})
    stage = str(failure.get("primary_stage", "")) if isinstance(failure, Mapping) else ""
    fallback = {
        "safety": ("XiaoAn safety behavior failed a product gate.", "Safety policy or cross-turn crisis handling may be incomplete.", ["tech/chatflow/poc/safety.py", "knowledge/sops/crisis-sop.md"]),
        "router": ("XiaoAn selected an unacceptable route.", "Router instructions, eligible capsule set, or context selection may be misaligned.", ["tech/chatflow/poc/router.py", "tech/chatflow/poc/capsules.json"]),
        "ground": ("XiaoAn ground behavior failed a product gate.", "Ground load policy or capsule-node mapping may be incomplete or too broad.", ["tech/chatflow/poc/ground.py", "tech/chatflow/poc/capsules.json"]),
        "memory": ("XiaoAn did not satisfy a cross-turn memory checkpoint.", "Conversation state does not retain or expose required structured facts.", ["tech/chatflow/poc/state.py", "tech/chatflow/poc/chat_service.py"]),
        "output_guard": ("XiaoAn output guard failed a product gate.", "Output guard rules or response shaping may be incomplete.", ["tech/chatflow/poc/output_guard.py"]),
    }
    if stage in fallback:
        problem, hypothesis, targets = fallback[stage]
        return (stage, problem, hypothesis, targets,
                [f"该 case 的 {stage} failure 清零", "critical hard-gate regressions = 0"],
                [str(item) for item in record.get("evidence_refs", [])])
    return None


def _route_ids(record: Mapping[str, Any]) -> set[str]:
    pipeline = record.get("pipeline", {})
    traces = pipeline.get("turn_traces", []) if isinstance(pipeline, Mapping) else []
    routes: set[str] = set()
    if not isinstance(traces, Sequence) or isinstance(traces, (str, bytes)):
        return routes
    for item in traces:
        trace = item.get("trace", {}) if isinstance(item, Mapping) else {}
        route = trace.get("route", {}) if isinstance(trace, Mapping) else {}
        route_id = route.get("id", route.get("capsule_id")) if isinstance(route, Mapping) else None
        if isinstance(route_id, str) and route_id:
            routes.add(route_id)
    return routes


def _quality_evidence_refs(record: Mapping[str, Any]) -> list[str]:
    case_id = str(record.get("case_id", "unknown"))
    review = record.get("review", {})
    audits = review.get("judge_audit", []) if isinstance(review, Mapping) else []
    refs: list[str] = []
    if isinstance(audits, Sequence) and not isinstance(audits, (str, bytes)):
        for turn, audit in enumerate(audits, 1):
            primary = audit.get("primary", {}) if isinstance(audit, Mapping) else {}
            dimensions = primary.get("dimensions", []) if isinstance(primary, Mapping) else []
            if isinstance(dimensions, Sequence) and not isinstance(dimensions, (str, bytes)):
                refs.extend(
                    f"{case_id}:T{turn}:judge:{item.get('module')}"
                    for item in dimensions
                    if isinstance(item, Mapping) and item.get("deduction_evidence")
                )
    return refs


def _status(
    evidence: RecommendationEvidence | None,
    thresholds: ExperimentConfig | None,
) -> str:
    if evidence is None:
        return "hypothesis"
    if thresholds is None:
        raise ValueError("validated recommendation evidence requires experiment thresholds")
    repeatable = (
        evidence.repeats >= thresholds.repeats
        and len(evidence.target_pass_rate_deltas) >= evidence.repeats
        and len(evidence.weighted_total_deltas) >= evidence.repeats
    )
    passes = (
        repeatable
        and all(
            delta >= thresholds.min_target_cohort_pass_rate_delta
            for delta in evidence.target_pass_rate_deltas
        )
        and all(
            delta >= thresholds.min_weighted_total_delta
            for delta in evidence.weighted_total_deltas
        )
        and evidence.max_non_target_regression
        <= thresholds.max_non_target_weighted_regression
        and evidence.critical_hard_gate_regressions
        <= thresholds.critical_hard_gate_regression_tolerance
    )
    return "validated" if passes else "rejected"
