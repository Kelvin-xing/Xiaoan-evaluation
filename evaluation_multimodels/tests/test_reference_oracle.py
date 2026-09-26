from copy import deepcopy
from dataclasses import asdict, replace
from pathlib import Path
import pytest
from xiaoan_eval.cases import load_case
from xiaoan_eval.coverage import case_coverage
from xiaoan_eval.metrics import evaluate_turn_metrics
from xiaoan_eval.reference_oracle import parse_reference_oracle, reviewed_expected
from xiaoan_eval.rules import load_rating_rule


def case42():
    case = load_case('test-cases/TC-42.yaml', load_rating_rule('ratings rule.yml'), lambda _: True).case
    # Keep the review-boundary fixture independent of later dataset approvals.
    turns = tuple(replace(turn, expected=replace(turn.expected, reference_oracle={
        **turn.expected.reference_oracle, 'status': 'provisional',
        'reviewed_by': None, 'reviewed_at': None,
    })) for turn in case.turns)
    return replace(case, turns=turns)


def test_new_labels_do_not_inherit_response_approval():
    case = case42()
    assert case.oracle_gate_eligible
    expected = asdict(case.turns[0].expected)
    filtered = reviewed_expected(expected)
    assert 'route_ids' not in filtered
    assert 'source_refs' not in filtered
    assert filtered['response_oracle'] == expected['response_oracle']
    coverage = case_coverage(case)
    assert coverage['authored']['route'] == 2
    assert coverage['reviewed']['route'] == 0
    assert coverage['reviewed']['claims'] == 2
    result = evaluate_turn_metrics(case.turns[0].expected, {}, oracle_approved=True)
    assert 'provisional' in result['route'].reason


def test_review_requires_explicit_reviewer():
    e = asdict(case42().turns[0].expected)
    c = deepcopy(e['reference_oracle'])
    c['status'] = 'reviewed'
    c.pop('reviewed_by', None)
    c.pop('reviewed_at', None)
    with pytest.raises(ValueError, match='reviewed_by'):
        parse_reference_oracle(c)
    c.update(reviewed_by='test-reviewer', reviewed_at='2026-09-13')
    e['reference_oracle'] = parse_reference_oracle(c)
    assert reviewed_expected(e)['source_refs'] == e['source_refs']


@pytest.mark.parametrize('mutation', [
    lambda c: c.update(snapshot_id='latest'),
    lambda c: c.update(scope=['route_ids']),
    lambda c: c['ground'].update(required_node_ids=[]),
    lambda c: c['ground'].update(activation='not_applicable'),
])
def test_invalid_contract_rejected(mutation):
    c = deepcopy(case42().turns[0].expected.reference_oracle)
    mutation(c)
    with pytest.raises(ValueError):
        parse_reference_oracle(c)


def test_every_case_has_versioned_labels():
    rule = load_rating_rule('ratings rule.yml')
    paths = list(Path('test-cases').glob('TC-*.yaml')) + list(Path('test-cases/proposed').glob('TC-*.yaml'))
    for path in paths:
        case = load_case(path, rule, lambda _: True).case
        for turn in case.turns:
            e = turn.expected
            assert e.reference_oracle is not None
            assert e.route_ids and e.safety_levels
            assert e.capsule_ids == e.route_ids
            assert 'k1' not in e.route_ids
            assert e.response_oracle.required_claims and e.response_oracle.forbidden_claims


def test_explicit_reference_review_restores_labels():
    expected = asdict(case42().turns[0].expected)
    expected['reference_oracle'].update(status='reviewed', reviewed_by='test-reviewer', reviewed_at='2026-09-23')
    filtered = reviewed_expected(expected)
    assert 'route_ids' in filtered
    assert 'source_refs' in filtered
    assert filtered['response_oracle'] == expected['response_oracle']
