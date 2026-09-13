import json
import pytest
from xiaoan_eval.judge_client import JudgeClient
from xiaoan_eval.rules import load_rating_rule


def test_client_injects_provider_and_validates_response() -> None:
    rule = load_rating_rule("ratings rule.yml")
    payload = {
        "red_lines": [{"id": r.id, "triggered": False, "evidence": [], "uncertainty": "low"} for r in rule.red_lines],
        "dimensions": [{"module": m.name, "score": 2, "supporting_evidence": [], "deduction_evidence": [], "uncertainty": "low"} for m in rule.modules],
        "legal_claims": [],
        "faithfulness_claims": [],
    }
    seen = []
    client = JudgeClient(lambda request: seen.append(request) or json.dumps(payload), rule)
    result = client.judge({"response": "answer"})
    assert result.dimensions[0].score == 2
    assert seen[0]["response"] == "answer"
    assert seen[0]["oracle_contract"]["items"] == []
    assert result.oracle_assessment["status"] == "NOT_APPLICABLE"


def test_client_checkpoints_raw_response_before_validation() -> None:
    events = []
    client = JudgeClient(
        lambda _request: "[]",
        load_rating_rule("ratings rule.yml"),
        checkpoint=events.append,
        checkpoint_event="primary_judge",
    )

    with pytest.raises(ValueError):
        client.judge({"case_id": "TC-01", "turn": 2})

    assert events[0] == {
        "event": "primary_judge",
        "case_id": "TC-01",
        "turn": 2,
        "raw_response": "[]",
        "provider_usage": {},
        "error": None,
    }
    assert events[1]["event"] == "primary_judge_validation"
    assert events[1]["status"] == "ERROR"
    assert "JudgeValidationError" in events[1]["error"]


def test_client_checkpoints_provider_cache_usage() -> None:
    rule = load_rating_rule("ratings rule.yml")
    payload = {
        "red_lines": [{"id": item.id, "triggered": False, "evidence": [], "uncertainty": "low"} for item in rule.red_lines],
        "dimensions": [{"module": item.name, "score": 2, "supporting_evidence": [], "deduction_evidence": [], "uncertainty": "low"} for item in rule.modules],
        "legal_claims": [], "faithfulness_claims": [],
    }

    class TextWithUsage(str):
        usage = {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 80, "cache_write_tokens": 10}}

    events = []
    JudgeClient(lambda _request: TextWithUsage(json.dumps(payload)), rule, checkpoint=events.append).judge({"case_id": "TC-01", "turn": 1})

    assert events[0]["provider_usage"]["input_tokens_details"] == {"cached_tokens": 80, "cache_write_tokens": 10}
