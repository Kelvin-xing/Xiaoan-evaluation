"""Lossless numeric-string repair, audited and revalidated with the frozen evaluator."""
import copy
import hashlib
import json
from pathlib import Path
import retry_failed_judges as retry


def normalize(text):
    value = json.loads(text)
    dims = value.get('dimensions') if isinstance(value, dict) else None
    if not isinstance(dims, dict):
        raise ValueError('dimensions must be an object')
    changed = []
    for name, score in dims.items():
        if isinstance(score, str) and score in {'0','1','2','3'}:
            dims[name] = int(score)
            changed.append(name)
    return json.dumps(value, ensure_ascii=False), changed


def main():
    cases, subjects, judges, rule, target = retry.prepare_retry()
    old = retry.previous.old
    original = [json.loads(l) for l in (retry.SOURCE/'checkpoint.jsonl').open()]
    events = [json.loads(l) for l in target.open()]
    def key(e):
        if e['event']=='cell': return (e['row']['answer_id'],e['row']['judge']['id'])
        if e['event']=='judgement':return (e['answer_id'],old.mm._spec_id(e['judge']))
    original_cells = {key(e):e for e in original if e['event']=='cell'}
    current_cells = {key(e):e for e in events if e['event']=='cell'}
    original_judges = {key(e):e for e in original if e['event']=='judgement'}
    repairs=[];audit=[]
    for k,e in original_judges.items():
        if e['judge']['provider']!='gemini' or original_cells[k]['row']['status']=='PASS': continue
        if current_cells.get(k,{}).get('row',{}).get('status')=='PASS':continue
        text=e['judgement'].get('text','')
        try:normalized,fields=normalize(text)
        except (ValueError,TypeError):continue
        if not fields:continue
        fixed=copy.deepcopy(e);fixed['judgement']['text']=normalized
        result=old.mm._validated_scores(old.mm._provider_response_from_mapping(fixed['judgement']),rule)
        if result[0].status!='PASS':continue
        audit.append({'answer_id':k[0],'judge_id':k[1],'fields':fields,'original_sha256':hashlib.sha256(text.encode()).hexdigest(),'normalized_sha256':hashlib.sha256(normalized.encode()).hexdigest(),'conversion':'exact strings 0/1/2/3 to integers; no score changes'})
        repairs.append(fixed)
    repaired={key(e) for e in repairs}
    # Complete a separate offline snapshot with previous failures. It never replaces the live checkpoint.
    snapshot=[e for e in events if not (e['event'] in {'cell','judgement'} and key(e) in repaired)]
    for k,e in original_cells.items():
        if k not in current_cells and k not in repaired:
            if k in original_judges:snapshot.append(original_judges[k])
            snapshot.append(e)
    snapshot.extend(repairs)
    path=retry.OUT/'repair-offline-checkpoint.jsonl'
    path.write_text(''.join(json.dumps(e,ensure_ascii=False)+'\n' for e in snapshot))
    def no_api(*args):raise AssertionError('Offline repair must never call providers')
    rows=old.mm.run_matrix(cases,subjects,judges,rating_rule=rule,subject_transport=no_api,judge_transport=no_api,checkpoint_path=path,resume=True,retry_unavailable=False,isolate_self_judging=False)
    built=[json.loads(l) for l in path.open()]
    added=[e for e in built[len(snapshot):] if e['event']=='cell' and key(e) in repaired]
    assert len(added)==len(repairs) and all(e['row']['status']=='PASS' for e in added)
    with target.open('a') as f:
        for e in repairs+added:f.write(json.dumps(e,ensure_ascii=False)+'\n')
    (retry.OUT/'format-repair-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2))
    old.mm.write_matrix_workbook(rows,retry.OUT/'progress-results.xlsx')
    print(f'Repaired and validated {len(added)} Gemini cells without API calls.')

if __name__=='__main__':main()
