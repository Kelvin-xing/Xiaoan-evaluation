from pathlib import Path

import pytest

from xiaoan_eval.deliverables import publish_deliverables, render_decision_report, validate_pair
from xiaoan_eval.report_model import build_report_model


def _record():
    return {
        "case_id": "TC-01", "status": "PASS",
        "safety": {"hard_gate_passed": True}, "pipeline": {"turns": [], "turn_traces": []},
        "conversation": {"conversation_id": "", "turns": []},
        "quality": {"weighted_total": 2.5}, "performance": {},
        "review": {"status": "not_requested"}, "failure": {"primary_stage": None},
    }


def test_publisher_creates_exactly_one_workbook_and_one_report(tmp_path: Path):
    model = build_report_model([_record()])
    output = tmp_path / "run"

    publish_deliverables(model, output, render_decision_report(model))

    assert sorted(path.name for path in output.iterdir()) == ["report.md", "results.xlsx"]
    facts = validate_pair(output)
    assert facts.generation_id == model.generation_id
    report = (output / "report.md").read_text(encoding="utf-8")
    assert model.generation_id in report
    assert "# 評估決策報告" in report
    assert "## 執行結果" in report
    assert "## 測試案例結果" in report
    assert "Evaluation Decision Report" not in report


def test_publisher_refuses_unknown_files_without_deleting_them(tmp_path: Path):
    model = build_report_model([_record()])
    output = tmp_path / "run"
    output.mkdir()
    unknown = output / "old.json"
    unknown.write_text("{}", encoding="utf-8")

    with pytest.raises(ValueError, match="unknown files"):
        publish_deliverables(model, output, render_decision_report(model))

    assert unknown.read_text(encoding="utf-8") == "{}"


def test_typed_facts_are_in_both_public_deliverables(tmp_path: Path):
    model = build_report_model(
        [_record()],
        typed_facts={"DiagnosisFact": [{"diagnosis_id": "d1", "evidence_state": "INCONCLUSIVE"}]},
    )
    output = tmp_path / "run"

    publish_deliverables(model, output, render_decision_report(model))

    facts = validate_pair(output)
    assert facts.manifest["typed_facts"]["DiagnosisFact"][0]["diagnosis_id"] == "d1"
    report = (output / "report.md").read_text(encoding="utf-8")
    assert "`DiagnosisFact`：`1` 筆事實" in report


def test_report_exposes_capsule_and_ground_citation_scores(tmp_path: Path):
    model = build_report_model([_record()])
    metrics = list(model.metrics)
    metrics.extend([
        {"case_id": "__RUN__", "metric_id": "v3:capsule_attribution.claim_alignment", "raw_score": 0.75},
        {"case_id": "__RUN__", "metric_id": "rag:metrics.ground_precision.mean", "raw_score": 0.8},
        {"case_id": "__RUN__", "metric_id": "rag:metrics.ground_recall.mean", "raw_score": 0.6},
    ])
    from dataclasses import replace
    model = replace(model, metrics=tuple(metrics))
    report = render_decision_report(model)

    assert "## Capsule／Ground 引用分數" in report
    assert "| Capsule 引用 | 0.7500 |" in report
    assert "| Ground 引用 | 不可用（UNAVAILABLE） |" in report
