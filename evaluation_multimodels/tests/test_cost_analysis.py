import json
import pytest

from xiaoan_eval.cost_analysis import UNAVAILABLE, build_cost_analysis, render_cost_analysis


CATALOG = {
    "catalog_version": "test-1",
    "rates": [
        {"provider": "subject-p", "model": "s1", "billing_route": "direct", "currency": "USD", "input_per_million": 1, "output_per_million": 2, "cached_input_per_million": .1, "cache_write_per_million": 1.25},
        {"provider": "judge-p", "model": "j1", "billing_route": "direct", "currency": "HKD", "input_per_million": 3, "output_per_million": 4},
    ],
}


def row(answer_id="a1", judge_id="j1", score=4):
    return {
        "answer_id": answer_id,
        "subject": {"provider": "subject-p", "model": "s1", "billing_route": "direct"},
        "judge": {"provider": "judge-p", "model": "j1", "billing_route": "direct", "id": judge_id},
        "answer": {"provider": "subject-p", "model": "s1", "billing_route": "direct", "status": "PASS", "input_tokens": 100, "output_tokens": 50, "cached_input_tokens": 1000},
        "judgement": {"provider": "judge-p", "model": "j1", "billing_route": "direct", "status": "PASS", "input_tokens": 200, "output_tokens": 25},
        "weighted_score": score,
    }


def test_subject_is_deduplicated_across_judges_and_currency_is_separate():
    result = build_cost_analysis([row(), row(judge_id="j2", score=2)], CATALOG)
    assert result["subject_unique_count"] == 1
    assert result["matrix_row_count"] == 2
    assert result["totals_by_currency"]["USD"]["cost"] == pytest.approx(.0003)
    assert result["totals_by_currency"]["HKD"]["cost"] == pytest.approx(.0014)
    assert result["quality_by_pair"]["subject-p:s1:judge-p:j1"]["quality_observations"] == 2


def test_unknown_route_model_and_usage_are_unavailable_without_fabrication():
    unknown = row()
    unknown["answer"] = {**unknown["answer"], "billing_route": "globalai"}
    unknown["answer"]["attempt_count"] = 2
    unknown["answer"]["attempts"] = []
    unknown["judgement"] = {**unknown["judgement"], "input_tokens": None}
    result = build_cost_analysis([unknown], CATALOG)
    subject, judge = result["lines"]
    assert subject["status"] == UNAVAILABLE
    assert judge["status"] == UNAVAILABLE
    assert subject["cost"] is None and judge["cost"] is None


def test_markdown_is_renderable_and_catalog_path_is_supported(tmp_path):
    path = tmp_path / "pricing.json"
    path.write_text(json.dumps(CATALOG), encoding="utf-8")
    markdown = render_cost_analysis(build_cost_analysis([row()], path))
    assert "## Cost by currency" in markdown
    assert "## Quality by subject/Judge pair" in markdown
