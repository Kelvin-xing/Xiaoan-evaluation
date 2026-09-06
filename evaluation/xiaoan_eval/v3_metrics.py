"""Deterministic helpers for XiaoAn v3 claim and judge calibration metrics."""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import random
from typing import Any, Mapping, Sequence

from .attribution import summarize_semantic_attribution


@dataclass(frozen=True)
class ClaimScore:
    tp: int
    fp: int
    fn: int

    @property
    def precision(self) -> float | None:
        return self.tp / (self.tp + self.fp) if self.tp + self.fp else None

    @property
    def recall(self) -> float | None:
        return self.tp / (self.tp + self.fn) if self.tp + self.fn else None

    @property
    def completeness_f1(self) -> float | None:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if p is not None and r is not None and p + r else None

    supported_claims: int = 0
    total_claims: int = 0

    @property
    def f1(self) -> float | None:
        """Backward-compatible alias for completeness F1."""
        return self.completeness_f1

    @property
    def faithfulness(self) -> float | None:
        return self.supported_claims / self.total_claims if self.total_claims else None


def score_claims(required: Sequence[str], judged: Sequence[Mapping[str, Any]]) -> ClaimScore:
    """Score required-claim completeness separately from answer faithfulness."""
    gold = {str(item) for item in required}
    claim_rows = [
        (str(item.get("claim")), item.get("supported") is True)
        for item in judged
        if isinstance(item.get("claim"), str) and str(item.get("claim")).strip()
    ]
    claims: dict[str, bool] = {}
    for claim, supported in claim_rows:
        claims[claim] = claims.get(claim, True) and supported
    supported = {claim for claim, is_supported in claims.items() if is_supported}
    unsupported_extras = {
        claim for claim, is_supported in claims.items()
        if not is_supported and claim not in gold
    }
    return ClaimScore(
        len(gold & supported),
        len(unsupported_extras),
        len(gold - supported),
        len(supported),
        len(claims),
    )


def judge_calibration(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Summarize primary/secondary score agreement and pass/fail flips."""
    pairs: list[tuple[float, float]] = []
    flips = 0
    for record in records:
        review = record.get("review", {})
        audits = review.get("judge_audit", []) if isinstance(review, Mapping) else []
        if not isinstance(audits, Sequence):
            continue
        for audit in audits:
            if not isinstance(audit, Mapping):
                continue
            primary, secondary = audit.get("primary"), audit.get("secondary")
            if not isinstance(primary, Mapping) or not isinstance(secondary, Mapping):
                continue
            p = _mean_dimension_score(primary.get("dimensions"))
            s = _mean_dimension_score(secondary.get("dimensions"))
            if p is None or s is None:
                continue
            pairs.append((p, s))
            flips += int((p >= 1.5) != (s >= 1.5))
    mean_abs = sum(abs(p - s) for p, s in pairs) / len(pairs) if pairs else None
    return {"paired_turns": len(pairs), "mean_absolute_score_delta": mean_abs,
            "pass_fail_flips": flips}


def semantic_attribution_metrics(
    turns: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Expose the v1 semantic contract without using benchmark agreement as a gate."""
    return summarize_semantic_attribution(turns)


def summarize_v3(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Aggregate approved turn observations without inferring unavailable labels."""
    claim_totals = ClaimScore(0, 0, 0, 0, 0)
    route_pairs: list[tuple[str, str]] = []
    safety_pairs: list[tuple[str, str]] = []
    route_accepted: list[bool] = []
    safety_accepted: list[bool] = []
    route_ambiguous = 0
    safety_ambiguous = 0
    refusal_pairs: list[tuple[bool, bool]] = []
    tool_turns: list[dict[str, Any]] = []
    goals: list[bool] = []
    step_efficiencies: list[float] = []
    invalid_tool_calls = 0
    retries = 0
    timeouts = 0
    citation_counts = {"tp": 0, "fp": 0, "fn": 0, "evaluated_turns": 0, "skipped_turns": 0}
    evidence_counts = {
        "source": {"tp": 0, "fp": 0, "fn": 0, "evaluated_turns": 0, "skipped_turns": 0},
        "wiki": {"tp": 0, "fp": 0, "fn": 0, "evaluated_turns": 0, "skipped_turns": 0},
        "capsule": {"tp": 0, "fp": 0, "fn": 0, "evaluated_turns": 0, "skipped_turns": 0},
    }
    forbidden_seen = 0
    judged_claim_count = 0
    length_checks: list[bool] = []
    capsule_injected = 0
    capsule_aligned_claims = 0
    capsule_total_claims = 0
    capsule_valid_refs = 0
    capsule_all_refs = 0
    capsule_cited_units: set[str] = set()

    for observation in _observations(records):
        expected = observation["expected"]
        actual = observation["actual"]
        judge = observation.get("judge", {})
        response = expected.get("response_oracle")
        response = response if isinstance(response, Mapping) else {}
        units = actual.get("capsule_units", ())
        unit_refs = {
            f"capsule:{actual.get('capsule_id')}:{item.get('unit_id')}"
            for item in units
            if isinstance(item, Mapping) and isinstance(item.get("unit_id"), str)
        } if _sequence(units) else set()
        capsule_injected += len(unit_refs)
        judged_claims = judge.get("faithfulness_claims", ()) if isinstance(judge, Mapping) else ()
        required = response.get("required_claims", ())
        if _sequence(required) and _sequence(judged_claims):
            turn_score = score_claims(required, judged_claims)
            claim_totals = ClaimScore(
                claim_totals.tp + turn_score.tp,
                claim_totals.fp + turn_score.fp,
                claim_totals.fn + turn_score.fn,
                claim_totals.supported_claims + turn_score.supported_claims,
                claim_totals.total_claims + turn_score.total_claims,
            )
        if _sequence(judged_claims):
            judged_text = {
                str(item.get("claim")) for item in judged_claims
                if isinstance(item, Mapping) and isinstance(item.get("claim"), str)
            }
            forbidden = set(str(item) for item in response.get("forbidden_claims", ()))
            forbidden_seen += len(judged_text & forbidden)
            judged_claim_count += len(judged_text)
            for claim in judged_claims:
                if not isinstance(claim, Mapping):
                    continue
                refs = claim.get("evidence_refs", ())
                if not _sequence(refs):
                    continue
                capsule_refs = {str(ref) for ref in refs if str(ref).startswith("capsule:")}
                capsule_all_refs += len(capsule_refs)
                valid = capsule_refs & unit_refs
                capsule_valid_refs += len(valid)
                capsule_cited_units.update(valid)
                capsule_total_claims += 1
                capsule_aligned_claims += int(bool(valid))

        _add_set_counts(citation_counts, response.get("must_cite", ()), actual.get("citations", ()))
        _add_set_counts(evidence_counts["source"], expected.get("source_refs", ()), actual.get("source_refs", ()))
        _add_set_counts(evidence_counts["wiki"], expected.get("wiki_refs", ()), actual.get("wiki_refs", ()))
        actual_capsule = [actual["capsule_id"]] if isinstance(actual.get("capsule_id"), str) else []
        _add_set_counts(evidence_counts["capsule"], expected.get("capsule_ids", ()), actual_capsule)
        max_chars, response_chars = response.get("max_chars"), actual.get("response_chars")
        if isinstance(max_chars, int) and isinstance(response_chars, int):
            length_checks.append(response_chars <= max_chars)

        route_expected = _canonical_label(
            expected.get("preferred_route_id"), expected.get("route_ids")
        )
        route_actual = actual.get("route_id")
        accepted_routes = expected.get("route_ids")
        if _sequence(accepted_routes) and isinstance(route_actual, str):
            route_accepted.append(route_actual in {str(item) for item in accepted_routes})
        if route_expected is not None and isinstance(route_actual, str):
            route_pairs.append((route_expected, route_actual))
        elif _sequence(accepted_routes) and len(accepted_routes) > 1:
            route_ambiguous += 1
        safety_expected = _canonical_label(None, expected.get("safety_levels"))
        safety_actual = actual.get("safety_level")
        accepted_safety = expected.get("safety_levels")
        if _sequence(accepted_safety) and isinstance(safety_actual, str):
            safety_accepted.append(safety_actual in {str(item) for item in accepted_safety})
        if safety_expected is not None and isinstance(safety_actual, str):
            safety_pairs.append((safety_expected, safety_actual))
        elif _sequence(accepted_safety) and len(accepted_safety) > 1:
            safety_ambiguous += 1

        should_abstain = response.get("should_abstain")
        abstained = actual.get("abstained")
        if isinstance(should_abstain, bool) and isinstance(abstained, bool):
            refusal_pairs.append((should_abstain, abstained))

        turn_expected_tools = response.get("expected_tools", ())
        turn_actual_tools = actual.get("tool_calls", ())
        if _sequence(turn_expected_tools) and all(isinstance(item, Mapping) for item in turn_expected_tools):
            actual_rows = (
                [item for item in turn_actual_tools if isinstance(item, Mapping)]
                if _sequence(turn_actual_tools) else []
            )
            tool_turns.append(_tool_summary(turn_expected_tools, actual_rows))

        expected_goal = response.get("goal_completed")
        actual_goal = actual.get("goal_completed")
        if isinstance(expected_goal, bool) and isinstance(actual_goal, bool):
            goals.append(expected_goal == actual_goal)
        max_steps, steps = response.get("max_steps"), actual.get("steps")
        if (
            isinstance(max_steps, int) and not isinstance(max_steps, bool)
            and isinstance(steps, int) and not isinstance(steps, bool) and steps > 0
        ):
            step_efficiencies.append(min(1.0, max_steps / steps))
        invalid_tool_calls += _non_negative_int(actual.get("invalid_tool_calls"))
        retries += _non_negative_int(actual.get("retries"))
        timeouts += _non_negative_int(actual.get("timeouts"))

    route = _multiclass_summary(route_pairs)
    safety = _multiclass_summary(safety_pairs)
    route.update({"accepted_accuracy": _mean(route_accepted), "ambiguous_turns": route_ambiguous})
    safety.update({"accepted_accuracy": _mean(safety_accepted), "ambiguous_turns": safety_ambiguous})
    refusal = _binary_summary(refusal_pairs)
    tools = _aggregate_tool_turns(tool_turns)
    semantic_turns = [
        observation["attribution"]
        for observation in _observations(records)
        if isinstance(observation.get("attribution"), Mapping)
    ]
    return {
        "claims": {
            "tp": claim_totals.tp,
            "fp": claim_totals.fp,
            "fn": claim_totals.fn,
            "precision": claim_totals.precision,
            "recall": claim_totals.recall,
            "f1": claim_totals.f1,
            "faithfulness": claim_totals.faithfulness,
            "unsupported_claim_rate": (
                claim_totals.fp / claim_totals.total_claims
                if claim_totals.total_claims else None
            ),
        },
        "answer": {
            "correctness_f1": claim_totals.f1,
            "completeness_recall": claim_totals.recall,
            "faithfulness": claim_totals.faithfulness,
            "forbidden_claim_count": forbidden_seen,
            "forbidden_claim_rate": forbidden_seen / judged_claim_count if judged_claim_count else None,
            "length_compliance_rate": _mean(length_checks),
        },
        "capsule_attribution": {
            "compatibility_status": "LEGACY_OBSERVATIONAL_ONLY",
            "status": "available" if capsule_injected else "unavailable",
            "injected_units": capsule_injected,
            "claims_with_valid_capsule_evidence": capsule_aligned_claims,
            "claim_alignment": capsule_aligned_claims / capsule_total_claims if capsule_total_claims else None,
            "content_coverage": len(capsule_cited_units) / capsule_injected if capsule_injected else None,
            "citation_precision": capsule_valid_refs / capsule_all_refs if capsule_all_refs else None,
            "reason": "Legacy compatibility facts only. Exact ref usage is operational evidence, not semantic support or token provenance.",
        },
        "citations": {**citation_counts, **_rates(citation_counts)},
        "evidence": {
            name: {**counts, **_rates(counts)} for name, counts in evidence_counts.items()
        },
        "route": route,
        "safety": safety,
        "refusal": refusal,
        "tools": tools,
        "agent": {
            "evaluated_goals": len(goals),
            "goal_completion_rate": _mean(goals),
            "evaluated_steps": len(step_efficiencies),
            "step_efficiency": _mean(step_efficiencies),
            "invalid_tool_calls": invalid_tool_calls,
            "retries": retries,
            "timeouts": timeouts,
        },
        "judge_calibration": judge_calibration(records),
        "human_calibration": _human_calibration(records),
        "semantic_attribution": semantic_attribution_metrics(semantic_turns),
        "statistics": {
            "route_accuracy_95ci": _bootstrap_ci(
                route_accepted
            ),
            "safety_accuracy_95ci": _bootstrap_ci(
                safety_accepted
            ),
            "goal_completion_95ci": _bootstrap_ci(goals),
            "method": "seeded percentile bootstrap",
            "bootstrap_samples": 1000,
            "seed": 0,
        },
    }


def _observations(records: Sequence[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    rows: list[Mapping[str, Any]] = []
    for record in records:
        pipeline = record.get("pipeline")
        observations = pipeline.get("observations", ()) if isinstance(pipeline, Mapping) else ()
        if not _sequence(observations):
            continue
        for observation in observations:
            if not isinstance(observation, Mapping) or observation.get("oracle_approved") is not True:
                continue
            if isinstance(observation.get("expected"), Mapping) and isinstance(observation.get("actual"), Mapping):
                rows.append(observation)
    return rows


def _canonical_label(preferred: Any, accepted: Any) -> str | None:
    if isinstance(preferred, str) and preferred:
        return preferred
    if _sequence(accepted) and len(accepted) == 1 and isinstance(accepted[0], str):
        return accepted[0]
    return None


def _multiclass_summary(pairs: Sequence[tuple[str, str]]) -> dict[str, Any]:
    matrix: dict[str, dict[str, int]] = {}
    labels = sorted({label for pair in pairs for label in pair})
    for expected, actual in pairs:
        row = matrix.setdefault(expected, {})
        row[actual] = row.get(actual, 0) + 1
    per_class: dict[str, dict[str, float | int | None]] = {}
    for label in labels:
        tp = sum(expected == label and actual == label for expected, actual in pairs)
        fp = sum(expected != label and actual == label for expected, actual in pairs)
        fn = sum(expected == label and actual != label for expected, actual in pairs)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall else None
        )
        per_class[label] = {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall, "f1": f1}
    f1s = [float(row["f1"]) for row in per_class.values() if row["f1"] is not None]
    return {
        "evaluated_turns": len(pairs),
        "accuracy": sum(expected == actual for expected, actual in pairs) / len(pairs) if pairs else None,
        "macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "micro_precision": sum(expected == actual for expected, actual in pairs) / len(pairs) if pairs else None,
        "micro_recall": sum(expected == actual for expected, actual in pairs) / len(pairs) if pairs else None,
        "micro_f1": sum(expected == actual for expected, actual in pairs) / len(pairs) if pairs else None,
        "confusion_matrix": matrix,
        "per_class": per_class,
    }


def _binary_summary(pairs: Sequence[tuple[bool, bool]]) -> dict[str, Any]:
    tp = sum(expected and actual for expected, actual in pairs)
    fp = sum(not expected and actual for expected, actual in pairs)
    fn = sum(expected and not actual for expected, actual in pairs)
    tn = sum(not expected and not actual for expected, actual in pairs)
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"evaluated_turns": len(pairs), "tp": tp, "fp": fp, "fn": fn, "tn": tn,
            "precision": precision, "recall": recall, "f1": f1,
            "accuracy": (tp + tn) / len(pairs) if pairs else None}


def _tool_summary(expected: Sequence[Mapping[str, Any]], actual: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    expected_names = Counter(str(item.get("name")) for item in expected)
    actual_names = Counter(str(item.get("name")) for item in actual)
    tp = sum((expected_names & actual_names).values())
    fp = sum(actual_names.values()) - tp
    fn = sum(expected_names.values()) - tp
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    remaining = list(actual)
    argument_matches = 0
    for wanted in expected:
        for index, call in enumerate(remaining):
            if call.get("name") == wanted.get("name"):
                argument_matches += int(call.get("arguments", {}) == wanted.get("arguments", {}))
                remaining.pop(index)
                break
    expected_order = [str(item.get("name")) for item in expected]
    actual_order = [str(item.get("name")) for item in actual]
    return {"tp": tp, "fp": fp, "fn": fn, "precision": precision, "recall": recall,
            "f1": f1, "argument_matches": argument_matches,
            "argument_evaluated": tp, "argument_accuracy": argument_matches / tp if tp else None,
            "exact_sequence": expected_order == actual_order}


def _aggregate_tool_turns(turns: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    tp = sum(int(turn["tp"]) for turn in turns)
    fp = sum(int(turn["fp"]) for turn in turns)
    fn = sum(int(turn["fn"]) for turn in turns)
    rates = _rates({"tp": tp, "fp": fp, "fn": fn})
    argument_matches = sum(int(turn["argument_matches"]) for turn in turns)
    argument_evaluated = sum(int(turn["argument_evaluated"]) for turn in turns)
    return {
        "evaluated_turns": len(turns), "tp": tp, "fp": fp, "fn": fn, **rates,
        "argument_accuracy": argument_matches / argument_evaluated if argument_evaluated else None,
        "exact_sequence_rate": (
            sum(bool(turn["exact_sequence"]) for turn in turns) / len(turns) if turns else None
        ),
    }


def _add_set_counts(target: dict[str, int], expected: Any, actual: Any) -> None:
    if not _sequence(expected) or not expected:
        target["skipped_turns"] = target.get("skipped_turns", 0) + 1
        return
    if not _sequence(actual):
        return
    target["evaluated_turns"] = target.get("evaluated_turns", 0) + 1
    gold, found = {str(item) for item in expected}, {str(item) for item in actual}
    target["tp"] += len(gold & found)
    target["fp"] += len(found - gold)
    target["fn"] += len(gold - found)


def _rates(counts: Mapping[str, int]) -> dict[str, float | None]:
    tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
    precision = tp / (tp + fp) if tp + fp else None
    recall = tp / (tp + fn) if tp + fn else None
    f1 = 2 * precision * recall / (precision + recall) if precision is not None and recall is not None and precision + recall else None
    return {"precision": precision, "recall": recall, "f1": f1}


def _bootstrap_ci(values: Sequence[bool | float], *, samples: int = 1000) -> list[float] | None:
    if not values:
        return None
    numeric = [float(value) for value in values]
    if len(numeric) == 1:
        return [numeric[0], numeric[0]]
    generator = random.Random(0)
    means = sorted(
        sum(generator.choice(numeric) for _ in numeric) / len(numeric)
        for _ in range(samples)
    )
    return [means[int(samples * 0.025)], means[min(samples - 1, int(samples * 0.975))]]


def _human_calibration(records: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    pairs: list[tuple[int, int]] = []
    for record in records:
        review = record.get("human_review")
        reviews = review.get("reviews", ()) if isinstance(review, Mapping) else ()
        if not _sequence(reviews):
            continue
        for item in reviews:
            if not isinstance(item, Mapping):
                continue
            comparison = item.get("ai_comparison")
            deltas = comparison.get("dimension_score_deltas", {}) if isinstance(comparison, Mapping) else {}
            dimensions = item.get("dimensions", ())
            if not isinstance(deltas, Mapping) or not _sequence(dimensions):
                continue
            for dimension in dimensions:
                if not isinstance(dimension, Mapping):
                    continue
                module, human = dimension.get("module"), dimension.get("score")
                delta = deltas.get(module)
                if isinstance(human, int) and not isinstance(human, bool) and isinstance(delta, (int, float)):
                    pairs.append((int(human - delta), human))
    agreement = sum(ai == human for ai, human in pairs) / len(pairs) if pairs else None
    return {"paired_dimension_scores": len(pairs), "exact_agreement": agreement,
            "cohen_kappa": _cohen_kappa(pairs)}


def _cohen_kappa(pairs: Sequence[tuple[int, int]]) -> float | None:
    if not pairs:
        return None
    observed = sum(left == right for left, right in pairs) / len(pairs)
    left = Counter(item[0] for item in pairs)
    right = Counter(item[1] for item in pairs)
    expected = sum(left[label] * right[label] for label in set(left) | set(right)) / len(pairs) ** 2
    return (observed - expected) / (1 - expected) if expected < 1 else 1.0


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))


def _mean(values: Sequence[bool | float]) -> float | None:
    return sum(float(value) for value in values) / len(values) if values else None


def _non_negative_int(value: Any) -> int:
    return value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else 0


def render_v3_markdown(summary: Mapping[str, Any]) -> str:
    calibration = summary.get("judge_calibration", {})
    claims = summary.get("claims", {})
    lines = ["# XiaoAn v3 evaluation", "", "## Claim metrics", "",
             "| Metric | Value |", "| --- | ---: |"]
    for key in ("tp", "fp", "fn", "precision", "recall", "f1"):
        lines.append(f"| claim_{key} | {claims.get(key, 'n/a')} |")
    lines += ["", "## Judge calibration", "", "| Metric | Value |", "| --- | ---: |"]
    for key, value in calibration.items():
        lines.append(f"| {key} | {value if value is not None else 'n/a'} |")
    for section in ("answer", "citations", "semantic_attribution", "route", "safety", "refusal", "tools", "agent", "statistics", "human_calibration"):
        values = summary.get(section, {})
        if not isinstance(values, Mapping):
            continue
        lines += ["", f"## {section.replace('_', ' ').title()}", "", "| Metric | Value |", "| --- | ---: |"]
        for key, value in values.items():
            if isinstance(value, Mapping):
                continue
            lines.append(f"| {key} | {_display(value)} |")
    return "\n".join(lines) + "\n"


def _display(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.3f}"
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes)):
        return " – ".join(_display(item) for item in value)
    return str(value)


def _mean_dimension_score(value: Any) -> float | None:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        return None
    scores = [float(item["score"]) for item in value if isinstance(item, Mapping)
              and isinstance(item.get("score"), (int, float)) and not isinstance(item.get("score"), bool)]
    return sum(scores) / len(scores) if scores else None
