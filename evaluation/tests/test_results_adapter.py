"""Canonical replacement for retired compact result projection tests."""
from xiaoan_eval_core.results import build_complete_results, seal_complete_results
from xiaoan_eval.frozen_export import SHEETS, project_results
from test_frozen_outputs import fixture_result


def test_complete_result_has_eight_views_one_relevancy_per_answer():
    result = fixture_result()
    result['envelopes'][0]['relevancy'] = {'answer_id':'a', 'status':'AVAILABLE','score':.8}
    seal_complete_results(result)
    tables = project_results(result)
    assert tuple(tables) == SHEETS
    assert SHEETS == (
        'Overview', 'Score Summary', 'Routing Summary', 'Coverage & Usage',
        'Case Eligibility', 'Spec', 'Answers', 'Scores',
        'Claims', 'Requirements', 'Rating Details', 'Human Review',
    )
    assert result['schema_version'] == 'xiaoan-results/v2'
    assert len(tables['Answers']) == 1
    assert tables['Answers'][0]['relevancy'] == .8
    assert len(tables['Scores']) == 4  # rubric + assessment for each Judge
    assert tables['Rating Details'][0]['detail_type'] == 'dimension'
    assert tables['Claims'][0]['claim'] == '完整主張'


def test_missing_stages_keep_answers_and_do_not_impute_quality_zero():
    fixture = fixture_result()
    result = build_complete_results(fixture['plan'], fixture['answers'], {}, [], [], [], [])
    tables = project_results(result)
    assert tables['Answers'][0]['answer'] == '完整回答'
    assert tables['Answers'][0]['relevancy'] is None
    assert not tables['Claims']
    metrics = [m for m in result['aggregates']['metrics'] if m['metric'] == 'rubric']
    assert metrics and all(m['value'] is None and m['effective_cases'] == 0 for m in metrics)
    assert len(tables['Human Review']) == 2


def test_undetermined_gate_is_not_displayed_as_zero(tmp_path):
    from openpyxl import load_workbook
    from xiaoan_eval.frozen_export import export_results_workbook

    fixture = fixture_result()
    result = build_complete_results(fixture['plan'], fixture['answers'], {}, [], [], [], [])
    gate = next(row for row in result['aggregates']['metrics']
                if row['scope'] == 'own_complete_cases' and row['metric'] == 'rubric_gate')
    assert gate['value'] == 0 and gate['gate_counts'] == {'UNDETERMINED': 1}
    book = load_workbook(export_results_workbook(result, tmp_path/'results.xlsx'), read_only=True)
    overview = list(book['Overview'].values)
    heading = next(index for index, row in enumerate(overview) if row[:3] == ('總體', '全部案例', 'rubric_gate'))
    assert overview[heading + 2][1:3] == ('UNAVAILABLE', 'UNAVAILABLE')
    book.close()


def test_all_claim_evidence_and_dimension_reasons_survive_projection():
    result = fixture_result()
    result['answers'][0]['context'] = [{'ref':'ctx-1','content':'第一份證據','layer':'CAPSULE'}, {'ref':'ctx-2','content':'第二份證據','layer':'WIKI'}]
    claim = result['envelopes'][0]['assessments'][0]['assessment']['claims'][0]
    claim['faithfulness'] = {'verdict':'ENTAILED','reason':'兩份證據共同支持','evidence':[
        {'ref':'ctx-1','start':0,'end':5,'text':'第一份證據'}, {'ref':'ctx-2','start':0,'end':5,'text':'第二份證據'}]}
    seal_complete_results(result)
    tables = project_results(result)
    evidence = tables['Claims'][0]['faithfulness_evidence']
    assert [e['ref'] for e in evidence] == ['ctx-1','ctx-2']
    assert [e['layer'] for e in evidence] == ['CAPSULE','WIKI']
    assert tables['Claims'][0]['faithfulness_reason'] == '兩份證據共同支持'
    assert tables['Rating Details'][0]['reason'] == '明確回應感受'
    assert tables['Claims'][0]['answer_quote'] == '完整回答'


def test_workbook_config_is_readable_summary_not_full_prompt_or_context():
    result = fixture_result()
    result['manifest']['evaluator_config'] = {'prompts/rubric.md': {'content':'SECRET_FULL_PROMPT', 'sha256':'hash'}, 'schemas/rubric.json': {'content':'FULL_SCHEMA','sha256':'schema-hash'}}
    result['manifest']['plan'] = {'aggregation_policy': {'comparison_scope': 'common_complete_cases'}, 'suite_id': 'fixture'}
    result['answers'][0]['history'] = [{'role':'user','content':'FULL_HISTORY'}]
    result['answers'][0]['trace'] = {'raw':'RAW_TRACE'}
    seal_complete_results(result)
    tables = project_results(result)
    import json
    exported = json.dumps({'Spec':tables['Spec'], 'Answers':tables['Answers']})
    assert 'SECRET_FULL_PROMPT' not in exported and 'FULL_SCHEMA' not in exported
    assert 'FULL_HISTORY' not in exported and 'RAW_TRACE' not in exported
    assert 'schema-hash' in exported
    assert 'common_complete_cases' not in exported
    assert tables['Scores'][0]['score:同理'] == 1
