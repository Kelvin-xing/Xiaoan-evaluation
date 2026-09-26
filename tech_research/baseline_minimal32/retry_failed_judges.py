"""Bounded retry of failed Judges over frozen answers; preserve the original run."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
import continue_three_judges as previous

SOURCE = previous.OUT
OUT = previous.old.HERE / 'runs/minimal32-three-judges-retry-20260923'

def prepare_retry():
    cases, subjects, judges, rule, source = previous.prepare()
    target = OUT / 'checkpoint.jsonl'
    if not target.exists():
        events = [json.loads(line) for line in source.read_text().splitlines()]
        answers, cells = {}, {}
        for e in events:
            if e['event'] == 'answer':
                answers[e['answer_id']] = e
            elif e['event'] == 'cell':
                r = e['row']; cells[r['answer_id'], r['judge']['id']] = r
        failed = {key for key, r in cells.items()
                  if r['status'] != 'PASS' and answers[key[0]]['answer']['status'] == 'PASS'}
        retained = []
        for e in events:
            key = None
            if e['event'] == 'cell':
                r = e['row']; key = (r['answer_id'], r['judge']['id'])
            elif e['event'] == 'judgement':
                key = (e['answer_id'], previous.old.mm._spec_id(e['judge']))
            if key not in failed:
                retained.append(e)
        assert len(answers) == 480 and len(cells) == 1440
        OUT.mkdir(parents=True)
        shutil.copytree(SOURCE / 'inputs', OUT / 'inputs')
        manifest = json.loads((SOURCE / 'manifest.json').read_text())
        manifest['retry'] = {'parent_run': str(SOURCE), 'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'failed_cells_selected': len(failed), 'timeout_seconds': 300, 'max_retries': 1,
            'subject_calls_enabled': False, 'successful_cells_preserved': sum(r['status']=='PASS' for r in cells.values())}
        (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        with target.open('x') as f:
            for e in retained: f.write(json.dumps(e, ensure_ascii=False)+'\n')
        assert {e['answer_id']:e for e in retained if e['event']=='answer'} == answers
        print(f'Selected {len(failed)} failed Judge cells; all 480 answers unchanged.', flush=True)
    return cases, subjects, judges, rule, target

def main():
    cases, subjects, judges, rule, target = prepare_retry()
    # Set after importing the frozen adapter, which establishes its original defaults.
    os.environ['XIAOAN_PROVIDER_TIMEOUT'] = '300'
    os.environ['GLOBALAI_MAX_RETRIES'] = '1'
    rows = previous.old.mm.run_matrix(cases, subjects, judges, rating_rule=rule,
        subject_transport=previous.no_generation, judge_transport=previous.judge,
        checkpoint_path=target, resume=True, retry_unavailable=False,
        subject_concurrency=32, judge_concurrency=3, max_in_flight=12,
        per_provider_concurrency=2, isolate_self_judging=False)
    previous.old.mm.write_matrix_workbook(rows, OUT / 'results.xlsx')
    (OUT / 'report.md').write_text('# 凍結回答的三 Judge 補評\n\n僅補評原失敗 Judge 格；Qwen/Kimi 不再呼叫。自評保留。\n\n'+previous.old.mm.render_matrix_report(rows))
    subprocess.run([sys.executable, str(previous.old.HERE/'summarize.py'), str(OUT)],check=True)
    print(dict(Counter(r['status'] for r in rows)), flush=True)

if __name__ == '__main__': main()
