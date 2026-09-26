from copy import deepcopy

import pytest

from xiaoan_eval.oracle_judge import contract, validate


def assessment(answer, quote, start, end):
    request = {"assistant_answer": answer, "expected": {
        "response_oracle": {"required_claims": ["提供安全支持"]}}}
    payload = {"binding": contract(request)["binding"], "items": [{
        "id": "R1", "verdict": "SATISFIED", "reason": "有原文证据",
        "spans": [{"start": start, "end": end, "quote": quote}]}]}
    return request, payload


def test_unique_quote_resolves_unicode_offsets_without_mutating_raw():
    request, payload = assessment('🙂\n请你先确认安全。', '先确认安全', 5, 11)
    raw = deepcopy(payload)
    result = validate(payload, request)
    assert payload == raw
    assert result['items'][0]['spans'] == [{'start': 4, 'end': 9, 'quote': '先确认安全'}]
    assert result['span_resolution']['corrections'] == [{
        'oracle_id': 'R1', 'span_index': 0, 'original_start': 5,
        'original_end': 11, 'resolved_start': 4, 'resolved_end': 9,
        'method': 'unique_exact_quote'}]


@pytest.mark.parametrize('answer,quote', [('安全安全', '安全'), ('aaa', 'aa'), ('安全。', '安全!'), ('安全', '')])
def test_missing_ambiguous_or_empty_quotes_remain_rejected(answer, quote):
    request, payload = assessment(answer, quote, 999, 1000)
    with pytest.raises(ValueError):
        validate(payload, request)


def test_correct_offsets_disambiguate_repeated_quote():
    request, payload = assessment('安全安全', '安全', 2, 4)
    result = validate(payload, request)
    assert result['items'][0]['spans'] == payload['items'][0]['spans']
    assert result['span_resolution']['corrections'] == []


@pytest.mark.parametrize('start,end', [(True, 2), ('0', 2), (0, None)])
def test_invalid_offset_types_are_not_repaired(start, end):
    request, payload = assessment('安全', '安全', start, end)
    with pytest.raises(ValueError):
        validate(payload, request)


@pytest.mark.parametrize('quote,accepted', [('安全', True), ('不存在', False)])
def test_judge_checkpoint_records_full_validation_and_offset_audit(quote, accepted):
    import json
    from xiaoan_eval.judge_client import JudgeClient
    from xiaoan_eval.rules import load_rating_rule
    rule = load_rating_rule('ratings rule.yml')
    request, oracle = assessment('请先确认安全。', quote, 99, 100)
    request.update(case_id='TC-test', turn=1, evidence_catalog=[])
    payload = {
        'red_lines': [{'id': r.id, 'triggered': False, 'evidence': [], 'uncertainty': 'low'} for r in rule.red_lines],
        'dimensions': [{'module': m.name, 'score': 2, 'supporting_evidence': [], 'deduction_evidence': [], 'uncertainty': 'low'} for m in rule.modules],
        'legal_claims': [], 'faithfulness_claims': [], 'oracle_assessment': oracle,
    }
    raw = json.dumps(payload)
    events = []
    client = JudgeClient(lambda _: raw, rule, checkpoint=events.append)
    if accepted:
        result = client.judge(request)
        assert result.oracle_assessment['items'][0]['spans'][0]['start'] == 4
        correction = next(e for e in events if e['event'] == 'judge_span_resolution')
        assert correction['case_id'] == 'TC-test'
        assert correction['corrections'][0]['original_start'] == 99
    else:
        with pytest.raises(ValueError):
            client.judge(request)
    assert events[0]['raw_response'] == raw
    assert [e['status'] for e in events if e['event'] == 'judge_validation'] == ['OK' if accepted else 'ERROR']
