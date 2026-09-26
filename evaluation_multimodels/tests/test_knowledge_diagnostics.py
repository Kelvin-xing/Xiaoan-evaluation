from xiaoan_eval.knowledge_diagnostics import (
    build_knowledge_diagnostics, detail_rows, render_knowledge_diagnostics,
)


def binding(answer="a", context="c"):
    return {"answer_sha256": answer, "context_sha256": context}


def analysis():
    identity = {"case_id": "TC-17", "turn": 1, "subject_id": "s1", "judge_id": "j1",
                "binding": binding()}
    claims = [
        {**identity, "claim_id": "c1", "kind": "FACTUAL", "answer_span": {"text": "full"},
         "relations": [{"relation": "ENTAILS", "layer": "CAPSULE", "evidence_ref": "cap-1"}]},
        {**identity, "claim_id": "c2", "kind": "FACTUAL", "answer_span": {"text": "partial"},
         "relations": [{"relation": "PARTIAL", "layer": "CAPSULE", "evidence_ref": "cap-1"},
                       {"relation": "ENTAILS", "layer": "SOURCE", "evidence_ref": "src-1"}]},
        {**identity, "claim_id": "c3", "kind": "FACTUAL", "answer_span": {"text": "other"},
         "relations": [{"relation": "ENTAILS", "layer": "WIKI", "evidence_ref": "wiki-1"}]},
        {**identity, "claim_id": "c4", "kind": "FACTUAL", "answer_span": {"text": "unknown"},
         "relations": [{"relation": "UNSUPPORTED", "layer": None}]},
    ]
    return {"schema_version": "scenario-analysis/v1", "turns": [
        {**identity, "answer_status": "AVAILABLE"}], "claims": claims}


def test_claim_support_is_explicit_and_does_not_call_other_evidence_capsule():
    result = build_knowledge_diagnostics(analysis())
    assert result["summary"]["capsule_supported_claim_share"] == .5
    by_id = {row["claim_id"]: row for row in result["claims"]}
    assert by_id["c1"]["capsule_support"] == "FULL"
    assert by_id["c2"]["capsule_support"] == "PARTIAL"
    assert by_id["c3"]["attribution"] == "SUPPORTED_BY_OTHER_OR_PROVIDED_EVIDENCE"
    assert by_id["c4"]["attribution"] == "UNSUPPORTED_WITHOUT_CAPSULE_EVIDENCE"


def test_reviewed_requirements_distinguish_adoption_and_verified_gap():
    identity = analysis()["turns"][0]
    reviews = {"schema_version": "knowledge-review/v1", "reviews": [{
        **identity, "need_to_capsule": [
            {"requirement_id": "r1", "text": "required safety step", "status": "REQUIRED",
             "review_status": "REVIEWED", "capsule_id": "N9", "adoption_status": "OMITTED",
             "adoption_evidence": ["oracle:R1"]},
            {"requirement_id": "r2", "text": "optional detail", "status": "OPTIONAL",
             "review_status": "REVIEWED", "capsule_id": "N9", "adoption_status": "ADOPTED"},
        ]}]}
    result = build_knowledge_diagnostics(analysis(), reviews)
    assert result["summary"]["verified_capsule_gap_count"] == 1
    assert result["requirements"][0]["adoption"] == "OMITTED"
    assert result["gaps"][0]["gap"] == "VERIFIED_CAPSULE_GAP"


def test_wrong_binding_is_unknown_and_rows_are_json_compatible():
    review = {"schema_version": "knowledge-review/v1", "reviews": [{
        "case_id": "TC-17", "turn": 1, "subject_id": "s1", "binding": binding("changed", "c"),
        "need_to_capsule": [{"requirement_id": "r", "text": "x", "status": "REQUIRED",
                              "review_status": "REVIEWED", "capsule_id": "N1"}],
    }]}
    result = build_knowledge_diagnostics(analysis(), review)
    assert result["requirements"] == []
    assert result["summary"]["unknown_corpus_coverage"] is True
    assert detail_rows(result)
    assert "UNKNOWN" in render_knowledge_diagnostics(result)
