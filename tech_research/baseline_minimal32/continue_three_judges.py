"""Score frozen answers with Claude/GPT/Gemini only; no subject API calls."""
import json
import hashlib
import shutil
from collections import Counter
from pathlib import Path
import continue_current as old

OUT = old.HERE / 'runs/minimal32-three-judges-20260921'
ALLOWED = {'claude', 'gpt', 'gemini'}


def no_generation(*args):
    raise RuntimeError('Subject generation disabled: preserve existing answers only')


def judge(spec, prompt):
    if spec.provider not in ALLOWED:
        raise RuntimeError('Provider cancelled by user')
    return old.base.judge_transport(spec, prompt)


def prepare():
    manifest = json.loads((old.OUT / 'manifest.json').read_text())
    manifest['judges'] = [j for j in manifest['judges'] if j['provider'] in ALLOWED]
    manifest['judge_calls_upper_bound'] = 1440
    manifest['parent_run'] = str(old.OUT)
    manifest['mode'] = 'frozen-answers-three-judges/v1'
    rule = old.load_rating_rule(old.OUT / 'inputs/ratings rule.yml')
    cases = [old.load_case(old.OUT / 'inputs' / f'{cid}.yaml', rule).case for cid in manifest['cases']]
    subjects = [old.mm.ModelSpec(**s) for s in manifest['subjects']]
    judges = [old.mm.ModelSpec(**j) for j in manifest['judges']]
    digest = old.contract_hash(cases, subjects, judges, rule)
    checkpoint = OUT / 'checkpoint.jsonl'
    if not checkpoint.exists():
        OUT.mkdir(exist_ok=True)
        shutil.copytree(old.OUT / 'inputs', OUT / 'inputs', dirs_exist_ok=True)
        answers, judgments, cells = {}, {}, {}
        source = old.OUT / 'checkpoint.jsonl'
        for line in source.read_text().splitlines():
            e = json.loads(line)
            if e['event'] == 'answer':
                aid = e['answer_id']
                answers[aid] = e
                judgments = {k: v for k, v in judgments.items() if k[0] != aid}
                cells = {k: v for k, v in cells.items() if k[0] != aid}
            elif e['event'] == 'judgement' and e['judge']['provider'] in ALLOWED:
                judgments[e['answer_id'], old.mm._spec_id(e['judge'])] = e
            elif e['event'] == 'cell' and e['row']['judge']['provider'] in ALLOWED:
                row = e['row']
                cells[row['answer_id'], row['judge']['id']] = e
        assert len(answers) == 480
        valid = {k for k, e in cells.items() if e['row']['status'] == 'PASS'}
        # Imported judgments may not yet have a cell. Revalidate them locally.
        for k, e in judgments.items():
            response = old.mm._provider_response_from_mapping(e['judgement'])
            if old.mm._validated_scores(response, rule)[0].status == 'PASS':
                valid.add(k)
        events = [*answers.values(), *[e for k, e in judgments.items() if k in valid],
                  *[e for k, e in cells.items() if k in valid and e['row']['status'] == 'PASS']]
        with checkpoint.open('x') as stream:
            for e in events:
                stream.write(json.dumps({**e, 'contract_sha256': digest,
                    'imported_from_contract': e['contract_sha256']}, ensure_ascii=False) + '\n')
        manifest['migration'] = {'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
            'answers_preserved': len(answers), 'validated_judgments_reused': len(valid),
            'cancelled_providers': ['qwen', 'kimi'], 'subject_calls_enabled': False}
        (OUT / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    return cases, subjects, judges, rule, checkpoint


def main():
    cases, subjects, judges, rule, checkpoint = prepare()
    print('Continuing only Claude/GPT/Gemini Judges; all 480 answer records frozen.', flush=True)
    rows = old.mm.run_matrix(cases, subjects, judges, rating_rule=rule,
        subject_transport=no_generation, judge_transport=judge, checkpoint_path=checkpoint,
        resume=True, retry_unavailable=False, subject_concurrency=12, judge_concurrency=3,
        max_in_flight=12, per_provider_concurrency=4, isolate_self_judging=False)
    old.mm.write_matrix_workbook(rows, OUT / 'results.xlsx')
    note = '# 現有回答 × 三個 Judge\n\nQwen/Kimi 不再呼叫；現有回答保留，缺失回答不重試。自評保留。原五Judge歷史留在parent_run。\n\n'
    (OUT / 'report.md').write_text(note + old.mm.render_matrix_report(rows))
    print(json.dumps(dict(Counter(r['status'] for r in rows))), flush=True)
    import subprocess, sys
    subprocess.run([sys.executable, str(old.HERE / 'summarize.py'), str(OUT)], check=True)


if __name__ == '__main__':
    main()
