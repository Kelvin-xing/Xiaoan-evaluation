import pytest

from xiaoan_eval.baseline import compare_baseline, compare_workbook_baseline
from xiaoan_eval.report_model import build_report_model
from xiaoan_eval.workbook import write_workbook


def test_compare_baseline_reports_case_cohort_and_global_deltas():
    baseline = [
        {"case_id": "TC-01", "status": "FAIL", "weighted_total": 1.5, "cohorts": ["risk:critical"]},
        {"case_id": "TC-02", "status": "PASS", "weighted_total": 2.5, "cohorts": ["risk:critical"]},
    ]
    variant = [
        {"case_id": "TC-01", "status": "PASS", "weighted_total": 2.0, "cohorts": ["risk:critical"]},
        {"case_id": "TC-02", "status": "PASS", "weighted_total": 2.5, "cohorts": ["risk:critical"]},
    ]

    diff = compare_baseline(baseline, variant)

    assert diff.cases["TC-01"].weighted_total_delta == 0.5
    assert diff.cohorts["risk:critical"].pass_rate_delta == 0.5
    assert diff.global_delta.weighted_total_delta == 0.25
    assert diff.global_delta.pass_rate_delta == 0.5


def test_compare_baseline_marks_non_comparable_case_sets():
    diff = compare_baseline(
        [{"case_id": "TC-01", "status": "PASS", "weighted_total": 2.0}],
        [{"case_id": "TC-02", "status": "PASS", "weighted_total": 2.0}],
    )

    assert diff.comparable is False
    assert diff.missing_in_variant == ("TC-01",)
    assert diff.new_in_variant == ("TC-02",)


def test_compare_baseline_accepts_pipeline_case_result_shape():
    baseline = [{
        "case_id": "TC-01", "status": "FAIL",
        "quality": {"weighted_total": 1.0},
        "cohorts": {"risk": ["critical"]},
    }]
    variant = [{
        "case_id": "TC-01", "status": "PASS",
        "quality": {"weighted_total": 1.5},
        "cohorts": {"risk": ["critical"]},
    }]

    diff = compare_baseline(baseline, variant)

    assert diff.global_delta.weighted_total_delta == 0.5
    assert diff.cohorts["risk:critical"].pass_rate_delta == 1.0


def _workbook_record(score=2.0, status="PASS"):
    return {
        "case_id": "TC-01", "status": status, "safety": {"hard_gate_passed": True},
        "pipeline": {"turns": [], "turn_traces": []}, "quality": {"weighted_total": score},
        "performance": {}, "review": {"status": "completed"}, "failure": {"primary_stage": None},
    }


def _manifest(rule="rule-1"):
    return {"rating_rule_hash": rule, "rating_rule_schema_version": "1.1", "judge_prompt_version": "judge-v1"}


def test_final_workbook_is_a_formal_baseline_source(tmp_path):
    baseline = build_report_model([_workbook_record(2.0)], manifest=_manifest())
    path = tmp_path / "baseline.xlsx"
    write_workbook(baseline, path)
    candidate = build_report_model([_workbook_record(2.5)], manifest=_manifest())

    diff, rows = compare_workbook_baseline(path, candidate)

    assert diff.comparable is True
    assert diff.global_delta.weighted_total_delta == 0.5
    assert next(row for row in rows if row["grain"] == "case")["delta"] == 0.5


def test_workbook_baseline_rejects_measurement_drift(tmp_path):
    baseline = build_report_model([_workbook_record()], manifest=_manifest("old-rule"))
    path = tmp_path / "baseline.xlsx"
    write_workbook(baseline, path)
    candidate = build_report_model([_workbook_record()], manifest=_manifest("new-rule"))

    with pytest.raises(ValueError, match="rating_rule_hash"):
        compare_workbook_baseline(path, candidate)


def test_missing_quality_is_unavailable_in_baseline_without_zero_or_crash(tmp_path):
    original = build_report_model([_workbook_record(2.0)], manifest=_manifest())
    path = tmp_path / 'baseline.xlsx'
    write_workbook(original, path)
    failed = build_report_model([_workbook_record(None, 'ERROR')], manifest=_manifest())
    diff, rows = compare_workbook_baseline(path, failed)
    assert not diff.comparable
    assert diff.global_delta.weighted_total_delta is None
    assert rows[0]['delta'] is None
    assert rows[0]['status'] == 'UNAVAILABLE'


def test_baseline_rejects_changed_scoring_contract(tmp_path):
    original = build_report_model([_workbook_record()], manifest={**_manifest(), 'scoring_contract_version':'response-effectiveness/v1'})
    path = tmp_path / 'baseline.xlsx'
    write_workbook(original, path)
    candidate = build_report_model([_workbook_record()], manifest={**_manifest(), 'scoring_contract_version':'response-effectiveness/v2'})
    with pytest.raises(ValueError, match='scoring_contract_version'):
        compare_workbook_baseline(path, candidate)
