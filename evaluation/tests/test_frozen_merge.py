from copy import deepcopy

import pytest

from test_frozen_end_to_end import FixtureProvider, IDENTITY
from xiaoan_eval.frozen_cli import execute_frozen
from xiaoan_eval.frozen_ingress import build_plan, freeze_answer
from xiaoan_eval.frozen_merge import merge_subject_results
from xiaoan_eval_core.results import validate_complete_results


def cohort(tmp_path, subject):
    spec = build_plan([subject], [IDENTITY], IDENTITY, case_ids=['TC-35'], relevancy_generator=IDENTITY)
    spec['rows'] = [freeze_answer(r, {'text': '這是離線合成回答。'}, [], generation_id=subject['id']) for r in spec['rows']]
    return execute_frozen(spec, tmp_path / subject['id'], provider=FixtureProvider())


def test_merge_preserves_cohorts_and_recomputes_subject_matrix(tmp_path):
    first = cohort(tmp_path, IDENTITY)
    second = cohort(tmp_path, {**IDENTITY, 'id': 'another-fixture'})
    result = merge_subject_results(first, second, tmp_path / 'merged')
    validate_complete_results(result)
    assert len(result['answers']) == len(first['answers']) + len(second['answers'])
    assert {r['answer_id'] for r in result['answers']} == {r['answer_id'] for r in first['answers'] + second['answers']}
    assert {r['subject_id'] for r in result['aggregates']['metrics']} == {'offline-fixture', 'another-fixture'}
    assert result['provenance'][-1]['source_generations'] == [first['result_generation'], second['result_generation']]
    assert (tmp_path / 'merged' / 'results.xlsx').exists()
    with pytest.raises(ValueError, match='overlap'):
        merge_subject_results(first, deepcopy(first), tmp_path / 'overlap')
