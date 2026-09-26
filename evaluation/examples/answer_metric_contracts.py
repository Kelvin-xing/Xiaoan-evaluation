"""Offline answer metric math. No provider access; callers must bind validated evidence."""
import hashlib
import json
import math


def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def faithfulness_counts(claims):
    """Strict per-claim entailment proxy from existing validated attribution.

    PARTIAL-only is not full entailment, including multiple PARTIAL relations.
    This cannot establish the completeness or atomicity of the extraction.
    """
    counts={'entailed':0,'partial_only':0,'contradicted':0,'not_supported':0}
    seen=set()
    for c in claims:
        if c['claim_id'] in seen:raise ValueError('duplicate claim ID')
        seen.add(c['claim_id'])
        rel={r['relation'] for r in c['relations']}
        if not rel or not rel <= {'ENTAILS','PARTIAL','CONTRADICTS','CONTEXT_ONLY','UNSUPPORTED'}:raise ValueError('invalid relations')
        if 'CONTRADICTS' in rel and rel & {'ENTAILS','PARTIAL'}:raise ValueError('conflicting verdicts')
        if 'UNSUPPORTED' in rel and len(rel)>1:raise ValueError('conflicting unsupported verdict')
        for r in c['relations']:
            if r['relation']!='UNSUPPORTED' and (not r.get('evidence_ref') or not r.get('evidence_span')):raise ValueError('evidence required')
        k='entailed' if 'ENTAILS' in rel else 'partial_only' if 'PARTIAL' in rel else 'contradicted' if 'CONTRADICTS' in rel else 'not_supported'
        counts[k]+=1
    n=sum(counts.values())
    return {**counts,'total':n,'score':counts['entailed']/n if n else None,'status':'AVAILABLE_PROXY' if n else 'NOT_APPLICABLE_NO_CLAIMS'}


def cosine(left,right):
    if not isinstance(left,list) or not isinstance(right,list) or not left or len(left)!=len(right):raise ValueError('invalid embedding dimensions')
    if any(type(x) not in (int,float) or not math.isfinite(x) for x in left+right):raise ValueError('non-finite embedding')
    # Scale before norm calculation to avoid overflow.
    lm=max(abs(x) for x in left);rm=max(abs(x) for x in right)
    if not lm or not rm:raise ValueError('zero embedding')
    a=[x/lm for x in left];b=[x/rm for x in right]
    value=math.fsum(x*y for x,y in zip(a,b))/(math.sqrt(math.fsum(x*x for x in a))*math.sqrt(math.fsum(x*x for x in b)))
    return min(1.,max(-1.,value))


def answer_relevancy(task,generation,embeddings):
    """Mean cosine for exactly N reverse questions; no rescale or refusal penalty.

    task includes original question + answer + generator contract. Generator only
    receives task['generation_input']; source question never goes to that call.
    embeddings = {'model_id':..., 'revision':..., 'vectors': {exact_text: [..]}}.
    """
    binding=digest(task)
    if not generation or generation.get('binding')!=binding:
        return {'status':'UNAVAILABLE','reason':'GENERATION_MISSING_OR_STALE','score':None,'binding':binding}
    qs=generation.get('questions');n=task['n']
    if type(n)!=int or n<1:raise ValueError('positive N required')
    if not isinstance(qs,list) or len(qs)!=n or any(not isinstance(q,str) or not q.strip() for q in qs):
        return {'status':'UNAVAILABLE','reason':'INVALID_QUESTION_COUNT_OR_TEXT','score':None,'binding':binding}
    if not embeddings or not embeddings.get('model_id') or not embeddings.get('revision'):
        return {'status':'UNAVAILABLE','reason':'EMBEDDING_CONFIG_MISSING','score':None,'binding':binding}
    vectors=embeddings.get('vectors',{})
    texts=[task['original_question'],*qs]
    if any(t not in vectors for t in texts):
        return {'status':'UNAVAILABLE','reason':'EMBEDDING_MISSING','score':None,'binding':binding}
    try: similarities=[cosine(vectors[texts[0]],vectors[q]) for q in qs]
    except ValueError as e:return {'status':'UNAVAILABLE','reason':str(e),'score':None,'binding':binding}
    return {'status':'AVAILABLE','score':math.fsum(similarities)/n,'n':n,'similarities':similarities,'duplicate_questions':n-len(set(qs)),'binding':binding,'embedding_model':embeddings['model_id'],'embedding_revision':embeddings['revision'],'interpretation':'Semantic alignment proxy, not completeness, concision or truth.'}
