from copy import deepcopy
import pytest
from xiaoan_eval_core.routing import route_analysis


def row(turn,preferred,actual,accepted=None,status='reviewed'):
    return {'answer_id':str(turn),'subject_id':'s','case_id':'TC-X','turn':turn,
        'oracle_source':{'preferred_route_id':preferred,'route_ids':accepted or [preferred],
            'reference_oracle':{'status':status,'scope':['route_ids','preferred_route_id'],
                                'route_contracts':{'n1':{},'n2':{}}}},
        'trace':{'route':{'capsule_id':actual}}}


def test_modes_and_legal_alternative_are_separate():
    rows=[row(1,'crisis_sop','crisis_sop'),row(2,'baseline','n1',['baseline','n1']),
          row(3,'n1','safety_clarification'),row(4,'n1','bogus'),row(5,'n1',None)]
    r=route_analysis(rows);s=r['summary'][0]
    assert s['matrix']['CRISIS']['CRISIS']==1
    assert s['matrix']['BASELINE']['CAPSULE']==1
    assert s['matrix']['CAPSULE']['SAFETY_CLARIFICATION']==1
    assert s['matrix']['CAPSULE']['UNKNOWN']==1 and s['matrix']['CAPSULE']['MISSING']==1
    assert s['accepted_hit_n']==2 and s['accepted_evaluated_n']==4
    assert s['preferred_mode_accuracy']==pytest.approx(1/3)


def test_approval_ambiguity_single_route_and_dedup():
    a=row(1,None,'baseline',['baseline','n1']);b=row(2,None,'n1',['n1'])
    c=row(3,'n1','n1',status='provisional')
    r=route_analysis([a,b,c,deepcopy(b)])
    assert r['summary'][0]['planned_turns']==3 and r['summary'][0]['matrix_turns']==1
    assert r['details'][0]['exclusion_reason']=='NO_UNIQUE_EXPECTED_ROUTE'
    assert r['details'][1]['expected_basis']=='single_accepted_route'
    assert r['details'][2]['accepted_hit'] is None


def test_conflicting_same_subject_case_turn_rejected():
    with pytest.raises(ValueError):route_analysis([row(1,'n1','n1'),row(1,'n1','n2')])


def test_workbook_and_report_show_matrix_without_judge_duplication(tmp_path):
    import json
    from openpyxl import load_workbook
    from test_frozen_outputs import fixture_result
    from xiaoan_eval_core.results import aggregate_complete_results,seal_complete_results
    from xiaoan_eval.frozen_export import export_results_workbook
    from evaluation_report_agent.presentation import render_readable
    from types import SimpleNamespace
    r=fixture_result();source=row(1,'baseline','n1',['baseline','n1'])
    r['answers'][0].update(oracle_source=source['oracle_source'],trace=source['trace'])
    r['aggregates']=aggregate_complete_results(r);seal_complete_results(r)
    assert r['aggregates']['routing']['summary'][0]['planned_turns']==1 # fixture has two judges
    path=export_results_workbook(r,tmp_path/'results.xlsx');wb=load_workbook(path,read_only=True)
    assert any('危機模式' in str(x[1]) for x in wb['Routing Summary'].values)
    assert not any('路由' in str(x[0]) for x in wb['Score Summary'].values if x[0] is not None)
    store=SimpleNamespace(result=r,generation=r['result_generation'],exposed={},sources={})
    text=render_readable({'title':'測試','findings':[],'facts':[]},store)
    assert '安全澄清' in text and '100%' in text
