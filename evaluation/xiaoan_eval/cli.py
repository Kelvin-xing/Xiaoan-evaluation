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

from .auto_experiment import run_auto_experiment, run_auto_file_experiment
from .attribution_client import AttributionClient
from .baseline import compare_baseline, compare_workbook_baseline
from .cases import CaseLoadResult, load_cases
from .checkpoint import JsonlCheckpoint
from .config import load_evaluator_config
from .judge_client import JudgeClient
from .manifest import RunManifest, SuiteManifest
from .pipeline import EvaluationPipeline
from .recommendations import (
    RecommendationEvidence,
    recommend,
    recommend_case,
    enrich_recommendation,
)
from .experiments import enforce_single_variable
from .rules import load_rating_rule
from .runner import EvaluationRunner
from .scoring import TurnDimensionFact, fact_dict, score_case_fact, score_scenario
from .stability import summarize_stability
from .transport import FastAPITransport
from .deliverables import (
    publish_deliverables,
    render_decision_report,
    validate_pair,
    validate_output_target,
)
from .report_model import build_model_from_rows, build_report_model
from .review_workbook import adjudicate_workbook, export_review_workbook, import_review_workbook


PREFLIGHT_ARTIFACTS = {
    "results": "1.1-preflight.json",
    "remediation": "1.2-case-remediation.md",
}

def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.command == "preflight":
        return _preflight(args)
    if args.command == "report":
        return _report(args)
    if args.command == "run":
        return _run(args)
    if args.command == "experiment":
        return _experiment(args)
    if args.command == "auto-experiment":
        return _auto_experiment(args)
    if args.command == "auto-file-experiment":
        return _auto_file_experiment(args)
    if args.command == "stability":
        return _stability(args)
    if args.command == "export-human-review":
        return _export_human_review(args)
    if args.command == "import-human-review":
        return _import_human_review(args)
    if args.command == "adjudicate":
        return _adjudicate(args)
    parser.error(f"unsupported command: {args.command}")
    return 2


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="xiaoan-eval")
    commands = parser.add_subparsers(dest="command", required=True)
    preflight = commands.add_parser("preflight", help="validate cases without running the SUT")
    preflight.add_argument("cases")
    preflight.add_argument("--rating-rule", default="ratings rule.yml")
    preflight.add_argument("--output")
    preflight.add_argument("--pii-validator", metavar="MODULE:CALLABLE")
    report = commands.add_parser("report", help="convert existing case-results JSONL to results.xlsx and report.md")
    report.add_argument("results")
    report.add_argument("--output", required=True)
    report.add_argument("--pii-validator", metavar="MODULE:CALLABLE")
    report.add_argument("--recommendation-plugin", metavar="MODULE:CALLABLE")
    report.add_argument("--compact", action="store_true", help="deprecated compatibility option; the output is always the two-file pair")
    run = commands.add_parser("run", help="execute cases against XiaoAn and render reports")
    run.add_argument("cases")
    run.add_argument("--base-url", required=True)
    run.add_argument("--judge-plugin", required=True, metavar="MODULE:CALLABLE")
    run.add_argument("--secondary-judge-plugin", metavar="MODULE:CALLABLE")
    run.add_argument("--attribution-judge-plugin", metavar="MODULE:CALLABLE")
    run.add_argument("--attribution-judge-version", default="attribution-judge/v1")
    run.add_argument("--disable-secondary-judge", action="store_true")
    run.add_argument("--egress-validator", metavar="MODULE:CALLABLE")
    run.add_argument("--context-provider", required=True, metavar="MODULE:CALLABLE")
    run.add_argument("--manifest", required=True)
    run.add_argument("--output", required=True)
    run.add_argument("--rating-rule", default="ratings rule.yml")
    run.add_argument("--config", default="evaluator-config.yml")
    run.add_argument("--baseline")
    run.add_argument("--release-review", action="store_true")
    run.add_argument("--recommendation-plugin", metavar="MODULE:CALLABLE")
    run.add_argument("--compact", action="store_true", help="deprecated compatibility option; the output is always the two-file pair")
    run.add_argument("--suite-id", default="canonical")
    run.add_argument("--suite-version", default="1")
    run.add_argument("--taxonomy-version", default="1")
    run.add_argument("--suite-ledger", help="private append-only JSONL; defaults beside the public output")
    run.add_argument("--case-concurrency", type=int, default=2, help="independent cases to evaluate concurrently")
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
    export_review = commands.add_parser(
        "export-human-review", help="export one blinded XLSX packet for pending review turns"
    )
    export_review.add_argument("results")
    export_review.add_argument("--manifest", help="deprecated; run identity is read from results.xlsx")
    export_review.add_argument("--rating-rule", default="ratings rule.yml")
    export_review.add_argument("--output", required=True)
    import_review = commands.add_parser(
        "import-human-review", help="validate a completed XLSX packet and update the official pair"
    )
    import_review.add_argument("packet")
    import_review.add_argument("--rating-rule", default="ratings rule.yml")
    import_review.add_argument("--output", required=True, help="deliverable directory containing results.xlsx and report.md")
    adjudicate = commands.add_parser(
        "adjudicate", help="resolve one red-line disagreement in the official workbook pair"
    )
    adjudicate.add_argument("results")
    adjudicate.add_argument("--case", required=True)
    adjudicate.add_argument("--turn", required=True, type=int)
    adjudicate.add_argument("--decision", required=True, choices=("automatic", "human"))
    adjudicate.add_argument("--adjudicator", required=True, help="self-declared operational label; not authenticated")
    adjudicate.add_argument("--rationale", required=True)
    adjudicate.add_argument("--rating-rule", default="ratings rule.yml")
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


def _report(args: argparse.Namespace) -> int:
    records = _read_jsonl(Path(args.results))
    output = Path(args.output)
    validate_output_target(output)
    validator = _load_plugin(args.pii_validator)
    recommendations = _build_recommendations(records, validator, _load_plugin(args.recommendation_plugin))
    model = build_report_model(records, recommendations=recommendations, pii_validator=validator)
    publish_deliverables(model, output, render_decision_report(model))
    return 0


def _run(args: argparse.Namespace) -> int:
    rule = load_rating_rule(args.rating_rule)
    config = load_evaluator_config(args.config)
    output = Path(args.output)
    validate_output_target(output)
    validator = _load_plugin(args.egress_validator)
    loaded = load_cases(args.cases, rule, validator)
    if any(item.case is None for item in loaded):
        return 2
    manifest_data = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
    if not isinstance(manifest_data, dict):
        raise ValueError("manifest must be a JSON object")
    manifest = RunManifest(**manifest_data)
    if manifest.rating_rule_schema_version != rule.schema_version:
        raise ValueError(
            "manifest rating_rule_schema_version does not match the loaded rating rule: "
            f"{manifest.rating_rule_schema_version!r} != {rule.schema_version!r}"
        )
    primary_provider = _load_plugin(args.judge_plugin)
    secondary_provider = (
        _load_plugin(args.secondary_judge_plugin)
        if args.secondary_judge_plugin and not args.disable_secondary_judge
        else None
    )
    context_provider = _load_plugin(args.context_provider)
    attribution_provider = _load_plugin(args.attribution_judge_plugin)
    configured_routes = manifest.run_config.get("known_route_ids", ())
    known_routes = frozenset(
        {"baseline", "crisis_sop", *(str(item) for item in configured_routes)}
    )
    raw_quality_threshold = manifest.run_config.get("quality_threshold")
    quality_threshold = (
        float(raw_quality_threshold) if raw_quality_threshold is not None else None
    )

    suite = SuiteManifest.from_cases(
        suite_id=args.suite_id,
        suite_version=args.suite_version,
        taxonomy_version=args.taxonomy_version,
        scoring_contract_version="response-effectiveness/v1",
        cases=[item.case for item in loaded if item.case],
        case_digests={
            item.case.id: hashlib.sha256(item.source.read_bytes()).hexdigest()
            for item in loaded if item.case
        },
        retry_policy=manifest.retry_policy,
        rollup=manifest.run_config.get("suite_rollup") if isinstance(manifest.run_config.get("suite_rollup"), Mapping) else None,
    )
    private_output = output.parent / f".{output.name}.private"
    checkpoint_path = private_output / "evaluation-checkpoint.jsonl"
    checkpoint_fingerprint = hashlib.sha256(
        f"{manifest.fingerprint}:{suite.fingerprint}".encode("utf-8")
    ).hexdigest()
    with JsonlCheckpoint(checkpoint_path, checkpoint_fingerprint) as checkpoint:
        def evaluate_case(case):
            with FastAPITransport(args.base_url) as transport:
                primary = JudgeClient(
                    primary_provider, rule, checkpoint=checkpoint,
                    checkpoint_event="primary_judge",
                )
                secondary = (
                    JudgeClient(
                        secondary_provider, rule, checkpoint=checkpoint,
                        checkpoint_event="secondary_judge",
                    )
                    if secondary_provider is not None else None
                )
                attribution_client = (
                    AttributionClient(
                        attribution_provider,
                        judge_version=args.attribution_judge_version,
                        checkpoint=checkpoint,
                    )
                    if attribution_provider is not None else None
                )
                pipeline = EvaluationPipeline(
                    EvaluationRunner(transport, checkpoint=checkpoint), rule, config,
                    primary_judge=primary, secondary_judge=secondary,
                    egress_validator=validator,
                    authoritative_context_provider=context_provider,
                    known_route_ids=known_routes,
                    quality_threshold=quality_threshold,
                    release_review=args.release_review,
                    attribution_client=attribution_client,
                )
                return pipeline.evaluate_case(case)

        ledger_path = Path(args.suite_ledger) if args.suite_ledger else private_output / "suite-attempts.jsonl"
        records, suite_execution_facts = _evaluate_suite(
            evaluate_case,
            [item.case for item in loaded if item.case],
            suite,
            ledger_path,
            checkpoint=checkpoint,
            max_workers=args.case_concurrency,
        )

    manifest_payload = {**manifest.to_dict(), "fingerprint": manifest.fingerprint}
    _require_safe(manifest_payload, validator, "manifest")
    recommendations = _build_recommendations(
        records, validator, _load_plugin(args.recommendation_plugin)
    )
    model = build_report_model(
        records,
        manifest=manifest_payload,
        recommendations=recommendations,
        pii_validator=validator,
        typed_facts=_suite_typed_facts(
            suite, records, rule, suite_execution_facts
        ),
    )
    if args.baseline:
        _, baseline_rows = compare_workbook_baseline(Path(args.baseline), model)
        _require_safe({"baseline": baseline_rows}, validator, "baseline diff")
        model = build_report_model(
            records,
            manifest=manifest_payload,
            recommendations=recommendations,
            baseline=baseline_rows,
            pii_validator=validator,
            generation_id=model.generation_id,
            typed_facts=_suite_typed_facts(
                suite, records, rule, suite_execution_facts
            ),
        )
    publish_deliverables(model, output, render_decision_report(model))
    return 1 if any(record["status"] != "PASS" for record in records) else 0


def _evaluate_suite(
    pipeline,
    cases,
    suite: SuiteManifest,
    ledger_path: Path,
    *,
    checkpoint: JsonlCheckpoint | None = None,
    max_workers: int = 1,
):
    if max_workers < 1:
        raise ValueError("max_workers must be at least 1")
    existing = _read_suite_ledger(ledger_path, suite.fingerprint)
    maximum = int(suite.retry_policy.get("max_attempts", 1))
    ledger_lock = threading.Lock()

    def evaluate(case):
        case_attempts = [row for row in existing if row["case_id"] == case.id]
        successful = [row for row in case_attempts if row.get("execution_complete") is True]
        for attempt in range(len(case_attempts) + 1, maximum + 1):
            if successful:
                break
            if checkpoint is not None:
                checkpoint.set_attempt(attempt)
            record = pipeline(case) if callable(pipeline) else pipeline.evaluate_case(case)
            execution_complete = _record_execution_complete(record, len(case.turns))
            row = {
                "suite_fingerprint": suite.fingerprint,
                "case_id": case.id,
                "attempt": attempt,
                "execution_complete": execution_complete,
                "outcome": "ANSWERED" if execution_complete else "RUNTIME_OR_PROVIDER_FAILURE",
                "record_digest": hashlib.sha256(
                    json.dumps(record, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
                ).hexdigest(),
                "record": record,
            }
            with ledger_lock:
                _append_suite_ledger(ledger_path, row)
            case_attempts.append(row)
            if execution_complete:
                successful.append(row)
        if checkpoint is not None:
            checkpoint.set_attempt(None)
        successful.sort(key=lambda row: int(row["attempt"]))
        if successful:
            return successful[0]["record"], {
                "case_id": case.id, "selected_attempt": successful[0]["attempt"],
                "attempt_count": len(case_attempts), "status": "COMPLETE",
            }
        return case_attempts[-1]["record"], {
            "case_id": case.id, "selected_attempt": None,
            "attempt_count": len(case_attempts), "status": "UNAVAILABLE",
        }

    with ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="evaluation-case") as executor:
        completed = list(executor.map(evaluate, cases))
    selected_records = [item[0] for item in completed]
    attempt_facts = [item[1] for item in completed]
    completed = sum(row["status"] == "COMPLETE" for row in attempt_facts)
    validity = "VALID" if completed == len(cases) else "PARTIAL" if completed else "INVALID"
    return selected_records, {
        "suite_fingerprint": suite.fingerprint, "validity": validity,
        "expected_cases": len(cases), "completed_cases": completed,
        "attempts": attempt_facts, "private_ledger_id": ledger_path.name,
    }


def _read_suite_ledger(path: Path, fingerprint: str):
    if not path.exists():
        return []
    rows = _read_jsonl(path)
    if any(row.get("suite_fingerprint") != fingerprint for row in rows):
        raise ValueError("suite ledger belongs to a different suite manifest")
    identities = [(row.get("case_id"), row.get("attempt")) for row in rows]
    if len(identities) != len(set(identities)):
        raise ValueError("suite ledger contains duplicate attempts")
    return rows


def _append_suite_ledger(path: Path, row: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def _record_execution_complete(record: Mapping[str, object], expected_turns: int) -> bool:
    conversation = record.get("conversation")
    conversation = conversation if isinstance(conversation, Mapping) else {}
    turns = conversation.get("turns")
    return (
        isinstance(turns, Sequence)
        and not isinstance(turns, (str, bytes))
        and len(turns) == expected_turns
        and all(isinstance(turn, Mapping) and isinstance(turn.get("assistant_response"), str) for turn in turns)
    )


def _suite_typed_facts(suite, records, rule, execution):
    turn_facts = []
    case_facts = {}
    cases_by_id = {binding.case_id: binding for binding in suite.cases}
    records_by_id = {str(record["case_id"]): record for record in records}
    for binding in suite.cases:
        record = records_by_id.get(binding.case_id, {})
        audits = record.get("review", {}).get("judge_audit", ()) if isinstance(record.get("review"), Mapping) else ()
        facts = []
        for turn, audit in enumerate(audits, 1):
            primary = audit.get("primary") if isinstance(audit, Mapping) else None
            dimensions = primary.get("dimensions", ()) if isinstance(primary, Mapping) else ()
            for dimension in dimensions:
                if isinstance(dimension, Mapping):
                    facts.append(TurnDimensionFact(
                        binding.case_id, turn, str(dimension.get("module")), "AVAILABLE", float(dimension.get("score"))
                    ))
        turn_facts.extend(fact_dict(fact) for fact in facts)
        focus = binding.quality_focus or tuple(module.name for module in rule.modules)
        case_facts[binding.case_id] = score_case_fact(
            case_id=binding.case_id, expected_turns=binding.expected_turns,
            quality_focus=focus, dimension_weights={module.name: module.weight for module in rule.modules},
            turn_facts=facts,
        )
    scenario_facts = []
    groups = sorted({(item.scenario_id, item.comparability_group) for item in suite.cases})
    case_rows = [
        {"case_id": item.case_id, "scenario_id": item.scenario_id,
         "comparability_group": item.comparability_group, "maturity": item.maturity}
        for item in suite.cases
    ]
    for scenario_id, group in groups:
        scenario_facts.append(fact_dict(score_scenario(
            scenario_id=scenario_id, comparability_group=group,
            cases=case_rows, case_scores=case_facts,
        )))
    return {
        "SuiteManifest": [{**suite.to_dict(), "fingerprint": suite.fingerprint}],
        "SuiteExecutionFact": [execution],
        "TurnDimensionFact": turn_facts,
        "CaseScoreFact": [fact_dict(fact) for fact in case_facts.values()],
        "ScenarioScoreFact": scenario_facts,
    }


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
            raise ValueError("variant case set differs from baseline")
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
    publish_deliverables(model, output, render_decision_report(model))
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
    publish_deliverables(model, output, render_decision_report(model))
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
    publish_deliverables(model, output, render_decision_report(model))


def _export_human_review(args: argparse.Namespace) -> int:
    export_review_workbook(Path(args.results), Path(args.output), load_rating_rule(args.rating_rule))
    return 0


def _import_human_review(args: argparse.Namespace) -> int:
    output = Path(args.output)
    model = import_review_workbook(Path(args.packet), output, load_rating_rule(args.rating_rule))
    publish_deliverables(model, output, render_decision_report(model))
    return 1 if model.artifact_state == "NEEDS_ADJUDICATION" else 0


def _adjudicate(args: argparse.Namespace) -> int:
    output = Path(args.results)
    model = adjudicate_workbook(
        output, case_id=args.case, turn=args.turn, decision_source=args.decision,
        adjudicator_id=args.adjudicator, rationale=args.rationale,
        rule=load_rating_rule(args.rating_rule),
    )
    publish_deliverables(model, output, render_decision_report(model))
    return 1 if model.artifact_state == "NEEDS_ADJUDICATION" else 0


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
