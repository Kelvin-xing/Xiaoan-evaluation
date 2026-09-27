import json

import pytest

from evaluation_report_agent.research import (
    candidate_fields, code_turn, collect, compact_unit, extract_unit, field_decisions,
    field_inventory, field_payload, render_report, summarize_patterns,
    validate_coding, validate_field_review,
)


def unit(judge, *, answer='a', status='ANALYZABLE'):
    return {'id': f'{answer}:{judge}', 'answer_id': answer, 'case_id': 'TC-01',
            'turn': 1, 'subject_id': 's', 'judge_id': judge,
            'status': status, 'question': '問題', 'answer': '回答', 'route': 'n1',
            'safety': 'NO_IMMEDIATE_CRISIS', 'ground_loaded': False,
            'ground_nodes': [], 'ground_expected': [], 'checks': {},
            'signals': [{'id': 'r:0', 'kind': 'rubric', 'score': 1, 'text': '缺少支持'}],
            'rubric_ref': '/envelopes/0/rubric/0'}


def test_extract_preserves_reason_and_partial_assessment():
    row = {'answer_id': 'a', 'case_id': 'TC-01', 'turn': 1, 'subject_id': 's',
           'question': '問題', 'answer': '回答',
           'trace': {'route': {'capsule_id': 'n1'}, 'ground': {'resolved_ground': ['one']}}}
    envelope = {'rubric': [{'judge_id': 'j', 'status': 'AVAILABLE', 'gate': 'FAIL',
                           'dimensions': [{'module':'法律維權','score':0,'reason':'缺法源'}],
                           'red_lines': [{'id':'RL-01','triggered':True,'reason':'風險'}]}],
                'assessments': [{'judge_id':'j','status':'PARTIAL',
                                 'claims':[{'id':'c1','faithfulness':{'verdict':'PARTIAL','reason':'部分'},
                                            'correctness':{'verdict':'UNKNOWN','reason':'無真值'}}],
                                 'requirements':[{'id':'req','verdict':'UNCERTAIN','reason':'未明確'}]}]}
    result = extract_unit(row,envelope,0,'j')
    assert result['status'] == 'ANALYZABLE' and result['assessment_status'] == 'PARTIAL'
    assert result['ground_nodes'] == ['one']
    assert [s['id'] for s in result['signals']] == ['r:0','red:0','claim:0:faithfulness','req:0']
    assert result['rubric_ref'] == '/envelopes/0/rubric/0'


def test_coding_requires_all_ids_and_real_reason_refs():
    units = [unit('j1'),unit('j2',status='UNAVAILABLE')]
    coded = {'units': [{'id':'a:j1','issues':[{'code':'UNSUPPORTED_CLAIM',
                       'evidence_ids':['r:0'],'note':'主張沒有依據'}]},
                       {'id':'a:j2','issues':[]}]}
    assert len(validate_coding(coded,units)) == 2
    with pytest.raises(ValueError,match='every unit'):
        validate_coding({'units':coded['units'][:1]},units)
    coded['units'][0]['issues'][0]['evidence_ids'] = ['fabricated']
    with pytest.raises(ValueError,match='evidence'):
        validate_coding(coded,units)


def test_ten_percent_gate_and_per_cell_comparability(tmp_path):
    units = [unit('j',answer=f'a{i}') for i in range(10)]
    groups = {('TC-01',i):[u] for i,u in enumerate(units)}
    # No paid checkpoints: none of these units may be presented as analyzed.
    _,_,coverage = collect(tmp_path,groups,'binding',{'j'})
    assert coverage['planned'] == 10 and coverage['analyzed'] == 0
    assert coverage['accepted'] is False and coverage['matrix'][0]['comparable'] is False


def test_pattern_uses_unique_answers_not_judge_votes(tmp_path):
    units = [unit('j1'),unit('j2')]
    coded = {u['id']:{'issues':[{'code':'UNSUPPORTED_CLAIM','evidence_ids':['r:0'],
                                'note':'缺法源'}]} for u in units}
    pattern = summarize_patterns(units,coded)[0]
    assert pattern['judge_units']==2 and pattern['unique_answers']==1 and pattern['case_count']==1
    capsule = tmp_path/'capsules.json'
    capsule.write_text(json.dumps([{'id':'n1','render_policy':'限制'}]))
    wiki = tmp_path/'nodes'
    wiki.mkdir()
    (wiki/'example.md').write_text('---\nsource_refs: []\n---\n## 適用\n內容')
    inventory = field_inventory(capsule,wiki)
    decisions = field_decisions([pattern],units,coded,inventory)
    assert any(x['target']=='Composer' and x['key']=='source_use' and
               x['status']=='INVESTIGATE' for x in decisions)
    assert any(x['target']=='Wiki example' and x['key']=='## 適用' and
               x['status']=='NO_EVIDENCE' for x in decisions)
    coverage = {'planned':2,'analyzed':2,'unavailable':0,'unavailable_ratio':0,
                'matrix':[{'subject_id':'s','judge_id':'j1','analyzed':1,'planned':1,'comparable':True},
                          {'subject_id':'s','judge_id':'j2','analyzed':1,'planned':1,'comparable':True}]}
    render_report(tmp_path,coverage,[pattern],decisions,units)
    report = (tmp_path/'report.md').read_text()
    assert '| capsule/wiki | 鍵位 | 修改建議 | 證據 |' in report
    assert '2 個評委單位' in report and '唯一回答 | 案例' in report


def test_field_review_requires_every_key_and_real_unit_reference():
    units = [unit('j1')]
    coded = {units[0]['id']:{'issues':[{'code':'UNSUPPORTED_CLAIM',
              'evidence_ids':['r:0'],'note':'未核法源'}]}}
    pattern = summarize_patterns(units,coded)[0]
    inventory = {('Composer','source_use'):'只用已給來源'}
    payload = field_payload(pattern,units,coded,inventory)
    decision = {'target':'Composer','key':'source_use','status':'VERIFY',
                'recommendation':'先查送達來源再重播','unit_ids':[units[0]['id']]}
    assert validate_field_review({'decisions':[decision]},payload) == [decision]
    with pytest.raises(ValueError,match='grounded'):
        validate_field_review({'decisions':[{**decision,'unit_ids':['fabricated']}]},payload)
    with pytest.raises(ValueError,match='omitted'):
        validate_field_review({'decisions':[]},payload)
    capsule_payload = {**payload,'fields':[{'target':'Capsule n1','key':'act',
                       'current':'先確認使用者的處境和能力限制再給出選項。'}]}
    with pytest.raises(ValueError,match='verbatim'):
        validate_field_review({'decisions':[{'target':'Capsule n1','key':'act',
          'status':'MODIFY_CANDIDATE','recommendation':'修改','current_quote':'不存在的句子',
          'unit_ids':[units[0]['id']]}]},capsule_payload)


def test_judge_applicability_does_not_generate_product_edit():
    units = [unit('j1')]
    coded = {units[0]['id']:{'issues':[{'code':'JUDGE_APPLICABILITY',
              'evidence_ids':['r:0'],'note':'危機時不宜給法條'}]}}
    pattern = summarize_patterns(units,coded)[0]
    assert candidate_fields(pattern,units,coded,{('Capsule n1','render_policy'):'x'}) == []


def test_invalid_large_response_retries_in_checkpointed_slices(tmp_path):
    units = [unit('j',answer=f'a{i}') for i in range(9)]
    calls = []
    def provider(_instructions,payload):
        calls.append(len(payload['units']))
        if len(payload['units']) == 9:
            return '{}', {}
        return json.dumps({'units':[{'id':item['id'],'issues':[]} for item in payload['units']]}), {}
    path = code_turn(tmp_path,('TC-01',1),units,provider,'binding')
    assert calls == [9,9,9,8,1]
    assert path.exists() and len(json.loads(path.read_text())['units']) == 9
    assert code_turn(tmp_path,('TC-01',1),units,provider,'binding') == path
    assert calls == [9,9,9,8,1]
