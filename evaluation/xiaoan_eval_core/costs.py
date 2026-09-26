"""Offline official-list-price estimates for answering models, not API invoices."""
from copy import deepcopy
from decimal import Decimal, InvalidOperation
from datetime import date
from pathlib import Path
import json
from .contracts import digest


def load_catalog(path=None):
    from .configuration import ROOT
    value=json.loads((ROOT/'official-prices.json' if path is None else Path(path)).read_text())
    if value.get('schema_version')!='official-model-prices/v1':raise ValueError('Unsupported pricing catalog')
    keys=set()
    for rate in value['rates']:
        key=(rate['provider'],rate['model'],rate.get('service_tier','standard'),rate.get('pricing_period'))
        if key in keys:raise ValueError('Duplicate price identity')
        keys.add(key)
        if not rate.get('source_url','').startswith('https://') or not rate.get('checked_date'):raise ValueError('Price provenance required')
        for name in ('input_per_million','output_per_million','cached_input_per_million','cache_write_per_million'):
            if name in rate and rate[name] is not None:
                amount=Decimal(str(rate[name]))
                if not amount.is_finite() or amount<0:raise ValueError('Invalid price')
    return value


def _count(value):
    if type(value) is not int or value<0:raise ValueError('INVALID_TOKEN_COUNT')
    return value


def answer_cost(answer,catalog):
    provider={'gpt':'openai','claude':'anthropic','gemini':'google'}.get(answer.get('subject_provider'),answer.get('subject_provider'))
    row={k:answer.get(k) for k in ('answer_id','case_id','turn','subject_id','subject_model')}
    row.update(currency=catalog.get('currency','USD'),basis='official_list_price_estimate',status='UNAVAILABLE',
               total_cost=None,input_cost=None,output_cost=None,reason=None,scope='answer_model_only',notes=[])
    usage=answer.get('usage') or {}
    if usage.get('no_model_call') is True:
        row.update(status='NOT_APPLICABLE',total_cost=0.0,input_cost=0.0,output_cost=0.0,reason='NO_ANSWER_MODEL_CALL')
        return row
    tier=usage.get('service_tier', 'standard')
    tier='standard' if tier in ('default','auto',None) else tier
    rates=[r for r in catalog['rates'] if (r['provider'],r['model'],r.get('service_tier','standard'))==(provider,answer.get('subject_model'),tier)]
    if any(r.get('pricing_period') for r in rates):
        if not usage.get('pricing_period'):
            row['reason']='PRICING_PERIOD_REQUIRED';return row
        rates=[r for r in rates if r.get('pricing_period')==usage['pricing_period']]
    if len(rates)!=1:
        row['reason']='OFFICIAL_PRICE_NOT_FOUND';return row
    rate=rates[0];row['rate']=deepcopy(rate)
    if rate.get('valid_until') and date.today().isoformat()>rate['valid_until']:
        row['reason']='PRICE_CATALOG_EXPIRED';return row
    inp=usage.get('input_tokens',usage.get('input'));out=usage.get('output_tokens',usage.get('output'))
    row.update(input_tokens=inp,output_tokens=out)
    if inp is None or out is None:
        row['reason']='ANSWER_TOKEN_USAGE_MISSING';return row
    try:
        inp,out=_count(inp),_count(out)
        cached=usage.get('cached_input_tokens',usage.get('raw_usage',{}).get('input_tokens_details',{}).get('cached_tokens'))
        written=usage.get('cache_write_tokens')
        if cached is None and written is None:row['notes'].append('快取分類未記錄，按普通輸入費率估算。')
        cached=_count(cached) if cached is not None else 0
        written=_count(written) if written is not None else 0
        if cached+written>inp:raise ValueError('CACHE_TOKENS_EXCEED_INPUT')
        if cached and rate.get('cached_input_per_million') is None:raise ValueError('CACHE_RATE_MISSING')
        if written and rate.get('cache_write_per_million') is None:raise ValueError('CACHE_WRITE_RATE_MISSING')
        long=inp>rate.get('long_context_threshold',10**30)
        im=Decimal(rate.get('long_input_multiplier','1')) if long else Decimal(1)
        om=Decimal(rate.get('long_output_multiplier','1')) if long else Decimal(1)
        plain=Decimal(inp-cached-written)*Decimal(str(rate['input_per_million']))
        read=Decimal(cached)*Decimal(str(rate.get('cached_input_per_million') or 0))
        write=Decimal(written)*Decimal(str(rate.get('cache_write_per_million') or 0))
        if written and rate.get('cache_write_1h_per_million'):
            breakdown=usage.get('raw_usage',{}).get('cache_creation',{})
            hour=breakdown.get('ephemeral_1h_input_tokens')
            short=breakdown.get('ephemeral_5m_input_tokens')
            if hour is None or short is None:raise ValueError('CACHE_WRITE_DURATION_REQUIRED')
            hour,short=_count(hour),_count(short)
            if hour+short!=written:raise ValueError('CACHE_WRITE_BREAKDOWN_MISMATCH')
            write=Decimal(short)*Decimal(str(rate['cache_write_per_million']))+Decimal(hour)*Decimal(str(rate['cache_write_1h_per_million']))
        input_cost=(plain+read+write)*im/Decimal(1000000)
        output_cost=Decimal(out)*Decimal(str(rate['output_per_million']))*om/Decimal(1000000)
    except (ValueError,InvalidOperation) as exc:
        row['reason']=str(exc);return row
    row.update(status='ESTIMATED',input_cost=float(input_cost),output_cost=float(output_cost),total_cost=float(input_cost+output_cost),
               cached_input_tokens=cached,cache_write_tokens=written,context_tier='long' if long else 'short',
               formula='((input-cached-write)*input_rate+cached*cached_rate+write*write_rate)*input_multiplier/1e6 + output*output_rate*output_multiplier/1e6')
    row['notes'].append('官方標準價估算；不包含 Safety／Router、Judge、embedding、報告或未記錄重試，不代表 KaroAPI 帳單。')
    return row


def build_answer_costs(answers,catalog=None):
    catalog=load_catalog() if catalog is None else catalog
    rows=[];seen={}
    for answer in answers:
        aid=answer['answer_id']
        if aid in seen:
            if seen[aid]!=digest(answer):raise ValueError('Conflicting answer identity for cost')
            continue
        seen[aid]=digest(answer);rows.append(answer_cost(answer,catalog))
    summaries=[]
    for subject in sorted({r['subject_id'] for r in rows}):
        group=[r for r in rows if r['subject_id']==subject]
        known=[r for r in group if r['total_cost'] is not None]
        missing=len(group)-len(known)
        subtotal=sum(Decimal(str(r['total_cost'])) for r in known)
        summaries.append({'subject_id':subject,'currency':catalog['currency'],
            'status':'COMPLETE_ESTIMATE' if not missing else 'PARTIAL' if known else 'UNAVAILABLE',
            'known_subtotal':float(subtotal) if known else None,'total_cost':float(subtotal) if not missing else None,
            'planned_answers':len(group),'priced_answers':len(known),'unavailable_answers':missing,
            'scope':'answer_model_only','basis':'official_list_price_estimate'})
    return {'catalog':deepcopy(catalog),'catalog_digest':digest(catalog),'rows':rows,'summary':summaries}
