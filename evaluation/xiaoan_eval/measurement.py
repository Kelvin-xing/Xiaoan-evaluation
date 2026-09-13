"""Strict, provider-neutral measurements over explicit observations and approved labels."""
from __future__ import annotations
from collections import defaultdict
import hashlib
import json
import math
import random
from statistics import mean
from typing import Mapping

VERSION='evaluation-methods/v3'

def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,allow_nan=False).encode()).hexdigest()

def number(value, name, minimum=None):
    if isinstance(value,bool) or not isinstance(value,(float,int)) or not math.isfinite(value):raise ValueError(f'{name}: finite number required')
    if minimum is not None and value<minimum:raise ValueError(f'{name}: below minimum')
    return value

def text(value,name):
    if not isinstance(value,str) or not value.strip():raise ValueError(f'{name}: nonempty string required')
    return value

def unique(rows,fields):
    seen=set()
    for row in rows:
        key=tuple(row[k] for k in fields)
        if key in seen:raise ValueError(f'duplicate observation: {key}')
        seen.add(key)

def cluster_interval(rows, *, paired=False, seed=0, samples=2000):
    """Equal-weight case means; resample cases, never correlated turns/judges."""
    if type(samples)!=int or not 100<=samples<=100000:raise ValueError('samples must be 100..100000')
    unique(rows,['case_id','unit_id'])
    groups=defaultdict(list);missing=0
    for row in rows:
        case=text(row.get('case_id'),'case_id');text(row.get('unit_id'),'unit_id')
        fields=('baseline','variant') if paired else ('value',)
        if row.get('status','AVAILABLE')!='AVAILABLE' or any(row.get(f) is None for f in fields):missing+=1;continue
        values=[number(row[f],f) for f in fields]
        groups[case].append(values[1]-values[0] if paired else values[0])
    means=[mean(v) for _,v in sorted(groups.items())];ci=None
    if len(means)>1:
        rng=random.Random(seed);boot=sorted(mean(rng.choices(means,k=len(means))) for _ in range(samples))
        ci=[boot[int(.025*samples)],boot[min(samples-1,int(.975*samples))]]
    return {'status':'AVAILABLE' if means else 'UNAVAILABLE','estimate':mean(means) if means else None,
            'ci95':ci,'case_n':len(means),'unit_n':sum(map(len,groups.values())),'missing_unit_n':missing,
            'method':'paired case-macro cluster bootstrap' if paired else 'case-macro cluster bootstrap',
            'seed':seed,'samples':samples,'interval_reason':None if ci else 'fewer than two independent cases'}

def retrieval(row):
    """Closed judged universe; an unjudged result is unknown, never irrelevant."""
    k=row.get('k')
    if type(k)!=int or k<1:raise ValueError('k must be positive integer')
    for key in ('query_id','corpus_version','chunk_version','retriever_version','reranker_version','qrels_version'):
        text(row.get(key),key)
    if row.get('status','AVAILABLE')!='AVAILABLE':return {'status':'UNAVAILABLE','reason':'retrieval execution unavailable'}
    ranks=row.get('ranked_ids');qrels=row.get('qrels')
    if not isinstance(ranks,list) or not isinstance(qrels,dict) or not qrels or row.get('judgments_complete') is not True:
        return {'status':'UNAVAILABLE','reason':'ranked list and complete judged universe required'}
    if any(not isinstance(x,str) or not x for x in ranks) or len(set(ranks))!=len(ranks):raise ValueError('ranked IDs must be unique strings')
    for key,grade in qrels.items():text(key,'qrel ID');number(grade,'relevance',0)
    if any(x not in qrels for x in ranks[:k]):return {'status':'UNAVAILABLE','reason':'unjudged candidate in top k'}
    top=ranks[:k];gold=sum(v>0 for v in qrels.values());hits=0;ap=0;rr=0;dcg=0
    for rank,key in enumerate(top,1):
        grade=qrels[key]
        if grade>0:
            hits+=1;ap+=hits/rank
            if rr==0:rr=1/rank
        dcg+=grade/math.log2(rank+1)
    ideal=sum(grade/math.log2(i+2) for i,grade in enumerate(sorted(qrels.values(),reverse=True)[:k]))
    return {'status':'AVAILABLE','k':k,'returned_n':len(top),'relevant_n':gold,
            'precision_at_k':hits/k,'recall_at_k':hits/gold if gold else None,
            'reciprocal_rank_at_k':rr if gold else None,'ap_at_k':ap/min(gold,k) if gold else None,
            'ndcg_at_k':dcg/ideal if ideal else None,'gain':'linear nonnegative relevance',
            'ap_denominator':'min(total relevant,k)','short_list_policy':'unfilled slots count in precision denominator',
            'input_hash':digest(row)}

def retrieval_batch(rows):
    unique(rows,['query_id']);results=[{'query_id':r['query_id'],**retrieval(r)} for r in rows]
    # Do not pool distinct corpora/configurations into one unexplained score.
    strata=defaultdict(list)
    for source,result in zip(rows,results):
        key=tuple(source[k] for k in ('corpus_version','chunk_version','retriever_version','reranker_version','qrels_version','k'))
        strata[key].append(result)
    aggregates=[]
    for key,group in strata.items():
        metrics={}
        for metric in ('precision_at_k','recall_at_k','reciprocal_rank_at_k','ap_at_k','ndcg_at_k'):
            vals=[r[metric] for r in group if r['status']=='AVAILABLE' and r[metric] is not None]
            metrics[metric]={'mean':mean(vals) if vals else None,'n':len(vals)}
        aggregates.append({'configuration':list(key),'metrics':metrics})
    return {'queries':results,'strata':aggregates,'status':'AVAILABLE' if any(r['status']=='AVAILABLE' for r in results) else 'UNAVAILABLE'}

def verified_outcome(spec, observation):
    """Trust boundary is an injected independent observer, not the subject trace."""
    required=('task_id','observer_id','subject_id','snapshot_id')
    for field in required:text(spec.get(field),field)
    if not isinstance(observation,Mapping) or observation.get('status')!='AVAILABLE':
        return {'status':'UNAVAILABLE','success':None,'reason':'independent observation missing'}
    if spec['observer_id']==spec['subject_id'] or observation.get('observer_id')!=spec['observer_id']:
        raise ValueError('independent observer identity required')
    if observation.get('task_id')!=spec['task_id'] or observation.get('snapshot_id')!=spec['snapshot_id']:
        raise ValueError('outcome binding mismatch')
    checks=spec.get('checks')
    if not isinstance(checks,list) or not checks:raise ValueError('outcome checks required')
    facts=observation.get('facts');
    if not isinstance(facts,dict):raise ValueError('observer facts required')
    unique(checks,['id']);results=[]
    for c in checks:
        text(c.get('id'),'check id');key=text(c.get('fact'),'fact')
        if 'equals' not in c:raise ValueError('explicit expected state required')
        observed=facts.get(key);present=key in facts and observed is not None
        results.append({'id':c['id'],'status':'PASS' if present and type(observed)==type(c['equals']) and observed==c['equals'] else 'FAIL' if present else 'UNAVAILABLE'})
    calls=observation.get('calls');allowed=spec.get('allowed_tools')
    if allowed is not None:
        if not isinstance(allowed,list) or not isinstance(calls,list):results.append({'id':'tool_telemetry','status':'UNAVAILABLE'})
        else:
            unique(calls,['call_id']);seen=set();effects=set()
            for call in calls:
                ident=text(call.get('call_id'),'call_id');auth=call.get('authorized');effect=call.get('unexpected_side_effect')
                status='FAIL' if call.get('name') not in allowed or auth is False or effect is True else 'UNAVAILABLE' if auth is not True or effect is not False or call.get('status') not in {'SUCCESS','FAILED'} else 'PASS' if call['status']=='SUCCESS' else 'FAIL'
                expected_status=spec.get('expected_call_status',{}).get(ident,'SUCCESS')
                if expected_status not in {'SUCCESS','FAILED'}:raise ValueError('invalid expected call status')
                if auth is True and effect is False and call.get('name') in allowed and call.get('status') in {'SUCCESS','FAILED'}:
                    status='PASS' if call['status']==expected_status else 'FAIL'
                effect_id=call.get('side_effect_id')
                if call.get('effect_applied') is True and effect_id is not None:
                    if effect_id in effects:status='FAIL'
                    effects.add(effect_id)
                results.append({'id':ident,'status':status});seen.add(ident)
            order={c['call_id']:i for i,c in enumerate(calls)}
            for a,b in spec.get('precedes',[]):
                results.append({'id':f'order:{a}:{b}','status':'UNAVAILABLE' if a not in order or b not in order else 'PASS' if order[a]<order[b] else 'FAIL'})
    status='FAIL' if any(c['status']=='FAIL' for c in results) else 'UNAVAILABLE' if any(c['status']=='UNAVAILABLE' for c in results) else 'PASS'
    return {'status':status,'success':True if status=='PASS' else False if status=='FAIL' else None,
            'checks':results,'observer_id':spec['observer_id'],'snapshot_id':spec['snapshot_id']}

def run_perturbations(specs,harness):
    """Harness owns isolated sessions and injects faults; no invented actual facts."""
    unique(specs,['id']);results=[]
    for spec in specs:
        text(spec.get('id'),'id');text(spec.get('kind'),'kind')
        controls=spec.get('controls')
        if not isinstance(controls,dict) or not controls:raise ValueError('fixed controls required')
        if not isinstance(spec.get('assertions'),list) or not spec['assertions']:raise ValueError('assertions required')
        outputs={};errors={}
        for arm in ('baseline','variant'):
            try:
                out=harness({'probe_id':spec['id'],'arm':arm,'scenario':spec[arm],
                             'session_id':f'{spec["id"]}:{arm}','control_hash':digest(controls),'controls':controls})
                if not isinstance(out,dict) or out.get('control_hash')!=digest(controls):raise ValueError('harness control mismatch')
                outputs[arm]=out
            except Exception as exc:errors[arm]=f'{type(exc).__name__}: {exc}'
        checks=[]
        for a in spec['assertions']:
            key=a['fact'];op=a['relation']
            if op not in {'same','different','equals'}:raise ValueError('unknown metamorphic relation')
            left=outputs.get('baseline',{});right=outputs.get('variant',{})
            lf=left.get('facts',{});rf=right.get('facts',{})
            missing=left.get('status')!='AVAILABLE' or right.get('status')!='AVAILABLE' or key not in rf or (op!='equals' and key not in lf)
            if op=='equals' and 'expected' not in a:raise ValueError('equals requires expected')
            ok=(rf.get(key)==lf.get(key)) if op=='same' else (rf.get(key)!=lf.get(key)) if op=='different' else (rf.get(key)==a['expected'])
            checks.append({'fact':key,'relation':op,'status':'UNAVAILABLE' if missing else 'PASS' if ok else 'FAIL'})
        status='FAIL' if any(c['status']=='FAIL' for c in checks) else 'UNAVAILABLE' if errors or any(c['status']=='UNAVAILABLE' for c in checks) else 'PASS'
        results.append({'id':spec['id'],'kind':spec['kind'],'status':status,'checks':checks,'errors':errors})
    return {'probes':results,'status':'AVAILABLE' if results else 'UNAVAILABLE','passed':sum(x['status']=='PASS' for x in results),'unavailable':sum(x['status']=='UNAVAILABLE' for x in results)}

def quantile(values,p):
    if not values:return None
    ordered=sorted(values);position=(len(ordered)-1)*p;i=int(position)
    return ordered[i]+(ordered[min(i+1,len(ordered)-1)]-ordered[i])*(position-i)

def online_summary(rows):
    unique(rows,['session_id']);groups=defaultdict(list)
    for r in rows:
        for k in ('session_id','arm','experiment_id','assignment_version'):text(r.get(k),k)
        if r.get('mode') not in {'shadow','controlled'}:raise ValueError('online mode must be shadow/controlled')
        groups[(r['experiment_id'],r['assignment_version'],r['mode'],r['arm'])].append(r)
    output=[]
    for key,group in groups.items():
        item={'stratum':list(key),'sessions':len(group),'metrics':{}}
        for metric in ('task_resolved','handoff_appropriate','exit_success','operational_failure'):
            valid=[]
            for r in group:
                if r.get('observation_complete') is True and type(r.get(metric)) is bool:valid.append(float(r[metric]))
            item['metrics'][metric]={'rate':mean(valid) if valid else None,'observed_n':len(valid),'missing_n':len(group)-len(valid)}
        for metric in ('latency_ms','cost'):
            vals=[number(r[metric],metric,0) for r in group if r.get(metric) is not None]
            item[metric]={'n':len(vals),'missing_n':len(group)-len(vals),'mean':mean(vals) if vals else None,'p50':quantile(vals,.5),'p95':quantile(vals,.95),'p99':quantile(vals,.99)}
        successes=[r['cost'] for r in group if r.get('observation_complete') is True and r.get('task_resolved') is True and r.get('cost') is not None]
        item['successful_session_cost_mean']=mean(successes) if successes else None
        output.append(item)
    return {'strata':output,'interpretation':'Descriptive session outcomes; no causal or real-world safety claim. Shadow outcomes require independent observations; never infer user success from a model answer.'}


def answer_quality(row):
    """Separate context support, independent truth, relevance and required content.

    Semantic labels are supplied by a judge/human and must be calibrated separately.
    This verifies bindings/evidence, not the truth of untrusted evaluator labels.
    """
    from .oracle_judge import validate, summarize
    answer=text(row.get('answer'),'answer')
    context=row.get('context',{});truth=row.get('reference_facts',{})
    for catalogue in (context,truth):
        if not isinstance(catalogue,dict):raise ValueError('evidence catalogue must be a mapping')
        for k,v in catalogue.items():text(k,'evidence ID');text(v,'evidence text')
    for k in ('context_version','truth_version','judge_version','question'):text(row.get(k),k)
    binding=digest({k:row[k] for k in ('answer','question','context','reference_facts','context_version','truth_version')})
    assessment=row.get('assessment')
    if not isinstance(assessment,dict) or assessment.get('binding')!=binding:return {'status':'UNAVAILABLE','reason':'answer assessment missing or stale','binding':binding}
    claims=assessment.get('claims')
    if not isinstance(claims,list):raise ValueError('claim inventory required')
    unique(claims,['id']);counts={key:{'positive':0,'known':0,'unknown':0} for key in ('faithfulness','correctness')}
    for claim in claims:
        start,end=claim.get('start'),claim.get('end')
        if type(start)!=int or type(end)!=int or not 0<=start<end<=len(answer) or answer[start:end]!=claim.get('quote'):raise ValueError('invalid answer claim span')
        for key,catalogue in (('faithfulness',context),('correctness',truth)):
            relation=claim.get(key);refs=claim.get(key+'_evidence')
            if relation not in {'SUPPORTED','CONTRADICTED','UNKNOWN','NOT_APPLICABLE'}:raise ValueError('invalid evidence relation')
            if not isinstance(refs,list):raise ValueError('evidence spans required')
            for span in refs:
                content=catalogue.get(span.get('ref'));a,b=span.get('start'),span.get('end')
                if not isinstance(content,str) or type(a)!=int or type(b)!=int or not 0<=a<b<=len(content) or content[a:b]!=span.get('quote'):raise ValueError('invalid reference span')
            if relation in {'SUPPORTED','CONTRADICTED'} and not refs:raise ValueError('semantic judgment requires evidence')
            if relation=='NOT_APPLICABLE':continue
            if relation=='UNKNOWN':counts[key]['unknown']+=1;continue
            counts[key]['known']+=1;counts[key]['positive']+=relation=='SUPPORTED'
    relevance=assessment.get('relevance')
    if relevance not in {'RELEVANT','IRRELEVANT','UNCERTAIN'}:raise ValueError('explicit relevance label required')
    text(assessment.get('relevance_reason'),'relevance_reason')
    if row.get('oracle_request') and (row['oracle_request'].get('assistant_answer')!=answer or row['oracle_request'].get('redacted_user_input')!=row['question']):raise ValueError('completeness request must bind same answer and question')
    complete=summarize([validate(row.get('oracle_assessment'),row['oracle_request'])]) if row.get('oracle_request') else {'status':'UNAVAILABLE'}
    return {'status':'AVAILABLE','binding':binding,'claim_n':len(claims),
            **{key:{**v,'rate':v['positive']/v['known'] if v['known'] else None} for key,v in counts.items()},
            'relevance':{'value':True if relevance=='RELEVANT' else False if relevance=='IRRELEVANT' else None,'reason':assessment['relevance_reason']},
            'completeness':complete,'inventory_complete':assessment.get('inventory_complete') is True,
            'limitation':'Claim extraction coverage must be measured against an independent human inventory; spans do not prove semantic correctness.'}
