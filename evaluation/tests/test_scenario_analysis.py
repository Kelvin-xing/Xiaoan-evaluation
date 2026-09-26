import copy
import json
from types import SimpleNamespace

from xiaoan_eval.scenario_analysis import build_analysis, binding, digest, attach_to_model, render_analysis
from xiaoan_eval.report_model import build_report_model, build_model_from_rows
from xiaoan_eval.workbook import write_workbook, read_workbook
from xiaoan_eval.cli import _parser, main


def record():
    answer = 'alpha beta'
    claims = [
        {'claim_id': 'c1', 'kind': 'FACTUAL', 'answer_span': {'start': 0, 'end': 5, 'text': 'alpha'},
         'relations': [{'relation': 'ENTAILS', 'layer': 'CAPSULE', 'evidence_ref': 'cap'},
                       {'relation': 'PARTIAL', 'layer': 'SOURCE', 'evidence_ref': 'src'}]},
        {'claim_id': 'c2', 'kind': 'SUPPORTIVE', 'answer_span': {'start': 6, 'end': 10, 'text': 'beta'},
         'relations': [{'relation': 'PARTIAL', 'layer': 'SOURCE', 'evidence_ref': 'src'}]},
    ]
    return {'case_id': 'TC-01', 'status': 'PASS', 'performance': {}, 'failure': {}, 'quality': {'weighted_total': 2},
            'safety': {'hard_gate_passed': True, 'red_lines': []}, 'review': {},
            'conversation': {'turns': [{'turn': 1, 'user_input': 'help', 'assistant_response': answer}]},
            'pipeline': {'planned_turns': [{'turn': 1, 'user_input': 'help'}, {'turn': 2, 'user_input': 'next'}],
                         'turns': [{'route_acceptance': {'status': 'fail', 'score': 0}}],
                         'turn_traces': [{'turn': 1, 'trace': {'models': {'response': 'model-a'}, 'route': {'id': 'n1'},
                                                              'effective_context_snapshot': {'id': 'context-a'}}}],
                         'observations': [{'turn': 1, 'judge': {'faithfulness_claims': [{'claim': 'alpha', 'supported': True}],
                                                               'oracle_assessment': {'status': 'AVAILABLE', 'items': [{'id': 'R1', 'kind': 'required', 'verdict': 'VIOLATED'}]}},
                                           'attribution': {'status': 'AVAILABLE', 'claims': claims}}]}}


def inputs(tmp_path):
    r = record()
    annotation = {'case_id': 'TC-01', 'turn': 1, 'user_history_sha256': digest([{'turn': 1, 'user': 'help'}]),
                  'annotation_status': 'PROVISIONAL', 'task': ['help'], 'topic': ['A', 'B'], 'constraints': [], 'dialogue': [], 'risk': []}
    a = tmp_path / 'annotations.json'
    a.write_text(json.dumps({'schema_version': 'scenario-annotations/v1', 'annotations': [annotation]}))
    ar = {'status': 'AVAILABLE', 'n': 3, 'similarities': [1., 0., -.5], 'questions': ['q1', 'q2', 'q3'],
          'embedding_model': 'embed', 'embedding_revision': 'v1', 'generator_model': 'gen', 'prompt_version': 'v1', 'query_mode': 'raw_current_user'}
    entry = {'case_id': 'TC-01', 'turn': 1, 'subject_id': 'model-a',
             'binding': binding('TC-01', 1, 'model-a', 'alpha beta', {'id': 'context-a'}), 'answer_relevancy': ar}
    f = tmp_path / 'analysis.json'
    f.write_text(json.dumps({'schema_version': 'answer-analysis/v1', 'results': [entry]}))
    return r, a, f, entry


def test_binding_and_missing_denominators(tmp_path):
    r, a, f, entry = inputs(tmp_path)
    result = build_analysis([r], annotations_path=a, analysis_path=f, subject_id='model-a')
    first, missing = result['turns']
    assert first['answer_relevancy']['score'] == 1/6
    assert missing['answer_status'] == 'UNAVAILABLE'
    total = next(g for g in result['groups'] if g['axis'] == 'all')
    assert total['n_turns'] == 2 and total['n_cases'] == 1
    assert total['answer_relevancy']['available_n'] == total['answer_relevancy']['unavailable_n'] == 1
    assert total['annotated_n'] == 1
    assert first['hypotheses'][0]['stage'] == 'routing'
    for subject, answer, snapshot in [('model-b', 'alpha beta', {'id': 'context-a'}),
                                      ('model-a', 'changed', {'id': 'context-a'}),
                                      ('model-a', 'alpha beta', {'id': 'changed'})]:
        modified = copy.deepcopy(r)
        modified['conversation']['turns'][0]['assistant_response'] = answer
        modified['pipeline']['turn_traces'][0]['trace']['effective_context_snapshot'] = snapshot
        value = build_analysis([modified], analysis_path=f, subject_id=subject)['turns'][0]['answer_relevancy']
        assert value['score'] is None and value['status'] == 'UNAVAILABLE'


def test_claim_layers_and_proxy_are_not_weighted_legacy(tmp_path):
    r, a, f, _ = inputs(tmp_path)
    result = build_analysis([r], annotations_path=a)
    first = result['turns'][0]
    assert first['subject_id'] == 'model-a'
    assert first['primary_binary']['score'] == 1
    assert first['strict_entailment_proxy']['score'] == .5  # not .75 PARTIAL weighting
    assert first['strict_entailment_proxy']['total'] == 2
    source = next(g for g in result['claim_groups'] if g['axis'] == 'layers' and g['label'] == 'SOURCE')
    assert source['support_counts'] == {'PARTIAL_ONLY': 2}
    assert len([g for g in result['groups'] if g['axis'] == 'topic' and g['label'] in ['A', 'B']]) == 2


def test_stale_annotation_and_invalid_ar_are_unavailable(tmp_path):
    r, a, f, entry = inputs(tmp_path)
    r['conversation']['turns'][0]['user_input'] = 'changed'
    entry['answer_relevancy']['similarities'] = [float('nan'), 1, 1]
    f.write_text(json.dumps({'schema_version': 'answer-analysis/v1', 'results': [entry]}))
    row = build_analysis([r], annotations_path=a, analysis_path=f)['turns'][0]
    assert row['annotation_status'] == 'UNLABELED'
    assert row['answer_relevancy']['reason'] == 'INVALID_RELEVANCY_CONTRACT'


def test_workbook_roundtrip_and_report_cli(tmp_path, monkeypatch):
    from xiaoan_eval.deliverables import publish_deliverables
    r, a, f, _ = inputs(tmp_path)
    # Intentionally an execution-only fixture: pass-through PII validator is local.
    result = build_analysis([r], annotations_path=a, analysis_path=f, subject_id='model-a')
    model = attach_to_model(build_report_model([r]), result)
    path = tmp_path / 'roundtrip.xlsx'
    write_workbook(model, path)
    facts = read_workbook(path)
    assert any(m['metric_id'] == 'scenario.claims' for m in facts.metrics)
    assert facts.core_digest == model.core_digest
    out = tmp_path / 'published'
    # Scenario analysis remains a deterministic diagnostic; it does not invoke a second report agent.
    publish_deliverables(model, out)
    assert set(p.name for p in out.iterdir()) == {'report.md', 'results.xlsx'}
    assert any(m['metric_id'] == 'scenario.turns' for m in read_workbook(out / 'results.xlsx').metrics)


def test_matrix_answer_level_deduplication(tmp_path):
    r, a, f, _ = inputs(tmp_path)
    rows = [{'case_id': 'TC-01', 'turn': 1, 'subject': {'id': 'model-a'}, 'judge': {'id': judge},
             'answer': {'text': 'alpha beta', 'status': 'PASS', 'trace': r['pipeline']['turn_traces'][0]['trace']},
             'attribution': {'status': 'AVAILABLE', 'result': {'claims': r['pipeline']['observations'][0]['attribution']['claims']}},
             'oracle_assessment': {}} for judge in ['j1', 'j2', 'j3']]
    case = SimpleNamespace(id='TC-01', turns=[SimpleNamespace(turn=1, user='help')], quality_focus=[])
    result = build_analysis(rows, cases=[case], annotations_path=a, analysis_path=f)
    assert len(result['turns']) == 3
    total = next(g for g in result['answer_groups'] if g['axis'] == 'all')
    assert total['n_turns'] == total['answer_relevancy']['available_n'] == 1
    assert total['answer_relevancy']['turn_macro_mean'] == 1/6


def test_contextual_relevancy_cannot_be_mixed_with_raw_query(tmp_path):
    r, a, f, entry = inputs(tmp_path)
    entry['answer_relevancy']['query_mode'] = 'contextual_standalone'
    f.write_text(json.dumps({'schema_version': 'answer-analysis/v1', 'results': [entry]}))
    row = build_analysis([r], analysis_path=f)['turns'][0]
    assert row['answer_relevancy']['status'] == 'UNAVAILABLE'
    assert row['answer_relevancy']['reason'] == 'INVALID_RELEVANCY_CONTRACT'
