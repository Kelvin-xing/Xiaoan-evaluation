"""Selective retry never changes a sealed parent or calls unselected stages."""
from copy import deepcopy
import json

import pytest

from test_frozen_end_to_end import FixtureProvider, IDENTITY
from xiaoan_eval.frozen_cli import execute_frozen
from xiaoan_eval.frozen_generation import generate
from xiaoan_eval.frozen_ingress import build_plan, freeze_answer
from xiaoan_eval.frozen_retry import retry_evaluation, extend_judges, import_successful_checkpoints
from xiaoan_eval_core.results import validate_complete_results


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
