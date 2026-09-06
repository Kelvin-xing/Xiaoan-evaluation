from xiaoan_eval.recommendations import (
    RecommendationEvidence,
    recommend,
    recommend_case,
    recommendations_markdown,
    enrich_recommendation,
)
from xiaoan_eval.config import load_evaluator_config


THRESHOLDS = load_evaluator_config("evaluator-config.yml").experiment


def test_failure_without_variant_evidence_is_hypothesis_and_suggests_experiment():
    recommendation = recommend(
        recommendation_id="REC-001",
        lever_type="prompt",
        target="router.prompt",
        affected_cases=["TC-01"],
        affected_cohorts=["risk:critical"],
        trace_evidence_refs=["TC-01:T1:route"],
        rationale="safety passed but route failed",
    )

    assert recommendation.status == "hypothesis"
    assert recommendation.action_label == "建议实验"


def test_repeatable_threshold_passing_variant_is_validated_and_suggests_change():
    evidence = RecommendationEvidence(
        repeats=3,
        target_pass_rate_deltas=(0.12, 0.11, 0.13),
        weighted_total_deltas=(0.16, 0.18, 0.17),
        max_non_target_regression=0.04,
        critical_hard_gate_regressions=0,
    )
    recommendation = recommend(
        recommendation_id="REC-002",
        lever_type="hyperparameter",
        target="router.context_turns",
        affected_cases=["TC-01", "TC-03"],
        affected_cohorts=["risk:critical"],
        trace_evidence_refs=["run-2:TC-01:T1"],
        rationale="repeatable route improvement",
        variant={"candidate": 8, "controls": ["model_hash", "prompt_hash"]},
        evidence=evidence,
        thresholds=THRESHOLDS,
    )

    assert recommendation.status == "validated"
    assert recommendation.action_label == "建议修改"


def test_variant_that_fails_threshold_is_rejected():
    evidence = RecommendationEvidence(
        repeats=3,
        target_pass_rate_deltas=(0.12, 0.08, 0.13),
        weighted_total_deltas=(0.16, 0.18, 0.17),
        max_non_target_regression=0.04,
        critical_hard_gate_regressions=0,
    )

    result = recommend(
        recommendation_id="REC-003",
        lever_type="prompt",
        target="composer.prompt",
        affected_cases=["TC-01"],
        affected_cohorts=[],
        trace_evidence_refs=["run-3:TC-01:T1"],
        rationale="inconsistent result",
        variant={"patch": "minimal"},
        evidence=evidence,
        thresholds=THRESHOLDS,
    )

    assert result.status == "rejected"
    assert result.action_label == "不建议修改"


def test_case_quality_evidence_produces_actionable_crisis_sop_experiment() -> None:
    record = {
        "case_id": "TC-01",
        "status": "NEEDS_REVIEW",
        "quality": {
            "weighted_total": 0.65,
            "dimensions": {"行动赋权": 0.76, "法律维权": 0.20},
        },
        "review": {
            "judge_audit": [{
                "primary": {"dimensions": [{
                    "module": "行动赋权",
                    "score": 0.76,
                    "deduction_evidence": [
                        "用户已说明门反锁、窗户封死，回答仍主要询问能否离开。",
                        "未具体处理孩子在隔壁房间这一风险。",
                    ],
                }]},
                "secondary": None,
                "reconciliation_reasons": ["second judge required but unavailable"],
            }],
        },
        "pipeline": {"turn_traces": [{
            "turn": 4,
            "trace": {"route": {"id": "crisis_sop"}},
        }]},
        "failure": {"primary_stage": "performance"},
        "evidence_refs": ["TC-01:T4:timings", "TC-01:T4:tokens"],
    }

    recommendation = recommend_case(record)

    assert recommendation.lever_type == "prompt"
    assert recommendation.target == "knowledge/sops/crisis-sop.md"
    assert recommendation.variant["proposed_changes"][0]["instruction"]
    assert "孩子" in recommendation.rationale
    assert recommendation.variant["experiment"]["repeats"] == 3
    assert recommendation.variant["rubric_note"]["法律维权"]

    report = recommendations_markdown([recommendation])
    assert "# 評估改善建議" in report
    assert "### 建議理由" in report
    assert "Evaluation Recommendations" not in report
    assert "knowledge/sops/crisis-sop.md" in report
    assert "每轮先承接最新现场限制" in report
    assert "weighted_total_delta" in report


def test_llm_enrichment_cannot_override_validation_or_evidence() -> None:
    original = recommend(
        recommendation_id="REC-004",
        lever_type="knowledge",
        target="ground",
        affected_cases=["TC-45"],
        affected_cohorts=[],
        trace_evidence_refs=["TC-45:T1:authoritative_context"],
        rationale="ground overflow",
    )
    enriched = enrich_recommendation(original, {
        "problem_statement": "TC-45 T1 展开了 42 个 ground refs。",
        "root_cause_hypothesis": "n2a 的 ground nodes 范围过宽。",
        "target_files": ["tech/chatflow/poc/capsules.json"],
        "proposed_changes": [{"location": "n2a.ground.nodes", "instruction": "收窄到取证相关节点。"}],
        "success_criteria": ["resolved refs <= 12"],
        "experiment_proposal": {
            "experiment_type": "capsule_ground_nodes",
            "target": {"file": "tech/chatflow/poc/capsules.json", "entity_id": "n2a", "field": "ground.nodes"},
            "operation": "replace", "before": ["a", "b"], "after": ["b"],
        },
        "status": "validated",
        "trace_evidence_refs": [],
    })
    assert enriched.status == "hypothesis"
    assert enriched.trace_evidence_refs == ("TC-45:T1:authoritative_context",)
    assert enriched.target_files == ("tech/chatflow/poc/capsules.json",)
    assert enriched.variant["proposed_changes"][0]["location"] == "n2a.ground.nodes"
    assert enriched.variant["proposal"]["operation"] == "replace"
