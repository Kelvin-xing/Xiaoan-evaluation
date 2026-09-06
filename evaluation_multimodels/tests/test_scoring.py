from xiaoan_eval.scoring import TurnDimensionFact, score_case_fact, score_scenario


def test_case_score_averages_turns_before_applying_focus_weights():
    facts = [
        TurnDimensionFact("TC-01", 1, "a", "AVAILABLE", 3),
        TurnDimensionFact("TC-01", 2, "a", "AVAILABLE", 1),
        TurnDimensionFact("TC-01", 1, "b", "AVAILABLE", 2),
        TurnDimensionFact("TC-01", 2, "b", "AVAILABLE", 2),
    ]

    score = score_case_fact(
        case_id="TC-01",
        expected_turns=(1, 2),
        quality_focus=("a", "b"),
        dimension_weights={"a": 3, "b": 1},
        turn_facts=facts,
    )

    assert score.status == "AVAILABLE"
    assert score.dimension_means == {"a": 2, "b": 2}
    assert score.value == 2


def test_missing_turn_is_unavailable_not_zero():
    score = score_case_fact(
        case_id="TC-01",
        expected_turns=(1, 2),
        quality_focus=("a",),
        dimension_weights={"a": 1},
        turn_facts=[TurnDimensionFact("TC-01", 1, "a", "AVAILABLE", 0)],
    )

    assert score.status == "UNAVAILABLE"
    assert score.value is None
    assert score.exclusions == ("a:TURN_2_UNAVAILABLE",)


def test_scenario_only_aggregates_approved_comparable_available_cases():
    one = score_case_fact(
        case_id="TC-01", expected_turns=(1,), quality_focus=("a",),
        dimension_weights={"a": 1},
        turn_facts=[TurnDimensionFact("TC-01", 1, "a", "AVAILABLE", 3)],
    )
    two = score_case_fact(
        case_id="TC-02", expected_turns=(1,), quality_focus=("a",),
        dimension_weights={"a": 1},
        turn_facts=[TurnDimensionFact("TC-02", 1, "a", "AVAILABLE", 1)],
    )
    score = score_scenario(
        scenario_id="crisis",
        comparability_group="v1",
        cases=[
            {"case_id": "TC-01", "scenario_id": "crisis", "comparability_group": "v1", "maturity": "APPROVED_AGGREGATE"},
            {"case_id": "TC-02", "scenario_id": "crisis", "comparability_group": "v1", "maturity": "REVIEWED"},
        ],
        case_scores={"TC-01": one, "TC-02": two},
    )

    assert score.value == 3
    assert score.eligible_cases == 1
    assert score.exclusions == {"TC-02": "MATURITY_INELIGIBLE"}
