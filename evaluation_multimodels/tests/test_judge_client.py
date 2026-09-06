import json
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
    assert seen == [{"response": "answer"}]
