from pathlib import Path

import pytest

from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval_core.rubric import RubricContractError, evaluate_rubric


RULE = load_rating_rule(Path(__file__).parents[1] / "ratings rule.yml")


def payload(score=2, *, triggered=(), evidence=True):
    return {
        "dimensions": [
            {
                "module": module.name,
                "score": score,
                "reason": "fixture judgement",
                "supporting_evidence": ["answer span"] if evidence else [],
                "deduction_evidence": [],
                "uncertainty": "low",
            }
            for module in RULE.modules
        ],
        "red_lines": [
            {
                "id": red.id,
                "triggered": red.id in triggered,
                "reason": "fixture redline judgement",
                "evidence": ["dangerous span"] if red.id in triggered else [],
                "uncertainty": "low",
            }
            for red in RULE.red_lines
        ],
    }


def test_scores_all_dimensions_with_details():
    result = evaluate_rubric({"quality_focus": []}, payload(2), RULE)

    assert result["status"] == "AVAILABLE"
    assert result["scores"] == {module.name: 2 for module in RULE.modules}
    assert result["weighted_total"] == pytest.approx(2.0)
    assert len(result["dimension_details"]) == len(RULE.modules)
    assert result["gate"] == "PASS"


def test_red_line_fails_gate_without_zeroing_scores():
    result = evaluate_rubric({}, payload(3, triggered={"RL-03"}), RULE)

    assert result["red_line_triggered"] is True
    assert result["triggered_red_lines"] == ["RL-03"]
    assert result["scores"] == {module.name: 3 for module in RULE.modules}
    assert result["weighted_total"] == pytest.approx(3.0)
    assert "RL-03" in result["reasons"][0]


def test_dynamic_focus_preserves_existing_weight_formula():
    result = evaluate_rubric({"quality_focus": ["行动赋权"]}, payload(0), RULE)

    assert result["final_weights"]["行动赋权"] == pytest.approx(0.27 / 1.09)
    assert result["final_weights"]["基础能力"] == pytest.approx(0.22 / 1.09)


def test_missing_judge_is_unavailable_and_never_zero():
    result = evaluate_rubric({}, None, RULE, reason="provider timeout")

    assert result["status"] == "UNAVAILABLE"
    assert result["weighted_total"] is None
    assert result["scores"] == {}
    assert "legacy" not in result


def test_incomplete_payload_is_contract_error():
    bad = payload()
    bad["dimensions"] = bad["dimensions"][:-1]
    with pytest.raises(RubricContractError, match="dimensions"):
        evaluate_rubric({}, bad, RULE)


def test_judge_payload_with_missing_reasons_is_rejected():
    raw = payload(1)
    del raw['red_lines'][0]['reason']
    with pytest.raises(RubricContractError, match='reason'):
        evaluate_rubric({}, raw, RULE)
