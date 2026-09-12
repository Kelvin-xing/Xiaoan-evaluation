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


def _pair(**overrides):
    payload = {
        "contract_version": "pairwise/v1",
        "case_id": "TC-01",
        "turn": 1,
        "left_answer_id": "answer:a",
        "right_answer_id": "answer:b",
        "judge_id": "judge:1",
        "display_order": "A_LEFT",
        "winner": "LEFT",
        "status": "AVAILABLE",
        "rationale": "A follows the safety constraint more completely.",
        "control_digest": "sha256:controls",
    }
    payload.update(overrides)
    return pairwise_decision(payload)


def test_pairwise_contract_keeps_ties_and_unavailable_out_of_directional_wins():
    summary = summarize_pairwise([
        _pair(),
        _pair(winner="TIE"),
        _pair(winner="INVALID", status="UNAVAILABLE"),
    ])
    assert summary == {
        "status": "AVAILABLE", "attempted_n": 3, "eligible_n": 2,
        "missing_n": 1, "left_wins": 1, "right_wins": 0, "ties": 1,
        "position_retests_n": 0, "position_flip_rate": None,
        "tie_policy": "SEPARATE",
    }


def test_pairwise_contract_rejects_operational_failure_as_quality_choice():
    with pytest.raises(ValueError, match="winner=INVALID"):
        _pair(status="UNAVAILABLE", winner="LEFT")


def test_pairwise_runner_uses_immutable_answers_and_keeps_provider_failure_unavailable():
    answers = [
        {"answer_id": "a", "case_id": "TC", "turn": 1, "status": "PASS", "text": "A"},
        {"answer_id": "b", "case_id": "TC", "turn": 1, "status": "PASS", "text": "B"},
    ]
    before = [dict(item) for item in answers]
    decisions = run_pairwise_pass(
        answers, [("a", "b")], ["good", "failed"],
        lambda request: ({"winner": "TIE", "rationale": "equivalent"} if request["judge_id"] == "good" else (_ for _ in ()).throw(TimeoutError("judge timeout"))),
        controls={"rule": "1.1", "prompt": "p"}, seed="fixed",
    )
    assert answers == before
    assert [item.status for item in decisions] == ["AVAILABLE", "UNAVAILABLE"]
    assert decisions[1].winner == "INVALID"


def test_position_retest_compares_winning_answer_identity_after_side_swap():
    summary = summarize_pairwise([
        _pair(left_answer_id="a", right_answer_id="b", display_order="A_LEFT", winner="LEFT"),
        _pair(left_answer_id="b", right_answer_id="a", display_order="B_LEFT", winner="RIGHT"),
    ])
    assert summary["position_retests_n"] == 1
    assert summary["position_flip_rate"] == 0


def test_agreement_excludes_self_judging_and_unavailable_cells():
    rows = []
    for subject_id, scores in (("s1", (0, 0)), ("s2", (1, 1)), ("s3", (3, 3))):
        for judge_id, score in zip(("j1", "j2"), scores):
            rows.append({
                "case_id": "TC-1", "turn": 1, "status": "PASS",
                "subject": {"id": subject_id}, "judge": {"id": judge_id},
                "scores": {"quality": score}, "self_judging": False,
            })
    rows.extend([
        {"case_id": "TC-4", "turn": 1, "status": "UNAVAILABLE", "subject": {"id": "subject"}, "judge": {"id": "j1"}, "scores": {}, "self_judging": False},
        {"case_id": "TC-4", "turn": 1, "status": "PASS", "subject": {"id": "subject"}, "judge": {"id": "j2"}, "scores": {"quality": 2}, "self_judging": True},
    ])
    report = agreement_report(rows, "quality")
    assert report["interpretation"] == "DESCRIPTIVE_ONLY"
    assert report["attempted_n"] == 8
    assert report["eligible_n"] == 6
    assert report["missing_n"] == 2
    assert report["krippendorff_alpha_ordinal"] == pytest.approx(1)
    assert report["kendall_w"] == pytest.approx(1)
    assert report["pairwise_spearman"][0]["spearman_rho"] == pytest.approx(1)


def test_kendall_w_diagonal_self_matrix_keeps_missing_ranks_unavailable():
    rows = []
    subjects = ("a", "b", "c")
    for subject_index, subject in enumerate(subjects):
        for judge_index, judge in enumerate(subjects):
            rows.append({
                "case_id": "TC", "turn": 1, "status": "PASS",
                "subject": {"id": subject}, "judge": {"id": judge},
                "scores": {"quality": subject_index},
                "self_judging": subject == judge,
            })
    report = agreement_report(rows, "quality")
    stratum = report["kendall_strata"][0]
    assert stratum["subject_n"] == 3
    assert stratum["judge_n"] == 3
    assert stratum["missing_n"] == 3
    assert stratum["missing_policy"] == "NO_IMPUTATION"
    assert stratum["kendall_w"] is None


def test_red_line_nominal_agreement_excludes_self_and_reports_denominator():
    rows = [
        {"case_id": "TC", "turn": 1, "status": "PASS", "subject": {"id": "s"}, "judge": {"id": "j1"}, "self_judging": False, "triggered_red_lines": ("RL",), "red_line_evidence": {"RL": ("span",)}},
        {"case_id": "TC", "turn": 1, "status": "PASS", "subject": {"id": "s"}, "judge": {"id": "j2"}, "self_judging": False, "triggered_red_lines": ("RL",), "red_line_evidence": {"RL": ("span",)}},
        {"case_id": "TC", "turn": 1, "status": "PASS", "subject": {"id": "s"}, "judge": {"id": "self"}, "self_judging": True, "triggered_red_lines": (), "red_line_evidence": {"RL": ()}},
    ]
    report = red_line_agreement_report(rows, "RL")
    assert report["eligible_n"] == 2
    assert report["missing_n"] == 1
    assert report["krippendorff_alpha_nominal"] is None


def test_self_judging_requires_same_provider_and_model():
    assert self_judging({"provider": "gpt", "model": "m"}, {"provider": "gpt", "model": "m"})
    assert not self_judging({"provider": "gpt", "model": "m"}, {"provider": "gpt", "model": "other"})


def test_memory_metrics_preserve_missing_denominator():
    summary = summarize_memory_metrics([
        {"status": "pass"}, {"status": "fail"}, {"status": "skip"},
    ])
    assert summary["eligible_n"] == 2
    assert summary["missing_n"] == 1
    assert summary["retention_and_use_rate"] == pytest.approx(0.5)


def test_non_retrieval_memory_checks_do_not_create_false_fact_false_negatives():
    summary = summarize_memory_metrics([
        {"status": "pass", "check_type": "retrieve", "expected_facts": ["a", "b"], "retrieved_facts": ["a", "extra"]},
        {"status": "pass", "check_type": "not_use", "expected_facts": ["forbidden"], "retrieved_facts": []},
        {"status": "fail", "check_type": "isolation", "contamination_candidates": ["other-user"]},
    ])
    assert summary["fact_retrieval"] == {"tp": 1, "fp": 1, "fn": 1, "precision": 0.5, "recall": 0.5}
    assert summary["contamination"]["candidate_n"] == 1
    assert summary["contamination"]["clean_rate"] == 0
