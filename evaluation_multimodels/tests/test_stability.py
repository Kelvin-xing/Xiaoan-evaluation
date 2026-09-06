import pytest

from xiaoan_eval.stability import summarize_stability


def _record(route: str, refs: list[str], response_hash: str) -> dict:
    return {
        "case_id": "TC-01",
        "pipeline": {
            "turn_traces": [
                {
                    "turn": 1,
                    "response_sha256": response_hash,
                    "trace": {
                        "route": {"id": route},
                        "ground": {"resolved_ground": refs},
                    },
                }
            ]
        },
    }


def test_stability_compares_router_ground_and_response_across_repeated_runs() -> None:
    summary = summarize_stability(
        [
            [_record("n3", ["a", "b"], "same")],
            [_record("n3", ["a", "b"], "same")],
            [_record("n4", ["a", "c"], "different")],
        ]
    )

    turn = summary["turns"][0]
    assert summary["run_count"] == 3
    assert turn["capsule_modal_agreement"] == pytest.approx(2 / 3)
    assert turn["ground_pairwise_jaccard"] == pytest.approx(5 / 9)
    assert turn["response_exact_modal_agreement"] == pytest.approx(2 / 3)
    assert summary["global"]["capsule_modal_agreement"] == pytest.approx(2 / 3)
    assert summary["classification"] == "DESCRIPTIVE_ONLY"
    assert summary["global"]["pass_fail_flip_turns"] == 0
    assert summary["global"]["score_variance"] is None
    assert summary["limitation"].startswith("Repeatability is not correctness")


def test_stability_rejects_non_comparable_run_case_sets() -> None:
    with pytest.raises(ValueError, match="same case and turn set"):
        summarize_stability(
            [
                [_record("n3", ["a"], "one")],
                [{**_record("n3", ["a"], "one"), "case_id": "TC-02"}],
            ]
        )
