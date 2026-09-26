from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict
import hashlib
import importlib
import json
from pathlib import Path
import threading
from typing import Mapping, Sequence

from .scenario_analysis import build_analysis, attach_to_model, append_matrix_sheets
from .knowledge_diagnostics import build_knowledge_diagnostics, detail_rows
from .cost_analysis import build_cost_analysis
from .measurement_cli import register as register_measurements, run as run_measurement
from .auto_experiment import run_auto_experiment, run_auto_file_experiment
from .baseline import compare_baseline, compare_workbook_baseline
from .cases import CaseLoadResult, load_cases
from .checkpoint import JsonlCheckpoint
from .config import load_evaluator_config
from .manifest import RunManifest, SuiteManifest
from .recommendations import (
    RecommendationEvidence,
    recommend,
    recommend_case,
    enrich_recommendation,
)
from .experiments import enforce_single_variable
from .rules import load_rating_rule
from .scoring import SCORING_CONTRACT_VERSION, TurnDimensionFact, fact_dict, score_case_fact, score_scenario
from .stability import summarize_stability
from .deliverables import (
    publish_deliverables,
    validate_pair,
    validate_output_target,
)
from .report_model import build_model_from_rows, build_report_model


PREFLIGHT_ARTIFACTS = {
    "results": "1.1-preflight.json",
    "remediation": "1.2-case-remediation.md",
}

def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command in {'run','matrix','report','cost','route-analysis','import-human-review','export-human-review','refresh-derived-results','merge-subject-results','frozen-calibration','retry-evaluation','retry-subject-lanes'}:
        from .frozen_cli import dispatch
        return dispatch(args)
    if args.command == "measure":
        return run_measurement(args)
    if args.command == "preflight":
        return _preflight(args)
    if args.command == "experiment":
        return _experiment(args)
    if args.command == "auto-experiment":
        return _auto_experiment(args)
    if args.command == "auto-file-experiment":
        return _auto_file_experiment(args)
    if args.command == "stability":
        return _stability(args)
    parser.error(f"unsupported command: {args.command}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog='xiaoan-eval')
    commands = parser.add_subparsers(dest='command', required=True)
    register_measurements(commands)
    from .frozen_cli import register_generation
    register_generation(commands)
    preflight = commands.add_parser('preflight',help='validate cases without provider calls')
    preflight.add_argument('cases')
    preflight.add_argument('--rating-rule',default='ratings rule.yml')
    preflight.add_argument('--output')
    preflight.add_argument('--pii-validator')
    experiment = commands.add_parser("experiment", help="aggregate controlled variant runs")
    experiment.add_argument("--baseline", required=True)
    experiment.add_argument("--variants", nargs="+", required=True)
    experiment.add_argument("--baseline-manifest", required=True)
    experiment.add_argument("--variant-manifests", nargs="+", required=True)
    experiment.add_argument("--target-cohort", required=True)
    experiment.add_argument("--lever-type", required=True)
    experiment.add_argument("--target", required=True)
    experiment.add_argument("--config", default="evaluator-config.yml")
    experiment.add_argument("--output", required=True)
    experiment.add_argument("--pii-validator", metavar="MODULE:CALLABLE")
    automatic = commands.add_parser("auto-experiment", help="execute and validate a recommendation variant")
    automatic.add_argument("--baseline", required=True)
    automatic.add_argument("--baseline-manifest", required=True)
    automatic.add_argument("--recommendation", required=True)
    automatic.add_argument("--target-cohort", required=True)
    automatic.add_argument("--variant-runner-plugin", required=True, metavar="MODULE:CALLABLE")
    automatic.add_argument("--config", default="evaluator-config.yml")
    automatic.add_argument("--output", required=True)
    file_automatic = commands.add_parser("auto-file-experiment", help="execute an allowlisted same-snapshot file variant")
    file_automatic.add_argument("--recommendation", required=True)
    file_automatic.add_argument("--target-cohort", required=True)
    file_automatic.add_argument("--variant-runner-plugin", default="approved_experiment_plugins:run_capsule_ground_variant", metavar="MODULE:CALLABLE")
    file_automatic.add_argument("--config", default="evaluator-config.yml")
    file_automatic.add_argument("--output", required=True)
    stability = commands.add_parser(
        "stability", help="compare repeated runs for router, RAG, and response stability"
    )
    stability.add_argument("--runs", nargs="+", required=True)
    stability.add_argument("--manifests", nargs="+", required=True)
    stability.add_argument("--output", required=True)
    stability.add_argument("--pii-validator", metavar="MODULE:CALLABLE")
    return parser


def _preflight(args: argparse.Namespace) -> int:
    rule = load_rating_rule(args.rating_rule)
    validator = _load_plugin(args.pii_validator)
    results = load_cases(args.cases, rule, validator)
    rows = [_preflight_row(result) for result in results]
    _require_safe({"preflight": rows}, validator, "preflight")
    if args.output:
        output = Path(args.output)
        output.mkdir(parents=True, exist_ok=True)
        (output / PREFLIGHT_ARTIFACTS["results"]).write_text(
            json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        (output / PREFLIGHT_ARTIFACTS["remediation"]).write_text(
            _remediation_markdown(results), encoding="utf-8"
        )
    else:
        print(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True))
    return 2 if any(row["status"] == "invalid" for row in rows) else 0


def _experiment(args: argparse.Namespace) -> int:
    if len(args.variants) != len(args.variant_manifests):
        raise ValueError("each variant run requires one variant manifest")
    output = Path(args.output)
    facts = validate_pair(output)
    if facts.artifact_state != "FINAL":
        raise ValueError("experiment results can only attach to a FINAL deliverable pair")
    config = load_evaluator_config(args.config)
    if len(set(args.variants)) != len(args.variants):
        raise ValueError("variant result paths must be distinct")
    baseline_records = _read_jsonl(Path(args.baseline))
    baseline_manifest = _manifest_document(Path(args.baseline_manifest))
    baseline_settings = _manifest_settings(baseline_manifest, Path(args.baseline_manifest))
    changes = []
    diffs = []
    critical_regressions = 0
    observed_seeds = []
    for result_path, manifest_path in zip(
        args.variants, args.variant_manifests, strict=True
    ):
        variant_records = _read_jsonl(Path(result_path))
        variant_manifest = _manifest_document(Path(manifest_path))
        _validate_controls(baseline_manifest, variant_manifest)
        observed_seeds.append(variant_manifest.get("seed"))
        change = enforce_single_variable(
            baseline_settings,
            _manifest_settings(variant_manifest, Path(manifest_path)),
            config.parameters,
        )
        changes.append(change)
        diff = compare_baseline(baseline_records, variant_records)
        if not diff.comparable:
            raise ValueError("variant case set differs from baseline or quality is unavailable")
        diffs.append(diff)
        critical_regressions += _critical_regressions(
            baseline_records, variant_records
        )
    if any(change.path != changes[0].path for change in changes) or changes[0].path != args.target:
        raise ValueError("all variants must change the declared single target")
    if len({change.variant_value for change in changes}) != 1:
        raise ValueError("all repeated runs must use the same candidate value")
    if tuple(observed_seeds) != config.experiment.seeds:
        raise ValueError("variant manifest seeds must match configured experiment seeds")
    evidence = RecommendationEvidence(
        repeats=len(diffs),
        target_pass_rate_deltas=tuple(
            diff.cohorts[args.target_cohort].pass_rate_delta for diff in diffs
        ),
        weighted_total_deltas=tuple(
            diff.global_delta.weighted_total_delta for diff in diffs
        ),
        max_non_target_regression=max(
            (max(0.0, -delta.weighted_total_delta) for diff in diffs for name, delta in diff.cohorts.items() if name != args.target_cohort),
            default=0.0,
        ),
        critical_hard_gate_regressions=critical_regressions,
    )
    recommendation = recommend(
        recommendation_id=f"EXP-{changes[0].path}",
        lever_type=args.lever_type,
        target=args.target,
        affected_cases=[str(record["case_id"]) for record in baseline_records],
        affected_cohorts=[args.target_cohort],
        trace_evidence_refs=[],
        rationale="Controlled repeated variant comparison",
        variant={
            "path": changes[0].path,
            "baseline": changes[0].baseline_value,
            "candidate": changes[0].variant_value,
        },
        evidence=evidence,
        thresholds=config.experiment,
    )
    validator = _load_plugin(args.pii_validator)
    _require_safe(asdict(recommendation), validator, "experiment recommendation")
    experiment_row = {
        "experiment_id": recommendation.recommendation_id,
        "hypothesis": recommendation.rationale,
        "control": json.dumps({"path": changes[0].path, "value": changes[0].baseline_value}, ensure_ascii=False, sort_keys=True),
        "candidate": json.dumps({"path": changes[0].path, "value": changes[0].variant_value}, ensure_ascii=False, sort_keys=True),
        "repetitions": len(diffs),
        "target_result": json.dumps({"pass_rate_deltas": evidence.target_pass_rate_deltas, "weighted_total_deltas": evidence.weighted_total_deltas}, ensure_ascii=False),
        "non_target_regression": evidence.max_non_target_regression,
        "guardrails": json.dumps({"critical_hard_gate_regressions": evidence.critical_hard_gate_regressions}, ensure_ascii=False),
        "verdict": recommendation.status,
        "next_action": recommendation.action_label,
    }
    model = build_model_from_rows(
        manifest=facts.manifest,
        artifact_state=facts.artifact_state,
        cases=facts.cases,
        turns=facts.turns,
        metrics=facts.metrics,
        baseline=facts.baseline,
        experiments=(*facts.experiments, experiment_row),
        human_review=facts.human_review,
        stability=facts.stability,
        text_content=facts.text_content,
    )
    publish_deliverables(model, output)
    return 0


def _stability(args: argparse.Namespace) -> int:
    if len(args.runs) != len(args.manifests):
        raise ValueError("each stability run requires one manifest")
    output = Path(args.output)
    facts = validate_pair(output)
    if facts.artifact_state != "FINAL":
        raise ValueError("stability can only attach to a FINAL deliverable pair")
    manifests = [_manifest_document(Path(path)) for path in args.manifests]
    for manifest in manifests[1:]:
        _validate_stability_controls(manifests[0], manifest)
    runs = [_read_jsonl(Path(path)) for path in args.runs]
    summary = summarize_stability(runs)
    validator = _load_plugin(args.pii_validator)
    _require_safe(summary, validator, "stability report")
    stability_rows = [
        {"section": "run", "metric": "classification", "value": summary["classification"], "status": "AVAILABLE"},
        {"section": "run", "metric": "run_count", "value": summary["run_count"], "status": "AVAILABLE"},
        *[
            {"section": "global", "metric": key, "value": value, "status": "AVAILABLE" if value is not None else "UNAVAILABLE"}
            for key, value in summary["global"].items()
        ],
    ]
    model = build_model_from_rows(
        manifest=facts.manifest,
        artifact_state=facts.artifact_state,
        cases=facts.cases,
        turns=facts.turns,
        metrics=facts.metrics,
        baseline=facts.baseline,
        experiments=facts.experiments,
        human_review=facts.human_review,
        stability=stability_rows,
        text_content=facts.text_content,
    )
    publish_deliverables(model, output)
    return 0


def _auto_experiment(args: argparse.Namespace) -> int:
    output = Path(args.output)
    facts = validate_pair(output)
    if facts.artifact_state != "FINAL":
        raise ValueError("automatic experiment results can only attach to a FINAL pair")
    recommendation = json.loads(Path(args.recommendation).read_text(encoding="utf-8"))
    if not isinstance(recommendation, Mapping):
        raise ValueError("recommendation must be a JSON object")
    report = run_auto_experiment(
        baseline_records=_read_jsonl(Path(args.baseline)),
        baseline_manifest=_manifest_document(Path(args.baseline_manifest)),
        recommendation=recommendation,
        target_cohort=args.target_cohort,
        config=load_evaluator_config(args.config),
        output=output,
        runner=_load_plugin(args.variant_runner_plugin),
    )
    _attach_auto_experiment(facts, output, report)
    return 0 if report["verdict"]["status"] == "validated" else 1


def _auto_file_experiment(args: argparse.Namespace) -> int:
    output = Path(args.output)
    facts = validate_pair(output)
    if facts.artifact_state != "FINAL":
        raise ValueError("automatic file experiment results can only attach to a FINAL pair")
    recommendation = json.loads(Path(args.recommendation).read_text(encoding="utf-8"))
    if not isinstance(recommendation, Mapping):
        raise ValueError("recommendation must be a JSON object")
    report = run_auto_file_experiment(
        recommendation=recommendation, target_cohort=args.target_cohort,
        config=load_evaluator_config(args.config), output=output,
        runner=_load_plugin(args.variant_runner_plugin),
    )
    _attach_auto_experiment(facts, output, report)
    return 0 if report["verdict"]["status"] == "validated" else 1


def _attach_auto_experiment(facts, output: Path, report: Mapping[str, object]) -> None:
    verdict = report.get("verdict", {})
    verdict = verdict if isinstance(verdict, Mapping) else {}
    evidence = report.get("evidence", {})
    evidence = evidence if isinstance(evidence, Mapping) else {}
    change = report.get("change", report.get("proposal", {}))
    change = change if isinstance(change, Mapping) else {}
    row = {
        "experiment_id": verdict.get("recommendation_id", "AUTO-EXPERIMENT"),
        "hypothesis": verdict.get("rationale", "Automated controlled comparison"),
        "control": json.dumps(change.get("baseline_value", change.get("before", {})), ensure_ascii=False, sort_keys=True),
        "candidate": json.dumps(change.get("variant_value", change.get("after", {})), ensure_ascii=False, sort_keys=True),
        "repetitions": evidence.get("repeats"),
        "target_result": json.dumps({"pass_rate_deltas": evidence.get("target_pass_rate_deltas"), "weighted_total_deltas": evidence.get("weighted_total_deltas")}, ensure_ascii=False),
        "non_target_regression": evidence.get("max_non_target_regression"),
        "guardrails": json.dumps({"critical_hard_gate_regressions": evidence.get("critical_hard_gate_regressions")}, ensure_ascii=False),
        "verdict": verdict.get("status"),
        "next_action": verdict.get("action_label"),
    }
    model = build_model_from_rows(
        manifest=facts.manifest, artifact_state=facts.artifact_state,
        cases=facts.cases, turns=facts.turns, metrics=facts.metrics,
        baseline=facts.baseline, experiments=(*facts.experiments, row),
        human_review=facts.human_review, stability=facts.stability,
        text_content=facts.text_content,
    )
    publish_deliverables(model, output)


def _validate_stability_controls(
    baseline: dict[str, object], candidate: dict[str, object]
) -> None:
    ignored = {"run_started_at", "seed", "fingerprint"}
    before = {key: value for key, value in baseline.items() if key not in ignored}
    after = {key: value for key, value in candidate.items() if key not in ignored}
    if before != after:
        raise ValueError(
            "stability runs changed deployment/model/prompt/knowledge or hyperparameter controls"
        )


def _manifest_document(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"manifest must be a JSON object: {path}")
    return value


def _manifest_settings(value: dict[str, object], path: Path) -> dict[str, object]:
    settings = value.get("hyperparameters")
    if not isinstance(settings, dict):
        raise ValueError(f"manifest has no hyperparameters object: {path}")
    return settings


def _validate_controls(baseline: dict[str, object], variant: dict[str, object]) -> None:
    ignored = {"run_started_at", "seed", "hyperparameters", "fingerprint"}
    before = {key: value for key, value in baseline.items() if key not in ignored}
    after = {key: value for key, value in variant.items() if key not in ignored}
    if before != after:
        raise ValueError("variant changed model/prompt/process/knowledge controls")


def _critical_regressions(baseline, variant) -> int:
    before = {str(record["case_id"]): record for record in baseline}
    regressions = 0
    for record in variant:
        previous = before.get(str(record["case_id"]), {})
        previous_safety = previous.get("safety", {})
        current_safety = record.get("safety", {})
        if (
            isinstance(previous_safety, dict)
            and isinstance(current_safety, dict)
            and previous_safety.get("hard_gate_passed") is True
            and current_safety.get("hard_gate_passed") is False
        ):
            regressions += 1
    return regressions


def _build_recommendations(records, pii_validator, recommendation_plugin=None):
    recommendations = [
        _candidate_recommendation(record)
        for record in records
        if record.get("status") != "PASS"
    ]
    if recommendation_plugin is not None:
        enriched = []
        for record, recommendation in zip(
            (item for item in records if item.get("status") != "PASS"), recommendations
        ):
            try:
                enhancement = recommendation_plugin(
                    {"record": record, "deterministic_recommendation": asdict(recommendation)}
                )
                if isinstance(enhancement, str):
                    enhancement = json.loads(enhancement)
                enriched.append(
                    enrich_recommendation(recommendation, enhancement)
                    if isinstance(enhancement, Mapping)
                    else recommendation
                )
            except Exception:
                enriched.append(recommendation)
        recommendations = enriched
    payload = [asdict(item) for item in recommendations]
    _require_safe({"recommendations": payload}, pii_validator, "recommendations")
    return payload


def _load_plugin(reference: str | None):
    if reference is None:
        return None
    module_name, separator, attribute = reference.partition(":")
    if not separator or not module_name or not attribute:
        raise ValueError("plugin reference must use MODULE:CALLABLE")
    plugin = getattr(importlib.import_module(module_name), attribute, None)
    if not callable(plugin):
        raise ValueError(f"plugin is not callable: {reference}")
    return plugin


def _require_safe(payload, validator, label: str) -> None:
    if validator is not None and not validator(payload):
        raise ValueError(f"{label} failed PII validation")


def _read_jsonl(path: Path) -> list[dict[str, object]]:
    records: list[dict[str, object]] = []
    for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        value = json.loads(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number} must contain a JSON object")
        records.append(value)
    return records


def _candidate_recommendation(record: dict[str, object]):
    return recommend_case(record)


def _preflight_row(result: CaseLoadResult) -> dict[str, object]:
    return {
        "case_id": result.case_id,
        "source": str(result.source),
        "status": result.preflight.status,
        "issues": [asdict(issue) for issue in result.preflight.issues],
        "remediations": [asdict(item) for item in result.preflight.remediations],
    }


def _remediation_markdown(results: Sequence[CaseLoadResult]) -> str:
    lines = ["# Case Remediation", ""]
    for result in results:
        lines.extend((f"## {result.case_id}", "", f"Status: `{result.preflight.status}`", ""))
        if not result.preflight.remediations:
            lines.extend(("No remediation required.", ""))
            continue
        for item in result.preflight.remediations:
            lines.extend(
                (
                    f"### {item.issue_type}",
                    "",
                    item.reason,
                    "",
                    f"Reviewer: `{item.required_reviewer}`; confidence: `{item.confidence}`.",
                    "",
                    "```json",
                    json.dumps(item.suggested_patch, ensure_ascii=False, indent=2),
                    "```",
                    "",
                )
            )
    return "\n".join(lines)
