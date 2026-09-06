from xiaoan_eval.attribution import summarize_semantic_attribution


def test_semantic_summary_keeps_overlapping_layers_and_unsupported_denominator() -> None:
    turns = [
        {
            "status": "AVAILABLE",
            "judge_version": "judge-a",
            "benchmark": {"status": "NOT_MEASURED", "version": None},
            "capsule_cohort": "ordinary_capsule",
            "evidence_catalog": [
                {"ref": "capsule:a:T1", "layer": "CAPSULE", "occurrence_id": "a:T1"},
                {"ref": "wiki:w:T1", "layer": "WIKI", "occurrence_id": "w:T1"},
            ],
            "claims": [
                {
                    "claim_id": "c1",
                    "kind": "FACTUAL",
                    "relations": [
                        {"relation": "ENTAILS", "evidence_ref": "capsule:a:T1"},
                        {"relation": "ENTAILS", "evidence_ref": "wiki:w:T1"},
                    ],
                    "unsupported_category": None,
                },
                {
                    "claim_id": "c2",
                    "kind": "RECOMMENDATION",
                    "relations": [
                        {"relation": "UNSUPPORTED", "evidence_ref": None}
                    ],
                    "unsupported_category": "UNVERIFIABLE_UNSUPPORTED",
                },
            ],
            "policies": [],
        }
    ]

    summary = summarize_semantic_attribution(turns)

    assert summary["claim_support"]["denominator_weight"] == 2
    assert summary["claim_support"]["overall_rate"] == 0.5
    assert summary["claim_support"]["by_layer"]["CAPSULE"]["rate"] == 0.5
    assert summary["claim_support"]["by_layer"]["WIKI"]["rate"] == 0.5
    assert summary["unsupported_content"]["UNVERIFIABLE_UNSUPPORTED"] == 1
    assert summary["benchmark_status"] == "NOT_MEASURED"


def test_occurrences_policy_denominators_and_no_capsule_cohorts_are_explicit() -> None:
    turns = [
        {
            "status": "AVAILABLE",
            "judge_version": "judge-a",
            "benchmark": {"status": "MEASURED", "version": "hb-1"},
            "capsule_cohort": "baseline_appropriate",
            "evidence_catalog": [
                {"ref": "prompt:p:T1", "layer": "PROMPT", "occurrence_id": "p:T1"},
                {"ref": "prompt:p:T2", "layer": "PROMPT", "occurrence_id": "p:T2"},
            ],
            "claims": [
                {
                    "claim_id": "c1",
                    "kind": "ACTION",
                    "relations": [
                        {"relation": "PARTIAL", "evidence_ref": "prompt:p:T1"}
                    ],
                    "unsupported_category": None,
                }
            ],
            "policies": [
                {"applicability": "APPLICABLE", "compliance": "PARTIAL"},
                {"applicability": "NOT_APPLICABLE", "compliance": "NOT_APPLICABLE"},
                {"applicability": "UNCERTAIN", "compliance": "UNCERTAIN"},
            ],
        },
        {
            "status": "UNAVAILABLE",
            "reason": "provider failed",
            "capsule_cohort": "injection_failed",
        },
    ]

    summary = summarize_semantic_attribution(turns)

    assert summary["exposed_unit_utilization"] == {
        "used_occurrences": 1,
        "evaluated_occurrences": 2,
        "rate": 0.5,
        "by_layer": {
            "PROMPT": {"used_occurrences": 1, "evaluated_occurrences": 2, "rate": 0.5}
        },
    }
    assert summary["policy_obligation_coverage"]["denominator"] == 1
    assert summary["policy_obligation_coverage"]["weighted_covered"] == 0.5
    assert summary["policy_obligation_coverage"]["uncertain_applicability"] == 1
    assert summary["availability"]["unavailable_turns"] == 1
    assert summary["no_capsule_cohorts"] == {
        "baseline_appropriate": 1,
        "capsule_missed": 0,
        "crisis_short_circuited": 0,
        "injection_failed": 1,
    }
