"""Immutable, descriptive human-benchmark lifecycle primitives."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from fractions import Fraction
import hashlib
import json
from typing import Any, Mapping, Sequence


ANNOTATION_SCHEMA_VERSION = "human-benchmark-annotation/v1"
MANIFEST_SCHEMA_VERSION = "human-benchmark-manifest/v1"
TARGETS = frozenset({"ATTRIBUTION", "QUALITY_RED_LINE"})
ROLES = frozenset({"REVIEWER", "ADJUDICATOR"})
UNCERTAINTY = frozenset({"LOW", "MEDIUM", "HIGH"})
RELATIONS = frozenset(
    {"ENTAILS", "PARTIAL", "CONTEXT_ONLY", "CONTRADICTS", "UNSUPPORTED"}
)
CLAIM_KINDS = frozenset(
    {"FACTUAL", "INTERPRETIVE", "RECOMMENDATION", "ACTION", "SUPPORTIVE"}
)
UNSUPPORTED_CATEGORIES = frozenset(
    {"UNVERIFIABLE_UNSUPPORTED", "PERMITTED_INFERENCE", "NON_FACTUAL_SUPPORTIVE"}
)


class BenchmarkValidationError(ValueError):
    """Raised when benchmark evidence is incomplete, mutable, or ambiguous."""


@dataclass(frozen=True)
class FrozenBenchmark:
    benchmark_version: str
    target: str
    status: str
    manifest_digest: str
    artifact_digest: str
    supersedes: str | None
    change_reason: str | None
    descriptive_only: bool = True


def build_sampling_manifest(
    population: Sequence[Mapping[str, Any]],
    *,
    benchmark_version: str,
    selector_version: str,
    seed: int,
    stratum_targets: Mapping[str, int],
    minimum_cases: int = 16,
    minimum_outputs: int = 32,
    deficit_reasons: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    """Select a stable multi-label cohort and publish auditable coverage."""
    benchmark_version = _text(benchmark_version, "benchmark_version")
    selector_version = _text(selector_version, "selector_version")
    if isinstance(seed, bool) or not isinstance(seed, int):
        raise BenchmarkValidationError("seed must be an integer")
    if minimum_cases < 1 or minimum_outputs < 1:
        raise BenchmarkValidationError("minimum_cases and minimum_outputs must be positive")
    targets = _targets(stratum_targets)
    normalized = [_population_item(item, index) for index, item in enumerate(population)]
    by_id = {item["item_id"]: item for item in normalized}
    if len(by_id) != len(normalized):
        raise BenchmarkValidationError("population contains duplicate item_id")
    ordered_population = sorted(normalized, key=lambda item: str(item["item_id"]))
    population_digest = _digest(ordered_population)
    ranked = sorted(
        ordered_population,
        key=lambda item: (
            hashlib.sha256(f"{seed}:{item['item_id']}".encode("utf-8")).hexdigest(),
            str(item["item_id"]),
        ),
    )
    selected: dict[str, dict[str, Any]] = {}
    for stratum in sorted(targets):
        candidates = [item for item in ranked if stratum in item["observed_strata"]]
        for item in candidates:
            achieved = sum(
                stratum in selected_item["observed_strata"]
                for selected_item in selected.values()
            )
            if achieved >= targets[stratum]:
                break
            selected[str(item["item_id"])] = item
    for item in ranked:
        selected.setdefault(str(item["item_id"]), item)
        cases = {str(selected_item["case_id"]) for selected_item in selected.values()}
        if len(selected) >= minimum_outputs and len(cases) >= minimum_cases:
            break
    reasons = dict(deficit_reasons or {})
    coverage: dict[str, dict[str, Any]] = {}
    unexplained: list[str] = []
    for stratum, target in sorted(targets.items()):
        achieved = sum(
            stratum in selected_item["observed_strata"]
            for selected_item in selected.values()
        )
        deficit = max(0, target - achieved)
        reason = reasons.get(stratum)
        if deficit and (not isinstance(reason, str) or not reason.strip()):
            unexplained.append(stratum)
        coverage[stratum] = {
            "target": target,
            "achieved": achieved,
            "deficit": deficit,
            "deficit_reason": reason if deficit else None,
        }
    case_count = len({str(item["case_id"]) for item in selected.values()})
    if len(selected) < minimum_outputs:
        unexplained.append("minimum_outputs")
    if case_count < minimum_cases:
        unexplained.append("minimum_cases")
    if unexplained:
        raise BenchmarkValidationError(
            f"unexplained coverage deficit: {', '.join(sorted(set(unexplained)))}"
        )
    selected_items = sorted(selected.values(), key=lambda item: str(item["item_id"]))
    manifest = {
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "benchmark_version": benchmark_version,
        "eligible_population_digest": population_digest,
        "selector_version": selector_version,
        "seed": seed,
        "inclusion_rules": ["item has immutable case/turn/output and bound digests"],
        "exclusion_rules": ["items failing immutable binding validation"],
        "overlap_policy": "multi_label_each_selected_item_counts_once_per_stratum",
        "minimum_cases": minimum_cases,
        "minimum_outputs": minimum_outputs,
        "selected_case_count": case_count,
        "selected_output_count": len(selected_items),
        "coverage": coverage,
        "items": selected_items,
    }
    manifest["manifest_digest"] = _digest(manifest)
    return manifest


def freeze_benchmark(
    manifest: Mapping[str, Any],
    *,
    target: str,
    supersedes: str | None = None,
    change_reason: str | None = None,
    adjudicated: bool = False,
) -> FrozenBenchmark:
    target = _target(target)
    _validate_manifest_digest(manifest)
    if supersedes is not None:
        supersedes = _text(supersedes, "supersedes")
        change_reason = _text(change_reason, "change_reason")
    elif change_reason is not None:
        change_reason = _text(change_reason, "change_reason")
    artifacts = [
        {
            "item_id": item["item_id"],
            "answer_sha256": item["answer_sha256"],
            "context_sha256": item["context_sha256"],
            "target_input_sha256": item["target_input_sha256"],
        }
        for item in manifest["items"]
    ]
    return FrozenBenchmark(
        benchmark_version=str(manifest["benchmark_version"]),
        target=target,
        status="FROZEN_ADJUDICATED" if adjudicated else "FROZEN_NOT_ADJUDICATED",
        manifest_digest=str(manifest["manifest_digest"]),
        artifact_digest=_digest(artifacts),
        supersedes=supersedes,
        change_reason=change_reason,
    )


def build_blinded_review_packet(
    manifest: Mapping[str, Any],
    item: Mapping[str, Any],
    *,
    target: str,
    rubric_version: str,
    target_input: Mapping[str, Any],
) -> dict[str, Any]:
    """Create reviewer input without judge, experiment-arm, or candidate identity."""
    target = _target(target)
    _validate_manifest_digest(manifest)
    item_id = _text(item.get("item_id"), "item.item_id")
    manifest_item = next(
        (entry for entry in manifest["items"] if entry.get("item_id") == item_id), None
    )
    if manifest_item is None:
        raise BenchmarkValidationError("review item is not in the sampling manifest")
    for field in ("answer_sha256", "context_sha256", "target_input_sha256"):
        if item.get(field) != manifest_item.get(field):
            raise BenchmarkValidationError(f"review item {field} does not match manifest")
    target_input_digest = _digest(target_input)
    if target_input_digest != item.get("target_input_sha256"):
        raise BenchmarkValidationError("target_input does not match target_input_sha256")
    answer = item.get("answer")
    if not isinstance(answer, str) or hashlib.sha256(answer.encode()).hexdigest() != item.get("answer_sha256"):
        raise BenchmarkValidationError("answer does not match answer_sha256")
    packet = {
        "schema_version": "human-benchmark-review-packet/v1",
        "benchmark_version": manifest["benchmark_version"],
        "target": target,
        "item_id": item_id,
        "case_id": manifest_item["case_id"],
        "turn": manifest_item["turn"],
        "output_id": manifest_item["output_id"],
        "observed_strata": list(manifest_item["observed_strata"]),
        "answer": answer,
        "answer_sha256": manifest_item["answer_sha256"],
        "context_sha256": manifest_item["context_sha256"],
        "target_input_sha256": manifest_item["target_input_sha256"],
        "rubric_version": _text(rubric_version, "rubric_version"),
        "target_input": json.loads(
            json.dumps(target_input, ensure_ascii=False, sort_keys=True)
        ),
        "blinded": True,
    }
    return packet


def record_judge_run(
    benchmark: FrozenBenchmark,
    *,
    judge_version: str,
    judge_control_digest: str,
    agreement_report: Mapping[str, Any],
) -> dict[str, Any]:
    """Append-only comparison identity; deliberately contains no decision field."""
    if benchmark.status != "FROZEN_ADJUDICATED":
        raise BenchmarkValidationError(
            "judge runs require a frozen adjudicated benchmark reference"
        )
    judge_version = _text(judge_version, "judge_version")
    judge_control_digest = _sha256(judge_control_digest, "judge_control_digest")
    report = dict(_mapping(agreement_report, "agreement_report"))
    if report.get("benchmark_version") != benchmark.benchmark_version:
        raise BenchmarkValidationError("agreement report benchmark version mismatch")
    if report.get("judge_version") != judge_version:
        raise BenchmarkValidationError("agreement report judge version mismatch")
    if report.get("target") != benchmark.target:
        raise BenchmarkValidationError("agreement report target mismatch")
    payload = {
        "schema_version": "human-benchmark-judge-run/v1",
        "benchmark_version": benchmark.benchmark_version,
        "benchmark_manifest_digest": benchmark.manifest_digest,
        "benchmark_artifact_digest": benchmark.artifact_digest,
        "target": benchmark.target,
        "judge_version": judge_version,
        "judge_control_digest": judge_control_digest,
        "agreement_report_digest": _digest(report),
        "descriptive_only": True,
    }
    payload["judge_run_id"] = "HBJ-" + _digest(payload)[:24]
    return payload


def validate_annotation(
    annotation: Mapping[str, Any], item: Mapping[str, Any]
) -> dict[str, Any]:
    root = dict(_mapping(annotation, "annotation"))
    if root.get("schema_version") != ANNOTATION_SCHEMA_VERSION:
        raise BenchmarkValidationError(
            f"annotation.schema_version must be {ANNOTATION_SCHEMA_VERSION}"
        )
    target = _target(root.get("target"))
    role = root.get("role")
    if role not in ROLES:
        raise BenchmarkValidationError(f"annotation.role must be one of {sorted(ROLES)}")
    normalized: dict[str, Any] = {
        "schema_version": ANNOTATION_SCHEMA_VERSION,
        "benchmark_version": _text(root.get("benchmark_version"), "benchmark_version"),
        "target": target,
        "item_id": _text(root.get("item_id"), "item_id"),
        "reviewer_id": _text(root.get("reviewer_id"), "reviewer_id"),
        "role": role,
        "answer_sha256": _sha256(root.get("answer_sha256"), "answer_sha256"),
        "context_sha256": _sha256(root.get("context_sha256"), "context_sha256"),
        "target_input_sha256": _sha256(
            root.get("target_input_sha256"), "target_input_sha256"
        ),
        "rubric_version": _text(root.get("rubric_version"), "rubric_version"),
        "submitted_at": _timestamp(root.get("submitted_at")),
    }
    if normalized["item_id"] != item.get("item_id"):
        raise BenchmarkValidationError("annotation item_id does not match bound item")
    for field in ("answer_sha256", "context_sha256", "target_input_sha256"):
        if normalized[field] != item.get(field):
            raise BenchmarkValidationError(f"annotation {field} does not match bound item")
    abstention = root.get("abstention")
    if not isinstance(abstention, bool):
        raise BenchmarkValidationError("annotation.abstention must be boolean")
    normalized["abstention"] = abstention
    uncertainty = root.get("uncertainty")
    if uncertainty not in UNCERTAINTY:
        raise BenchmarkValidationError("annotation.uncertainty is invalid")
    normalized["uncertainty"] = uncertainty
    labels = _mapping(root.get("labels"), "annotation.labels")
    normalized["labels"] = (
        _attribution_labels(labels, item)
        if target == "ATTRIBUTION"
        else _quality_labels(labels)
    )
    if role == "ADJUDICATOR":
        source_ids = root.get("source_submission_ids")
        if not isinstance(source_ids, list) or len(source_ids) != 2 or any(
            not isinstance(value, str) or not value.strip() for value in source_ids
        ):
            raise BenchmarkValidationError(
                "adjudicator source_submission_ids must contain two IDs"
            )
        reasons = root.get("adjudication_reasons")
        if not isinstance(reasons, list) or not reasons or any(
            not isinstance(value, str) or not value.strip() for value in reasons
        ):
            raise BenchmarkValidationError("adjudication_reasons must be non-empty")
        normalized["source_submission_ids"] = list(source_ids)
        normalized["adjudication_reasons"] = list(reasons)
    normalized["submission_id"] = "HBA-" + _digest(normalized)[:24]
    return normalized


def validate_reviewer_set(
    reviews: Sequence[Mapping[str, Any]], adjudication: Mapping[str, Any]
) -> dict[str, Any]:
    if len(reviews) != 2:
        raise BenchmarkValidationError("exactly two independent reviewer submissions required")
    reviewers = [dict(review) for review in reviews]
    for review in reviewers:
        _verify_submission_id(review)
    if any(review.get("role") != "REVIEWER" for review in reviewers):
        raise BenchmarkValidationError("review submissions must have REVIEWER role")
    reviewer_ids = [str(review.get("reviewer_id")) for review in reviewers]
    if len(set(reviewer_ids)) != 2:
        raise BenchmarkValidationError("reviewer submissions must be independent")
    adjudicated = dict(adjudication)
    _verify_submission_id(adjudicated)
    if adjudicated.get("role") != "ADJUDICATOR":
        raise BenchmarkValidationError("adjudication must have ADJUDICATOR role")
    if adjudicated.get("reviewer_id") in reviewer_ids:
        raise BenchmarkValidationError("a distinct adjudicator is required")
    identity_fields = (
        "benchmark_version",
        "target",
        "item_id",
        "answer_sha256",
        "context_sha256",
        "target_input_sha256",
        "rubric_version",
    )
    for field in identity_fields:
        values = {review.get(field) for review in reviewers}
        values.add(adjudicated.get(field))
        if len(values) != 1:
            raise BenchmarkValidationError(f"reviewer set has mismatched {field}")
    expected_sources = {str(review.get("submission_id")) for review in reviewers}
    if set(adjudicated.get("source_submission_ids", ())) != expected_sources:
        raise BenchmarkValidationError("adjudication does not bind both reviewer submissions")
    return {
        "status": "ADJUDICATED",
        "reviewer_ids": sorted(reviewer_ids),
        "adjudicator_id": adjudicated["reviewer_id"],
        "adjudicated_submission_id": adjudicated["submission_id"],
    }


def match_spans(
    human_spans: Sequence[Mapping[str, Any]],
    judge_spans: Sequence[Mapping[str, Any]],
    *,
    threshold: float = 0.5,
) -> dict[str, Any]:
    """Exact-first, then maximum-total-IoU one-to-one matching."""
    if not 0 < threshold <= 1:
        raise BenchmarkValidationError("span matching threshold must be in (0, 1]")
    human = sorted(
        (_match_span(item, "human") for item in human_spans), key=lambda item: item[0]
    )
    judge = sorted(
        (_match_span(item, "judge") for item in judge_spans), key=lambda item: item[0]
    )
    if len({item[0] for item in human}) != len(human):
        raise BenchmarkValidationError("human spans contain duplicate claim_id")
    if len({item[0] for item in judge}) != len(judge):
        raise BenchmarkValidationError("judge spans contain duplicate claim_id")
    matched_human: set[str] = set()
    matched_judge: set[str] = set()
    matches: list[dict[str, Any]] = []
    for human_id, start, end in human:
        exact = next(
            (
                judge_id
                for judge_id, judge_start, judge_end in judge
                if judge_id not in matched_judge
                and start == judge_start
                and end == judge_end
            ),
            None,
        )
        if exact is not None:
            matched_human.add(human_id)
            matched_judge.add(exact)
            matches.append(
                {"human_id": human_id, "judge_id": exact, "match": "EXACT", "iou": 1.0}
            )
    remaining_human = [item for item in human if item[0] not in matched_human]
    remaining_judge = [item for item in judge if item[0] not in matched_judge]
    assignment = _maximum_assignment(remaining_human, remaining_judge, threshold)
    for human_index, judge_index, iou in assignment:
        human_id = remaining_human[human_index][0]
        judge_id = remaining_judge[judge_index][0]
        matched_human.add(human_id)
        matched_judge.add(judge_id)
        matches.append(
            {
                "human_id": human_id,
                "judge_id": judge_id,
                "match": "OVERLAP",
                "iou": round(float(iou), 12),
            }
        )
    matches.sort(key=lambda item: (str(item["human_id"]), str(item["judge_id"])))
    return {
        "matching_policy_version": "exact-then-max-iou/v1",
        "threshold": threshold,
        "matches": matches,
        "unmatched_human": sorted(item[0] for item in human if item[0] not in matched_human),
        "unmatched_judge": sorted(item[0] for item in judge if item[0] not in matched_judge),
        "exact_matches": sum(item["match"] == "EXACT" for item in matches),
        "overlap_matches": sum(item["match"] == "OVERLAP" for item in matches),
    }


def build_agreement_report(
    human: Mapping[str, Any],
    judge: Mapping[str, Any],
    *,
    benchmark_version: str,
    judge_version: str,
    stratum_coverage: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Build target-specific descriptive agreement from normalized labels."""
    target = _target(human.get("target"))
    if judge.get("target") != target:
        raise BenchmarkValidationError("agreement targets do not match")
    report: dict[str, Any] = {
        "benchmark_version": benchmark_version,
        "judge_version": judge_version,
        "target": target,
        "descriptive_only": True,
        "stratum_coverage": dict(stratum_coverage or {}),
    }
    human_labels = _mapping(human.get("labels"), "human.labels")
    judge_labels = _mapping(judge.get("labels"), "judge.labels")
    if target == "ATTRIBUTION":
        human_claims = _array(human_labels.get("claims"), "human.labels.claims")
        judge_claims = _array(judge_labels.get("claims"), "judge.labels.claims")
        span_report = match_spans(
            [
                {"claim_id": item["claim_id"], **item["answer_span"]}
                for item in human_claims
            ],
            [
                {"claim_id": item["claim_id"], **item["answer_span"]}
                for item in judge_claims
            ],
        )
        human_by_id = {item["claim_id"]: item for item in human_claims}
        judge_by_id = {item["claim_id"]: item for item in judge_claims}
        relation_pairs: list[tuple[str, str]] = []
        evidence_human: list[dict[str, Any]] = []
        evidence_judge: list[dict[str, Any]] = []
        for match in span_report["matches"]:
            human_claim = human_by_id[match["human_id"]]
            judge_claim = judge_by_id[match["judge_id"]]
            human_relations = _relations_by_occurrence(human_claim)
            judge_relations = _relations_by_occurrence(judge_claim)
            for occurrence in sorted(set(human_relations) | set(judge_relations)):
                human_relation = human_relations.get(occurrence)
                judge_relation = judge_relations.get(occurrence)
                relation_pairs.append(
                    (
                        str(human_relation.get("relation")) if human_relation else "UNAVAILABLE",
                        str(judge_relation.get("relation")) if judge_relation else "UNAVAILABLE",
                    )
                )
                if human_relation and judge_relation and occurrence != "__unsupported__":
                    human_span = human_relation.get("evidence_span")
                    judge_span = judge_relation.get("evidence_span")
                    if isinstance(human_span, Mapping) and isinstance(judge_span, Mapping):
                        prefix = f"{match['human_id']}:{occurrence}"
                        evidence_human.append(
                            {"claim_id": prefix, "start": human_span["start"], "end": human_span["end"]}
                        )
                        evidence_judge.append(
                            {"claim_id": prefix, "start": judge_span["start"], "end": judge_span["end"]}
                        )
        for human_id in span_report["unmatched_human"]:
            for relation in _relations_by_occurrence(human_by_id[human_id]).values():
                relation_pairs.append((str(relation.get("relation")), "UNAVAILABLE"))
        for judge_id in span_report["unmatched_judge"]:
            for relation in _relations_by_occurrence(judge_by_id[judge_id]).values():
                relation_pairs.append(("UNAVAILABLE", str(relation.get("relation"))))
        evidence_span_report = match_spans(evidence_human, evidence_judge)
        human_policies = _policies_by_occurrence(human_labels)
        judge_policies = _policies_by_occurrence(judge_labels)
        policy_keys = sorted(set(human_policies) | set(judge_policies))
        applicability_pairs = [
            (
                str(human_policies[key].get("applicability")) if key in human_policies else "UNAVAILABLE",
                str(judge_policies[key].get("applicability")) if key in judge_policies else "UNAVAILABLE",
            )
            for key in policy_keys
        ]
        compliance_pairs = [
            (
                str(human_policies[key].get("compliance")) if key in human_policies else "UNAVAILABLE",
                str(judge_policies[key].get("compliance")) if key in judge_policies else "UNAVAILABLE",
            )
            for key in policy_keys
        ]
        report.update(
            {
                "span_matching": span_report,
                "relation_agreement": _label_agreement(relation_pairs),
                "evidence_span_matching": evidence_span_report,
                "policy_applicability_agreement": _label_agreement(applicability_pairs),
                "policy_compliance_agreement": _label_agreement(compliance_pairs),
                "unavailable_denominator": len(span_report["unmatched_human"])
                + len(span_report["unmatched_judge"]),
            }
        )
    else:
        human_dimensions = {
            item["module"]: int(item["score"])
            for item in _array(human_labels.get("dimensions"), "human.labels.dimensions")
        }
        judge_dimensions = {
            item["module"]: int(item["score"])
            for item in _array(judge_labels.get("dimensions"), "judge.labels.dimensions")
        }
        modules = sorted(set(human_dimensions) & set(judge_dimensions))
        pairs = [(human_dimensions[module], judge_dimensions[module]) for module in modules]
        human_red = {
            item["id"]: bool(item["triggered"])
            for item in _array(human_labels.get("red_lines"), "human.labels.red_lines")
        }
        judge_red = {
            item["id"]: bool(item["triggered"])
            for item in _array(judge_labels.get("red_lines"), "judge.labels.red_lines")
        }
        red_ids = sorted(set(human_red) & set(judge_red))
        report.update(
            {
                "ordinal_exact_agreement": (
                    sum(left == right for left, right in pairs) / len(pairs) if pairs else None
                ),
                "ordinal_weighted_kappa": _weighted_kappa(pairs),
                "red_line_agreement": _label_agreement(
                    [(human_red[item], judge_red[item]) for item in red_ids]
                ),
                "unavailable_denominator": (
                    len(set(human_dimensions) ^ set(judge_dimensions))
                    + len(set(human_red) ^ set(judge_red))
                ),
            }
        )
    return report


def classify_measurement_change(
    change: str, *, lossless: bool = False
) -> dict[str, str]:
    matrix = {
        "JUDGE_ONLY": ("RERUN_FROZEN_BENCHMARK", "APPEND_JUDGE_RUN"),
        "RUBRIC_SEMANTICS": ("RELABEL", "SUPERSEDE_VERSION"),
        "SCHEMA_SEMANTICS": ("RELABEL", "SUPERSEDE_VERSION"),
        "PROMPT_CONTEXT": ("REGENERATE_AND_RELABEL", "SUPERSEDE_VERSION"),
        "BOUND_ARTIFACT": ("REGENERATE_AND_RELABEL", "SUPERSEDE_VERSION"),
        "POPULATION_COHORT": ("RESELECT_AND_RELABEL", "SUPERSEDE_VERSION"),
    }
    if change == "SCHEMA_REPRESENTATION":
        if not lossless:
            raise BenchmarkValidationError(
                "schema representation change requires a recorded lossless adapter"
            )
        return {"action": "APPLY_LOSSLESS_ADAPTER", "version_action": "KEEP_VERSION"}
    if change not in matrix:
        raise BenchmarkValidationError(f"unknown measurement change {change}")
    action, version_action = matrix[change]
    return {"action": action, "version_action": version_action}


def _population_item(value: Mapping[str, Any], index: int) -> dict[str, Any]:
    item = _mapping(value, f"population[{index}]")
    strata = item.get("strata")
    if not isinstance(strata, list) or not strata or any(
        not isinstance(value, str) or not value.strip() for value in strata
    ):
        raise BenchmarkValidationError(f"population[{index}].strata must be non-empty")
    normalized = {
        "item_id": _text(item.get("item_id"), f"population[{index}].item_id"),
        "case_id": _text(item.get("case_id"), f"population[{index}].case_id"),
        "turn": _positive_int(item.get("turn"), f"population[{index}].turn"),
        "output_id": _text(item.get("output_id"), f"population[{index}].output_id"),
        "observed_strata": sorted(set(strata)),
        "answer_sha256": _sha256(
            item.get("answer_sha256"), f"population[{index}].answer_sha256"
        ),
        "context_sha256": _sha256(
            item.get("context_sha256"), f"population[{index}].context_sha256"
        ),
        "target_input_sha256": _sha256(
            item.get("target_input_sha256"),
            f"population[{index}].target_input_sha256",
        ),
    }
    answer = item.get("answer")
    if answer is not None:
        if not isinstance(answer, str) or hashlib.sha256(answer.encode()).hexdigest() != normalized["answer_sha256"]:
            raise BenchmarkValidationError(
                f"population[{index}].answer does not match answer_sha256"
            )
    return normalized


def _targets(value: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(value, Mapping) or not value:
        raise BenchmarkValidationError("stratum_targets must be a non-empty object")
    result: dict[str, int] = {}
    for raw_name, target in value.items():
        name = _text(raw_name, "stratum target name")
        if isinstance(target, bool) or not isinstance(target, int) or target < 1:
            raise BenchmarkValidationError(f"stratum target {name} must be positive")
        result[name] = target
    return result


def _validate_manifest_digest(manifest: Mapping[str, Any]) -> None:
    root = dict(_mapping(manifest, "manifest"))
    if root.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise BenchmarkValidationError("unsupported benchmark manifest schema")
    digest = root.pop("manifest_digest", None)
    if not isinstance(digest, str) or digest != _digest(root):
        raise BenchmarkValidationError("manifest_digest does not match immutable content")
    if not isinstance(root.get("items"), list):
        raise BenchmarkValidationError("manifest.items must be an array")


def _attribution_labels(labels: Mapping[str, Any], item: Mapping[str, Any]) -> dict[str, Any]:
    answer = item.get("answer")
    if not isinstance(answer, str):
        raise BenchmarkValidationError("bound item requires answer text for span validation")
    evidence_catalog = item.get("evidence_catalog")
    if not isinstance(evidence_catalog, Mapping):
        raise BenchmarkValidationError("bound item requires evidence_catalog for attribution")
    claims: list[dict[str, Any]] = []
    for index, raw_claim in enumerate(_array(labels.get("claims"), "labels.claims")):
        claim = _mapping(raw_claim, f"labels.claims[{index}]")
        claim_id = _text(claim.get("claim_id"), f"labels.claims[{index}].claim_id")
        kind = claim.get("kind")
        if kind not in CLAIM_KINDS:
            raise BenchmarkValidationError(f"labels.claims[{index}].kind is invalid")
        relations: list[dict[str, Any]] = []
        for relation_index, raw_relation in enumerate(
            _array(claim.get("relations"), f"labels.claims[{index}].relations")
        ):
            relation = _mapping(
                raw_relation, f"labels.claims[{index}].relations[{relation_index}]"
            )
            relation_name = relation.get("relation")
            if relation_name not in RELATIONS:
                raise BenchmarkValidationError("annotation relation is invalid")
            ref = relation.get("evidence_ref")
            span = relation.get("evidence_span")
            if relation_name == "UNSUPPORTED":
                if ref is not None or span is not None:
                    raise BenchmarkValidationError("UNSUPPORTED annotation has no evidence")
                relations.append(
                    {"relation": relation_name, "evidence_ref": None, "evidence_span": None}
                )
                continue
            if not isinstance(ref, str) or ref not in evidence_catalog:
                raise BenchmarkValidationError("annotation has unknown evidence_ref")
            evidence_text, _ = _evidence_entry(evidence_catalog[ref], ref)
            relations.append(
                {
                    "relation": relation_name,
                    "evidence_ref": ref,
                    "evidence_span": _bound_span(span, evidence_text, "evidence_span"),
                }
            )
        categories = {relation["relation"] for relation in relations}
        unsupported_category = claim.get("unsupported_category")
        if "UNSUPPORTED" in categories:
            if len(relations) != 1 or unsupported_category not in UNSUPPORTED_CATEGORIES:
                raise BenchmarkValidationError(
                    "UNSUPPORTED claim requires one relation and a supported category"
                )
        elif unsupported_category is not None:
            raise BenchmarkValidationError(
                "unsupported_category is only valid for UNSUPPORTED claims"
            )
        claims.append(
            {
                "claim_id": claim_id,
                "kind": kind,
                "answer_span": _bound_span(
                    claim.get("answer_span"), answer, "answer_span"
                ),
                "relations": relations,
                "unsupported_category": unsupported_category,
            }
        )
    if len({claim["claim_id"] for claim in claims}) != len(claims):
        raise BenchmarkValidationError("annotation claims require unique claim_id")
    policies: list[dict[str, Any]] = []
    for index, raw_policy in enumerate(_array(labels.get("policies"), "labels.policies")):
        policy = _mapping(raw_policy, f"labels.policies[{index}]")
        policy_id = _text(policy.get("policy_id"), f"labels.policies[{index}].policy_id")
        evidence_ref = _text(
            policy.get("evidence_ref"), f"labels.policies[{index}].evidence_ref"
        )
        if evidence_ref not in evidence_catalog:
            raise BenchmarkValidationError("policy annotation has unknown evidence_ref")
        _, policy_ids = _evidence_entry(evidence_catalog[evidence_ref], evidence_ref)
        if policy_id not in policy_ids:
            raise BenchmarkValidationError(
                "policy_id is not bound to the evidence occurrence"
            )
        applicability = policy.get("applicability")
        compliance = policy.get("compliance")
        if applicability not in {"APPLICABLE", "NOT_APPLICABLE", "UNCERTAIN"}:
            raise BenchmarkValidationError("policy applicability is invalid")
        valid_compliance = {
            "APPLICABLE": {"COMPLIANT", "PARTIAL", "NON_COMPLIANT"},
            "NOT_APPLICABLE": {"NOT_APPLICABLE"},
            "UNCERTAIN": {"UNCERTAIN"},
        }
        if compliance not in valid_compliance[applicability]:
            raise BenchmarkValidationError(
                "policy compliance is incompatible with applicability"
            )
        answer_spans = [
            _bound_span(span, answer, "policy.answer_spans[]")
            for span in _array(policy.get("answer_spans"), "policy.answer_spans")
        ]
        policies.append(
            {
                "policy_id": policy_id,
                "evidence_ref": evidence_ref,
                "applicability": applicability,
                "compliance": compliance,
                "answer_spans": answer_spans,
            }
        )
    policy_keys = [(policy["policy_id"], policy["evidence_ref"]) for policy in policies]
    if len(set(policy_keys)) != len(policy_keys):
        raise BenchmarkValidationError("policy annotations must be unique per occurrence")
    return {"claims": claims, "policies": policies}


def _quality_labels(labels: Mapping[str, Any]) -> dict[str, Any]:
    dimensions: list[dict[str, Any]] = []
    for raw in _array(labels.get("dimensions"), "labels.dimensions"):
        item = _mapping(raw, "labels.dimensions[]")
        score = item.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or score not in {0, 1, 2, 3}:
            raise BenchmarkValidationError("quality dimension score must be 0, 1, 2, or 3")
        dimensions.append(
            {"module": _text(item.get("module"), "dimension.module"), "score": score}
        )
    red_lines: list[dict[str, Any]] = []
    for raw in _array(labels.get("red_lines"), "labels.red_lines"):
        item = _mapping(raw, "labels.red_lines[]")
        triggered = item.get("triggered")
        if not isinstance(triggered, bool):
            raise BenchmarkValidationError("red line triggered must be boolean")
        red_lines.append(
            {"id": _text(item.get("id"), "red_line.id"), "triggered": triggered}
        )
    if len({item["module"] for item in dimensions}) != len(dimensions):
        raise BenchmarkValidationError("quality dimensions must be unique")
    if len({item["id"] for item in red_lines}) != len(red_lines):
        raise BenchmarkValidationError("red lines must be unique")
    return {"dimensions": dimensions, "red_lines": red_lines}


def _maximum_assignment(
    human: Sequence[tuple[str, int, int]],
    judge: Sequence[tuple[str, int, int]],
    threshold: float,
) -> list[tuple[int, int, Fraction]]:
    if not human or not judge:
        return []
    threshold_fraction = Fraction(str(threshold))
    columns = len(judge) + len(human)
    weights: list[list[Fraction]] = []
    for _, start, end in human:
        row: list[Fraction] = []
        for _, judge_start, judge_end in judge:
            intersection = max(0, min(end, judge_end) - max(start, judge_start))
            union = max(end, judge_end) - min(start, judge_start)
            iou = Fraction(intersection, union) if union else Fraction(0)
            row.append(iou if iou >= threshold_fraction else Fraction(-1))
        row.extend(Fraction(0) for _ in human)
        weights.append(row)
    assignment = _hungarian_max(weights)
    result: list[tuple[int, int, Fraction]] = []
    for human_index, column in enumerate(assignment):
        if column < len(judge) and weights[human_index][column] >= threshold_fraction:
            result.append((human_index, column, weights[human_index][column]))
    return result


def _hungarian_max(weights: Sequence[Sequence[Fraction]]) -> list[int]:
    """Rectangular Hungarian assignment; sorted inputs make ties deterministic."""
    row_count = len(weights)
    column_count = len(weights[0])
    if row_count > column_count:
        raise BenchmarkValidationError("assignment requires at least as many columns as rows")
    u = [Fraction(0) for _ in range(row_count + 1)]
    v = [Fraction(0) for _ in range(column_count + 1)]
    p = [0 for _ in range(column_count + 1)]
    way = [0 for _ in range(column_count + 1)]
    for row in range(1, row_count + 1):
        p[0] = row
        column0 = 0
        minv: list[Fraction | None] = [None for _ in range(column_count + 1)]
        used = [False for _ in range(column_count + 1)]
        while True:
            used[column0] = True
            row0 = p[column0]
            delta: Fraction | None = None
            column1 = 0
            for column in range(1, column_count + 1):
                if used[column]:
                    continue
                cost = -weights[row0 - 1][column - 1]
                current = cost - u[row0] - v[column]
                if minv[column] is None or current < minv[column]:
                    minv[column] = current
                    way[column] = column0
                if delta is None or minv[column] < delta:
                    delta = minv[column]
                    column1 = column
            if delta is None:
                raise BenchmarkValidationError("span assignment failed")
            for column in range(column_count + 1):
                if used[column]:
                    u[p[column]] += delta
                    v[column] -= delta
                elif minv[column] is not None:
                    minv[column] -= delta
            column0 = column1
            if p[column0] == 0:
                break
        while True:
            column1 = way[column0]
            p[column0] = p[column1]
            column0 = column1
            if column0 == 0:
                break
    assignment = [column_count for _ in range(row_count)]
    for column in range(1, column_count + 1):
        if p[column]:
            assignment[p[column] - 1] = column - 1
    return assignment


def _match_span(value: Mapping[str, Any], side: str) -> tuple[str, int, int]:
    item = _mapping(value, f"{side} span")
    identifier = _text(item.get("claim_id"), f"{side} span claim_id")
    start = item.get("start")
    end = item.get("end")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end <= start
    ):
        raise BenchmarkValidationError(f"{side} span is invalid")
    return identifier, start, end


def _bound_span(value: Any, content: str, location: str) -> dict[str, Any]:
    item = _mapping(value, location)
    start = item.get("start")
    end = item.get("end")
    if (
        isinstance(start, bool)
        or isinstance(end, bool)
        or not isinstance(start, int)
        or not isinstance(end, int)
        or start < 0
        or end <= start
        or end > len(content)
    ):
        raise BenchmarkValidationError(f"{location} must be a valid half-open span")
    text = item.get("text")
    if not isinstance(text, str) or text != content[start:end]:
        raise BenchmarkValidationError(f"{location}.text does not match bound content")
    return {"start": start, "end": end, "text": text}


def _primary_relation(claim: Mapping[str, Any]) -> str:
    relations = claim.get("relations")
    if not isinstance(relations, list) or not relations:
        return "UNAVAILABLE"
    precedence = {"ENTAILS": 5, "PARTIAL": 4, "CONTRADICTS": 3, "CONTEXT_ONLY": 2, "UNSUPPORTED": 1}
    return max(
        (str(item.get("relation")) for item in relations if isinstance(item, Mapping)),
        key=lambda label: precedence.get(label, 0),
        default="UNAVAILABLE",
    )


def _relations_by_occurrence(claim: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = claim.get("relations")
    if not isinstance(rows, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for relation in rows:
        if not isinstance(relation, Mapping):
            continue
        ref = relation.get("evidence_ref")
        key = str(ref) if isinstance(ref, str) else "__unsupported__"
        result[key] = relation
    return result


def _policies_by_occurrence(labels: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    rows = labels.get("policies")
    if not isinstance(rows, list):
        return {}
    result: dict[str, Mapping[str, Any]] = {}
    for policy in rows:
        if not isinstance(policy, Mapping):
            continue
        ref = policy.get("evidence_ref")
        policy_id = policy.get("policy_id")
        if isinstance(ref, str) and isinstance(policy_id, str):
            result[f"{policy_id}:{ref}"] = policy
    return result


def _evidence_entry(value: Any, ref: str) -> tuple[str, Sequence[str]]:
    if isinstance(value, str):
        return value, ()
    item = _mapping(value, f"evidence_catalog[{ref}]")
    content = item.get("content")
    if not isinstance(content, str) or not content:
        raise BenchmarkValidationError("annotation evidence content must be non-empty text")
    policy_ids = item.get("policy_ids", [])
    if not isinstance(policy_ids, list) or any(
        not isinstance(policy_id, str) or not policy_id.strip() for policy_id in policy_ids
    ):
        raise BenchmarkValidationError("annotation evidence policy_ids must be strings")
    return content, policy_ids


def _verify_submission_id(submission: Mapping[str, Any]) -> None:
    supplied = submission.get("submission_id")
    if not isinstance(supplied, str) or not supplied.startswith("HBA-"):
        raise BenchmarkValidationError("submission_id is missing")
    payload = {key: value for key, value in submission.items() if key != "submission_id"}
    expected = "HBA-" + _digest(payload)[:24]
    if supplied != expected:
        raise BenchmarkValidationError("submission_id does not match immutable content")


def _label_agreement(pairs: Sequence[tuple[Any, Any]]) -> dict[str, Any]:
    matrix: dict[str, dict[str, int]] = {}
    for expected, actual in pairs:
        row = matrix.setdefault(str(expected), {})
        row[str(actual)] = row.get(str(actual), 0) + 1
    labels = sorted({str(label) for pair in pairs for label in pair})
    per_label: dict[str, dict[str, Any]] = {}
    for label in labels:
        tp = sum(str(left) == label and str(right) == label for left, right in pairs)
        fp = sum(str(left) != label and str(right) == label for left, right in pairs)
        fn = sum(str(left) == label and str(right) != label for left, right in pairs)
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        per_label[label] = {
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    f1s = [item["f1"] for item in per_label.values() if item["f1"] is not None]
    correct = sum(left == right for left, right in pairs)
    return {
        "evaluated": len(pairs),
        "accuracy": correct / len(pairs) if pairs else None,
        "micro_f1": correct / len(pairs) if pairs else None,
        "macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "confusion_matrix": matrix,
        "per_label": per_label,
    }


def _weighted_kappa(pairs: Sequence[tuple[int, int]]) -> float | None:
    if not pairs:
        return None
    labels = sorted({value for pair in pairs for value in pair})
    if len(labels) == 1:
        return 1.0
    maximum = max(labels) - min(labels)
    observed = sum(((left - right) / maximum) ** 2 for left, right in pairs) / len(pairs)
    left = Counter(pair[0] for pair in pairs)
    right = Counter(pair[1] for pair in pairs)
    expected = sum(
        left[a] * right[b] * ((a - b) / maximum) ** 2
        for a in labels
        for b in labels
    ) / (len(pairs) ** 2)
    return 1 - observed / expected if expected else 1.0


def _digest(value: Any) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _mapping(value: Any, location: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise BenchmarkValidationError(f"{location} must be an object")
    return value


def _array(value: Any, location: str) -> list[Any]:
    if not isinstance(value, list):
        raise BenchmarkValidationError(f"{location} must be an array")
    return value


def _text(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise BenchmarkValidationError(f"{location} must be non-empty text")
    return value.strip()


def _target(value: Any) -> str:
    if value not in TARGETS:
        raise BenchmarkValidationError(f"target must be one of {sorted(TARGETS)}")
    return str(value)


def _sha256(value: Any, location: str) -> str:
    text = _text(value, location)
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise BenchmarkValidationError(f"{location} must be a lowercase SHA-256 digest")
    return text


def _positive_int(value: Any, location: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1:
        raise BenchmarkValidationError(f"{location} must be a positive integer")
    return value


def _timestamp(value: Any) -> str:
    text = _text(value, "submitted_at")
    try:
        parsed = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise BenchmarkValidationError("submitted_at must be ISO 8601") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise BenchmarkValidationError("submitted_at must include timezone")
    return text
