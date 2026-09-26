from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from threading import Lock
import time
import pytest
from xiaoan_eval_core.contracts import digest
from xiaoan_eval_core.runtime import ResponseStore, evaluate
from xiaoan_eval_core.rubric import evaluate_rubric, RubricContractError
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval_core.configuration import ROOT
from test_unified_evaluation import spec, provider


def test_remote_protocol_disconnect_is_bounded_retry(tmp_path):
    import httpx
    store=ResponseStore(tmp_path,max_attempts=2)
    calls=[]
    def invoke(request):
        calls.append(request)
        if len(calls)==1: raise httpx.RemoteProtocolError('disconnect')
        return {'value':1}
    assert store.call({'task':'network'},invoke,lambda value,request:value)=={'value':1}
    assert len(calls)==2
    assert store.receipts[0]['attempts'][0]['retryable'] is True


def test_http_status_retry_records_only_status_and_bounded_retry_after(tmp_path,monkeypatch):
    import httpx
    from xiaoan_eval_core import runtime
    waits=[];monkeypatch.setattr(runtime.time,'sleep',waits.append)
    request=httpx.Request('POST','https://example.invalid/private?key=secret')
    store=ResponseStore(tmp_path/'rate',max_attempts=2)
    calls=[]
    def throttled(_):
        calls.append(True)
        if len(calls)==1:
            response=httpx.Response(429,request=request,headers={'Retry-After':'120'},text='sensitive upstream error')
            raise httpx.HTTPStatusError('sensitive upstream error',request=request,response=response)
        return {'ok':True}
    assert store.call({'task':'test'},throttled,lambda value,_:value)=={'ok':True}
    assert len(calls)==2 and waits==[30.0]
    first=store.receipts[0]['attempts'][0]
    assert (first['http_status_code'],first['retryable'],first['retry_after_seconds'])==(429,True,30.0)
    journal=''.join(p.read_text() for p in (tmp_path/'rate').glob('*.events.jsonl'))
    assert 'secret' not in journal and 'sensitive' not in journal

    rejected=ResponseStore(tmp_path/'region',max_attempts=3)
    calls.clear()
    def unsupported(_):
        calls.append(True)
        response=httpx.Response(400,request=request,text='region blocked')
        raise httpx.HTTPStatusError('region blocked',request=request,response=response)
    with pytest.raises(httpx.HTTPStatusError):
        rejected.call({'task':'test'},unsupported,lambda value,_:value)
    assert len(calls)==1 and rejected.receipts[0]['attempts'][0]['http_status_code']==400
    assert rejected.receipts[0]['attempts'][0]['retryable'] is False


def test_barrier_parallel_limits_and_success_cache(tmp_path):
    s = spec()
    s['rows'].append({**deepcopy(s['rows'][0]), 'answer_id':'a2', 'turn':2, 'answer':'A. B. D.'})
    s['planned_turns']['case-1'] = [1,2]
    active=0; peak=0; finished=[]; lock=Lock()
    def wrapped(request):
        nonlocal active,peak
        with lock:
            active+=1; peak=max(peak,active)
            if request['task']=='assess_claims':
                assert len(finished)==2
        time.sleep(.01)
        result=provider(request)
        with lock:
            active-=1
            if request['task']=='extract_claims': finished.append(request['binding'])
        return {'payload':result,'usage':{'input_tokens':10,'output_tokens':5}}
    result=evaluate(s,wrapped,checkpoint_dir=tmp_path)
    assert all(c['status']=='AVAILABLE' for c in result['cells'])
    assert 1 < peak <= 2
    recovered=evaluate(s,lambda _:pytest.fail('cache miss'),checkpoint_dir=tmp_path)
    assert recovered['cells']==result['cells']
    assert all(r['incremental_usage']['input_tokens']==0 for r in recovered['receipts'])
    assert not any('primary_eligible' in c or 'same_model_family' in c for c in result['cells'])


def test_partial_dimension_preserves_correctness_and_requirements():
    def faulty(request):
        result=provider(request)
        if request['task']=='assess_claims':
            result['claims'][0]['faithfulness']['evidence'][0]['text']='bad'
        return result
    result=evaluate(spec(),faulty)
    cell=result['cells'][0]
    assert cell['status']=='PARTIAL'
    assert cell['assessment']['dimension_status']=={'faithfulness':'UNAVAILABLE','correctness':'AVAILABLE'}
    assert cell['requirements']['release_gate']=='PASS'
    assert cell['assessment']['claims'][0]['correctness']['verdict']=='UNKNOWN'


def test_missing_context_keeps_other_axes():
    s=spec();s['rows'][0]['context_capture']='UNAVAILABLE';s['rows'][0]['context']=[]
    def absent(request):
        result=provider(request)
        if request['task']=='assess_claims':
            for claim in result['claims'][:2]:
                claim['faithfulness']={'verdict':'UNKNOWN','reason':'snapshot missing','evidence':[]}
        return result
    result=evaluate(s,absent)
    assert result['cells'][0]['status']=='AVAILABLE'
    assert result['cells'][0]['metrics']['faithfulness']['unknown_n']==2
    assert result['cells'][0]['metrics']['evidence_citation_coverage']['status']=='UNAVAILABLE'


def test_store_inflight_dedup_and_failure_retry(tmp_path):
    store=ResponseStore(tmp_path);count=0
    def call(request):
        nonlocal count
        count+=1;time.sleep(.01)
        return {'value':1}
    with ThreadPoolExecutor(4) as pool:
        values=list(pool.map(lambda _:store.call({'task':'test'},call,lambda v,r:v),range(4)))
    assert count==1 and values==[{'value':1}]*4
    assert sum(len(r['attempts']) for r in store.receipts)==1


def test_rubric_redline_keeps_scores_requires_reasons():
    rule=load_rating_rule(ROOT/'rating-rule.yml')
    payload={'dimensions':[{'module':m.name,'score':3,'reason':'supported','supporting_evidence':[],'deduction_evidence':[]} for m in rule.modules],
             'red_lines':[{'id':r.id,'triggered':True,'reason':'violation','evidence':[]} for r in rule.red_lines]}
    result=evaluate_rubric({},payload,rule)
    assert result['weighted_total']==pytest.approx(3)
    assert result['gate']=='FAIL' and result['dimension_details'][0]['reason']=='supported'
    del payload['dimensions'][0]['reason']
    with pytest.raises(RubricContractError):evaluate_rubric({},payload,rule)


def test_partial_retry_preserves_valid_axis_and_records_conflict(tmp_path):
    def broken(request):
        value=provider(request)
        if request['task']=='assess_claims':
            value['claims'][0]['faithfulness']['evidence'][0]['text']='invalid'
        return value
    first=evaluate(spec(),broken,checkpoint_dir=tmp_path)
    assert first['cells'][0]['status']=='PARTIAL'
    def conflicting(request):
        value=provider(request)
        if request['task']=='assess_claims':
            value['claims'][0]['correctness']['reason']='new wording changes saved judgement'
        return value
    second=evaluate(spec(),conflicting,checkpoint_dir=tmp_path)
    assert second['cells'][0]['status']=='PARTIAL'
    assert second['cells'][0]['assessment']['retry_conflicts']
    assert second['cells'][0]['assessment']['claims'][0]['correctness']==first['cells'][0]['assessment']['claims'][0]['correctness']
    third=evaluate(spec(),provider,checkpoint_dir=tmp_path)
    assert third['cells'][0]['status']=='AVAILABLE'


def test_interrupted_provider_receipt_is_unknown_not_exactly_once(tmp_path):
    store=ResponseStore(tmp_path)
    key=digest({'task':'test'})
    store.journal(key, {'attempt_id':'interrupted','execution_status':'RUNNING','usage':None})
    store.call({'task':'test'},lambda _: {'ok':True},lambda v,r:v)
    prior=store.receipts[0]['historical_interrupted_attempts'][0]
    assert prior['error']=='INTERRUPTED_RESULT_UNKNOWN'
    assert prior['usage'] is None


def test_transport_config_changes_cache_key(tmp_path):
    calls=[]
    for value in ('low','high'):
        store=ResponseStore(tmp_path, provider_options={'XIAOAN_REASONING_EFFORT':value})
        store.call({'task':'test'},lambda request: calls.append(request) or {'ok':True},lambda v,r:v)
    assert len(calls)==2
    assert calls[0]['provider_options']!=calls[1]['provider_options']


def test_candidate_config_reuses_answers_but_changes_judge_requests(tmp_path):
    import shutil
    from xiaoan_eval_core import configuration
    from xiaoan_eval_core.orchestration import run_orchestration
    from test_orchestration import rubric_payload
    baseline = configuration.ROOT
    source = spec()
    source['branches'] = ['rubric']
    source['rows'][0]['row_digest'] = digest(source['rows'][0])
    source['manifest'] = {'evaluator_config': configuration.snapshot(), 'manifest_digest':'frozen-generation'}
    original = deepcopy(source)
    first = run_orchestration(source, rubric_provider=lambda request:rubric_payload(), checkpoint_dir=tmp_path/'calls')
    candidate = tmp_path/'candidate'
    shutil.copytree(baseline,candidate)
    prompt_path = candidate/'prompts/rubric.md'
    prompt_path.write_text(prompt_path.read_text()+'\n特別檢查使用者限制。\n')
    try:
        configuration.configure(candidate)
        with pytest.raises(ValueError,match='evaluation snapshot'):
            run_orchestration(source,rubric_provider=lambda request:rubric_payload())
        source['evaluation_config'] = configuration.snapshot()
        second=run_orchestration(source,rubric_provider=lambda request:rubric_payload(),checkpoint_dir=tmp_path/'calls')
    finally:
        configuration.configure(baseline)
    assert source['rows']==original['rows']
    assert first['answers']==second['answers']
    assert first['manifest']==second['manifest']==original['manifest']
    assert first['evaluation_config']!=second['evaluation_config']
    assert {s['request_digest'] for s in first['stages']} != {s['request_digest'] for s in second['stages']}
    assert not any(s.get('reused_from') for s in second['stages'])
