import json
import sys
import threading
import time
import types

import pytest

from xiaoan_eval.cli import main, _evaluate_suite
from xiaoan_eval.deliverables import publish_deliverables, render_decision_report
from xiaoan_eval.manifest import SuiteCaseBinding, SuiteManifest
from xiaoan_eval.cases import OracleProvenance, TestCase as EvaluationCase, TestTurn as EvaluationTurn
from xiaoan_eval.report_model import build_report_model
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval.workbook import read_workbook


def test_suite_orchestration_retries_execution_failure_and_resumes(tmp_path) -> None:
    case = EvaluationCase(
        schema_version="2.0", id="TC-01", test_objective="suite",
        quality_focus=("行动赋权",), turns=(EvaluationTurn(1, "hello"),),
        oracle_provenance=OracleProvenance("test", "provisional"),
    )
    suite = SuiteManifest(
        suite_id="canonical", suite_version="1", taxonomy_version="1",
        scoring_contract_version="response-effectiveness/v1",
        cases=(SuiteCaseBinding(
            case_id="TC-01", case_digest="case", expected_turns=(1,),
            scenario_id="baseline", coverage_axes={}, comparability_group="v1",
            maturity="PROVISIONAL_DESCRIPTIVE", quality_focus=("行动赋权",),
        ),), retry_policy={"max_attempts": 2},
    )

    class Pipeline:
        calls = 0

        def evaluate_case(self, _case):
            self.calls += 1
            response = None if self.calls == 1 else "answer"
            return {
                "case_id": "TC-01", "status": "ERROR" if response is None else "PASS",
                "conversation": {"turns": [{"turn": 1, "assistant_response": response}]},
                "review": {"judge_audit": []}, "quality": {},
            }

    pipeline = Pipeline()
    ledger = tmp_path / "private" / "attempts.jsonl"
    records, execution = _evaluate_suite(pipeline, [case], suite, ledger)
    assert execution["validity"] == "VALID"
    assert execution["attempts"][0]["selected_attempt"] == 2
    assert pipeline.calls == 2

    resumed, repeated_execution = _evaluate_suite(pipeline, [case], suite, ledger)
    assert resumed == records
    assert repeated_execution["validity"] == "VALID"
    assert pipeline.calls == 2


def test_suite_orchestration_runs_cases_concurrently_but_returns_manifest_order(tmp_path) -> None:
    cases = [
        EvaluationCase(
            schema_version="2.0", id=f"TC-{index}", test_objective="suite",
            quality_focus=(), turns=(EvaluationTurn(1, "hello"),),
            oracle_provenance=OracleProvenance("test", "provisional"),
        )
        for index in range(1, 4)
    ]
    suite = SuiteManifest(
        suite_id="canonical", suite_version="1", taxonomy_version="1",
        scoring_contract_version="response-effectiveness/v1",
        cases=tuple(SuiteCaseBinding(
            case_id=case.id, case_digest=case.id, expected_turns=(1,),
            scenario_id="baseline", coverage_axes={}, comparability_group="v1",
            maturity="PROVISIONAL_DESCRIPTIVE", quality_focus=(),
        ) for case in cases), retry_policy={"max_attempts": 1},
    )
    lock = threading.Lock()
    active = 0
    maximum_active = 0

    def evaluate(case):
        nonlocal active, maximum_active
        with lock:
            active += 1
            maximum_active = max(maximum_active, active)
        time.sleep(0.03)
        with lock:
            active -= 1
        return {
            "case_id": case.id, "status": "PASS",
            "conversation": {"turns": [{"turn": 1, "assistant_response": "answer"}]},
            "review": {"judge_audit": []}, "quality": {},
        }

    records, execution = _evaluate_suite(
        evaluate, cases, suite, tmp_path / "attempts.jsonl", max_workers=3
    )

    assert maximum_active == 3
    assert [record["case_id"] for record in records] == ["TC-1", "TC-2", "TC-3"]
    assert execution["validity"] == "VALID"


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


def test_report_command_renders_existing_case_results_without_pii_validator(tmp_path) -> None:
    results = tmp_path / "case-results.jsonl"
    results.write_text(
        json.dumps(
            {
                "case_id": "TC-01",
                "status": "FAIL",
                "safety": {"hard_gate_passed": True},
                "pipeline": {
                    "turns": [{
                        "ground_recall": {"status": "pass", "score": 1.0},
                        "ground_precision": {"status": "pass", "score": 1.0},
                    }],
                    "turn_traces": [{
                        "turn": 1,
                        "response_sha256": "abc",
                        "trace": {
                            "route": {"id": "n3"},
                            "ground": {"resolved_ground": ["source:1"]},
                        },
                    }],
                },
                "quality": {"weighted_total": 1.5},
                "performance": {"total_ms": 10},
                "review": {"status": "completed"},
                "failure": {"primary_stage": "router"},
                "cohorts": {"risk": ["critical"]},
            },
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    output = tmp_path / "report"
    assert main([
        "report", str(results), "--output", str(output),
    ]) == 0
    assert sorted(path.name for path in output.iterdir()) == ["report.md", "results.xlsx"]
    workbook = read_workbook(output / "results.xlsx")
    assert workbook.cases[0]["case_id"] == "TC-01"
    assert workbook.metrics[0]["metric_id"] == "ground_recall"
    assert workbook.metrics[0]["raw_score"] == 1
    summary_text = (output / "report.md").read_text(encoding="utf-8")
    assert "指標發現" in summary_text
    assert "改善建議" in summary_text
    assert "REC-TC-01-router" in summary_text
    assert "仍屬假設" in summary_text

    compact_output = tmp_path / "compact-report"
    assert main([
        "report", str(results), "--output", str(compact_output), "--compact",
    ]) == 0
    assert sorted(path.name for path in compact_output.iterdir()) == ["report.md", "results.xlsx"]


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
    assert "穩定性只表示可重複性" in (output / "report.md").read_text(encoding="utf-8")


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


def test_run_command_executes_cases_and_writes_complete_report(tmp_path, monkeypatch) -> None:
    cases = tmp_path / "cases"
    cases.mkdir()
    (cases / "TC-01.yaml").write_text(
        """\
schema_version: "2.0"
id: TC-01
user_variable: adult
test_objective: runnable v2 case
quality_focus: [行动赋权]
turns: [{turn: 1, user: hello}]
memory_checkpoints: []
oracle_provenance: {source: test, status: provisional}
""",
        encoding="utf-8",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(
        json.dumps(
            {
                "run_started_at": "2026-08-17T10:00:00+08:00",
                "product_version": "test",
                "safety_policy_version": "test",
                "output_guard_version": "stub",
                "prompt_hashes": {},
                "knowledge_versions": {},
                "model_ids": {},
                "provider_versions": {},
                "hyperparameters": {},
                "run_config": {},
                "evaluator_version": "0.1.0",
                "rating_rule_hash": "test",
                "rating_rule_schema_version": "1.1",
                "judge_prompt_version": "test",
                "seed": 101,
                "retry_policy": {"max_attempts": 1},
            }
        ),
        encoding="utf-8",
    )
    rule = load_rating_rule("ratings rule.yml")

    def judge(_request):
        return json.dumps(
            {
                "red_lines": [
                    {"id": item.id, "triggered": False, "evidence": [], "uncertainty": "low"}
                    for item in rule.red_lines
                ],
                "dimensions": [
                    {
                        "module": item.name,
                        "score": 2,
                        "supporting_evidence": [],
                        "deduction_evidence": [],
                        "uncertainty": "low",
                    }
                    for item in rule.modules
                ],
                "legal_claims": [],
                "faithfulness_claims": [],
            },
            ensure_ascii=False,
        )

    plugins = types.ModuleType("test_eval_plugins")
    plugins.judge = judge
    plugins.context = lambda case, turn, trace: {"refs": []}
    monkeypatch.setitem(sys.modules, "test_eval_plugins", plugins)

    class FakeTransport:
        def __init__(self, *args, **kwargs): pass
        def __enter__(self): return self
        def __exit__(self, *args): return None
        def create_conversation(self): return "c1"
        def send_turn(self, conversation_id, user):
            return {
                "response": "safe",
                "trace": {
                    "safety": {"level": "baseline"},
                    "route": {"id": "baseline"},
                    "ground": {"resolved_refs": []},
                    "guard": {"passed": True},
                    "state": {},
                    "timings": {"ttft_ms": 1, "first_guarded_delta_ms": 1, "router_ms": 1, "ground_ms": 0, "generation_ms": 1, "total_ms": 2},
                    "tokens": {"input": 1, "output": 1},
                },
            }

    monkeypatch.setattr("xiaoan_eval.cli.FastAPITransport", FakeTransport)
    output = tmp_path / "run"

    code = main([
        "run", str(cases), "--base-url", "http://unused", "--judge-plugin",
        "test_eval_plugins:judge",
        "--context-provider", "test_eval_plugins:context",
        "--manifest", str(manifest), "--output", str(output), "--release-review",
    ])

    assert code == 0
    assert sorted(path.name for path in output.iterdir()) == ["report.md", "results.xlsx"]
    workbook = read_workbook(output / "results.xlsx")
    assert workbook.artifact_state == "FINAL"
    assert workbook.manifest["fingerprint"]
    assert workbook.turns[0]["case_id"] == "TC-01"
    text = {row["role"]: row["content"] for row in workbook.text_content}
    assert text == {"user_input": "hello", "assistant_response": "safe"}
    assert workbook.human_review == ()
    checkpoint = output.parent / f".{output.name}.private" / "evaluation-checkpoint.jsonl"
    events = [json.loads(line) for line in checkpoint.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == [
        "subject_turn",
        "primary_judge",
        "primary_judge_validation",
    ]
    assert {event["attempt"] for event in events} == {1}


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
    assert "重複次數：`3`" in report
    assert "非目標退化" in report
