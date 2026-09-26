from evaluation_report_agent.presentation import metric_view, source_label, render_readable
from types import SimpleNamespace


def result():
    return {'answers':[{'answer_id':'a','case_id':'TC-35','turn':2,'subject_id':'s','reference_facts':[]}],
        'plan':{'judges':[{'id':'j','model':'model-j'}]},
        'evaluation_config':{'rating-rule.yml':{'content':'score_scale:\n- score: 0\n- score: 3\n'}},
        'stages':[{'answer_id':'a','task':'assess_claims','identity':{'model':'model-j'}}],
        'aggregates':{'metrics':[
          {'metric':'rubric','value':1.5,'effective_cases':1,'planned_cases':1},
          {'metric':'correctness','value':0.0,'unknown_ratio':1.0,'subject_id':'s'},
          {'metric':'requirements_gate','value':None,'gate_counts':{'NOT_APPLICABLE':1}},
        ]}}


def test_scale_unknown_and_null_are_explicit():
    r=result()
    rows=[metric_view(r,{'pointer':f'/aggregates/metrics/{i}/value','value':m['value']}) for i,m in enumerate(r['aggregates']['metrics'])]
    assert rows[0][1]=='1.5／3'
    assert '100%' in rows[1][4] and '不表示全部已被判錯' in rows[1][4]
    assert '獨立核准真值' in rows[1][4]
    assert rows[2][1]=='無法計算（不適用）' and '並非零分' in rows[2][4]


def test_stage_labels_follow_answer_identity_not_position():
    r=result()
    assert source_label(r,'/answers/0')=='TC-35 第二輪回答'
    assert 'TC-35 第二輪｜主張與要求評估' in source_label(r,'/stages/0')


def test_body_uses_labels_and_appendix_retains_pointers():
    r=result();store=SimpleNamespace(result=r,generation='g',exposed={'/answers/0':[]},sources={'/answers/0':{}})
    report={'title':'報告','facts':[{'pointer':'/aggregates/metrics/0/value','value':1.5}],
       'findings':[{'kind':'judge','conclusion':'見 /stages/0 的判定。','scope':'/answers/0',
                   'quotes':[{'ref':'/answers/0','text':'原文不改。'}],'verification':'核對 /stages/0。'}]}
    text=render_readable(report,store)
    body,appendix=text.split('## 技術附錄')
    assert '/answers/' not in body and '/stages/' not in body and '/aggregates/' not in body
    assert '1.5／3' in body and '滿分／範圍' in body and 'TC-35 第二輪回答' in body
    assert '/answers/0' in appendix and '/stages/0' in appendix
    assert '> 原文不改。' in body


def test_unavailable_scale_never_invented():
    r=result();r.pop('evaluation_config')
    row=metric_view(r,{'pointer':'/aggregates/metrics/0/value','value':1.5})
    assert row[1]=='1.5' and row[2]=='來源未提供量尺'
