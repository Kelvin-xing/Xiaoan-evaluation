import hashlib
import json

import pytest

from xiaoan_eval.attribution_judge import (
    AttributionValidationError,
    parse_attribution_response,
)


ANSWER = "You can call the police now."
EVIDENCE = "Police can be contacted for immediate help."


def _catalog() -> list[dict]:
    return [
        {
            "ref": "source:source:police:T1:1",
            "layer": "SOURCE",
            "occurrence_id": "source:police:T1:1",
            "unit_id": "source:police",
            "source_turn": 1,
            "content": EVIDENCE,
            "content_sha256": "sha256:"
            + hashlib.sha256(EVIDENCE.encode()).hexdigest(),
            "policy_ids": ["policy:urgent-help"],
            "snapshot_id": "snap-1",
            "invocation": "composer",
        }
    ]


def _response() -> dict:
    return {
        "contract_version": "attribution/v1",
        "claims": [
            {
                "claim_id": "c1",
                "kind": "ACTION",
                "answer_span": {"start": 0, "end": 27, "text": ANSWER[:27]},
                "relations": [
                    {
                        "relation": "ENTAILS",
                        "evidence_ref": "source:source:police:T1:1",
                        "evidence_span": {
                            "start": 0,
                            "end": len(EVIDENCE),
                            "text": EVIDENCE,
                        },
                    }
                ],
                "unsupported_category": None,
                "uncertainty": "LOW",
            }
        ],
        "policies": [
            {
                "policy_id": "policy:urgent-help",
                "evidence_ref": "source:source:police:T1:1",
                "applicability": "APPLICABLE",
                "compliance": "COMPLIANT",
                "answer_spans": [{"start": 0, "end": 27, "text": ANSWER[:27]}],
                "uncertainty": "LOW",
            }
        ],
        "abstention": {"status": "ANSWERED", "reason": None},
    }


def test_parser_binds_answer_evidence_and_policy_occurrences() -> None:
    result = parse_attribution_response(json.dumps(_response()), ANSWER, _catalog())

    assert result.claims[0].relations[0].layer == "SOURCE"
    assert result.claims[0].relations[0].occurrence_id == "source:police:T1:1"
    assert result.policies[0].policy_id == "policy:urgent-help"


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (
            lambda payload: payload["claims"][0]["relations"][0].update(
                {"evidence_ref": "source:fabricated"}
            ),
            "unknown evidence_ref",
        ),
        (
            lambda payload: payload["claims"][0]["answer_span"].update(
                {"end": 100, "text": "wrong"}
            ),
            "answer_span",
        ),
        (
            lambda payload: payload["policies"][0].update(
                {"policy_id": "policy:fabricated"}
            ),
            "policy_id",
        ),
    ],
)
def test_parser_fails_closed_on_unbound_attribution(mutate, message: str) -> None:
    payload = _response()
    mutate(payload)
    with pytest.raises(AttributionValidationError, match=message):
        parse_attribution_response(json.dumps(payload), ANSWER, _catalog())


def test_unsupported_claim_cannot_carry_evidence() -> None:
    payload = _response()
    payload["claims"][0]["relations"][0]["relation"] = "UNSUPPORTED"
    payload["claims"][0]["unsupported_category"] = "UNVERIFIABLE_UNSUPPORTED"

    with pytest.raises(AttributionValidationError, match="UNSUPPORTED.*no evidence"):
        parse_attribution_response(json.dumps(payload), ANSWER, _catalog())


def test_partial_remains_distinct_and_requires_bound_spans() -> None:
    payload = _response()
    payload["claims"][0]["relations"][0]["relation"] = "PARTIAL"

    result = parse_attribution_response(json.dumps(payload), ANSWER, _catalog())

    assert result.claims[0].relations[0].relation == "PARTIAL"
