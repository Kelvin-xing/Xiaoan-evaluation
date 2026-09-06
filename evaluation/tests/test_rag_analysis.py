from xiaoan_eval.rag_analysis import render_rag_markdown, summarize_rag


def test_summarize_rag_aggregates_metrics_and_trace_attribution() -> None:
    records = [
        {
            "case_id": "TC-01",
            "pipeline": {
                "turns": [
                    {
                        "route": {"status": "pass", "score": 1.0},
                        "route_preference": {"status": "fail", "score": 0.0},
                        "ground_recall": {"status": "pass", "score": 1.0},
                        "ground_precision": {"status": "fail", "score": 0.5},
                    },
                    {
                        "route": {"status": "skip", "score": None},
                        "route_preference": {"status": "skip", "score": None},
                        "ground_recall": {"status": "skip", "score": None},
                        "ground_precision": {"status": "skip", "score": None},
                    },
                ],
                "turn_traces": [
                    {
                        "turn": 1,
                        "trace": {
                            "route": {"id": "n3"},
                            "ground": {"resolved_ground": ["source:1"]},
                        },
                    },
                    {
                        "turn": 2,
                        "trace": {
                            "route": {"id": "baseline"},
                            "ground": {"resolved_ground": []},
                        },
                    },
                ],
            },
            "review": {
                "judge_audit": [
                    {
                        "primary": {
                            "faithfulness_claims": [
                                {
                                    "claim": "识别了风险",
                                    "supported": True,
                                    "evidence_refs": ["capsule:n3:recognize:0"],
                                    "uncertainty": "low",
                                },
                                {
                                    "claim": "建议联系朋友",
                                    "supported": True,
                                    "evidence_refs": ["source:1"],
                                    "uncertainty": "low",
                                },
                            ]
                        }
                    },
                    {"primary": {"faithfulness_claims": []}},
                ]
            },
        }
    ]

    summary = summarize_rag(records)

    assert "ground_recall" not in summary["metrics"]
    assert "ground_precision" not in summary["metrics"]
    assert summary["metrics"]["route_acceptance"] == {
        "evaluated_turns": 1,
        "mean": 1.0,
    }
    assert summary["metrics"]["route_preference"] == {
        "evaluated_turns": 1,
        "mean": 0.0,
    }
    assert summary["attribution"]["counts"] == {
        "grounded_capsule": 1,
        "capsule_only": 0,
        "grounded_baseline": 0,
        "baseline_no_resolved_refs": 1,
    }
    assert summary["attribution"]["turns"][0]["case_id"] == "TC-01"
    assert summary["capsule_usage"] == {
        "status": "unavailable",
        "reason": "current Chatflow traces do not expose verifiable capsule content units",
    }

    markdown = render_rag_markdown(summary)
    assert "# Routing and RAG metrics" in markdown
    assert "| route_acceptance | 1 | 1.000 |" in markdown
    assert "| route_preference | 1 | 0.000 |" in markdown
    assert "Capsule content attribution: unavailable" in markdown
    assert "capsule_claim_alignment" not in markdown


def test_summarize_rag_uses_pipeline_observations_for_ranking_and_route_confusion() -> None:
    records = [{
        "case_id": "TC-01",
        "pipeline": {
            "turns": [],
            "turn_traces": [],
            "observations": [{
                "turn": 1,
                "oracle_approved": True,
                "expected": {
                    "preferred_route_id": "crisis_sop",
                    "relevant_ground_refs": ["a", "b"],
                },
                "actual": {
                    "route_id": "crisis_sop",
                    "ranked_refs": ["x", "b", "a"],
                },
                "judge": {},
            }],
        },
    }]

    summary = summarize_rag(records)

    assert summary["retrieval"]["mrr"] is None
    assert summary["retrieval"]["evaluated_turns"] == 0
    assert summary["route_confusion"] == {"crisis_sop": {"crisis_sop": 1}}


def test_ranking_metrics_deduplicate_repeated_refs() -> None:
    records = [{"case_id": "TC-01", "pipeline": {
        "turns": [], "turn_traces": [], "observations": [{
            "turn": 1, "oracle_approved": True,
            "expected": {"preferred_route_id": "n1", "relevant_ground_refs": ["a"]},
            "actual": {"route_id": "n1", "ranked_refs": ["a", "a", "x"]},
            "judge": {},
        }],
    }}]

    retrieval = summarize_rag(records)["retrieval"]

    assert retrieval["mrr"] is None
    assert retrieval["ndcg"] is None


def test_summarize_rag_micro_aggregates_retrieval_counts() -> None:
    records = [{"case_id": "TC-01", "pipeline": {
        "turns": [
            {"ground_recall": {"status": "fail", "score": 0.5,
                               "counts": {"tp": 1, "fp": 1, "fn": 1}}},
            {"ground_recall": {"status": "pass", "score": 1.0,
                               "counts": {"tp": 2, "fp": 0, "fn": 0}}},
        ],
        "turn_traces": [],
    }}]

    retrieval = summarize_rag(records)["retrieval"]

    assert retrieval["evaluated_turns"] == 0


def test_summarize_rag_reports_capsule_usage_when_units_are_traced() -> None:
    summary = summarize_rag([{"case_id": "TC-01", "pipeline": {
        "turns": [], "turn_traces": [], "observations": [{
            "oracle_approved": True,
            "expected": {},
            "actual": {"capsule_id": "n3", "capsule_units": [
                {"unit_id": "recognize:0"}, {"unit_id": "act:0"}
            ]},
            "judge": {},
        }],
    }}])

    assert summary["capsule_usage"]["status"] == "available"
    assert summary["capsule_usage"]["injected_units"] == 2
    assert "available" in render_rag_markdown(summary)
