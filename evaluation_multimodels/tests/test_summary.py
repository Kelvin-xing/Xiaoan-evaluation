from xiaoan_eval.summary import build_summary, render_summary


def test_summary_explains_stage_evidence_interpretation_and_next_step() -> None:
    record = {
        "case_id": "TC-01",
        "status": "FAIL",
        "pipeline": {"turns": [{
            "ground_recall": {"status": "fail", "score": 0.5,
                               "counts": {"tp": 1, "fp": 1, "fn": 1}},
        }]},
        "failure": {"primary_stage": "ground", "secondary_stages": []},
        "evidence_refs": ["TC-01:T1:ground_recall"],
    }

    summary = build_summary([record], {"retrieval": {"recall": 0.5}}, [])
    markdown = render_summary(summary)

    assert summary["overview"]["failed_cases"] == 1
    assert summary["issues"][0]["stage"] == "ground"
    assert summary["issues"][0]["evidence"] == ["TC-01:T1:ground_recall"]
    assert "Evidence" in markdown
    assert "Interpretation" in markdown
    assert "hypothesis" in markdown
    assert "retrieval" in markdown.lower()
    assert "Metric snapshot" in markdown


def test_summary_is_clear_when_no_product_issue_exists() -> None:
    summary = build_summary([{"case_id": "TC-01", "status": "PASS"}], {}, [])

    assert summary["issues"] == []
    assert "No product issue" in render_summary(summary)
