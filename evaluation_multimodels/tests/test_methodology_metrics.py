import pytest

from xiaoan_eval.methodology_metrics import (
    agreement_report,
    pairwise_decision,
    run_pairwise_pass,
    self_judging,
    summarize_memory_metrics,
    summarize_pairwise,
)


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
