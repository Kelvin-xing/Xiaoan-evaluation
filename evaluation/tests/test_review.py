from dataclasses import replace
from xiaoan_eval.judge import DimensionJudgement, JudgeResult, RedLineJudgement
from xiaoan_eval.review import ReviewStatus, reconcile_judges, should_request_second_judge


def result(score=2.0, uncertainty="low", triggered=False):
    return JudgeResult(
        (RedLineJudgement("RL", triggered, (), uncertainty),),
        (DimensionJudgement("quality", score, (), (), uncertainty),),
    )


CONFIG = {"uncertainty_levels": ["medium", "high"], "quality_threshold_margin": .15, "judge_score_disagreement": .5}


def test_second_judge_risk_triggers_are_config_driven() -> None:
    assert should_request_second_judge(result(uncertainty="medium"), CONFIG)
    assert should_request_second_judge(result(1.9), CONFIG, critical=True, quality_threshold=2.0)
    assert should_request_second_judge(result(), CONFIG, contradiction=True)
    assert not should_request_second_judge(result(), CONFIG)


def test_structured_contradiction_triggers_review_automatically() -> None:
    primary = JudgeResult(
        (RedLineJudgement("RL", True, (), "low"),), result().dimensions
    )
    assert should_request_second_judge(primary, {"review": CONFIG})


def test_safety_or_score_disagreement_needs_human_review() -> None:
    assert reconcile_judges(result(), result(triggered=True), CONFIG).status is ReviewStatus.NEEDS_REVIEW
    assert reconcile_judges(result(2), result(2.6), CONFIG).status is ReviewStatus.NEEDS_REVIEW
    assert reconcile_judges(result(2), result(2.4), CONFIG).status is ReviewStatus.AGREED
