"""Offline exact-span validation for replayed attribution responses."""
from copy import deepcopy
import json
from .attribution_judge import parse_attribution_response


def validate_replay(raw, answer, catalog, judge_version):
    payload=deepcopy(json.loads(raw));corrections=[]
    texts={e['ref']:e['content'] for e in catalog}
    def locate(span, content, location):
        if not isinstance(span,dict) or type(span.get('start')) is not int or type(span.get('end')) is not int:
            raise ValueError('invalid span shape')
        q=span.get('text');a=span['start'];b=span['end']
        if not isinstance(q,str) or not q:raise ValueError('empty span')
        if 0<=a<b<=len(content) and content[a:b]==q:return
        start=content.find(q)
        if start<0 or content.find(q,start+1)>=0:raise ValueError('quote missing or ambiguous')
        corrections.append({'location':location,'original_start':a,'original_end':b,'start':start,'end':start+len(q),'method':'unique_exact_quote'})
        span.update(start=start,end=start+len(q))
    for i,c in enumerate(payload.get('claims',[])):
        locate(c['answer_span'],answer,f'claims.{i}.answer_span')
        for j,r in enumerate(c['relations']):
            if r.get('evidence_span') is not None:
                locate(r['evidence_span'],texts[r['evidence_ref']],f'claims.{i}.relations.{j}')
    for i,p in enumerate(payload.get('policies',[])):
        for j,s in enumerate(p['answer_spans']):locate(s,answer,f'policies.{i}.answer_spans.{j}')
    result=parse_attribution_response(json.dumps(payload,ensure_ascii=False),answer,catalog,judge_version=judge_version)
    if not result.claims:raise ValueError('nonempty answer requires claim coverage')
    expected_policies={(e['ref'],p) for e in catalog for p in e.get('policy_ids',[])}
    actual_policies={(p.evidence_ref,p.policy_id) for p in result.policies}
    if expected_policies!=actual_policies:raise ValueError('policy coverage incomplete or invalid')
    return result,corrections
