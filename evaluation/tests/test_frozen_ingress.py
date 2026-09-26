from copy import deepcopy
import hashlib
import json
from pathlib import Path
import pytest
import yaml
from xiaoan_eval.frozen_ingress import build_plan, freeze_answer, validate_frozen_spec, verify_minimal33
from xiaoan_eval_core.taxonomy import case_taxonomy
from xiaoan_eval_core.contracts import digest
from xiaoan_eval.frozen_generation import generate
from xiaoan_eval.cli import _parser


IDENTITY={'id':'test','provider':'fixture','model':'test','prompt_version':'v1'}


def test_local_subject_captures_real_composer_boundary(monkeypatch):
    from xiaoan_eval.frozen_generation import LocalChatflowSubject
    subject=LocalChatflowSubject()
    import chat_service
    from context_snapshot import record_request,snapshot
    def fake_turn(message,capsules,*,state,debug_callback,**kwargs):
        record_request('composer',{'model':'test','messages':[{'role':'system','content':'fixed prompt'},
            {'role':'user','content':json.dumps({'user_message':message})}]})
        debug_callback({'effective_context_snapshot':snapshot(1)})
        return 'answer',state
    monkeypatch.setattr(chat_service,'run_turn',fake_turn)
    response,_=subject.turn(IDENTITY,{'question':'question'},None,[])
    assert response['trace']['effective_context_snapshot']['invocations']['composer']['status']=='INVOKED'


def test_approved_suite_and_plan_includes_all_missing_rows():
    selection, approval, _ = verify_minimal33()
    assert selection['case_count']==33 and approval['turn_count']==100
    spec=build_plan([IDENTITY],[IDENTITY],IDENTITY)
    assert len(spec['rows'])==100
    assert all(r['answer'] is None and r['availability']=='UNAVAILABLE' for r in spec['rows'])
    assert all(r['test_type'] and r['scenario_category'] and r['scenario_tags'] for r in spec['rows'])


def test_all_case_taxonomy_matches_registry_and_mirror():
    root=Path(__file__).resolve().parents[2]
    registry=json.loads((root/'evaluation/test-cases/scenario-taxonomy.json').read_text())['cases']
    assert len(registry)==75
    for case_id, expected in registry.items():
        for directory in ('evaluation/test-cases','evaluation_multimodels/test-cases'):
            case=yaml.safe_load((root/directory/(case_id+'.yaml')).read_text())
            labels=case_taxonomy(case)
            assert [labels['test_type'],labels['scenario_category'],labels['scenario_tags']]==expected


def test_answer_missing_snapshot_stays_available_and_mutation_rejected():
    spec=build_plan([IDENTITY],[IDENTITY],IDENTITY,case_ids=['TC-35'])
    spec['rows']=[freeze_answer(r,{'text':'凍結回答'},[],generation_id='one') for r in spec['rows']]
    validate_frozen_spec(spec)
    assert spec['rows'][0]['status']=='AVAILABLE'
    assert spec['rows'][0]['context_capture']=='UNAVAILABLE'
    spec['rows'][0]['answer']='modified'
    with pytest.raises(ValueError,match='hash'):validate_frozen_spec(spec)


def test_lane_history_and_success_reuse(tmp_path):
    spec=build_plan([IDENTITY],[IDENTITY],IDENTITY,case_ids=['TC-35'])
    class Subject:
        calls=[]
        def start(self,*args):return None
        def turn(self,subject,row,state,history):
            self.calls.append(deepcopy(history));return {'text':'回答'+str(row['turn'])},state
    subject=Subject()
    first=generate(spec,subject,checkpoint_dir=tmp_path,max_workers=1)
    assert subject.calls[0]==[] and len(subject.calls[1])==2
    second=generate(spec,subject,checkpoint_dir=tmp_path,max_workers=1)
    assert len(subject.calls)==2
    assert first['rows']==second['rows']


def test_old_commands_removed():
    parser=_parser()
    for old in ('unified','staged'):
        with pytest.raises(SystemExit):parser.parse_args(['measure',old,'input.json','--output','out'])
    args=parser.parse_args(['measure','frozen-answer-evaluation','input.json','--output','out'])
    assert args.method=='frozen-answer-evaluation'


def test_manifest_binding_required_and_model_identity_sealed():
    spec = build_plan([IDENTITY], [IDENTITY], IDENTITY, case_ids=['TC-35'])
    validate_frozen_spec(spec)
    tampered = deepcopy(spec)
    tampered['manifest']['provider_options'] = {'temperature': 0.2}
    with pytest.raises(ValueError, match='manifest digest'):
        validate_frozen_spec(tampered)
    tampered = deepcopy(spec)
    tampered['rows'][0] = freeze_answer(tampered['rows'][0], {'text': 'answer'}, [], generation_id='x')
    tampered['rows'][0]['manifest_digest'] = 'tampered'
    tampered['manifest']['manifest_digest'] = digest({k:v for k,v in tampered['manifest'].items() if k != 'manifest_digest'})
    with pytest.raises(ValueError, match='manifest binding'):
        validate_frozen_spec(tampered)


def test_factual_gold_requires_independent_scope_and_hash(tmp_path):
    case = {'id': 'TC-X', 'oracle_provenance': {'status': 'reviewed'}}
    turn = {'turn': 1, 'expected': {'source_refs': ['content/sops/crisis-sop.md'],
        'reference_oracle': {'status': 'reviewed'}}}
    from xiaoan_eval.frozen_ingress import oracle_row
    row = oracle_row(case, turn)
    assert row['reference_facts'] == []
    assert 'TRUTH_SCOPE_NOT_APPROVED' in row['remediation']
    import xiaoan_eval.frozen_ingress as ingress
    expected = {'source_refs': ['content/sops/crisis-sop.md'],
      'reference_oracle': {'fact_approval': {'status': 'approved', 'scope': ['reference_facts'],
          'approved_by': 'owner', 'truth_version': 'v1', 'source_hashes': {'content/sops/crisis-sop.md': 'bad'}}}}

    # An approved path with a false hash fails closed.
    with pytest.raises(ValueError, match='hash mismatch'):
        ingress.resolve_reference_facts(expected)


def test_independent_fact_resolver_freezes_approved_source_and_rejects_changed_snapshot(tmp_path):
    from xiaoan_eval.frozen_ingress import resolve_reference_facts, file_hash
    source = tmp_path / 'fact.md'
    source.write_text('Exact approved source fact.', encoding='utf-8')
    expected = {'source_refs': ['fact.md'], 'reference_oracle': {'fact_approval': {
        'status': 'approved', 'scope': ['reference_facts'], 'truth_version': 'v1',
        'approved_by': 'owner', 'source_hashes': {'fact.md': file_hash(source)}}}}
    facts, status, version, reasons = resolve_reference_facts(expected, root=tmp_path)
    assert facts[0]['content'] == 'Exact approved source fact.'
    assert (status, version, reasons) == ('approved', 'v1', [])
    source.write_text('Changed after approval.', encoding='utf-8')
    with pytest.raises(ValueError, match='hash mismatch'):
        resolve_reference_facts(expected, root=tmp_path)


def test_provider_options_sealed_and_transcript_not_claimed_as_effective_input():
    first = build_plan([IDENTITY], [IDENTITY], IDENTITY, case_ids=['TC-35'],
                       provider_options={'request_bodies': {'temperature': 0.1}})
    second = build_plan([IDENTITY], [IDENTITY], IDENTITY, case_ids=['TC-35'],
                       provider_options={'request_bodies': {'temperature': 0.8}})
    assert first['manifest']['manifest_digest'] != second['manifest']['manifest_digest']
    first['provider_options'] = second['provider_options']
    with pytest.raises(ValueError, match='provider_options mismatch'):
        validate_frozen_spec(first)
    row = freeze_answer(second['rows'][0], {'text': 'answer'}, [{'role': 'user', 'content': 'prior'}])
    assert row['history_kind'] == 'conversation_transcript'
    assert row['effective_generation_input_status'] == 'UNAVAILABLE'
    assert row['effective_generation_input'] is None


def test_partial_abstention_annotates_existing_requirements_and_no_extra_score():
    spec = build_plan([IDENTITY], [IDENTITY], IDENTITY, case_ids=['TC-35'])
    row = spec['rows'][1]
    scopes = [r for r in row['requirements'] if r.get('abstention_scope')]
    assert len(scopes) == 4
    assert all(r['provenance']['field'] != 'partial_abstention' for r in row['requirements'])
    completed = freeze_answer(row, {'text': 'answer'}, [])
    del completed['row_digest']
    spec['rows'][1] = completed
    with pytest.raises(ValueError, match='digest required'):
        validate_frozen_spec(spec)
