import json

import pytest

from xiaoan_eval.artifacts import ArtifactSafetyError, build_artifacts


def _record(case_id="TC-01", status="FAIL", stage="router"):
    return {
        "case_id": case_id,
        "status": status,
        "safety": {"hard_gate_passed": True, "red_lines": []},
        "pipeline": {"route_accuracy": 0.0, "ground_recall": 1.0},
        "conversation": {
            "conversation_id": "c1",
            "turns": [{"turn": 1, "user_input": "question", "assistant_response": "answer"}],
        },
        "quality": {"weighted_total": 1.8},
        "performance": {"latency_ms": 120, "tokens": 80},
        "review": {"status": "not_requested"},
        "failure": {"primary_stage": stage, "secondary_stages": []},
        "cohorts": {"risk": ["critical"], "persona": ["survivor"]},
        "evidence_refs": ["TC-01:T1:route"],
        "remediation": {"suggested_patch": {"turns[0].expected.route_ids": ["crisis_sop"]}},
    }


def test_build_artifacts_produces_stable_jsonl_and_three_markdown_views():
    artifacts = build_artifacts([_record("TC-02", "PASS"), _record()], lambda _: True)

    lines = artifacts.to_jsonl().splitlines()
    assert [json.loads(line)["case_id"] for line in lines] == ["TC-01", "TC-02"]
    assert list(artifacts.markdown) == ["case", "cohort", "global"]
    assert "TC-01" in artifacts.markdown["case"]
    assert "risk:critical" in artifacts.markdown["cohort"]
    assert "router" in artifacts.markdown["global"]
    assert artifacts.cases[0].quality["weighted_total"] == 1.8


def test_report_preserves_complete_conversation_content():
    artifacts = build_artifacts([_record()], lambda _: True)

    assert artifacts.cases[0].conversation["turns"][0] == {
        "turn": 1,
        "user_input": "question",
        "assistant_response": "answer",
    }


def test_case_report_shows_quality_scores_and_turn_judge_evidence():
    record = _record()
    record["quality"] = {
        "weighted_total": 0.6504,
        "dimensions": {"行动赋权": 0.8775, "法律维权": 0.2325},
    }
    record["review"] = {
        "status": "NEEDS_REVIEW",
        "per_turn": ["NEEDS_REVIEW"],
        "judge_audit": [
            {
                "primary": {
                    "dimensions": [
                        {
                            "module": "行动赋权",
                            "score": 1,
                            "supporting_evidence": ["给出立即避险步骤"],
                            "deduction_evidence": ["未确认手机是否可安全使用"],
                        }
                    ]
                },
                "secondary": None,
                "reconciliation_reasons": ["second judge required but unavailable"],
            }
        ],
    }

    report = build_artifacts([record], lambda _: True).markdown["case"]

    assert "Overall quality score: 0.6504/3" in report
    assert "| Dimension | Score (0-3) |" in report
    assert "行动赋权 | 0.8775/3" in report
    assert "/100" not in report
    assert "Turn 1" in report
    assert "给出立即避险步骤" in report
    assert "未确认手机是否可安全使用" in report
    assert "second judge required but unavailable" in report


def test_report_rejects_legacy_unanchored_judge_scores():
    record = _record()
    record["review"] = {
        "status": "completed",
        "judge_audit": [
            {
                "primary": {
                    "dimensions": [{"module": "行动赋权", "score": 0.92}]
                }
            }
        ],
    }

    with pytest.raises(ValueError, match="not an anchored rating-rule score"):
        build_artifacts([record], lambda _: True)


def test_remediation_is_output_only_and_does_not_mutate_source_mapping():
    record = _record()
    before = json.dumps(record, sort_keys=True)

    artifacts = build_artifacts([record], lambda _: True)

    assert json.dumps(record, sort_keys=True) == before
    assert artifacts.cases[0].remediation["suggested_patch"] == {
        "turns[0].expected.route_ids": ["crisis_sop"]
    }


def test_report_rejects_pii_values_even_under_unexpected_field_names():
    record = _record()
    record["pipeline"]["reason"] = "call 13800138000"

    with pytest.raises(ArtifactSafetyError, match="failed PII validation"):
        build_artifacts([record], lambda value: "13800138000" not in json.dumps(value))
