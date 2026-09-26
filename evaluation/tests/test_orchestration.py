import json
from pathlib import Path

from test_unified_evaluation import provider, spec
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval_core.orchestration import run_orchestration
from xiaoan_eval_core.relevancy import build_request


RULE = load_rating_rule(Path(__file__).parents[1] / "ratings rule.yml")


def rubric_payload():
    return {
        "dimensions": [{"module": m.name, "score": 2, "reason": "fixture score",
                        "supporting_evidence": ["A."], "deduction_evidence": [],
                        "uncertainty": "low"} for m in RULE.modules],
        "red_lines": [{"id": r.id, "triggered": False, "reason": "fixture no redline", "evidence": [],
                       "uncertainty": "low"} for r in RULE.red_lines],
    }


def test_orchestration_runs_three_branches_and_builds_canonical_results():
    s = spec()
    calls = []

    def faith(request):
        calls.append(request["task"])
        return provider(request)

    def rubric(request):
        calls.append(request["task"])
        return rubric_payload()

    def generate(payload):
        calls.append("generate_questions")
        task = build_request("a1", "Can you help?", "A. B. C.")
        return {"binding": task["binding"], "questions": ["original", "original", "original"]}

    def embed(texts, task):
        calls.append("embed")
        return {"model_id": "fixture", "revision": "v1",
                "vectors": {text: [1.0, 0.0] for text in texts}}

    result = run_orchestration(s, faithfulness_provider=faith,
                               rubric_provider=rubric,
                               generation_provider=generate,
                               embedding_provider=embed,
                               rating_rule=RULE)
    assert result['schema_version'] == 'xiaoan-results/v2'
    envelope = result['envelopes'][0]
    assert len(envelope['rubric']) == 2
    assert all(item['status'] == 'AVAILABLE' for item in envelope['rubric'])
    assert len(envelope['assessments']) == 2
    assert envelope['relevancy']['status'] == 'AVAILABLE'
    assert calls.count('rubric') == 2
    assert calls.count('generate_questions') == 1
    assert calls.count('embed') == 1


def test_orchestration_keeps_unconfigured_branches_unavailable():
    result = run_orchestration(spec(), faithfulness_provider=provider)
    envelope = result['envelopes'][0]
    assert len(envelope['rubric']) == 2
    assert all(item['status'] == 'UNAVAILABLE' for item in envelope['rubric'])
    assert envelope['relevancy']['status'] == 'UNAVAILABLE'


def test_branch_plan_disables_semantic_requirements_without_losing_rows():
    source=spec();source['branches']=['rubric']
    result=run_orchestration(source,rubric_provider=lambda request:rubric_payload())
    envelope=result['envelopes'][0]
    assert not result['inventories']
    assert all(c['execution_status']=='NOT_PLANNED' for c in envelope['assessments'])
    assert all(c['status']=='AVAILABLE' for c in envelope['rubric'])
