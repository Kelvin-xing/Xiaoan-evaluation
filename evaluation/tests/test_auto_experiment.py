from xiaoan_eval.auto_experiment import run_auto_experiment, run_auto_file_experiment
from xiaoan_eval.config import load_evaluator_config


def test_auto_experiment_runs_registered_variant_three_times_and_validates(tmp_path) -> None:
    config = load_evaluator_config("evaluator-config.yml")
    baseline = [{
        "case_id": "TC-01", "status": "FAIL", "quality": {"weighted_total": 1.0},
        "cohorts": {"risk": ["critical"]},
    }]
    manifest = {
        "seed": 101,
        "hyperparameters": {path: spec.candidates[0] for path, spec in config.parameters.items()},
    }
    target = "router.context_turns"
    baseline_value = manifest["hyperparameters"][target]
    candidate = next(value for value in config.parameters[target].candidates if value != baseline_value)
    seen = []

    def runner(request):
        seen.append(request["seed"])
        variant_manifest = {**manifest, "seed": request["seed"], "hyperparameters": {
            **manifest["hyperparameters"], target: candidate,
        }}
        return {
            "records": [{
                "case_id": "TC-01", "status": "PASS", "quality": {"weighted_total": 1.3},
                "cohorts": {"risk": ["critical"]},
            }],
            "manifest": variant_manifest,
            "artifact_dir": f"seed-{request['seed']}",
        }

    report = run_auto_experiment(
        baseline_records=baseline,
        baseline_manifest=manifest,
        recommendation={
            "recommendation_id": "REC-1", "lever_type": "hyperparameter",
            "target": target, "variant": {"candidate": candidate}, "trace_evidence_refs": [],
        },
        target_cohort="risk:critical", config=config, output=tmp_path, runner=runner,
    )

    assert seen == [101, 202, 303]
    assert report["verdict"]["status"] == "validated"
    assert list(tmp_path.iterdir()) == []


def test_auto_file_experiment_compares_same_seed_baseline_and_variant(tmp_path) -> None:
    config = load_evaluator_config("evaluator-config.yml")

    def runner(request):
        baseline = {"case_id": "TC-45", "status": "FAIL", "quality": {"weighted_total": 1.0}, "cohorts": {"risk": ["high"]}}
        variant = {"case_id": "TC-45", "status": "PASS", "quality": {"weighted_total": 1.3}, "cohorts": {"risk": ["high"]}}
        return {"baseline_records": [baseline], "records": [variant], "change": {"field": "ground.nodes"}}

    report = run_auto_file_experiment(
        recommendation={
            "recommendation_id": "REC-TC-45-ground", "lever_type": "knowledge",
            "affected_cases": ["TC-45"], "trace_evidence_refs": ["TC-45:T1:authoritative_context"],
            "variant": {"proposal": {
                "experiment_type": "capsule_ground_nodes",
                "target": {"file": "tech/chatflow/poc/capsules.json", "entity_id": "n2a", "field": "ground.nodes"},
                "operation": "replace", "before": ["a", "b"], "after": ["b"],
            }},
        },
        target_cohort="risk:high", config=config, output=tmp_path, runner=runner,
    )
    assert [run["seed"] for run in report["runs"]] == [101, 202, 303]
    assert report["verdict"]["status"] == "validated"
