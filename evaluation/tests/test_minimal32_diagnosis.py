from examples.complete_minimal32_audit import classify


def test_unavailable_reasons_are_distinct_and_not_quality_zero():
    for code in ('ORACLE_MISSING','NOT_APPROVED','TRACE_MISSING','PROVIDER_ERROR','OUTPUT_GUARD_REJECTED','DEPENDENCY_NOT_RUN','JUDGE_INVALID'):
        result=classify(blockers=[code])
        assert result['status']=='UNAVAILABLE'
        assert result['reason_code']==code
        assert result['descriptive_value'] is None


def test_inapplicable_metric_never_becomes_a_failure():
    result=classify(applicable=False,blockers=['TRACE_MISSING'],value=False)
    assert result['status']=='NOT_APPLICABLE'
    assert result['descriptive_value'] is None


def test_pending_label_does_not_hide_other_blockers_or_become_formal_score():
    result=classify(blockers=['NOT_APPROVED','ORACLE_MISSING','TRACE_MISSING'],value=False)
    assert result['status']=='UNAVAILABLE'
    assert result['blockers']==['NOT_APPROVED','ORACLE_MISSING','TRACE_MISSING']
    assert result['descriptive_value'] is False
