"""Reproducible semantic attribution metrics over validated turn facts."""

from __future__ import annotations

from collections import Counter
from typing import Any, Mapping, Sequence


SUBSTANTIVE_KINDS = frozenset(
    {"FACTUAL", "INTERPRETIVE", "RECOMMENDATION", "ACTION"}
)
LAYERS = ("PROMPT", "CAPSULE", "WIKI", "SOURCE", "CURRENT_INPUT", "PRIOR_USER", "PRIOR_ASSISTANT")
SUPPORT_WEIGHTS = {"ENTAILS": 1.0, "PARTIAL": 0.5}
NO_CAPSULE_COHORTS = (
    "baseline_appropriate",
    "capsule_missed",
    "crisis_short_circuited",
    "injection_failed",
)


def summarize_semantic_attribution(
    turns: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Aggregate eligible attribution facts without treating provenance as a gate."""
    available_turns = 0
    unavailable_turns = 0
    skipped_turns = 0
    substantive_weight = 0.0
    overall_support = 0.0
    layer_support = {layer: 0.0 for layer in LAYERS}
    relation_counts: Counter[str] = Counter()
    unsupported: Counter[str] = Counter()
    occurrence_layers: dict[str, str] = {}
    used_occurrences: set[str] = set()
    policy_denominator = 0
    policy_weighted = 0.0
    policy_uncertain = 0
    policy_not_applicable = 0
    cohorts = {cohort: 0 for cohort in NO_CAPSULE_COHORTS}
    judge_versions: set[str] = set()
    benchmark_statuses: set[str] = set()
    benchmark_versions: set[str] = set()

    for turn in turns:
        cohort = turn.get("capsule_cohort")
        if cohort in cohorts:
            cohorts[str(cohort)] += 1
        status = turn.get("status")
        if status == "UNAVAILABLE":
            unavailable_turns += 1
            continue
        if status in {"SKIPPED", "NOT_APPLICABLE"}:
            skipped_turns += 1
            continue
        if status != "AVAILABLE":
            unavailable_turns += 1
            continue
        available_turns += 1
        judge_version = turn.get("judge_version")
        if isinstance(judge_version, str) and judge_version:
            judge_versions.add(judge_version)
        benchmark = turn.get("benchmark")
        benchmark = benchmark if isinstance(benchmark, Mapping) else {}
        benchmark_status = benchmark.get("status", "NOT_MEASURED")
        if isinstance(benchmark_status, str):
            benchmark_statuses.add(benchmark_status)
        benchmark_version = benchmark.get("version")
        if isinstance(benchmark_version, str) and benchmark_version:
            benchmark_versions.add(benchmark_version)

        catalog = turn.get("evidence_catalog", ())
        catalog_index: dict[str, Mapping[str, Any]] = {}
        if _sequence(catalog):
            for entry in catalog:
                if not isinstance(entry, Mapping):
                    continue
                ref = entry.get("ref")
                occurrence = entry.get("occurrence_id")
                layer = entry.get("layer")
                if not all(isinstance(item, str) and item for item in (ref, occurrence, layer)):
                    continue
                catalog_index[str(ref)] = entry
                occurrence_layers[str(occurrence)] = str(layer)

        claims = turn.get("claims", ())
        if _sequence(claims):
            for claim in claims:
                if not isinstance(claim, Mapping):
                    continue
                relations = claim.get("relations", ())
                relation_rows = (
                    [item for item in relations if isinstance(item, Mapping)]
                    if _sequence(relations)
                    else []
                )
                for relation in relation_rows:
                    name = relation.get("relation")
                    if isinstance(name, str):
                        relation_counts[name] += 1
                    ref = relation.get("evidence_ref")
                    entry = catalog_index.get(str(ref)) if isinstance(ref, str) else None
                    if entry is not None and name in SUPPORT_WEIGHTS:
                        occurrence = entry.get("occurrence_id")
                        if isinstance(occurrence, str):
                            used_occurrences.add(occurrence)
                category = claim.get("unsupported_category")
                if isinstance(category, str):
                    unsupported[category] += 1
                if claim.get("kind") not in SUBSTANTIVE_KINDS:
                    continue
                substantive_weight += 1.0
                overall_support += max(
                    (SUPPORT_WEIGHTS.get(str(row.get("relation")), 0.0) for row in relation_rows),
                    default=0.0,
                )
                per_layer: dict[str, float] = {}
                for relation in relation_rows:
                    ref = relation.get("evidence_ref")
                    entry = catalog_index.get(str(ref)) if isinstance(ref, str) else None
                    if entry is None:
                        continue
                    layer = entry.get("layer")
                    if not isinstance(layer, str) or layer not in layer_support:
                        continue
                    per_layer[layer] = max(
                        per_layer.get(layer, 0.0),
                        SUPPORT_WEIGHTS.get(str(relation.get("relation")), 0.0),
                    )
                for layer, weight in per_layer.items():
                    layer_support[layer] += weight

        policies = turn.get("policies", ())
        if _sequence(policies):
            for policy in policies:
                if not isinstance(policy, Mapping):
                    continue
                applicability = policy.get("applicability")
                if applicability == "UNCERTAIN":
                    policy_uncertain += 1
                    continue
                if applicability == "NOT_APPLICABLE":
                    policy_not_applicable += 1
                    continue
                if applicability != "APPLICABLE":
                    continue
                policy_denominator += 1
                policy_weighted += {
                    "COMPLIANT": 1.0,
                    "PARTIAL": 0.5,
                    "NON_COMPLIANT": 0.0,
                }.get(str(policy.get("compliance")), 0.0)

    by_layer = {
        layer: {
            "supported_weight": layer_support[layer],
            "denominator_weight": substantive_weight,
            "rate": layer_support[layer] / substantive_weight if substantive_weight else None,
        }
        for layer in LAYERS
        if layer_support[layer] or any(value == layer for value in occurrence_layers.values())
    }
    utilization_by_layer: dict[str, dict[str, Any]] = {}
    for layer in sorted(set(occurrence_layers.values())):
        occurrences = {key for key, value in occurrence_layers.items() if value == layer}
        used = occurrences & used_occurrences
        utilization_by_layer[layer] = {
            "used_occurrences": len(used),
            "evaluated_occurrences": len(occurrences),
            "rate": len(used) / len(occurrences) if occurrences else None,
        }
    all_occurrences = set(occurrence_layers)
    used = all_occurrences & used_occurrences
    overall_status = "AVAILABLE" if available_turns else "UNAVAILABLE"
    return {
        "status": overall_status,
        "availability": {
            "evaluated_turns": available_turns,
            "unavailable_turns": unavailable_turns,
            "skipped_turns": skipped_turns,
        },
        "claim_support": {
            "supported_weight": overall_support,
            "denominator_weight": substantive_weight,
            "overall_rate": overall_support / substantive_weight if substantive_weight else None,
            "by_layer": by_layer,
        },
        "relation_counts": dict(sorted(relation_counts.items())),
        "unsupported_content": dict(sorted(unsupported.items())),
        "exposed_unit_utilization": {
            "used_occurrences": len(used),
            "evaluated_occurrences": len(all_occurrences),
            "rate": len(used) / len(all_occurrences) if all_occurrences else None,
            "by_layer": utilization_by_layer,
        },
        "policy_obligation_coverage": {
            "weighted_covered": policy_weighted,
            "denominator": policy_denominator,
            "rate": policy_weighted / policy_denominator if policy_denominator else None,
            "uncertain_applicability": policy_uncertain,
            "not_applicable": policy_not_applicable,
        },
        "no_capsule_cohorts": cohorts,
        "judge_versions": sorted(judge_versions),
        "benchmark_status": _single_or_mixed(benchmark_statuses, "NOT_MEASURED"),
        "benchmark_versions": sorted(benchmark_versions),
        "benchmark_is_descriptive_provenance": True,
    }


def _single_or_mixed(values: set[str], default: str) -> str:
    if not values:
        return default
    if len(values) == 1:
        return next(iter(values))
    return "MIXED"


def _sequence(value: Any) -> bool:
    return isinstance(value, Sequence) and not isinstance(value, (str, bytes))
