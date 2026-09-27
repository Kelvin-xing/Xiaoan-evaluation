"""Selective retry never changes a sealed parent or calls unselected stages."""
from copy import deepcopy
import json

import pytest

from test_frozen_end_to_end import FixtureProvider, IDENTITY
from xiaoan_eval.frozen_cli import execute_frozen
from xiaoan_eval.frozen_generation import generate
from xiaoan_eval.frozen_ingress import build_plan, freeze_answer
from xiaoan_eval.frozen_retry import retry_evaluation, extend_judges, import_successful_checkpoints
from xiaoan_eval_core.results import seal_complete_results, validate_complete_results


def frozen_fixture():
    spec=build_plan([IDENTITY],[IDENTITY],IDENTITY,case_ids=['TC-35'],relevancy_generator=IDENTITY)
    spec['rows']=[freeze_answer(row,{'text':'這是離線合成回答。'},[],generation_id='same') for row in spec['rows']]
    return spec


def test_only_failed_rubric_is_called_and_parent_is_unchanged(tmp_path):
    spec=frozen_fixture()
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='rubric' and request['answer_id']==spec['rows'][0]['answer_id']:
                raise ValueError('fixture failure')
            return super().__call__(request)
    original=execute_frozen(spec,tmp_path/'parent',provider=First())
    saved=deepcopy(original)
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append((request['task'],request['answer_id']))
            return super().__call__(request)
    child=retry_evaluation(spec,original,tmp_path/'child',stages=['rubric'],provider=Retry())
    validate_complete_results(child)
    assert calls==[('rubric',spec['rows'][0]['answer_id'])]
    assert original==saved
    assert child['result_generation']!=original['result_generation']
    assert all(env['rubric'][0]['status']=='AVAILABLE' for env in child['envelopes'])
    assert child['envelopes'][1]['assessments']==original['envelopes'][1]['assessments']
    assert json.loads((tmp_path/'parent/results.json').read_text())==original
    assert len(list((tmp_path/'child/checkpoint').glob('*.events.jsonl')))==1


def test_in_place_retry_replaces_sealed_result_without_rerunning_successes(tmp_path):
    spec=frozen_fixture()
    target=spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self, request):
            if request['task']=='rubric' and request['answer_id']==target:
                raise ValueError('offline fixture failure')
            return super().__call__(request)
    parent=execute_frozen(spec,tmp_path/'run',provider=First())
    before={p.name:(p.read_bytes(),p.stat().st_mtime_ns) for p in (tmp_path/'run/checkpoint').glob('*.json')}
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self, request):
            calls.append((request['task'],request['answer_id']))
            return super().__call__(request)
    result=retry_evaluation(spec,parent,tmp_path/'run',stages=['rubric'],provider=Retry())
    assert calls==[('rubric',target)]
    assert result['result_generation']!=parent['result_generation']
    assert validate_complete_results(json.loads((tmp_path/'run/results.json').read_text()))==result
    assert all(e['rubric'][0]['status']=='AVAILABLE' for e in result['envelopes'])
    assert all((tmp_path/'run/checkpoint'/name).read_bytes()==data and
               (tmp_path/'run/checkpoint'/name).stat().st_mtime_ns==stamp
               for name,(data,stamp) in before.items())


def test_conflict_only_reconciliation_keeps_semantic_disputes_for_review(tmp_path):
    from xiaoan_eval.frozen_retry import reconcile_assessment_conflicts
    spec=frozen_fixture()
    parent=execute_frozen(spec,tmp_path/'run',provider=FixtureProvider())
    original=deepcopy(parent['envelopes'][0]['assessments'][0]['assessment']['requirements'][0])
    wording=deepcopy(original)
    wording['reason']='alternative explanation'
    semantic=deepcopy(original)
    semantic['verdict']='VIOLATED' if original['verdict']!='VIOLATED' else 'UNCERTAIN'
    for env,candidate in zip(parent['envelopes'],(wording,semantic)):
        cell=env['assessments'][0]
        cell['status']=cell['assessment']['status']='PARTIAL'
        cell['assessment']['retry_conflicts']=[{'requirement_id':original['id'],
                                                'preserved':deepcopy(original),'candidate':candidate}]
    seal_complete_results(parent)
    (tmp_path/'run/results.json').write_text(json.dumps(parent,ensure_ascii=False))
    summary=reconcile_assessment_conflicts(deepcopy(parent))
    assert summary=={'resolved_non_scoring':1,'needs_review':1}
    result=retry_evaluation(spec,parent,tmp_path/'run',stages=['assessment'],
                            provider=lambda _:pytest.fail('no provider call for conflict-only cells'))
    assert [e['assessments'][0]['status'] for e in result['envelopes']]==['AVAILABLE','PARTIAL']
    assert result['envelopes'][0]['assessments'][0]['assessment']['retry_conflicts']
    assert result['envelopes'][1]['assessments'][0]['assessment']['conflict_review']=='REQUIRED'


def test_conflict_only_mode_publishes_in_place_without_provider(tmp_path):
    spec=frozen_fixture()
    parent=execute_frozen(spec,tmp_path/'run',provider=FixtureProvider())
    cell=parent['envelopes'][0]['assessments'][0]
    saved=deepcopy(cell['assessment']['requirements'][0])
    alternative={**saved,'reason':'different explanation'}
    cell['status']=cell['assessment']['status']='PARTIAL'
    cell['assessment']['retry_conflicts']=[{'requirement_id':saved['id'],
                                            'preserved':saved,'candidate':alternative}]
    seal_complete_results(parent)
    (tmp_path/'run/results.json').write_text(json.dumps(parent,ensure_ascii=False))
    result=retry_evaluation(spec,parent,tmp_path/'run',reconcile_only=True,
                            provider=lambda _:pytest.fail('offline mode called provider'))
    assert result['envelopes'][0]['assessments'][0]['status']=='AVAILABLE'
    assert result['provenance'][-1]['operation']=='reconcile_assessment_conflicts'
    assert result['aggregates']['answer_costs']==parent['aggregates']['answer_costs']
    validate_complete_results(json.loads((tmp_path/'run/results.json').read_text()))


def test_runtime_concurrency_change_reuses_successful_checkpoint_without_rewriting_it(tmp_path):
    from xiaoan_eval.rules import load_rating_rule
    from xiaoan_eval_core.configuration import ROOT
    from xiaoan_eval_core.orchestration import build_rubric_request
    from xiaoan_eval_core.runtime import ResponseStore
    spec = frozen_fixture()
    target = spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self, request):
            if request['task'] == 'rubric' and request['answer_id'] == target:
                raise ValueError('first generation unavailable')
            return super().__call__(request)
    parent = execute_frozen(spec, tmp_path/'parent', provider=First())
    calls = []
    class Retry(FixtureProvider):
        def __call__(self, request):
            calls.append(request['task'])
            return super().__call__(request)
    probe = Retry()
    request = build_rubric_request(spec['rows'][0], load_rating_rule(ROOT/'rating-rule.yml'),
                                   judge=spec['judges'][0])
    store = ResponseStore(tmp_path/'child/checkpoint', provider_options=spec.get('provider_options'))
    key = store.request_digest(request)
    store.call(request, probe, lambda payload, _: payload)
    path = tmp_path/'child/checkpoint'/f'{key}.json'
    original = path.read_bytes()
    original_mtime = path.stat().st_mtime_ns
    assert calls == ['rubric']
    calls.clear()
    child = retry_evaluation(spec, parent, tmp_path/'child', stages=['rubric'], provider=probe,
                             max_workers=11, provider_max_inflight=11)
    assert child['envelopes'][0]['rubric'][0]['status'] == 'AVAILABLE'
    assert calls == []
    assert path.read_bytes() == original and path.stat().st_mtime_ns == original_mtime
    assert child['provenance'][-1]['execution_limits']['provider_max_inflight'] == 11


def test_add_judge_keeps_original_manifest_answers_and_successful_checkpoint(tmp_path):
    from xiaoan_eval.frozen_ingress import validate_frozen_spec
    from xiaoan_eval_core.orchestration import build_rubric_request
    from xiaoan_eval.rules import load_rating_rule
    from xiaoan_eval_core.configuration import ROOT
    from xiaoan_eval_core.runtime import ResponseStore
    spec = frozen_fixture()
    parent = execute_frozen(spec, tmp_path/'parent', provider=FixtureProvider())
    another = {**IDENTITY, 'id':'new-judge'}
    extended = extend_judges(spec, [another])
    assert extended['manifest'] == spec['manifest']
    assert extended['rows'] == spec['rows']
    validate_frozen_spec(extended)
    with pytest.raises(ValueError, match='already planned'):
        extend_judges(extended, [another])
    altered = deepcopy(extended)
    altered['plan']['subject_mode'] = 'direct'
    with pytest.raises(ValueError, match='extension mismatch'):
        validate_frozen_spec(altered)

    requests = []
    class Probe(FixtureProvider):
        def __call__(self, request):
            requests.append((request['task'], request.get('identity', {}).get('id')))
            return super().__call__(request)
    probe = Probe()
    source = tmp_path/'unsealed'
    request = build_rubric_request(spec['rows'][0], load_rating_rule(ROOT/'rating-rule.yml'), judge=another)
    store = ResponseStore(source/'checkpoint', provider_options=spec.get('provider_options'))
    store.call(request, probe, lambda payload, _: payload)
    requests.clear()
    checkpoint = next((source/'checkpoint').glob('*.json'))
    before = checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns
    child = retry_evaluation(extended, parent, tmp_path/'child', provider=probe,
                             checkpoint_sources=[source], max_workers=30, provider_max_inflight=30)
    assert child['manifest'] == parent['manifest']
    assert child['answers'] == parent['answers']
    assert child['plan']['judges'] == extended['judges']
    assert all({cell['judge_id'] for cell in env['rubric']} == {IDENTITY['id'], 'new-judge'}
               for env in child['envelopes'])
    assert sorted(requests) == sorted([('rubric', 'new-judge'),
                                       ('assess_claims', 'new-judge'),
                                       ('assess_claims', 'new-judge')])
    assert (checkpoint.read_bytes(), checkpoint.stat().st_mtime_ns) == before
    assert (tmp_path/'child/checkpoint'/checkpoint.name).read_bytes() == before[0]
    assert child['provenance'][-1]['execution_limits']['provider_max_inflight'] == 30


def test_appended_judge_checkpoint_outside_selected_answers_stays_unselected(tmp_path):
    spec = frozen_fixture()
    added = {**IDENTITY, 'id': 'new-judge'}
    extended = extend_judges(spec, [added])

    class NoExtraction(FixtureProvider):
        def __call__(self, request):
            if request['task'] == 'extract_claims':
                raise ValueError('fixture extraction unavailable')
            return super().__call__(request)

    parent = execute_frozen(spec, tmp_path / 'parent', provider=NoExtraction())
    execute_frozen(extended, tmp_path / 'source', provider=FixtureProvider())
    selected = spec['rows'][0]['answer_id']
    child = retry_evaluation(extended, parent, tmp_path / 'child', answer_ids=[selected],
                             provider=FixtureProvider(), checkpoint_sources=[tmp_path / 'source'])
    validate_complete_results(child)
    selected_env = next(e for e in child['envelopes'] if e['answer_id'] == selected)
    other_env = next(e for e in child['envelopes'] if e['answer_id'] != selected)
    assert selected_env['inventory_id'] is not None
    assert other_env['inventory_id'] is None
    assert next(c for c in other_env['assessments'] if c['judge_id'] == added['id']) == {
        'answer_id': other_env['answer_id'], 'case_id': 'TC-35', 'turn': 2,
        'subject_id': IDENTITY['id'], 'judge_id': added['id'], 'judge_identity': added,
        'status': 'UNAVAILABLE', 'execution_status': 'SKIPPED', 'reason': 'NOT_SELECTED'}


def test_assessment_retry_reuses_inventory_without_extraction_call(tmp_path):
    spec=frozen_fixture()
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='assess_claims' and request['answer_id']==spec['rows'][0]['answer_id']:
                raise ValueError('fixture failure')
            return super().__call__(request)
    original=execute_frozen(spec,tmp_path/'parent',provider=First())
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append(request['task'])
            return super().__call__(request)
    child=retry_evaluation(spec,original,tmp_path/'child',stages=['assessment'],provider=Retry())
    assert calls==['assess_claims']
    assert len(child['inventories'])==len(original['inventories'])==2
    assert all(env['assessments'][0]['status']=='AVAILABLE' for env in child['envelopes'])


def test_assessment_retry_supplies_preserved_inventory_when_extraction_cache_misses(tmp_path):
    spec=frozen_fixture()
    target=spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='assess_claims' and request['answer_id']==target:
                raise ValueError('fixture failure')
            return super().__call__(request)
    parent=execute_frozen(spec,tmp_path/'parent',provider=First())
    for receipt in parent['stages']:
        if receipt.get('task')=='extract_claims' and receipt.get('answer_id')==target:
            receipt.pop('raw_response',None)
    seal_complete_results(parent)
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append(request['task'])
            return super().__call__(request)
    child=retry_evaluation(spec,parent,tmp_path/'child',stages=['assessment'],
                           answer_ids=[target],provider=Retry())
    assert calls==['assess_claims']
    assert child['envelopes'][0]['assessments'][0]['status']=='AVAILABLE'
    assert child['envelopes'][0]['inventory_id']==parent['envelopes'][0]['inventory_id']
    assert all('inventory' not in row for row in child['answers'])
    assert len([receipt for receipt in child['stages'] if receipt.get('task')=='extract_claims']) == len(
        [receipt for receipt in parent['stages'] if receipt.get('task')=='extract_claims'])
    legacy=deepcopy(child)
    preserved=next(inv for inv in child['inventories'] if inv['answer_id']==target)
    legacy['answers'][0]['inventory']={
        'binding':preserved['binding'],
        'claims':preserved['claims']}
    seal_complete_results(legacy)
    with pytest.raises(ValueError,match='No unavailable selected stage cells'):
        retry_evaluation(spec,legacy,tmp_path/'followup',stages=['rubric'],
                         answer_ids=[target],dry_run=True)


def test_missing_inventory_is_extracted_before_selected_assessment(tmp_path):
    spec=frozen_fixture()
    target=spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='extract_claims' and request['answer_id']==target:
                raise ValueError('fixture failure')
            return super().__call__(request)
    parent=execute_frozen(spec,tmp_path/'parent',provider=First())
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append((request['task'],request['answer_id']))
            return super().__call__(request)
    child=retry_evaluation(spec,parent,tmp_path/'child',stages=['assessment'],
                           answer_ids=[target],provider=Retry())
    assert calls==[('extract_claims',target),('assess_claims',target)]
    assert len(child['inventories'])==2
    assert child['envelopes'][0]['assessments'][0]['status']=='AVAILABLE'
    assert child['envelopes'][1]['assessments']==parent['envelopes'][1]['assessments']


def test_partial_assessment_is_retried_not_cached_as_success(tmp_path):
    spec=frozen_fixture()
    target=spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self,request):
            response=super().__call__(request)
            if request['task']=='assess_claims' and request['answer_id']==target:
                response['payload']['claims'][0]['faithfulness']['evidence']=[
                    {'ref':'unknown','start':0,'end':1,'text':'x'}]
            return response
    parent=execute_frozen(spec,tmp_path/'parent',provider=First())
    assert parent['envelopes'][0]['assessments'][0]['status']=='PARTIAL'
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append((request['task'],request['answer_id']))
            return super().__call__(request)
    child=retry_evaluation(spec,parent,tmp_path/'child',stages=['assessment'],provider=Retry())
    assert calls==[('assess_claims',target)]
    assert child['envelopes'][0]['assessments'][0]['status']=='AVAILABLE'
    assert child['envelopes'][1]['assessments']==parent['envelopes'][1]['assessments']


def test_v2_partial_migrates_valid_dimension_into_v3_request(tmp_path):
    from xiaoan_eval_core.contracts import digest
    from xiaoan_eval_core.configuration import prompt
    spec=frozen_fixture()
    target=spec['rows'][0]['answer_id']
    class First(FixtureProvider):
        def __call__(self, request):
            response=super().__call__(request)
            if request['task']=='assess_claims' and request['answer_id']==target:
                response['payload']['claims'][0]['faithfulness']['evidence']=[
                    {'ref':'unknown','start':0,'end':1,'text':'x'}]
            return response
    parent=execute_frozen(spec,tmp_path/'parent',provider=First())
    prior=parent['envelopes'][0]['assessments'][0]['assessment']['claims'][0]['correctness']
    receipt=next(r for r in parent['stages'] if r['task']=='assess_claims'
                 and r['answer_id']==target and r.get('availability')=='PARTIAL')
    old_request=deepcopy(receipt['request'])
    old_request['validator_version']='frozen/v2'
    old_request['instructions']=prompt('claim-assessment.md')
    old_key=digest(old_request)
    receipt.update(request=old_request,request_digest=old_key,stage_id=old_key)
    seal_complete_results(parent)
    class Retry(FixtureProvider):
        def __call__(self, request):
            response=super().__call__(request)
            if request['task']=='assess_claims' and request['answer_id']==target:
                response['payload']['claims'][0]['correctness']['reason']='new wording'
            return response
    child=retry_evaluation(spec,parent,tmp_path/'child',stages=['assessment'],provider=Retry())
    cell=child['envelopes'][0]['assessments'][0]
    assert cell['status']=='AVAILABLE'
    assert cell['assessment']['claims'][0]['correctness']==prior
    assert cell['assessment']['retry_conflicts']


def test_unavailable_only_preserves_partial_assessment(tmp_path):
    spec=frozen_fixture()
    partial_id,unavailable_id=(row['answer_id'] for row in spec['rows'])
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='assess_claims' and request['answer_id']==unavailable_id:
                raise ValueError('fixture failure')
            response=super().__call__(request)
            if request['task']=='assess_claims' and request['answer_id']==partial_id:
                response['payload']['claims'][0]['faithfulness']['evidence']=[
                    {'ref':'unknown','start':0,'end':1,'text':'x'}]
            return response
    parent=execute_frozen(spec,tmp_path/'parent',provider=First())
    assert [env['assessments'][0]['status'] for env in parent['envelopes']]==['PARTIAL','UNAVAILABLE']
    calls=[]
    class Retry(FixtureProvider):
        def __call__(self,request):
            calls.append((request['task'],request['answer_id']))
            return super().__call__(request)
    child=retry_evaluation(spec,parent,tmp_path/'child',stages=['assessment'],
                           unavailable_only=True,provider=Retry())
    assert calls==[('assess_claims',unavailable_id)]
    assert child['envelopes'][0]['assessments']==parent['envelopes'][0]['assessments']
    assert child['envelopes'][1]['assessments'][0]['status']=='AVAILABLE'


def test_rubric_retry_ignores_conflicting_unselected_partial_assessments(tmp_path):
    spec = frozen_fixture()
    target = spec['rows'][0]['answer_id']

    class First(FixtureProvider):
        def __call__(self, request):
            if request['task'] == 'rubric' and request['answer_id'] == target:
                raise ValueError('rubric failed')
            response = super().__call__(request)
            if request['task'] == 'assess_claims' and request['answer_id'] == target:
                response['payload']['claims'][0]['faithfulness']['evidence'] = [
                    {'ref': 'unknown', 'start': 0, 'end': 1, 'text': 'x'}]
            return response

    parent = execute_frozen(spec, tmp_path / 'parent', provider=First())
    receipt = next(r for r in parent['stages'] if r.get('task') == 'assess_claims'
                   and r.get('answer_id') == target)
    duplicate = deepcopy(receipt)
    duplicate['output']['retry_conflicts'] = ['later_generation']
    parent['stages'].append(duplicate)
    seal_complete_results(parent)
    child = retry_evaluation(spec, parent, tmp_path / 'child', stages=['rubric'],
                             answer_ids=[target], provider=FixtureProvider())
    assert child['envelopes'][0]['rubric'][0]['status'] == 'AVAILABLE'
    assert child['envelopes'][0]['assessments'] == parent['envelopes'][0]['assessments']


def test_import_partial_preserves_source_and_revalidates_before_merge(tmp_path):
    from xiaoan_eval_core.runtime import ResponseStore
    from xiaoan_eval_core.contracts import validate_assessment_parts
    from test_unified_evaluation import spec as core_spec, provider as core_provider
    from xiaoan_eval_core.contracts import extraction_request, assessment_request, validate_inventory
    core=core_spec();row=core['rows'][0]
    source=ResponseStore(tmp_path/'source/checkpoint')
    inventory=source.call(extraction_request(row,core['extractor']),core_provider,validate_inventory)
    request=assessment_request(row,inventory,core['judges'][0])
    def broken(current):
        result=core_provider(current)
        result['claims'][0]['faithfulness']['evidence'][0]['text']='invalid'
        return result
    assert source.call(request,broken,validate_assessment_parts)['status']=='PARTIAL'
    key=source.request_digest(request)
    partial=tmp_path/'source/checkpoint'/f'{key}.partial.json'
    original=partial.read_bytes()
    import_successful_checkpoints(tmp_path/'destination',[tmp_path/'source'])
    imported=tmp_path/'destination/checkpoint'/partial.name
    assert imported.stat().st_ino==partial.stat().st_ino
    recovered=ResponseStore(tmp_path/'destination/checkpoint')
    recovered.partial[key]={'status':'PARTIAL','claims':[],'requirements':[]}
    result=recovered.call(request,core_provider,validate_assessment_parts)
    assert result['status']=='AVAILABLE'
    assert result['claims'][0]['correctness']==source.receipts[-1]['output']['claims'][0]['correctness']
    assert partial.read_bytes()==original
    assert (tmp_path/'destination/checkpoint'/f'{key}.json').exists()
    assert not (tmp_path/'source/checkpoint'/f'{key}.json').exists()

    bad=tmp_path/'bad/checkpoint';bad.mkdir(parents=True)
    (bad/f'{key}.partial.json').write_text(json.dumps({'request_hash':'wrong','response':{'claims':[],'requirements':[]}}))
    with pytest.raises(ValueError,match='Invalid checkpoint'):
        import_successful_checkpoints(tmp_path/'unused',[tmp_path/'bad'])


def test_failed_subject_lane_replaces_only_its_answers(tmp_path):
    plan=build_plan([IDENTITY,{**IDENTITY,'id':'other'}],[IDENTITY],IDENTITY,
                    case_ids=['TC-35'],relevancy_generator=IDENTITY)
    class Subject:
        def __init__(self,fail):self.fail=fail;self.calls=[]
        def start(self,*args):return None
        def turn(self,subject,row,state,history):
            self.calls.append((subject['id'],row['turn']))
            if self.fail and subject['id']=='other':raise ValueError('fixture failure')
            return {'text':'這是離線合成回答。'},state
    first=generate(plan,Subject(True),checkpoint_dir=tmp_path/'first-lanes')
    parent=execute_frozen(first,tmp_path/'parent',provider=FixtureProvider())
    second_provider=Subject(False)
    second=generate(plan,second_provider,checkpoint_dir=tmp_path/'second-lanes',
                    previous_rows=parent['answers'],retry_lanes={('other','TC-35')})
    assert second_provider.calls==[('other',1),('other',2)]
    assert [r['answer_id'] for r in second['rows'] if r['subject_id']=='offline-fixture']==[
        r['answer_id'] for r in parent['answers'] if r['subject_id']=='offline-fixture']
    child=retry_evaluation(second,parent,tmp_path/'child',provider=FixtureProvider())
    validate_complete_results(child)
    assert all(r['status']=='AVAILABLE' for r in child['answers'])
    assert not ({r['answer_id'] for r in child['answers']} &
                {r['answer_id'] for r in parent['answers'] if r['subject_id']=='other'})
    assert all(env['assessments'][0]['status']=='AVAILABLE' for env in child['envelopes'])
    with pytest.raises(ValueError,match='unavailable lane'):
        generate(plan,Subject(False),checkpoint_dir=tmp_path/'third-lanes',
                 previous_rows=child['answers'],retry_lanes={('other','TC-35')})


def test_still_failed_subject_lane_is_sealed_without_new_judge_calls(tmp_path):
    plan=build_plan([IDENTITY],[IDENTITY],IDENTITY,case_ids=['TC-35'],relevancy_generator=IDENTITY)
    class Failing:
        def start(self,*args):return None
        def turn(self,*args):raise ValueError('fixture failure')
    first=generate(plan,Failing(),checkpoint_dir=tmp_path/'first-lanes')
    parent=execute_frozen(first,tmp_path/'parent',provider=FixtureProvider())
    second=generate(plan,Failing(),checkpoint_dir=tmp_path/'second-lanes',
                    previous_rows=parent['answers'],retry_lanes={(IDENTITY['id'],'TC-35')})
    child=retry_evaluation(second,parent,tmp_path/'child',provider=lambda _:pytest.fail('provider called'))
    validate_complete_results(child)
    assert all(row['status']=='UNAVAILABLE' for row in child['answers'])
    assert child['result_generation']!=parent['result_generation']


def test_config_drift_requires_new_cohort(tmp_path):
    import shutil
    from xiaoan_eval_core import configuration
    spec=frozen_fixture()
    parent=execute_frozen(spec,tmp_path/'parent',provider=FixtureProvider())
    original=configuration.ROOT
    candidate=tmp_path/'candidate'
    shutil.copytree(original,candidate)
    prompt=candidate/'prompts/rubric.md'
    prompt.write_text(prompt.read_text()+'\n僅用於離線回歸測試。\n')
    try:
        configuration.configure(candidate)
        with pytest.raises(ValueError,match='Evaluator configuration changed'):
            retry_evaluation(spec,parent,tmp_path/'blocked',provider=lambda _:pytest.fail('provider called'))
        calls=[]
        class Retry(FixtureProvider):
            def __call__(self,request):
                calls.append(request['task'])
                return super().__call__(request)
        child=retry_evaluation(spec,parent,tmp_path/'cohort',provider=Retry(),
                               new_evaluator_cohort=True)
    finally:
        configuration.configure(original)
    assert child['answers']==parent['answers']
    assert child['evaluation_config']!=parent['evaluation_config']
    assert calls.count('rubric')==2
    assert calls.count('extract_claims')==2
    assert calls.count('assess_claims')==2
    assert all(env['rubric'][0]['status']=='AVAILABLE' for env in child['envelopes'])
    with pytest.raises(ValueError,match='every frozen answer'):
        retry_evaluation(spec,parent,tmp_path/'partial',stages=['rubric'],
                         new_evaluator_cohort=True)


def test_runtime_migration_only_accepts_strict_schema_root(tmp_path):
    import hashlib
    from xiaoan_eval.frozen_retry import compatible_schema_update
    from xiaoan_eval_core.configuration import snapshot
    old = snapshot()
    previous = deepcopy(old)
    name = 'schemas/rubric.json'
    schema = json.loads(previous[name]['content'])
    assert schema.pop('additionalProperties') is False
    previous[name]['content'] = json.dumps(schema)
    previous[name]['sha256'] = hashlib.sha256(previous[name]['content'].encode()).hexdigest()
    assert compatible_schema_update(previous, old)
    changed = deepcopy(old)
    changed['prompts/rubric.md']['content'] += '\nchanged'
    assert not compatible_schema_update(previous, changed)
    changed = deepcopy(old)
    changed[name]['content'] = changed[name]['content'].replace('"type": "object"', '"type": "string"', 1)
    assert not compatible_schema_update(previous, changed)


def test_runtime_migration_accepts_only_completed_array_shapes():
    import hashlib
    from xiaoan_eval.frozen_retry import compatible_schema_update
    from xiaoan_eval_core.configuration import snapshot
    current = snapshot()
    previous = deepcopy(current)
    for name in ('claim-extraction', 'claim-assessment', 'relevancy', 'rubric'):
        key = f'schemas/{name}.json'
        schema = json.loads(previous[key]['content'])
        schema.pop('$defs', None)
        for field in schema['properties'].values():
            if field['type'] == 'array':
                field.pop('items')
        previous[key]['content'] = json.dumps(schema)
        previous[key]['sha256'] = hashlib.sha256(previous[key]['content'].encode()).hexdigest()
    assert compatible_schema_update(previous, current)
    changed = deepcopy(current)
    rubric = changed['schemas/rubric.json']
    value = json.loads(rubric['content'])
    value['properties']['dimensions']['type'] = 'string'
    rubric['content'] = json.dumps(value)
    rubric['sha256'] = hashlib.sha256(rubric['content'].encode()).hexdigest()
    assert not compatible_schema_update(previous, changed)


def test_cli_exposes_explicit_retry_selection():
    from xiaoan_eval.cli import _parser
    parser=_parser()
    args=parser.parse_args(['retry-evaluation','--from-results','source/results.json',
                            '--output','new-run','--stages','rubric','--answer-ids','a1',
                            '--judges','judge-1','--execute'])
    assert (args.command,args.stages,args.answer_ids,args.judges,args.execute)==(
        'retry-evaluation',['rubric'],['a1'],['judge-1'],True)
    lanes=parser.parse_args(['retry-subject-lanes','--from-results','source/results.json',
                             '--output','new-run','--lanes','model:TC-35'])
    assert lanes.lanes==['model:TC-35'] and not lanes.execute


def test_cli_dry_run_is_read_only(tmp_path,capsys):
    from xiaoan_eval.cli import main
    from xiaoan_eval.frozen_provider import transport_options
    from xiaoan_eval_core.model_config import read_env
    spec=build_plan([IDENTITY],[IDENTITY],IDENTITY,case_ids=['TC-35'],
                    relevancy_generator=IDENTITY,provider_options=transport_options(read_env()))
    spec['rows']=[freeze_answer(row,{'text':'這是離線合成回答。'},[],generation_id='same')
                  for row in spec['rows']]
    class First(FixtureProvider):
        def __call__(self,request):
            if request['task']=='rubric' and request['answer_id']==spec['rows'][0]['answer_id']:
                raise ValueError('fixture failure')
            return super().__call__(request)
    execute_frozen(spec,tmp_path/'parent',provider=First())
    output=tmp_path/'preview'
    assert main(['retry-evaluation','--from-results',str(tmp_path/'parent/results.json'),
                 '--output',str(output),'--stages','rubric'])==0
    assert json.loads(capsys.readouterr().out)['selected']=={'rubric':1}
    assert not output.exists()
    with pytest.raises(ValueError,match='No unavailable'):
        main(['retry-evaluation','--from-results',str(tmp_path/'parent/results.json'),
              '--output',str(output),'--stages','relevancy'])
