import hashlib
import json

import pytest

from xiaoan_eval.attribution_client import AttributionClient, build_attribution_request


def _digest(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode()).hexdigest()


def _snapshot() -> dict:
    content = "Grounded evidence."
    return {
        "schema_version": "effective-context-snapshot/v1",
        "snapshot_id": "snap-1",
        "turn": 1,
        "context_kind": "ordinary",
        "experiment_arm": "candidate",
        "candidate_id": "secret-candidate",
        "router": {"status": "NOT_APPLICABLE", "units": []},
        "composer": {
            "status": "INVOKED",
            "units": [
                {
                    "occurrence_id": "source:s1:T1:1",
                    "unit_id": "source:s1",
                    "layer": "SOURCE",
                    "source_turn": 1,
                    "content": content,
                    "content_sha256": _digest(content),
                    "policy_ids": [],
                }
            ],
        },
    }


def test_request_is_blinded_and_marks_captured_text_untrusted() -> None:
    request = build_attribution_request("Answer.", _snapshot(), judge_version="judge-a")

    serialized = json.dumps(request)
    assert "candidate" not in serialized
    assert "secret-candidate" not in serialized
    assert request["content_is_untrusted"] is True
    assert request["judge_version"] == "judge-a"
    assert request["output_contract"]["strict"] is True
    assert request["output_contract"]["schema"]["additionalProperties"] is False
    assert request["evidence_catalog"][0]["ref"] == "source:source:s1:T1:1"


def test_client_invokes_injected_provider_and_validates_result() -> None:
    answer = "Answer."

    def provider(request):
        assert request["task"] == "attribute_answer_to_captured_evidence"
        return json.dumps(
            {
                "contract_version": "attribution/v1",
                "claims": [
                    {
                        "claim_id": "c1",
                        "kind": "FACTUAL",
                        "answer_span": {"start": 0, "end": 7, "text": answer},
                        "relations": [
                            {
                                "relation": "UNSUPPORTED",
                                "evidence_ref": None,
                                "evidence_span": None,
                            }
                        ],
                        "unsupported_category": "UNVERIFIABLE_UNSUPPORTED",
                        "uncertainty": "LOW",
                    }
                ],
                "policies": [],
                "abstention": {"status": "ANSWERED", "reason": None},
            }
        )

    result = AttributionClient(provider, judge_version="judge-a").judge(
        answer, _snapshot()
    )

    assert result.judge_version == "judge-a"
    assert result.claims[0].unsupported_category == "UNVERIFIABLE_UNSUPPORTED"


def test_client_checkpoints_raw_response_before_validation() -> None:
    events = []
    client = AttributionClient(
        lambda _request: "[]",
        judge_version="judge-a",
        checkpoint=events.append,
    )

    with pytest.raises(ValueError):
        client.judge("Answer.", _snapshot(), case_id="TC-01")

    assert events[0]["event"] == "attribution_judge"
    assert events[0]["case_id"] == "TC-01"
    assert events[0]["snapshot_id"] == "snap-1"
    assert events[0]["turn"] == 1
    assert events[0]["raw_response"] == "[]"
    assert events[0]["error"] is None
    assert events[1]["event"] == "attribution_judge_validation"
    assert events[1]["status"] == "ERROR"
    assert events[1]["error"]
