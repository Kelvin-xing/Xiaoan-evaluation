from copy import deepcopy

import pytest

from test_frozen_end_to_end import FixtureProvider, IDENTITY
from xiaoan_eval.frozen_cli import execute_frozen
from xiaoan_eval.frozen_ingress import build_plan, freeze_answer
from xiaoan_eval.frozen_reconcile import reconcile_generations
from xiaoan_eval_core.results import seal_complete_results, validate_complete_results


def result(tmp_path):
    spec = build_plan([IDENTITY], [IDENTITY], IDENTITY, case_ids=['TC-35'], relevancy_generator=IDENTITY)
    spec['rows'] = [freeze_answer(row, {'text': '這是測試回答。'}, [], generation_id='test')
                    for row in spec['rows']]
    return execute_frozen(spec, tmp_path / 'source', provider=FixtureProvider())


def test_recovers_successful_cells_without_changing_answers(tmp_path):
    source = result(tmp_path)
    base = deepcopy(source)
    base['envelopes'][0]['rubric'][0]['status'] = 'UNAVAILABLE'
    seal_complete_results(base)
    recovered = reconcile_generations(base, source, tmp_path / 'reconciled',
                                      base_path='base.json', addition_path='source.json')
    merged = validate_complete_results(__import__('json').loads(
        (tmp_path / 'reconciled' / 'results.json').read_text()))
    assert recovered[('rubric', 'AVAILABLE')] == 1
    assert merged['answers'] == source['answers']
    assert merged['envelopes'][0]['rubric'][0] == source['envelopes'][0]['rubric'][0]


def test_rejects_different_successful_cells(tmp_path):
    source = result(tmp_path)
    altered = deepcopy(source)
    altered['envelopes'][0]['rubric'][0]['rubric']['weighted_total'] = 99
    seal_complete_results(altered)
    with pytest.raises(ValueError, match='Conflicting successful rubric'):
        reconcile_generations(source, altered, tmp_path / 'conflict',
                              base_path='base.json', addition_path='other.json')
    assert not (tmp_path / 'conflict' / 'results.json').exists()
