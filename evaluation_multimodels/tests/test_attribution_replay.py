import json
import pytest
from xiaoan_eval.attribution_replay import validate_replay


def payload(quote='safe'):
    return {'contract_version':'attribution/v1','claims':[{'claim_id':'c1','kind':'RECOMMENDATION','answer_span':{'start':9,'end':10,'text':quote},'relations':[{'relation':'ENTAILS','evidence_ref':'capsule:x','evidence_span':{'start':0,'end':4,'text':'safe'}}],'unsupported_category':None,'uncertainty':'LOW'}],'policies':[],'abstention':{'status':'ANSWERED','reason':None}}


def test_exact_quote_repair_retains_raw_and_binds_to_actual_evidence():
    raw=json.dumps(payload());catalog=[{'ref':'capsule:x','content':'safe','layer':'CAPSULE','occurrence_id':'x','policy_ids':[]}]
    result,corrections=validate_replay(raw,'be safe',catalog,'test')
    assert result.claims[0].answer_span.start==3
    assert json.loads(raw)['claims'][0]['answer_span']['start']==9
    assert len(corrections)==1


@pytest.mark.parametrize('answer',['safe safe','unrelated'])
def test_ambiguous_or_missing_quote_is_not_repaired(answer):
    with pytest.raises(ValueError):validate_replay(json.dumps(payload()),answer,[{'ref':'capsule:x','content':'safe','policy_ids':[]}],'test')


def test_policy_omission_does_not_count_as_complete_review():
    with pytest.raises(ValueError,match='policy coverage'):
        validate_replay(json.dumps(payload()),'be safe',[{'ref':'capsule:x','content':'safe','policy_ids':['p1']}],'test')
