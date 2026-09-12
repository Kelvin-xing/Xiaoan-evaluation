"""Offline diagnostic probes; no provider calls and no repository changes.

Run once per project: python THIS_FILE /absolute/path/to/evaluation[_multimodels]
Synthetic data only. Prints observed behavior, not desired assertions.
"""
from pathlib import Path
import json
import os
import sys
import tempfile

project = Path(sys.argv[1]).resolve()
os.chdir(project)
sys.path.insert(0, str(project))
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval.config import load_evaluator_config
from xiaoan_eval.cases import TestCase, TestTurn, ExpectedOutcome, OracleProvenance, MemoryCheckpoint
from xiaoan_eval.runner import CaseRunResult, TurnRunResult
from xiaoan_eval.pipeline import EvaluationPipeline
from xiaoan_eval.judge_client import JudgeClient
from xiaoan_eval.report_model import build_report_model
from xiaoan_eval.metrics import evaluate_memory_checkpoint
from xiaoan_eval.scoring import score_case, score_case_fact, TurnQuality, TurnDimensionFact
from xiaoan_eval.v3_metrics import summarize_v3
from xiaoan_eval.methodology_metrics import _ordinal_alpha, _nominal_alpha, run_pairwise_pass

rule = load_rating_rule(project / 'ratings rule.yml')
config = load_evaluator_config(project / 'evaluator-config.yml')
case = TestCase('2.0', 'TC-01', 'synthetic audit', ('行动赋权',),
                (TestTurn(1, 'synthetic input', ExpectedOutcome(route_ids=('baseline',))),),
                OracleProvenance('synthetic', 'approved', 'audit', '2026-09-13'))
trace = {'safety': {'level': 'baseline'}, 'route': {'id': 'baseline'},
         'ground': {'resolved_refs': []}, 'guard': {'passed': True}, 'state': {},
         'timings': dict(ttft_ms=1, first_guarded_delta_ms=2, router_ms=1, ground_ms=0,
                         generation_ms=4, total_ms=5), 'tokens': {'input': 3, 'output': 4}}

class Runner:
    def __init__(self, fail=False): self.fail = fail
    def run_cases(self, cases):
        return [CaseRunResult('TC-01', 'error' if self.fail else 'pass', 'synthetic',
                [TurnRunResult(1, None if self.fail else 'synthetic answer', trace,
                               'synthetic timeout' if self.fail else None)])]

def judge(_):
    return json.dumps({'red_lines': [dict(id=r.id, triggered=False, evidence=[], uncertainty='low') for r in rule.red_lines],
        'dimensions': [dict(module=m.name, score=1, supporting_evidence=['trace:T1'], deduction_evidence=[], uncertainty='low') for m in rule.modules],
        'legal_claims': [], 'faithfulness_claims': []})

out = {'project': project.name}
for fail in (False, True):
    record = EvaluationPipeline(Runner(fail), rule, config,
        primary_judge=JudgeClient(judge, rule), egress_validator=lambda _: True,
        authoritative_context_provider=lambda *_: {'refs': []}).evaluate_case(case)
    report = build_report_model([record])
    out['failed_run' if fail else 'low_quality_run'] = {
        'status': record['status'], 'quality': record['quality']['weighted_total'],
        'overview': [dict(x) for x in report.overview if x.get('metric') in ('Overall score', 'Evaluation verdict')]}

checkpoint = MemoryCheckpoint(1, ('secret',), 'must not use', 'not_use')
out['not_use_checkpoint'] = evaluate_memory_checkpoint(checkpoint,
    {'state': {'memory_facts': ['secret'], 'memory_used': False}}).status.value
obs = {'oracle_approved': True, 'expected': {'route_ids': [], 'response_oracle': {
    'required_claims': ['required'], 'goal_completed': False}},
    'actual': {'route_id': 'baseline', 'goal_completed': False},
    'judge': {'faithfulness_claims': [{'claim': 'required', 'supported': False}]}}
v3 = summarize_v3([{'pipeline': {'observations': [obs]}}])
out['v3'] = {key: v3[key] for key in ('claims', 'route', 'agent')}
out['constant_alpha'] = {'ordinal': _ordinal_alpha([{'a': 3, 'b': 3}]*3),
                         'nominal': _nominal_alpha([{'a': False, 'b': False}]*3)}
scores = {m.name: 3 if m.name == '行动赋权' else 0 for m in rule.modules}
out['dynamic_weighted_score'] = score_case(rule, [TurnQuality(scores)], ['行动赋权']).weighted_total
out['focused_case_fact'] = score_case_fact(case_id='TC-01', expected_turns=[1], quality_focus=['行动赋权'],
    dimension_weights={m.name: m.weight for m in rule.modules},
    turn_facts=[TurnDimensionFact('TC-01', 1, k, 'AVAILABLE', v) for k,v in scores.items()]).value
requests = []
run_pairwise_pass([dict(answer_id=x, case_id='TC-01', turn=1, answer=x, user='user context', status='PASS') for x in ('a','b')],
    [('a','b')], ['j'], lambda req: requests.append(req) or {'winner': 'TIE', 'rationale': 'synthetic'},
    controls={'rubric': 'synthetic'}, seed='audit')
out['pairwise_request_fields'] = sorted(requests[0])

if project.name == 'evaluation_multimodels':
    from xiaoan_eval.multimodel import weighted_score, _memory_observations, render_matrix_report, write_matrix_workbook
    from openpyxl import load_workbook
    out['matrix_base_weighted_score'] = weighted_score(scores, rule)
    out['matrix_missing_memory'] = {typ: _memory_observations(
        {'memory_checkpoints': [{'after_turn': 1, 'facts': ['x'], 'type': typ}]}, 1, {'state': {}})[0]['status']
        for typ in ('use', 'isolation', 'retrieve')}
    rows = [dict(answer_id=f'a{i}', case_id='TC-01', turn=i+1, subject={'id':'s'}, judge={'id':'j'},
        scores={'synthetic': score}, weighted_score=score, status='PASS', primary_eligible=True,
        self_judging=False, answer={'text':'synthetic'}, judgement={}, attribution={'status':'NOT_RUN'})
        for i, score in enumerate([0, 0, 3])]
    markdown = render_matrix_report(rows)
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory)/'probe.xlsx'
        write_matrix_workbook(rows, path)
        wb = load_workbook(path, data_only=True)
        out['matrix_rendering'] = {'markdown_row': next(x for x in markdown.splitlines() if x.startswith('| s |')),
                                   'excel_B2': wb['Matrix']['B2'].value}
        wb.close()

print(json.dumps(out, ensure_ascii=False, indent=2))
