import pytest

from xiaoan_eval.experiments import (
    ExperimentValidationError,
    VariableSpec,
    enforce_single_variable,
)


REGISTRY = {
    "router.context_turns": VariableSpec(
        path="router.context_turns", minimum=1, maximum=10, candidates=(4, 6, 8)
    ),
    "composer.temperature": VariableSpec(
        path="composer.temperature",
        minimum=0.0,
        maximum=1.0,
        candidates=(0.0, 0.3, 0.6),
    ),
}


def test_enforce_single_variable_accepts_one_registered_candidate_change() -> None:
    change = enforce_single_variable(
        baseline={"router.context_turns": 6, "composer.temperature": 0.3},
        variant={"router.context_turns": 8, "composer.temperature": 0.3},
        registry=REGISTRY,
    )

    assert change.path == "router.context_turns"
    assert change.baseline_value == 6
    assert change.variant_value == 8


@pytest.mark.parametrize(
    ("variant", "message"),
    [
        (
            {"router.context_turns": 8, "composer.temperature": 0.6},
            "exactly one registered variable",
        ),
        (
            {"router.context_turns": 6, "composer.temperature": 0.3},
            "exactly one registered variable",
        ),
        (
            {
                "router.context_turns": 6,
                "composer.temperature": 0.3,
                "router.prompt_hash": "changed",
            },
            "unregistered variable",
        ),
        (
            {"router.context_turns": 7, "composer.temperature": 0.3},
            "explicit candidate",
        ),
    ],
)
def test_enforce_single_variable_rejects_uncontrolled_or_unregistered_variants(
    variant: dict, message: str
) -> None:
    with pytest.raises(ExperimentValidationError, match=message):
        enforce_single_variable(
            baseline={"router.context_turns": 6, "composer.temperature": 0.3},
            variant=variant,
            registry=REGISTRY,
        )


def test_variable_spec_rejects_candidates_outside_registered_range() -> None:
    with pytest.raises(ExperimentValidationError, match="within the registered range"):
        VariableSpec(
            path="composer.temperature",
            minimum=0.0,
            maximum=1.0,
            candidates=(0.3, 1.2),
        )
