from pathlib import Path

import pytest

from xiaoan_eval.config import ConfigError, load_evaluator_config


def test_load_evaluator_config_exposes_review_experiment_and_registry() -> None:
    config = load_evaluator_config(Path("evaluator-config.yml"))

    assert config.experiment.repeats == 3
    assert config.review.uncertainty_levels == ("medium", "high")
    assert config.parameters["router.context_turns"].candidates == (4, 6, 8)
    assert config.parameters["model.reasoning_effort"].candidates == ("low", "medium", "high")
    assert config.parameters["model.reasoning_effort"].minimum is None


def test_load_evaluator_config_fails_closed_on_missing_required_section(tmp_path) -> None:
    path = tmp_path / "config.yml"
    path.write_text('schema_version: "1.0"\nreview: {}\n', encoding="utf-8")

    with pytest.raises(ConfigError, match="experiment"):
        load_evaluator_config(path)


def test_load_evaluator_config_rejects_candidate_outside_range(tmp_path) -> None:
    path = tmp_path / "config.yml"
    path.write_text(
        """\
schema_version: "1.0"
experiment:
  repeats: 1
  seeds: [1]
  min_target_cohort_pass_rate_delta: 0.1
  min_weighted_total_delta: 0.1
  max_non_target_weighted_regression: 0.1
  critical_hard_gate_regression_tolerance: 0
review:
  uncertainty_levels: [high]
  quality_threshold_margin: 0.1
  judge_score_disagreement: 0.5
parameters:
  p:
    current: 1
    min: 0
    max: 2
    candidates: [3]
""",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="within min/max"):
        load_evaluator_config(path)
