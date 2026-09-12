import pytest

from xiaoan_eval.methodology_metrics import (
    agreement_report,
    pairwise_decision,
    red_line_agreement_report,
    run_pairwise_pass,
    self_judging,
    summarize_memory_metrics,
    summarize_pairwise,
)
from xiaoan_eval.methodology_runtime import build_matrix_summaries


def _pair(**overrides):
    payload = {
        "contract_version": "pairwise/v1", "case_id": "TC-01", "turn": 1,
        "left_answer_id": "answer:a", "right_answer_id": "answer:b",
        "judge_id": "judge:1", "display_order": "A_LEFT", "winner": "LEFT",
        "status": "AVAILABLE", "rationale": "A is safer.",
        "control_digest": "sha256:controls",
    }
    payload.update(overrides)
    return pairwise_decision(payload)


def test_pairwise_contract_and_operational_denominator():
    summary = summarize_pairwise([_pair(), _pair(winner="TIE"), _pair(winner="INVALID", status="UNAVAILABLE")])
    assert summary["eligible_n"] == 2
    assert summary["missing_n"] == 1
    assert summary["ties"] == 1
    with pytest.raises(ValueError, match="winner=INVALID"):
        _pair(status="UNAVAILABLE", winner="LEFT")


def test_pairwise_runner_is_a_second_pass_over_existing_answers():
    answers = [
        {"answer_id": "a", "case_id": "TC", "turn": 1, "status": "PASS", "text": "A"},
        {"answer_id": "b", "case_id": "TC", "turn": 1, "status": "PASS", "text": "B"},
    ]
    decisions = run_pairwise_pass(
        answers, [("a", "b")], ["j"],
        lambda _request: {"winner": "LEFT", "rationale": "safer"},
        controls={"matrix": "v1"}, seed="fixed",
    )
    assert len(decisions) == 1
    assert decisions[0].status == "AVAILABLE"
    assert decisions[0].control_digest.startswith("sha256:")


def test_agreement_self_judging_and_memory_are_denominator_aware():
    rows = []
    for subject_id, score in (("s1", 0), ("s2", 1), ("s3", 3)):
        for judge_id in ("j1", "j2"):
            rows.append({"case_id": "TC-1", "turn": 1, "status": "PASS", "subject": {"id": subject_id}, "judge": {"id": judge_id}, "scores": {"quality": score}, "self_judging": False})
    rows.append({"case_id": "TC-4", "turn": 1, "status": "PASS", "subject": {"id": "subject"}, "judge": {"id": "self"}, "scores": {"quality": 2}, "self_judging": True})
    report = agreement_report(rows, "quality")
    assert report["eligible_n"] == 6
    assert report["missing_n"] == 1
    assert report["krippendorff_alpha_ordinal"] == pytest.approx(1)
    assert self_judging({"provider": "gpt", "model": "m"}, {"provider": "gpt", "model": "m"})
    memory = summarize_memory_metrics([{"status": "pass"}, {"status": "skip"}])
    assert memory["retention_and_use_rate"] == 1
    assert memory["missing_n"] == 1


def test_diagonal_self_matrix_keeps_kendall_population_and_red_line_denominator():
    rows = []
    for subject_index, subject in enumerate(("a", "b", "c")):
        for judge in ("a", "b", "c"):
            rows.append({
                "case_id": "TC", "turn": 1, "status": "PASS",
                "subject": {"id": subject}, "judge": {"id": judge},
                "scores": {"quality": subject_index}, "self_judging": subject == judge,
                "triggered_red_lines": (), "red_line_evidence": {"RL": ()},
            })
    quality = agreement_report(rows, "quality")
    assert quality["kendall_strata"][0]["subject_n"] == 3
    assert quality["kendall_strata"][0]["missing_policy"] == "NO_IMPUTATION"
    assert quality["kendall_strata"][0]["kendall_w"] is None
    red_line = red_line_agreement_report(rows, "RL")
    assert red_line["eligible_n"] == 6
    assert red_line["missing_n"] == 3


def test_memory_fact_metrics_exclude_not_use_and_report_contamination():
    memory = summarize_memory_metrics([
        {"status": "pass", "check_type": "retrieve", "expected_facts": ["a", "b"], "retrieved_facts": ["a", "extra"]},
        {"status": "pass", "check_type": "not_use", "expected_facts": ["forbidden"], "retrieved_facts": []},
        {"status": "fail", "check_type": "isolation", "contamination_candidates": ["other-user"]},
    ])
    assert memory["fact_retrieval"]["precision"] == pytest.approx(0.5)
    assert memory["fact_retrieval"]["recall"] == pytest.approx(0.5)
    assert memory["contamination"]["candidate_n"] == 1


def test_attribution_summary_distinguishes_not_run_from_all_failed():
    assert build_matrix_summaries([])["attribution"]["status"] == "NOT_RUN"
    failed = build_matrix_summaries([], attribution_results=[{"status": "UNAVAILABLE"}])
    assert failed["attribution"]["status"] == "UNAVAILABLE"


def test_red_line_agreement_preserves_all_missing_contract_rows():
    rows = [{
        "status": "UNAVAILABLE", "expected_red_line_ids": ("RL-01",),
        "red_line_evidence": {}, "triggered_red_lines": (),
        "subject": {"id": "s"}, "judge": {"id": "j"},
        "case_id": "TC", "turn": 1, "scores": {},
    }]
    report = build_matrix_summaries(rows)["red_line_agreement"]["RL-01"]
    assert report["eligible_n"] == 0
    assert report["missing_n"] == 1
