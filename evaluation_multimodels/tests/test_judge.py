import json

import pytest

from xiaoan_eval.judge import (
    JudgeValidationError,
    parse_judge_response,
    validate_claim_evidence,
)
from xiaoan_eval.rules import load_rating_rule


MODULES = [
    "基础能力",
    "行动赋权",
    "法律维权",
    "求助转介",
    "表达能力",
    "丰富性",
    "包容性与可及性",
]
RULE = load_rating_rule("ratings rule.yml")


def valid_payload() -> dict:
    return {
        "red_lines": [
            {
                "id": f"RL-{number:02d}",
                "triggered": False,
                "evidence": [],
                "uncertainty": "low",
            }
            for number in range(1, 7)
        ],
        "dimensions": [
            {
                "module": module,
                "score": 2,
                "supporting_evidence": ["answer excerpt"],
                "deduction_evidence": [],
                "uncertainty": "low",
            }
            for module in MODULES
        ],
        "legal_claims": [],
        "faithfulness_claims": [],
    }


def test_parse_judge_response_returns_validated_structured_result() -> None:
    result = parse_judge_response(json.dumps(valid_payload(), ensure_ascii=False), RULE)

    assert result.red_lines[0].id == "RL-01"
    assert result.dimensions[-1].module == "包容性与可及性"
    assert result.dimensions[-1].score == 2


@pytest.mark.parametrize(
    ("raw", "message"),
    [
        ("not json", "valid JSON"),
        (json.dumps({"red_lines": []}), "dimensions"),
    ],
)
def test_parse_judge_response_rejects_invalid_json_or_schema(
    raw: str, message: str
) -> None:
    with pytest.raises(JudgeValidationError, match=message):
        parse_judge_response(raw, RULE)


@pytest.mark.parametrize("score", [-1, 0.5, 4, True, "2"])
def test_parse_judge_response_rejects_scores_outside_anchored_integer_scale(
    score: object,
) -> None:
    payload = valid_payload()
    payload["dimensions"][0]["score"] = score

    with pytest.raises(JudgeValidationError, match="anchored integer"):
        parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)


def test_parse_judge_response_requires_six_unique_red_lines_and_seven_dimensions() -> None:
    payload = valid_payload()
    payload["red_lines"] = payload["red_lines"][:-1]
    payload["dimensions"][1]["module"] = payload["dimensions"][0]["module"]

    with pytest.raises(JudgeValidationError, match="unique IDs from the rating rule"):
        parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)


def test_parse_judge_response_rejects_invented_rubric_modules() -> None:
    payload = valid_payload()
    payload["dimensions"][-1]["module"] = "invented module"

    with pytest.raises(JudgeValidationError, match="modules from the rating rule"):
        parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)


def test_supported_claim_requires_a_catalog_evidence_ref() -> None:
    payload = valid_payload()
    payload["faithfulness_claims"] = [{
        "claim": "可以联系妇联",
        "supported": True,
        "evidence_refs": [],
        "uncertainty": "low",
    }]
    result = parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)

    with pytest.raises(JudgeValidationError, match="requires at least one evidence_ref"):
        validate_claim_evidence(result, [])


def test_claim_evidence_refs_must_exist_in_the_turn_catalog() -> None:
    payload = valid_payload()
    payload["faithfulness_claims"] = [{
        "claim": "可以联系妇联",
        "supported": True,
        "evidence_refs": ["capsule:n3c:act:9"],
        "uncertainty": "low",
    }]
    result = parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)

    with pytest.raises(JudgeValidationError, match="unknown refs"):
        validate_claim_evidence(
            result,
            [{"ref": "capsule:n3c:act:0", "type": "capsule", "content": {}}],
        )


def test_unsupported_claim_cannot_cite_evidence() -> None:
    payload = valid_payload()
    payload["faithfulness_claims"] = [{
        "claim": "没有证据的说法",
        "supported": False,
        "evidence_refs": ["input:current"],
        "uncertainty": "low",
    }]
    result = parse_judge_response(json.dumps(payload, ensure_ascii=False), RULE)

    with pytest.raises(JudgeValidationError, match="requires empty evidence_refs"):
        validate_claim_evidence(
            result,
            [{"ref": "input:current", "type": "user_input", "content": "input"}],
        )
