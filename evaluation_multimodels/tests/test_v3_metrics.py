from xiaoan_eval.v3_metrics import (
    judge_calibration,
    render_v3_markdown,
    score_claims,
    semantic_attribution_metrics,
    summarize_v3,
)


def test_claim_score_and_report() -> None:
    score = score_claims(
        ["a", "b"],
        [
            {"claim": "a", "supported": True},
            {"claim": "useful extra", "supported": True},
            {"claim": "hallucination", "supported": False},
        ],
    )
    assert (score.tp, score.fp, score.fn) == (1, 1, 1)
    assert score.completeness_f1 == 0.5
    assert score.faithfulness == 2 / 3
    assert "claim_f1" in render_v3_markdown({"claims": {"f1": 0.5}, "judge_calibration": {}})


def test_judge_calibration_counts_disagreement() -> None:
    records = [{"review": {"judge_audit": [{
        "primary": {"dimensions": [{"score": 3}]},
        "secondary": {"dimensions": [{"score": 0}]},
    }]}}]
    result = judge_calibration(records)
    assert result["paired_turns"] == 1
    assert result["pass_fail_flips"] == 1


def test_summarize_v3_aggregates_claim_classification_tool_and_agent_metrics() -> None:
    records = [{
        "case_id": "TC-01",
        "pipeline": {"observations": [{
            "turn": 1,
            "oracle_approved": True,
            "expected": {
                "safety_levels": ["high"],
                "route_ids": ["crisis_sop"],
                "preferred_route_id": "crisis_sop",
                "response_oracle": {
                    "required_claims": ["a", "b"],
                    "forbidden_claims": ["dangerous"],
                    "must_cite": ["source:a"],
                    "should_abstain": False,
                    "expected_tools": [{"name": "lookup", "arguments": {"ref": "a"}}],
                    "goal_completed": True,
                    "max_steps": 2,
                },
            },
            "actual": {
                "safety_level": "high",
                "route_id": "crisis_sop",
                "abstained": False,
                "citations": ["source:a", "source:x"],
                "source_refs": ["source:a"],
                "wiki_refs": ["wiki:a"],
                "capsule_id": "crisis_sop",
                "tool_calls": [
                    {"name": "lookup", "arguments": {"ref": "a"}},
                    {"name": "extra", "arguments": {}},
                ],
                "goal_completed": True,
                "steps": 2,
                "invalid_tool_calls": 1,
                "retries": 2,
                "timeouts": 0,
            },
            "judge": {"faithfulness_claims": [
                {"claim": "a", "supported": True},
                {"claim": "hallucination", "supported": False},
            ]},
        }]},
        "review": {"judge_audit": []},
    }]

    summary = summarize_v3(records)

    assert summary["claims"]["tp"] == 1
    assert summary["claims"]["fp"] == 1
    assert summary["claims"]["fn"] == 1
    assert summary["claims"]["faithfulness"] == 0.5
    assert summary["answer"]["correctness_f1"] == 0.5
    assert summary["citations"]["precision"] == 0.5
    assert summary["citations"]["recall"] == 1.0
    assert summary["route"]["accuracy"] == 1.0
    assert summary["route"]["macro_f1"] == 1.0
    assert summary["route"]["micro_f1"] == 1.0
    assert summary["safety"]["accuracy"] == 1.0
    assert summary["refusal"]["tn"] == 1
    assert summary["tools"]["precision"] == 0.5
    assert summary["tools"]["recall"] == 1.0
    assert summary["tools"]["argument_accuracy"] == 1.0
    assert summary["agent"]["goal_completion_rate"] == 1.0
    assert summary["agent"]["invalid_tool_calls"] == 1
    assert summary["agent"]["retries"] == 2
    assert summary["agent"]["timeouts"] == 0
    assert summary["statistics"]["route_accuracy_95ci"] == [1.0, 1.0]


def test_multi_accepted_labels_are_counted_without_inventing_confusion_class() -> None:
    records = [{"pipeline": {"observations": [{
        "oracle_approved": True,
        "expected": {
            "route_ids": ["baseline", "n3"],
            "safety_levels": ["low", "normal"],
            "response_oracle": {},
        },
        "actual": {"route_id": "n3", "safety_level": "normal"},
        "judge": {},
    }]}, "review": {"judge_audit": []}}]

    summary = summarize_v3(records)

    assert summary["route"]["accepted_accuracy"] == 1.0
    assert summary["route"]["ambiguous_turns"] == 1
    assert summary["route"]["evaluated_turns"] == 0
    assert summary["safety"]["accepted_accuracy"] == 1.0


def test_capsule_attribution_requires_exact_injected_unit_refs() -> None:
    records = [{"pipeline": {"observations": [{
        "oracle_approved": True,
        "expected": {"response_oracle": {}},
        "actual": {
            "capsule_id": "crisis_sop",
            "capsule_units": [{"unit_id": "recognize:0", "content_hash": "sha256:abc"}],
        },
        "judge": {"faithfulness_claims": [
            {"claim": "a", "supported": True,
             "evidence_refs": ["capsule:crisis_sop:recognize:0"]},
            {"claim": "b", "supported": True,
             "evidence_refs": ["capsule:crisis_sop:recognize:9"]},
        ]},
    }]}, "review": {"judge_audit": []}}]

    attribution = summarize_v3(records)["capsule_attribution"]

    assert attribution["injected_units"] == 1
    assert attribution["claims_with_valid_capsule_evidence"] == 1
    assert attribution["claim_alignment"] == 0.5
    assert attribution["content_coverage"] == 1.0
    assert attribution["citation_precision"] == 0.5


def test_semantic_attribution_metrics_do_not_require_a_human_confidence_gate() -> None:
    result = semantic_attribution_metrics(
        [{
            "status": "AVAILABLE",
            "judge_version": "judge-a",
            "benchmark": {"status": "NOT_MEASURED", "version": None},
            "capsule_cohort": "ordinary_capsule",
            "evidence_catalog": [],
            "claims": [{
                "claim_id": "c1", "kind": "FACTUAL",
                "relations": [{"relation": "UNSUPPORTED", "evidence_ref": None}],
                "unsupported_category": "UNVERIFIABLE_UNSUPPORTED",
            }],
            "policies": [],
        }]
    )

    assert result["status"] == "AVAILABLE"
    assert result["benchmark_status"] == "NOT_MEASURED"
    assert result["claim_support"]["denominator_weight"] == 1
