from __future__ import annotations

from dataclasses import asdict
import hashlib
from typing import Any, Callable, Mapping, Protocol

from .cases import TestCase
from .attribution_client import AttributionClient
from .checkpoint import CheckpointWriteError
from .config import EvaluatorConfig
from .judge import JudgeResult
from .judge_client import JudgeClient
from .metrics import evaluate_hard_gates, evaluate_memory_checkpoint, evaluate_turn_metrics
from .review import (
    ReviewStatus,
    reconcile_judges,
    should_request_second_judge,
)
from .rules import MetricResult, MetricStatus, RatingRule
from .runner import CaseRunResult
from .scoring import CaseScore, TurnQuality, score_case


class EgressRejected(RuntimeError):
    pass


class CaseRunner(Protocol):
    def run_cases(self, cases: list[Mapping[str, Any]]) -> list[CaseRunResult]: ...


class EvaluationPipeline:
    def __init__(
        self,
        runner: CaseRunner,
        rating_rule: RatingRule,
        config: EvaluatorConfig,
        *,
        primary_judge: JudgeClient,
        secondary_judge: JudgeClient | None = None,
        authoritative_context_provider: Callable[[TestCase, Any, Mapping[str, Any]], Mapping[str, Any]],
        egress_validator: Callable[[Mapping[str, Any]], bool] | None = None,
        known_route_ids: frozenset[str] = frozenset({"baseline", "crisis_sop"}),
        quality_threshold: float | None = None,
        release_review: bool = False,
        attribution_client: AttributionClient | None = None,
    ) -> None:
        self._runner = runner
        self._rule = rating_rule
        self._config = config
        self._primary = primary_judge
        self._secondary = secondary_judge
        self._egress_validator = egress_validator
        self._context_provider = authoritative_context_provider
        self._known_route_ids = known_route_ids
        self._quality_threshold = quality_threshold
        self._release_review = release_review
        self._attribution = attribution_client

    def evaluate_case(self, case: TestCase) -> dict[str, Any]:
        run = self._runner.run_cases([_runner_case(case)])[0]
        metric_rows: list[dict[str, MetricResult]] = []
        qualities: list[TurnQuality] = []
        review_statuses: list[str] = []
        judge_audits: list[dict[str, Any]] = []
        turn_traces: list[dict[str, Any]] = []
        observations: list[dict[str, Any]] = []
        approved_history: list[str] = []

        for expected_turn, actual_turn in zip(case.turns, run.turns, strict=False):
            expected = expected_turn.expected
            if expected is None:
                from .cases import ExpectedOutcome

                expected = ExpectedOutcome()
            metrics = evaluate_turn_metrics(
                expected,
                actual_turn.trace,
                oracle_approved=case.oracle_gate_eligible,
            )
            response_safe = (
                self._egress_validator({"assistant_answer": actual_turn.response})
                if self._egress_validator is not None
                else None
            )
            metrics.update(
                evaluate_hard_gates(
                    actual_turn.trace,
                    response_is_pii_safe=response_safe,
                    known_route_ids=self._known_route_ids,
                )
            )
            for checkpoint in case.memory_checkpoints:
                if checkpoint.after_turn == expected_turn.turn:
                    metrics[f"memory_after_turn_{checkpoint.after_turn}"] = (
                        evaluate_memory_checkpoint(checkpoint, actual_turn.trace)
                    )
            metric_rows.append(metrics)
            observation = _turn_observation(
                expected_turn.turn,
                expected,
                actual_turn.trace,
                actual_turn.response,
                oracle_approved=case.oracle_gate_eligible,
            )
            observations.append(observation)

            turn_traces.append(
                {
                    "turn": expected_turn.turn,
                    "status": (
                        "error"
                        if any(
                            item.status is MetricStatus.ERROR
                            for name, item in metrics.items()
                            if name != "route_preference"
                        )
                        else "fail"
                        if any(
                            item.status is MetricStatus.FAIL
                            for name, item in metrics.items()
                            if name != "route_preference"
                        )
                        else "pass"
                    ),
                    "trace": actual_turn.trace,
                    "response_sha256": hashlib.sha256(
                        (actual_turn.response or "").encode("utf-8")
                    ).hexdigest(),
                    "redacted_input_sha256": (
                        hashlib.sha256(_redacted_input(actual_turn.trace).encode("utf-8")).hexdigest()
                        if _redacted_input(actual_turn.trace) is not None
                        else None
                    ),
                }
            )
            if actual_turn.error or response_safe is False:
                review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                judge_audits.append(
                    {
                        "primary": None,
                        "secondary": None,
                        "reconciliation_reasons": [
                            "execution error short-circuited judging"
                            if actual_turn.error
                            else "PII hard gate short-circuited judging"
                        ],
                    }
                )
                continue

            try:
                authoritative_context = self._context_provider(
                    case, expected_turn, actual_turn.trace
                )
            except RuntimeError as exc:
                context_error = MetricResult(
                    MetricStatus.ERROR,
                    None,
                    f"authoritative context resolution failed: {exc}",
                    (f"{case.id}:T{expected_turn.turn}:ground",),
                )
                metric_rows[-1]["authoritative_context"] = context_error
                turn_traces[-1]["status"] = "error"
                review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                judge_audits.append(
                    {
                        "primary": None,
                        "secondary": None,
                        "reconciliation_reasons": [context_error.reason],
                    }
                )
                continue

            request = {
                "schema_version": "1.0",
                "case_id": case.id,
                "turn": expected_turn.turn,
                "assistant_answer": actual_turn.response,
                "redacted_user_input": _redacted_input(actual_turn.trace),
                "redacted_conversation_history": tuple(approved_history),
                "trace": actual_turn.trace,
                "capsule_content_units": (
                    actual_turn.trace.get("capsule", {}).get("injected_units", [])
                    if isinstance(actual_turn.trace.get("capsule"), Mapping) else []
                ),
                "quality_focus": case.quality_focus,
                "expected": asdict(expected),
                "rating_rule": {
                    "schema_version": self._rule.schema_version,
                    "score_scale": [asdict(item) for item in self._rule.score_scale],
                    "red_lines": [asdict(item) for item in self._rule.red_lines],
                    "quality_rubric": [asdict(item) for item in self._rule.modules],
                },
                "authoritative_context": authoritative_context,
            }
            request["evidence_catalog"] = _evidence_catalog(request)
            if self._egress_validator is not None and not self._egress_validator(request):
                raise EgressRejected(
                    f"judge request for {case.id} turn {expected_turn.turn} failed egress validation"
                )
            redacted_input = request["redacted_user_input"]
            if isinstance(redacted_input, str):
                approved_history.append(redacted_input)
            try:
                primary = self._primary.judge(request)
            except CheckpointWriteError:
                raise
            except Exception as exc:
                judge_error = MetricResult(
                    MetricStatus.ERROR,
                    None,
                    f"primary judge unavailable: {type(exc).__name__}: {exc}",
                    (f"{case.id}:T{expected_turn.turn}:primary_judge",),
                )
                metric_rows[-1]["primary_judge"] = judge_error
                turn_traces[-1]["status"] = "error"
                review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                judge_audits.append(
                    {
                        "primary": None,
                        "secondary": None,
                        "reconciliation_reasons": [judge_error.reason],
                    }
                )
                continue
            qualities.append(
                TurnQuality(
                    {item.module: item.score for item in primary.dimensions},
                    tuple(item.id for item in primary.red_lines if item.triggered),
                )
            )
            observation["judge"] = {
                "faithfulness_claims": [asdict(item) for item in primary.faithfulness_claims],
                "legal_claims": [asdict(item) for item in primary.legal_claims],
            }
            snapshot = actual_turn.trace.get("effective_context_snapshot")
            if self._attribution is not None:
                if not isinstance(snapshot, Mapping):
                    observation["attribution"] = {
                        "status": "UNAVAILABLE",
                        "reason": "effective context snapshot is missing",
                    }
                else:
                    try:
                        attribution = self._attribution.judge(
                            actual_turn.response or "", snapshot, case_id=case.id
                        )
                        observation["attribution"] = {
                            "status": "AVAILABLE",
                            "capsule_cohort": _capsule_cohort(expected, actual_turn.trace),
                            "judge_version": attribution.judge_version,
                            "claims": [asdict(item) for item in attribution.claims],
                            "policies": [asdict(item) for item in attribution.policies],
                            "abstention_status": attribution.abstention_status,
                            "abstention_reason": attribution.abstention_reason,
                            "evidence_catalog": _snapshot_catalog(snapshot),
                        }
                        observation["parameter_contracts"] = _snapshot_parameter_contracts(snapshot)
                    except CheckpointWriteError:
                        raise
                    except Exception as exc:
                        observation["attribution"] = {
                            "status": "UNAVAILABLE",
                            "reason": f"attribution judge unavailable: {type(exc).__name__}: {exc}",
                        }
            needs_second = should_request_second_judge(
                primary,
                asdict(self._config.review),
                critical=_is_critical(case),
                quality_threshold=self._quality_threshold,
                release_requested=self._release_review,
            )
            if not needs_second:
                review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                judge_audits.append(
                    {"primary": _judge_dict(primary), "secondary": None, "reconciliation_reasons": []}
                )
            elif self._secondary is None:
                # Secondary judging is optional. A valid primary result remains
                # the score when the secondary judge is deliberately disabled.
                review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                judge_audits.append(
                    {"primary": _judge_dict(primary), "secondary": None, "reconciliation_reasons": ["secondary judge disabled; primary score used"]}
                )
            else:
                if self._egress_validator is not None and not self._egress_validator(request):
                    raise EgressRejected(
                        f"secondary judge request for {case.id} turn {expected_turn.turn} failed egress validation"
                    )
                try:
                    secondary = self._secondary.judge(request)
                except CheckpointWriteError:
                    raise
                except Exception as exc:
                    # Do not discard a usable primary score because the
                    # independent secondary provider is unavailable.
                    review_statuses.append(ReviewStatus.NOT_REQUESTED.value)
                    judge_audits.append(
                        {
                            "primary": _judge_dict(primary),
                            "secondary": None,
                            "reconciliation_reasons": [
                                f"secondary judge unavailable; primary score used: {type(exc).__name__}: {exc}"
                            ],
                        }
                    )
                    continue
                reconciliation = reconcile_judges(
                    primary, secondary, asdict(self._config.review)
                )
                review_statuses.append(reconciliation.status.value)
                judge_audits.append(
                    {
                        "primary": _judge_dict(primary),
                        "secondary": _judge_dict(secondary),
                        "reconciliation_reasons": list(reconciliation.reasons),
                    }
                )

        hard_gate_failed = any(
            metric.status in {MetricStatus.FAIL, MetricStatus.ERROR}
            for row in metric_rows
            for name, metric in row.items()
            if name in {"pii_leakage", "route_validity", "output_guard", "ground_resolution"}
        )
        if hard_gate_failed or run.status == "error" or not qualities:
            case_score = CaseScore(
                case_status="FAIL",
                red_line_triggered=False,
                triggered_red_lines=(),
                dimension_scores={item.name: 0.0 for item in self._rule.modules},
                final_weights={},
                weighted_total=0.0,
            )
        else:
            case_score = score_case(self._rule, tuple(qualities), case.quality_focus)
        status = _case_status(run, metric_rows, case_score.red_line_triggered, review_statuses)
        failure_stages = _failure_stages(metric_rows, case_score.red_line_triggered, run.status)

        return {
            "case_id": case.id,
            "status": status,
            "conversation": {
                "conversation_id": run.conversation_id,
                "turns": [
                    {
                        "turn": expected_turn.turn,
                        "user_input": expected_turn.user,
                        "assistant_response": actual_turn.response,
                    }
                    for expected_turn, actual_turn in zip(
                        case.turns, run.turns, strict=False
                    )
                ],
            },
            "safety": {
                "hard_gate_passed": not case_score.red_line_triggered and not hard_gate_failed,
                "red_lines": list(case_score.triggered_red_lines),
            },
            "pipeline": {
                "turns": [
                    {name: _metric_dict(metric) for name, metric in row.items()}
                    for row in metric_rows
                ],
                "turn_traces": turn_traces,
                "observations": observations,
            },
            "quality": {
                "dimensions": dict(case_score.dimension_scores),
                "final_weights": dict(case_score.final_weights),
                "weighted_total": case_score.weighted_total,
            },
            "performance": _performance(run),
            "review": {
                "status": (
                    ReviewStatus.NEEDS_REVIEW.value
                    if ReviewStatus.NEEDS_REVIEW.value in review_statuses
                    else "completed"
                ),
                "per_turn": review_statuses,
                "judge_audit": judge_audits,
            },
            "failure": {
                "primary_stage": failure_stages[0] if failure_stages else None,
                "secondary_stages": failure_stages[1:],
            },
            "cohorts": _cohorts(case),
            "evidence_refs": [
                f"{case.id}:T{index}:{name}"
                for index, row in enumerate(metric_rows, 1)
                for name, metric in row.items()
                if metric.status in {MetricStatus.FAIL, MetricStatus.ERROR}
            ],
            "remediation": {},
        }


def _runner_case(case: TestCase) -> Mapping[str, Any]:
    return {
        "id": case.id,
        "turns": [{"turn": turn.turn, "user": turn.user} for turn in case.turns],
    }


def _metric_dict(metric: MetricResult) -> dict[str, Any]:
    payload = {
        "status": metric.status.value,
        "score": metric.score,
        "reason": metric.reason,
        "evidence": list(metric.evidence),
    }
    if metric.counts is not None:
        payload["counts"] = dict(metric.counts)
    return payload


def _turn_observation(
    turn: int,
    expected: Any,
    trace: Mapping[str, Any],
    actual_response: str | None,
    *,
    oracle_approved: bool,
) -> dict[str, Any]:
    route = trace.get("route") if isinstance(trace.get("route"), Mapping) else {}
    safety = trace.get("safety") if isinstance(trace.get("safety"), Mapping) else {}
    ground = trace.get("ground") if isinstance(trace.get("ground"), Mapping) else {}
    answer = trace.get("answer") if isinstance(trace.get("answer"), Mapping) else {}
    tools = trace.get("tools") if isinstance(trace.get("tools"), Mapping) else {}
    agent = trace.get("agent") if isinstance(trace.get("agent"), Mapping) else {}
    source = trace.get("source") if isinstance(trace.get("source"), Mapping) else {}
    wiki = trace.get("wiki") if isinstance(trace.get("wiki"), Mapping) else {}
    capsule = trace.get("capsule") if isinstance(trace.get("capsule"), Mapping) else {}
    ranked = ground.get("ranked_refs")
    resolved = ground.get("resolved_refs", ground.get("resolved_ground", ()))
    calls = tools.get("calls", ())
    return {
        "turn": turn,
        "oracle_approved": oracle_approved,
        "expected": asdict(expected),
        "actual": {
            "safety_level": safety.get("level", safety.get("risk_level")),
            "route_id": route.get("id", route.get("route_id", route.get("capsule_id"))),
            "retrieved_refs": list(resolved) if _is_sequence(resolved) else [],
            "ranked_refs": list(ranked) if _is_sequence(ranked) else None,
            "abstained": answer.get("abstained", trace.get("abstained")),
            "citations": _section_refs(answer, ("citations", "citation_refs")),
            "response_chars": len(actual_response) if isinstance(actual_response, str) else None,
            "source_refs": _section_refs(source, ("resolved_refs", "refs", "source_refs")),
            "wiki_refs": _section_refs(wiki, ("resolved_refs", "refs", "wiki_refs")),
            "capsule_id": capsule.get("id", route.get("id", route.get("capsule_id"))),
            "capsule_units": list(capsule.get("injected_units", ())) if _is_sequence(capsule.get("injected_units", ())) else [],
            "tool_calls": list(calls) if _is_sequence(calls) else [],
            "goal_completed": agent.get("goal_completed"),
            "steps": agent.get("steps"),
            "invalid_tool_calls": tools.get("invalid_calls", agent.get("invalid_tool_calls", 0)),
            "retries": agent.get("retries", tools.get("retries", 0)),
            "timeouts": agent.get("timeouts", tools.get("timeouts", 0)),
        },
        "judge": {},
    }


def _is_sequence(value: Any) -> bool:
    from collections.abc import Sequence

    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _section_refs(section: Mapping[str, Any], keys: tuple[str, ...]) -> list[str]:
    for key in keys:
        value = section.get(key)
        if _is_sequence(value):
            return [str(item) for item in value]
    return []


def _judge_dict(result: JudgeResult) -> dict[str, Any]:
    return {
        "red_lines": [asdict(item) for item in result.red_lines],
        "dimensions": [asdict(item) for item in result.dimensions],
        "legal_claims": [asdict(item) for item in result.legal_claims],
        "faithfulness_claims": [asdict(item) for item in result.faithfulness_claims],
    }


def _evidence_catalog(request: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Build the only evidence references a judge may cite for this turn."""
    catalog: list[dict[str, Any]] = []
    current_input = request.get("redacted_user_input")
    if isinstance(current_input, str) and current_input:
        catalog.append(
            {"ref": "input:current", "type": "user_input", "content": current_input}
        )
    history = request.get("redacted_conversation_history", ())
    if _is_sequence(history):
        for index, content in enumerate(history, start=1):
            if isinstance(content, str) and content:
                catalog.append(
                    {"ref": f"history:{index}", "type": "conversation_history", "content": content}
                )

    trace = request.get("trace")
    trace = trace if isinstance(trace, Mapping) else {}
    capsule = trace.get("capsule")
    capsule = capsule if isinstance(capsule, Mapping) else {}
    capsule_id = capsule.get("id")
    units = request.get("capsule_content_units", ())
    if isinstance(capsule_id, str) and capsule_id and _is_sequence(units):
        for unit in units:
            if not isinstance(unit, Mapping) or not isinstance(unit.get("unit_id"), str):
                continue
            catalog.append(
                {
                    "ref": f"capsule:{capsule_id}:{unit['unit_id']}",
                    "type": "capsule",
                    "content": dict(unit),
                }
            )

    context = request.get("authoritative_context")
    context = context if isinstance(context, Mapping) else {}
    items = context.get("items", ())
    if _is_sequence(items):
        for item in items:
            if not isinstance(item, Mapping) or not isinstance(item.get("ref"), str):
                continue
            catalog.append(
                {"ref": f"ground:{item['ref']}", "type": "ground", "content": dict(item)}
            )
    return catalog


def _snapshot_catalog(snapshot: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Project the evaluator's captured snapshot into metric input facts."""
    try:
        from .evidence import build_evidence_catalog, validate_effective_context_snapshot

        validated = validate_effective_context_snapshot(snapshot)
        return build_evidence_catalog(validated)
    except Exception:
        return []


def _snapshot_parameter_contracts(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    invocations = snapshot.get("invocations")
    if isinstance(invocations, Mapping):
        return {
            "router": (invocations.get("router") or {}).get("parameter_contract", {})
            if isinstance(invocations.get("router"), Mapping) else {},
            "composer": (invocations.get("composer") or {}).get("parameter_contract", {})
            if isinstance(invocations.get("composer"), Mapping) else {},
            "ground_runtime": snapshot.get("ground_parameter_contract", {}),
        }
    return {
        "router": snapshot.get("router", {}).get("parameter_contract", {})
        if isinstance(snapshot.get("router"), Mapping) else {},
        "composer": snapshot.get("composer", {}).get("parameter_contract", {})
        if isinstance(snapshot.get("composer"), Mapping) else {},
        "ground_runtime": snapshot.get("ground_parameter_contract", {}),
    }


def _capsule_cohort(expected: Any, trace: Mapping[str, Any]) -> str | None:
    route = trace.get("route") if isinstance(trace.get("route"), Mapping) else {}
    capsule = trace.get("capsule") if isinstance(trace.get("capsule"), Mapping) else {}
    route_id = route.get("id", route.get("capsule_id"))
    if route_id == "crisis_sop":
        return "crisis_short_circuited"
    injected = capsule.get("injected_units", ())
    if route_id not in {None, "", "baseline"} and not _is_sequence(injected):
        return "injection_failed"
    if route_id not in {None, "", "baseline"} and _is_sequence(injected) and not injected:
        return "injection_failed"
    expected_ids = getattr(expected, "capsule_ids", ()) or getattr(expected, "route_ids", ())
    expects_ordinary = any(item not in {"baseline", "crisis_sop"} for item in expected_ids)
    if route_id in {None, "", "baseline"}:
        return "capsule_missed" if expects_ordinary else "baseline_appropriate"
    return None


def _redacted_input(trace: Mapping[str, Any]) -> str | None:
    redaction = trace.get("redaction")
    if not isinstance(redaction, Mapping):
        return None
    value = redaction.get("redacted_text")
    return value if isinstance(value, str) else None


def _case_status(run, rows, red_line, reviews) -> str:
    if red_line or any(status == ReviewStatus.NEEDS_REVIEW.value for status in reviews):
        return "FAIL" if red_line else "NEEDS_REVIEW"
    statuses = [
        metric.status
        for row in rows
        for name, metric in row.items()
        if name != "route_preference"
    ]
    if run.status == "error" or MetricStatus.ERROR in statuses:
        return "ERROR"
    if MetricStatus.FAIL in statuses:
        return "FAIL"
    return "PASS"


def _failure_stages(rows, red_line: bool, run_status: str) -> list[str]:
    stages: list[str] = []
    if red_line:
        stages.append("safety")
    mapping = {
        "pii_leakage": "output_guard",
        "route_validity": "router",
        "output_guard": "output_guard",
        "ground_resolution": "ground",
        "safety": "safety",
        "route": "router",
        "timings": "performance",
        "tokens": "performance",
        "trace": "performance",
    }
    for row in rows:
        for name, metric in row.items():
            if name == "route_preference":
                continue
            if metric.status in {MetricStatus.FAIL, MetricStatus.ERROR}:
                stage = "memory" if name.startswith("memory_") else mapping.get(name, "test_case")
                if stage not in stages:
                    stages.append(stage)
    if run_status == "error" and "performance" not in stages:
        stages.append("performance")
    return stages


def _performance(run: CaseRunResult) -> dict[str, Any]:
    total_ms = 0.0
    input_tokens = 0.0
    output_tokens = 0.0
    for turn in run.turns:
        timings = turn.trace.get("timings", {})
        tokens = turn.trace.get("tokens", {})
        if isinstance(timings, Mapping):
            total_ms += float(timings.get("total_ms", 0))
        if isinstance(tokens, Mapping):
            input_tokens += float(tokens.get("input", 0))
            output_tokens += float(tokens.get("output", 0))
    return {"total_ms": total_ms, "input_tokens": input_tokens, "output_tokens": output_tokens}


def _cohorts(case: TestCase) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}
    for key, value in case.tags.items():
        values = value if isinstance(value, list) else [value]
        result[str(key)] = tuple(str(item) for item in values)
    if case.category:
        result["category"] = (case.category,)
    return result


def _is_critical(case: TestCase) -> bool:
    risk = case.tags.get("risk")
    return risk == "critical" or (isinstance(risk, list) and "critical" in risk)
