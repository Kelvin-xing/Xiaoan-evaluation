"""Complete-result evidence exposure and independent report recovery."""
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation" / "tests"))
from test_frozen_outputs import fixture_result
from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results
from evaluation_report_agent.evidence import EvidenceStore
from evaluation_report_agent.agent import ReportAgent, validate_report


def report(store):
    return {"action": "finish", "generation": store.generation, "title": "評估結果", "findings": [{"kind": "judge", "conclusion": "評委的分數不同。", "scope": "本案", "quotes": [{"ref": "/answers/0", "text": "完整回答"}]}], "facts": [], "limitations": ["小型測試"]}


def test_read_exposure_and_wrong_generation(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    value = report(store)
    assert validate_report(value, store)
    store.query("read_evidence", {"ref": "/answers/0", "limit": 2})
    assert validate_report(value, store)
    store.query("read_evidence", {"ref": "/answers/0"})
    assert validate_report(value, store) == []
    value["generation"] = "wrong"
    assert validate_report(value, store)


def test_verbatim_json_fragment_must_be_in_an_exposed_page(tmp_path):
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    fragment = '"answer_id":'
    assert not store.was_exposed('/answers/0', fragment)
    store.query('read_evidence', {'ref':'/answers/0'})
    assert store.was_exposed('/answers/0', fragment)
    assert not store.was_exposed('/answers/1', fragment)


def test_bounded_report_and_cached_resume(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    class Provider:
        model = "fixture"
        endpoint = "offline"
        def __init__(self): self.calls = 0
        def __call__(self, instructions, payload):
            self.calls += 1
            value = ({"action": "inspect", "requests": [{"tool": "read_evidence", "args": {"ref": "/answers/0"}}]} if not payload["history"] else report(store))
            return json.dumps(value, ensure_ascii=False), {"total_tokens": 2}
    store = EvidenceStore(source)
    provider = Provider()
    output = tmp_path / "report"
    path = ReportAgent(store, provider, output, max_rounds=3).run()
    assert path.exists() and provider.calls == 2
    second_store = EvidenceStore(source)
    ReportAgent(second_store, provider, output, max_rounds=3).run()
    assert provider.calls == 2
    receipts = json.loads((output / "request-receipts.json").read_text())
    assert all(r["new_usage"]["total_tokens"] == 0 for r in receipts)


def test_agent_catalog_is_bounded_but_case_evidence_remains_queryable(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    compact = store.catalog(compact=True)
    assert {item['ref'] for item in compact['source_index']} == {'/manifest', '/plan', '/aggregates'}
    assert compact['source_count'] == len(store.sources)
    assert compact['case_ids'] == ['TC-01']
    assert compact['subjects'] == ['s']
    assert compact['judges'] == ['j1', 'j2']
    assert '/answers/0' in store.query('get_case', {'case_id':store.result['answers'][0]['case_id']})['refs']


def test_report_resumes_completed_calls_with_extended_budget(tmp_path):
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    class Provider:
        model, endpoint = 'fixture', 'offline'
        def __init__(self): self.calls = 0
        def __call__(self, instructions, payload):
            self.calls += 1
            value = ({'action':'inspect','requests':[{'tool':'read_evidence','args':{'ref':'/answers/0'}}]}
                     if not payload['history'] else report(store))
            return json.dumps(value, ensure_ascii=False), {'total_tokens':2}
    provider = Provider()
    folder = tmp_path / 'report'
    with pytest.raises(RuntimeError, match='exhausted'):
        ReportAgent(store, provider, folder, max_rounds=1).run()
    assert provider.calls == 1
    resumed = ReportAgent(EvidenceStore(source), provider, folder, max_rounds=2).run()
    assert resumed.exists() and provider.calls == 2
    assert json.loads((folder/'request-receipts.json').read_text())[0]['reused'] is True


def test_compact_catalog_with_balanced_plan_uses_frozen_answers(tmp_path):
    result = fixture_result()
    result['plan'].update(case_ids=['TC-01'], subjects=[{'id':'s'}])
    seal_complete_results(result)
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(result, ensure_ascii=False))
    compact = EvidenceStore(source).catalog(compact=True)
    assert compact['case_ids'] == ['TC-01']
    assert compact['subjects'] == ['s']


def test_runtime_mismatches_require_case_evidence_and_remain_hypotheses(tmp_path):
    result = fixture_result()
    answer = result['answers'][0]
    answer['oracle_source'] = {
        'reference_oracle': {'status':'approved', 'scope':['route_ids', 'preferred_route_id', 'safety_levels']},
        'route_ids':['baseline'], 'preferred_route_id':'baseline', 'safety_levels':['normal']}
    answer['trace'] = {'route':{'id':'crisis_sop'}, 'safety':{'level':'immediate_danger'}}
    answer['requirements'] = [{'id':'safety', 'provenance':{'field':'safety_levels'}, 'critical':False}]
    answer['observations'] = {'safety':{'status':'AVAILABLE', 'value':False, 'actual':'immediate_danger'}}
    result['aggregates'] = aggregate_complete_results(result)
    seal_complete_results(result)
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(result, ensure_ascii=False))
    store = EvidenceStore(source)
    assert [item['kind'] for item in store.diagnostics] == ['safety', 'routing']
    assert store.catalog(compact=True)['runtime_verification']['status'] == 'PENDING_HISTORICAL_SNAPSHOT'
    store.query('read_evidence', {'ref':'/answers/0'})
    value = report(store)
    assert 'required diagnostic evidence not read: /diagnostics/0' in validate_report(value, store)
    for item in store.diagnostics:
        for ref in item['required_refs']:
            store.query('read_evidence', {'ref':ref})
    assert validate_report(value, store) == []
    value['findings'][0].update(kind='hypothesis', root_cause_status='CONFIRMED')
    errors = validate_report(value, store)
    assert 'causal hypothesis requires a verification plan' in errors
    assert 'confirmed runtime bug requires verified historical code/config and reproduction' in errors


def test_diagnostics_ignore_unapproved_safety_and_include_failed_quality_gate(tmp_path):
    result = fixture_result()
    answer = result['answers'][0]
    answer['oracle_source'] = {'reference_oracle':{'status':'draft', 'scope':['safety_levels']}}
    answer['requirements'] = [{'id':'safety', 'provenance':{'field':'safety_levels'}}]
    answer['observations'] = {'safety':{'status':'AVAILABLE', 'value':False, 'actual':'immediate_danger'}}
    result['envelopes'][0]['rubric'][0]['rubric']['gate'] = 'FAIL'
    result['aggregates'] = aggregate_complete_results(result)
    seal_complete_results(result)
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(result, ensure_ascii=False))
    store = EvidenceStore(source)
    assert [item['kind'] for item in store.diagnostics] == ['quality']
    assert store.diagnostics[0]['required_refs'] == ['/diagnostics/0', '/answers/0', '/envelopes/0']


def test_numerical_fact_is_source_bound(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    store.query("read_evidence", {"ref": "/answers/0"})
    store.query("read_evidence", {"ref": "/aggregates"})
    value = report(store)
    value["facts"] = [{"pointer": "/aggregates/metrics/0/value", "value": 100}]
    assert "numeric fact mismatch" in validate_report(value, store)


def test_malformed_provider_payload_can_be_repaired(tmp_path):
    source=tmp_path/'results.json'
    source.write_text(json.dumps(fixture_result(),ensure_ascii=False))
    store=EvidenceStore(source)
    for value in [None,{'findings':None},{'findings':['bad']},{'findings':[{'quotes':[None]}]},{'facts':[{'pointer':None}]}]:
        assert validate_report(value,store)


def test_dimension_signals_keep_judges_separate_and_require_answer_and_reason(tmp_path):
    result = fixture_result()
    answer = result['answers'][0]
    answer['trace'] = {'route': {'capsule_id': 'N3b'}}
    result['envelopes'][0]['rubric'][0]['rubric']['dimension_details'] = [
        {'module': '法律维权', 'score': 1, 'reason': '缺少依據'},
        {'module': '法律協助', 'score': 2, 'reason': '部分支援'}]
    result['envelopes'][0]['rubric'][1]['rubric']['dimension_details'] = [
        {'module': '法律维权', 'score': 3, 'reason': '有依據'}]
    seal_complete_results(result)
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(result, ensure_ascii=False))
    store = EvidenceStore(source)
    assert [(x['judge_id'], x['low'], x['evaluated']) for x in store.dimension_signals] == [
        ('j1', 1, 1), ('j2', 0, 1)]
    lead = next(item for item in store.diagnostics if item['kind'] == '法律維權')
    assert lead['required_refs'] == [lead['ref'], '/answers/0', '/envelopes/0']
    for ref in lead['required_refs']:
        store.query('read_evidence', {'ref': ref})
    store.query('read_evidence', {'ref': '/aggregates'})
    value = report(store)
    value['diagnoses'] = [{'signal_ref': lead['ref'], 'field': 'capsule.ground',
                           'observation': '評委提到缺少依據', 'hypothesis': '載入條件待核對',
                           'experiment': '只改一個 Ground 條件，固定 Router 和 Composer，比較回歸及誤載入',
                           'quote': {'ref': '/envelopes/0', 'text': '缺少依據'}}]
    assert validate_report(value, store) == []
    value['diagnoses'][0]['field'] = 'capsule.use_when'
    assert 'diagnosis must target a candidate field of a selected diagnostic' in validate_report(value, store)
    value['diagnoses'][0]['field'] = 'capsule.ground'
    value['diagnoses'][0]['root_cause_status'] = 'CONFIRMED'
    assert 'confirmed diagnosis requires verified historical code/config and reproduction' in validate_report(value, store)
    value['diagnoses'][0]['root_cause_status'] = 'PENDING'
    value['diagnoses'][0]['quote']['text'] = 4
    assert 'diagnosis requires a verbatim answer or Judge quote that was read' in validate_report(value, store)


def test_crisis_rubric_does_not_generate_legal_content_lead(tmp_path):
    result = fixture_result()
    result['answers'][0]['trace'] = {'route': {'capsule_id': 'crisis_sop'}}
    result['envelopes'][0]['rubric'][0]['rubric']['dimension_details'] = [
        {'module': '法律维权', 'score': 0, 'reason': '未引用條文'}]
    seal_complete_results(result)
    source = tmp_path / 'results.json'
    source.write_text(json.dumps(result, ensure_ascii=False))
    store = EvidenceStore(source)
    assert store.dimension_signals == []
    assert all(item['kind'] != '法律維權' for item in store.diagnostics)
