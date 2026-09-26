import json
import sys
import threading
import time
import types

import pytest

from xiaoan_eval.cli import main
from xiaoan_eval.deliverables import publish_deliverables, render_decision_report
from xiaoan_eval.manifest import SuiteCaseBinding, SuiteManifest
from xiaoan_eval.cases import OracleProvenance, TestCase as EvaluationCase, TestTurn as EvaluationTurn
from xiaoan_eval.report_model import build_report_model
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval.workbook import read_workbook






def _install_safe_plugin(monkeypatch, name="safe_plugins"):
    plugins = types.ModuleType(name)
    plugins.safe = lambda payload: True
    monkeypatch.setitem(sys.modules, name, plugins)
    return f"{name}:safe"


def test_preflight_command_writes_reports_without_pii_validator(tmp_path) -> None:
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "TC-01.yaml").write_text(
        """\
schema_version: "2.0"
id: TC-01
user_variable: adult
test_objective: v2 preflight
quality_focus: [行动赋权]
turns: [{turn: 1, user: hello}]
memory_checkpoints: []
oracle_provenance: {source: test, status: provisional}
""",
        encoding="utf-8",
    )
    output = tmp_path / "output"

    exit_code = main(
        [
            "preflight",
            str(cases),
            "--rating-rule",
            "ratings rule.yml",
            "--output",
            str(output),
        ]
    )

    rows = json.loads((output / "1.1-preflight.json").read_text(encoding="utf-8"))
    assert exit_code == 0
    assert rows[0]["case_id"] == "TC-01"
    assert rows[0]["status"] == "needs_remediation"
    assert all(issue["issue_type"] != "pii_check_unavailable" for issue in rows[0]["issues"])
    assert "provisional_oracle" in (output / "1.2-case-remediation.md").read_text(encoding="utf-8")


def test_preflight_command_returns_nonzero_for_invalid_case(tmp_path, monkeypatch) -> None:
    case = tmp_path / "TC-02.yaml"
    case.write_text("id: TC-02\nscript: broken\n", encoding="utf-8")

    assert main([
        "preflight", str(case), "--rating-rule", "ratings rule.yml",
        "--pii-validator", _install_safe_plugin(monkeypatch, "invalid_safe_plugins"),
    ]) == 2




def test_stability_command_compares_repeated_result_files(tmp_path) -> None:
    runs = []
    manifests = []
    for index, route in enumerate(("n3", "n3", "n4"), 1):
        path = tmp_path / f"run-{index}.jsonl"
        path.write_text(json.dumps({
            "case_id": "TC-01",
            "pipeline": {"turn_traces": [{
                "turn": 1,
                "response_sha256": "same" if index < 3 else "different",
                "trace": {
                    "route": {"id": route},
                    "ground": {"resolved_refs": ["source:1"]},
                },
            }]},
        }) + "\n", encoding="utf-8")
        runs.append(str(path))
        manifest = tmp_path / f"manifest-{index}.json"
        manifest.write_text(json.dumps({
            "run_started_at": f"2026-08-19T00:0{index}:00+08:00",
            "seed": index,
            "fingerprint": f"run-{index}",
            "model_ids": {"router": "gpt-4o-mini", "response": "gpt-5.5"},
            "controls": "fixed",
        }), encoding="utf-8")
        manifests.append(str(manifest))

    output = tmp_path / "stability"
    base_model = build_report_model([{
        "case_id": "TC-01", "status": "PASS", "safety": {"hard_gate_passed": True},
        "pipeline": {"turns": [], "turn_traces": []}, "quality": {"weighted_total": 2.0},
        "performance": {}, "review": {"status": "completed"}, "failure": {"primary_stage": None},
    }])
    publish_deliverables(base_model, output, render_decision_report(base_model))
    code = main([
        "stability", "--runs", *runs, "--manifests", *manifests,
        "--output", str(output),
    ])

    assert code == 0
    result = read_workbook(output / "results.xlsx")
    values = {row["metric"]: row["value"] for row in result.stability}
    assert values["capsule_modal_agreement"] == pytest.approx(2 / 3)
    assert values["classification"] == "DESCRIPTIVE_ONLY"
    assert "generation_id:" in (output / "report.md").read_text(encoding="utf-8")


def test_stability_command_rejects_changed_controls(tmp_path) -> None:
    run = tmp_path / "run.jsonl"
    run.write_text(json.dumps({
        "case_id": "TC-01",
        "pipeline": {"turn_traces": []},
    }) + "\n", encoding="utf-8")
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    first.write_text(json.dumps({"model_ids": {"router": "gpt-4o-mini"}}))
    second.write_text(json.dumps({"model_ids": {"router": "different"}}))

    output = tmp_path / "output"
    base_model = build_report_model([{
        "case_id": "TC-01", "status": "PASS", "safety": {"hard_gate_passed": True},
        "pipeline": {"turns": [], "turn_traces": []}, "quality": {"weighted_total": 2.0},
        "performance": {}, "review": {"status": "completed"}, "failure": {"primary_stage": None},
    }])
    publish_deliverables(base_model, output, render_decision_report(base_model))
    with pytest.raises(ValueError, match="changed deployment/model"):
        main([
            "stability", "--runs", str(run), str(run),
            "--manifests", str(first), str(second),
            "--output", str(output),
        ])




def test_experiment_command_validates_without_pii_validator(tmp_path) -> None:
    baseline = tmp_path / "baseline.jsonl"
    baseline.write_text(json.dumps({
        "case_id": "TC-01", "status": "FAIL", "quality": {"weighted_total": 1.0},
        "cohorts": {"risk": ["critical"]}, "safety": {"hard_gate_passed": True},
    }) + "\n", encoding="utf-8")
    variants = []
    manifests = []
    for index in range(3):
        variant = tmp_path / f"variant-{index}.jsonl"
        variant.write_text(json.dumps({
            "case_id": "TC-01", "status": "PASS", "quality": {"weighted_total": 1.2},
            "cohorts": {"risk": ["critical"]}, "safety": {"hard_gate_passed": True},
        }) + "\n", encoding="utf-8")
        variants.append(str(variant))
        manifest = tmp_path / f"manifest-{index}.json"
        manifest.write_text(json.dumps({"seed": [101, 202, 303][index], "controls": "fixed", "hyperparameters": {
            "router.context_turns": 8,
            "state.active_capsule_ttl": 3,
            "state.activation_confidence": 0.45,
                "model.reasoning_effort": "medium",
                "response.verbosity": "medium",
        }}), encoding="utf-8")
        manifests.append(str(manifest))
    base_manifest = tmp_path / "baseline-manifest.json"
    base_manifest.write_text(json.dumps({"seed": 101, "controls": "fixed", "hyperparameters": {
        "router.context_turns": 6,
        "state.active_capsule_ttl": 3,
        "state.activation_confidence": 0.45,
            "model.reasoning_effort": "medium",
            "response.verbosity": "medium",
    }}), encoding="utf-8")
    output = tmp_path / "experiment"
    official = build_report_model([{
        "case_id": "TC-01", "status": "PASS", "safety": {"hard_gate_passed": True},
        "pipeline": {"turns": [], "turn_traces": []}, "quality": {"weighted_total": 1.2},
        "performance": {}, "review": {"status": "completed"}, "failure": {"primary_stage": None},
        "cohorts": {"risk": ["critical"]},
    }])
    publish_deliverables(official, output, render_decision_report(official))

    code = main([
        "experiment", "--baseline", str(baseline), "--variants", *variants,
        "--baseline-manifest", str(base_manifest), "--variant-manifests", *manifests,
        "--target-cohort", "risk:critical", "--lever-type", "hyperparameter",
        "--target", "router.context_turns", "--output", str(output),
    ])

    assert code == 0
    result = read_workbook(output / "results.xlsx")
    assert result.experiments[0]["verdict"] == "validated"
    assert result.experiments[0]["next_action"] == "建议修改"
    report = (output / "report.md").read_text(encoding="utf-8")
    assert "generation_id:" in report


