"""Controlled orchestration for recommendation experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Callable, Mapping, Sequence

from .baseline import BaselineDiff, compare_baseline
from .config import EvaluatorConfig
from .experiments import enforce_single_variable
from .recommendations import RecommendationEvidence, recommend


@dataclass(frozen=True)
class VariantRun:
    seed: int
    records: tuple[Mapping[str, Any], ...]
    manifest: Mapping[str, Any]
    artifact_dir: str


def run_auto_experiment(
    *, baseline_records: Sequence[Mapping[str, Any]], baseline_manifest: Mapping[str, Any],
    recommendation: Mapping[str, Any], target_cohort: str, config: EvaluatorConfig,
    output: Path, runner: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    target = str(recommendation.get("target", ""))
    variant = recommendation.get("variant", {})
    candidate = variant.get("candidate") if isinstance(variant, Mapping) else None
    if target not in config.parameters:
        raise ValueError(f"automatic experiment target is not registered: {target}")
    baseline_settings = _settings(baseline_manifest, config.parameters)
    variant_settings = dict(baseline_settings)
    variant_settings[target] = candidate
    change = enforce_single_variable(baseline_settings, variant_settings, config.parameters)

    runs: list[VariantRun] = []
    diffs: list[BaselineDiff] = []
    for seed in config.experiment.seeds:
        response = runner({
            "seed": seed, "target": target, "baseline": change.baseline_value,
            "candidate": change.variant_value, "recommendation": recommendation,
            "baseline_manifest": baseline_manifest,
            "baseline_case_ids": [str(row["case_id"]) for row in baseline_records],
        })
        records = tuple(response.get("records", ()))
        manifest = response.get("manifest", {})
        if not records or not isinstance(manifest, Mapping):
            raise ValueError(f"variant runner returned incomplete seed {seed} result")
        if manifest.get("seed") != seed:
            raise ValueError(f"variant runner manifest seed mismatch: {manifest.get('seed')} != {seed}")
        enforce_single_variable(baseline_settings, _settings(manifest, config.parameters), config.parameters)
        diff = compare_baseline(baseline_records, records)
        if not diff.comparable:
            raise ValueError(f"variant seed {seed} case set differs from baseline")
        runs.append(VariantRun(seed, records, manifest, str(response.get("artifact_dir", ""))))
        diffs.append(diff)

    evidence = RecommendationEvidence(
        repeats=len(runs),
        target_pass_rate_deltas=tuple(_cohort(diff, target_cohort).pass_rate_delta for diff in diffs),
        weighted_total_deltas=tuple(diff.global_delta.weighted_total_delta for diff in diffs),
        max_non_target_regression=max((max(0.0, -delta.weighted_total_delta)
            for diff in diffs for name, delta in diff.cohorts.items() if name != target_cohort), default=0.0),
        critical_hard_gate_regressions=sum(_critical_regressions(baseline_records, run.records) for run in runs),
    )
    verdict = recommend(
        recommendation_id=f"AUTO-{recommendation.get('recommendation_id', target)}",
        lever_type=str(recommendation.get("lever_type", "hyperparameter")), target=target,
        affected_cases=[str(row["case_id"]) for row in baseline_records],
        affected_cohorts=[target_cohort], trace_evidence_refs=recommendation.get("trace_evidence_refs", ()),
        rationale="Automated three-seed controlled variant comparison", variant={"candidate": candidate},
        evidence=evidence, thresholds=config.experiment,
    )
    report = {"schema_version": "1.0", "change": asdict(change), "runs": [
        {"seed": run.seed, "artifact_dir": run.artifact_dir, "global_delta": asdict(diff.global_delta),
         "target_cohort_delta": asdict(_cohort(diff, target_cohort))}
        for run, diff in zip(runs, diffs)
    ], "evidence": asdict(evidence), "verdict": asdict(verdict)}
    return report


def run_auto_file_experiment(
    *, recommendation: Mapping[str, Any], target_cohort: str, config: EvaluatorConfig,
    output: Path, runner: Callable[[Mapping[str, Any]], Mapping[str, Any]],
) -> Mapping[str, Any]:
    """Run same-snapshot baseline/variant pairs for an allowlisted file proposal."""
    proposal = recommendation.get("variant", {}).get("proposal") if isinstance(recommendation.get("variant"), Mapping) else None
    if not isinstance(proposal, Mapping):
        raise ValueError("file recommendation variant.proposal must be an object")
    runs = []
    diffs = []
    critical = 0
    for seed in config.experiment.seeds:
        response = runner({"seed": seed, "proposal": proposal, "recommendation": recommendation})
        baseline = tuple(response.get("baseline_records", ()))
        variant = tuple(response.get("records", ()))
        if not baseline or not variant:
            raise ValueError(f"file variant runner returned incomplete seed {seed} result")
        diff = compare_baseline(baseline, variant)
        if not diff.comparable:
            raise ValueError(f"file variant seed {seed} case set differs from baseline")
        diffs.append(diff)
        critical += _critical_regressions(baseline, variant)
        runs.append({"seed": seed, "baseline_artifact_dir": str(response.get("baseline_artifact_dir", "")),
                     "artifact_dir": str(response.get("artifact_dir", "")), "change": response.get("change", {}),
                     "global_delta": asdict(diff.global_delta), "target_cohort_delta": asdict(_cohort(diff, target_cohort))})
    evidence = RecommendationEvidence(
        repeats=len(runs),
        target_pass_rate_deltas=tuple(_cohort(diff, target_cohort).pass_rate_delta for diff in diffs),
        weighted_total_deltas=tuple(diff.global_delta.weighted_total_delta for diff in diffs),
        max_non_target_regression=max((max(0.0, -delta.weighted_total_delta)
            for diff in diffs for name, delta in diff.cohorts.items() if name != target_cohort), default=0.0),
        critical_hard_gate_regressions=critical,
    )
    verdict = recommend(
        recommendation_id=f"AUTO-{recommendation.get('recommendation_id', 'file-variant')}",
        lever_type=str(recommendation.get("lever_type", "knowledge")), target="capsule_ground_nodes",
        affected_cases=sorted({case for run in runs for case in ()}), affected_cohorts=[target_cohort],
        trace_evidence_refs=recommendation.get("trace_evidence_refs", ()),
        rationale="Automated same-snapshot file variant comparison", variant={"proposal": proposal},
        evidence=evidence, thresholds=config.experiment,
    )
    report = {"schema_version": "1.0", "experiment_type": "capsule_ground_nodes",
              "proposal": proposal, "runs": runs, "evidence": asdict(evidence), "verdict": asdict(verdict)}
    return report


def _settings(manifest: Mapping[str, Any], registry: Mapping[str, Any]) -> dict[str, Any]:
    hyper = manifest.get("hyperparameters", {})
    return {path: hyper[path] for path in registry if isinstance(hyper, Mapping) and path in hyper}


def _cohort(diff: BaselineDiff, name: str):
    if name not in diff.cohorts:
        raise ValueError(f"target cohort is absent: {name}")
    return diff.cohorts[name]


def _critical_regressions(before, after) -> int:
    old = {str(row["case_id"]): row for row in before}
    return sum(1 for row in after if "critical" in row.get("cohorts", {}).get("risk", ())
               and str(old.get(str(row["case_id"]), {}).get("status", "")).upper() == "PASS"
               and str(row.get("status", "")).upper() != "PASS")


def _markdown(report: Mapping[str, Any]) -> str:
    verdict = report["verdict"]
    lines = ["# Automated Experiment Report", "", f"Verdict: `{verdict['status']}` ({verdict['action_label']})", "",
             f"Target: `{report['change']['path']}`", f"Baseline: `{report['change']['baseline_value']}`",
             f"Candidate: `{report['change']['variant_value']}`", "", "## Repeated Runs", "",
             "| Seed | Weighted total delta | Target cohort pass-rate delta |", "| ---: | ---: | ---: |"]
    for run in report["runs"]:
        lines.append(f"| {run['seed']} | {run['global_delta']['weighted_total_delta']:.4f} | {run['target_cohort_delta']['pass_rate_delta']:.4f} |")
    lines.extend(["", "## Guardrails", "", f"- Critical hard-gate regressions: `{report['evidence']['critical_hard_gate_regressions']}`",
                  f"- Max non-target regression: `{report['evidence']['max_non_target_regression']:.4f}`", ""])
    return "\n".join(lines)


def _file_markdown(report: Mapping[str, Any]) -> str:
    verdict = report["verdict"]
    proposal = report["proposal"]
    lines = ["# Automated File Experiment Report", "", f"Verdict: `{verdict['status']}` ({verdict['action_label']})", "",
             f"Experiment: `{report['experiment_type']}`", f"Entity: `{proposal['target']['entity_id']}`",
             f"Field: `{proposal['target']['field']}`", "", "## Repeated Same-Snapshot Runs", "",
             "| Seed | Weighted total delta | Target cohort pass-rate delta |", "| ---: | ---: | ---: |"]
    for run in report["runs"]:
        lines.append(f"| {run['seed']} | {run['global_delta']['weighted_total_delta']:.4f} | {run['target_cohort_delta']['pass_rate_delta']:.4f} |")
    lines.extend(["", "## Guardrails", "", "- Main workspace modified: `no`",
                  f"- Critical hard-gate regressions: `{report['evidence']['critical_hard_gate_regressions']}`",
                  f"- Max non-target regression: `{report['evidence']['max_non_target_regression']:.4f}`", ""])
    return "\n".join(lines)
