import hashlib

import pytest

from xiaoan_eval.calibration import (
    BenchmarkValidationError,
    build_agreement_report,
    build_blinded_review_packet,
    build_sampling_manifest,
    classify_measurement_change,
    freeze_benchmark,
    match_spans,
    record_judge_run,
    validate_annotation,
    validate_reviewer_set,
)


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def _population() -> list[dict]:
    strata = [
        ["baseline", "single_turn"],
        ["crisis", "high_risk"],
        ["ordinary_capsule", "single_turn"],
        ["wiki_source", "multi_turn"],
    ]
    rows = []
    for index in range(8):
        answer = f"answer-{index}"
        context = f"context-{index}"
        rows.append(
            {
                "item_id": f"item-{index:02d}",
                "case_id": f"TC-{index // 2 + 1:02d}",
                "turn": index % 2 + 1,
                "output_id": f"output-{index:02d}",
                "strata": strata[index % len(strata)],
                "answer": answer,
                "answer_sha256": _sha(answer),
                "context_sha256": _sha(context),
                "target_input_sha256": _sha(f"target-{index}"),
            }
        )
    return rows


def test_sampling_manifest_is_reproducible_and_audits_overlap_coverage() -> None:
    kwargs = {
        "benchmark_version": "hb-1",
        "selector_version": "selector/v1",
        "seed": 17,
        "stratum_targets": {"baseline": 2, "crisis": 2, "single_turn": 2},
        "minimum_cases": 2,
        "minimum_outputs": 4,
    }

    first = build_sampling_manifest(_population(), **kwargs)
    second = build_sampling_manifest(list(reversed(_population())), **kwargs)

    assert first == second
    assert first["overlap_policy"] == "multi_label_each_selected_item_counts_once_per_stratum"
    assert all(item["observed_strata"] for item in first["items"])
    assert first["coverage"]["baseline"]["achieved"] >= 2
    assert first["coverage"]["crisis"]["achieved"] >= 2


def test_sampling_manifest_refuses_unexplained_coverage_deficit() -> None:
    with pytest.raises(BenchmarkValidationError, match="coverage deficit"):
        build_sampling_manifest(
            _population(),
            benchmark_version="hb-1",
            selector_version="selector/v1",
            seed=17,
            stratum_targets={"missing-stratum": 1},
            minimum_cases=1,
            minimum_outputs=1,
        )


def test_span_matching_is_exact_first_overlap_one_to_one_and_deterministic() -> None:
    human = [
        {"claim_id": "h2", "start": 10, "end": 20},
        {"claim_id": "h1", "start": 0, "end": 10},
    ]
    judge = [
        {"claim_id": "j2", "start": 1, "end": 10},
        {"claim_id": "j1", "start": 10, "end": 20},
        {"claim_id": "j3", "start": 0, "end": 9},
    ]

    report = match_spans(human, judge)

    assert report["matches"] == [
        {"human_id": "h1", "judge_id": "j2", "match": "OVERLAP", "iou": 0.9},
        {"human_id": "h2", "judge_id": "j1", "match": "EXACT", "iou": 1.0},
    ]
    assert report["unmatched_judge"] == ["j3"]


def _attribution_annotation(reviewer_id: str, role: str = "REVIEWER") -> dict:
    answer = "Call for help."
    evidence = "Call emergency services for urgent help."
    return {
        "schema_version": "human-benchmark-annotation/v1",
        "benchmark_version": "hb-1",
        "target": "ATTRIBUTION",
        "item_id": "item-01",
        "reviewer_id": reviewer_id,
        "role": role,
        "answer_sha256": _sha(answer),
        "context_sha256": _sha("context"),
        "target_input_sha256": _sha("target"),
        "rubric_version": "attribution-rubric/v1",
        "submitted_at": "2026-09-01T12:00:00+08:00",
        "abstention": False,
        "uncertainty": "LOW",
        "labels": {
            "claims": [
                {
                    "claim_id": "c1",
                    "kind": "ACTION",
                    "answer_span": {"start": 0, "end": len(answer), "text": answer},
                    "relations": [
                        {
                            "relation": "ENTAILS",
                            "evidence_ref": "source:s1:T1",
                            "evidence_span": {
                                "start": 0,
                                "end": len(evidence),
                                "text": evidence,
                            },
                        }
                    ],
                    "unsupported_category": None,
                }
            ],
            "policies": [
                {
                    "policy_id": "policy:urgent-help",
                    "evidence_ref": "source:s1:T1",
                    "applicability": "APPLICABLE",
                    "compliance": "COMPLIANT",
                    "answer_spans": [
                        {"start": 0, "end": len(answer), "text": answer}
                    ],
                }
            ],
        },
    }


def test_annotation_binds_spans_and_reviewer_set_requires_independent_adjudicator() -> None:
    item = {
        "item_id": "item-01",
        "answer": "Call for help.",
        "answer_sha256": _sha("Call for help."),
        "context_sha256": _sha("context"),
        "target_input_sha256": _sha("target"),
        "evidence_catalog": {
            "source:s1:T1": {
                "content": "Call emergency services for urgent help.",
                "policy_ids": ["policy:urgent-help"],
            }
        },
    }
    first = validate_annotation(_attribution_annotation("fixture-reviewer-a"), item)
    second = validate_annotation(_attribution_annotation("fixture-reviewer-b"), item)
    adjudicator = _attribution_annotation("fixture-adjudicator", role="ADJUDICATOR")
    adjudicator["source_submission_ids"] = [first["submission_id"], second["submission_id"]]
    adjudicator["adjudication_reasons"] = ["fixture resolution"]
    adjudicated = validate_annotation(adjudicator, item)

    result = validate_reviewer_set([first, second], adjudicated)

    assert result["status"] == "ADJUDICATED"
    assert result["reviewer_ids"] == ["fixture-reviewer-a", "fixture-reviewer-b"]

    adjudicated["reviewer_id"] = "tampered"
    with pytest.raises(BenchmarkValidationError, match="submission_id"):
        validate_reviewer_set([first, second], adjudicated)

    same_reviewer = _attribution_annotation(
        "fixture-reviewer-a", role="ADJUDICATOR"
    )
    same_reviewer["source_submission_ids"] = [
        first["submission_id"],
        second["submission_id"],
    ]
    same_reviewer["adjudication_reasons"] = ["fixture resolution"]
    same_reviewer = validate_annotation(same_reviewer, item)
    with pytest.raises(BenchmarkValidationError, match="distinct adjudicator"):
        validate_reviewer_set([first, second], same_reviewer)


def test_freeze_is_descriptive_and_change_matrix_has_distinct_paths() -> None:
    manifest = build_sampling_manifest(
        _population(),
        benchmark_version="hb-1",
        selector_version="selector/v1",
        seed=17,
        stratum_targets={"baseline": 1, "crisis": 1},
        minimum_cases=2,
        minimum_outputs=2,
    )
    frozen = freeze_benchmark(manifest, target="ATTRIBUTION")

    assert frozen.status == "FROZEN_NOT_ADJUDICATED"
    assert frozen.descriptive_only is True
    assert not hasattr(frozen, "release_eligible")
    assert classify_measurement_change("JUDGE_ONLY")["action"] == "RERUN_FROZEN_BENCHMARK"
    assert classify_measurement_change("SCHEMA_REPRESENTATION", lossless=True)["version_action"] == "KEEP_VERSION"
    assert classify_measurement_change("RUBRIC_SEMANTICS")["action"] == "RELABEL"
    assert classify_measurement_change("PROMPT_CONTEXT")["action"] == "REGENERATE_AND_RELABEL"


def test_quality_target_packet_agreement_and_judge_run_remain_descriptive() -> None:
    population = _population()
    target_input = {"rating_rule": "quality/v1"}
    for population_item in population:
        population_item["target_input_sha256"] = _sha(
            '{"rating_rule":"quality/v1"}'
        )
    manifest = build_sampling_manifest(
        population,
        benchmark_version="hb-quality-1",
        selector_version="selector/v1",
        seed=4,
        stratum_targets={"baseline": 1},
        minimum_cases=1,
        minimum_outputs=1,
    )
    selected = manifest["items"][0]
    original = next(item for item in population if item["item_id"] == selected["item_id"])
    packet = build_blinded_review_packet(
        manifest,
        original,
        target="QUALITY_RED_LINE",
        rubric_version="quality/v1",
        target_input=target_input,
    )

    assert packet["blinded"] is True
    assert "judge" not in packet
    assert "candidate" not in packet

    human = {
        "target": "QUALITY_RED_LINE",
        "labels": {
            "dimensions": [{"module": "safety", "score": 2}],
            "red_lines": [{"id": "RL-01", "triggered": False}],
        },
    }
    judge = {
        "target": "QUALITY_RED_LINE",
        "labels": {
            "dimensions": [{"module": "safety", "score": 1}],
            "red_lines": [{"id": "RL-01", "triggered": False}],
        },
    }
    report = build_agreement_report(
        human,
        judge,
        benchmark_version="hb-quality-1",
        judge_version="quality-judge-v2",
    )
    frozen = freeze_benchmark(
        manifest, target="QUALITY_RED_LINE", adjudicated=True
    )
    run = record_judge_run(
        frozen,
        judge_version="quality-judge-v2",
        judge_control_digest=_sha("quality-judge-control"),
        agreement_report=report,
    )

    assert report["ordinal_exact_agreement"] == 0
    assert report["red_line_agreement"]["accuracy"] == 1
    assert run["descriptive_only"] is True
    assert not any(key in run for key in ("release_eligible", "oracle_approved", "candidate_adopted"))


def test_attribution_agreement_compares_every_relation_policy_and_evidence_span() -> None:
    human = {
        "target": "ATTRIBUTION",
        "labels": {
            "claims": [
                {
                    "claim_id": "h1",
                    "answer_span": {"start": 0, "end": 10, "text": "0123456789"},
                    "relations": [
                        {
                            "relation": "ENTAILS",
                            "evidence_ref": "source:s1:T1",
                            "evidence_span": {"start": 0, "end": 10, "text": "abcdefghij"},
                        },
                        {
                            "relation": "PARTIAL",
                            "evidence_ref": "wiki:w1:T1",
                            "evidence_span": {"start": 2, "end": 8, "text": "cdefgh"},
                        },
                    ],
                }
            ],
            "policies": [
                {
                    "policy_id": "policy:p1",
                    "evidence_ref": "source:s1:T1",
                    "applicability": "APPLICABLE",
                    "compliance": "COMPLIANT",
                }
            ],
        },
    }
    judge = {
        "target": "ATTRIBUTION",
        "labels": {
            "claims": [
                {
                    "claim_id": "j1",
                    "answer_span": {"start": 0, "end": 10, "text": "0123456789"},
                    "relations": [
                        {
                            "relation": "PARTIAL",
                            "evidence_ref": "source:s1:T1",
                            "evidence_span": {"start": 1, "end": 10, "text": "bcdefghij"},
                        },
                        {
                            "relation": "PARTIAL",
                            "evidence_ref": "wiki:w1:T1",
                            "evidence_span": {"start": 2, "end": 8, "text": "cdefgh"},
                        },
                    ],
                }
            ],
            "policies": [
                {
                    "policy_id": "policy:p1",
                    "evidence_ref": "source:s1:T1",
                    "applicability": "APPLICABLE",
                    "compliance": "PARTIAL",
                }
            ],
        },
    }

    report = build_agreement_report(
        human,
        judge,
        benchmark_version="hb-1",
        judge_version="attribution-judge-v1",
    )

    assert report["relation_agreement"]["evaluated"] == 2
    assert report["relation_agreement"]["accuracy"] == 0.5
    assert report["evidence_span_matching"]["exact_matches"] == 1
    assert report["evidence_span_matching"]["overlap_matches"] == 1
    assert report["policy_applicability_agreement"]["accuracy"] == 1
    assert report["policy_compliance_agreement"]["accuracy"] == 0
