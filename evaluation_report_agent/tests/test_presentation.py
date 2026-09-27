from evaluation_report_agent.presentation import metric_view, source_label, render_readable, render_judge_matrices
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


def test_matrix_preserves_judge_identity_and_missing_values():
    r = result()
    r['plan']['judges'].append({'id':'j2','model':'model-j2'})
    r['aggregates']['metrics'][0].update(scope='own_complete_cases',subject_id='s',judge_id='j')
    text = '\n'.join(render_judge_matrices(r))
    assert '1 Subject × 2 Judge 指標矩陣' in text
    assert '| 被測模型 | j | j2 |' in text
    assert '1.5／3（1／1）' in text
    assert '無法計算' in text


def test_costs_only_show_subject_totals_and_partial_remains_unavailable():
    r = result()
    r['aggregates']['answer_costs'] = {
        'rows': [{'case_id':'TC-35','turn':2,'subject_model':'s','input_cost':1,'output_cost':2,'total_cost':3}],
        'summary': [{'subject_id':'s','total_cost':3,'priced_answers':1,'planned_answers':1},
                    {'subject_id':'missing','total_cost':None,'priced_answers':0,'planned_answers':1}],
        'catalog': {'version':'test'},
    }
    store = SimpleNamespace(result=r,generation='g',exposed={},sources={})
    report = {'title':'報告','facts':[],'findings':[]}
    text = render_readable(report,store)
    costs = text.split('## 回答模型成本')[1].split('Judge 模型')[0]
    assert '| s | US$3 | 1／1 | 完整估算 |' in costs
    assert '| missing | 無法計算 | 0／1 | 部分資料缺失；總計不可計算 |' in costs
    assert 'TC-35' not in costs and '輸入成本' not in costs


def test_chatflow_audit_separates_source_delivery_and_agent_reads():
    r = result()
    r['answers'] = [{
        'answer_id':'a','case_id':'TC-37','turn':1,'subject_id':'s',
        'trace': {'route': {'capsule_id':'n2a'}, 'redaction': {'pii_tags':[]},
                  'ground': {'loaded':True, 'loading_reason':'message matched global Ground intent'},
                  'output_guard': {'warnings':[], 'character_count':100, 'length_limit':300},
                  'effective_context_snapshot': {'invocations': {'composer': {'status':'INVOKED',
                      'context_units':[{'layer':'SOURCE'}]}}}},
    }]
    store = SimpleNamespace(result=r,generation='g',exposed={'/answers/0':[(0,10)]},
                            sources={'/answers/0':{}, '/aggregates':{}})
    text = render_readable({'title':'報告','facts':[],'findings':[]},store)
    assert '1 條在 Composer 上下文帶有 SOURCE 單元' in text
    assert '提供了單元不等於回答引用或使用了它' in text
    assert '1／2 個證據物件（1 條回答、0 個評估封套、0 條診斷' in text


def test_field_diagnosis_renders_with_judge_identity_and_version_boundary():
    r = result()
    store = SimpleNamespace(result=r, generation='g', exposed={}, sources={},
        dimension_signals=[{'domain': '法律維權', 'subject_id': 's', 'judge_id': 'j',
                            'low': 1, 'evaluated': 2, 'affected_cases': 1}])
    report = {'title': '報告', 'facts': [], 'findings': [], 'diagnoses': [
        {'signal_ref': '/diagnostics/0', 'field': 'capsule.ground',
         'observation': '來源未送達', 'hypothesis': '條件未匹配',
         'experiment': '僅改條件並重播',
         'quote': {'ref': '/envelopes/0', 'text': '缺少依據'}}]}
    text = render_readable(report, store)
    assert '| 法律維權 | s | j | 1／2 | 1 |' in text
    assert '| capsule/wiki | 鍵位 | 修改建議 | 證據 |' in text
    assert '| Capsule（鍵位待核） | capsule.ground |' in text
    assert '單變量實驗：僅改條件並重播' in text
    assert '缺少當次配置' in text


def test_report_order_and_field_table_use_case_route():
    r = result()
    r['answers'][0]['trace'] = {'route': {'capsule_id': 'n1'}}
    store = SimpleNamespace(result=r, generation='g', exposed={}, sources={},
        diagnostics=[{'ref': '/diagnostics/0', 'trace': {'route': {'capsule_id': 'n1'}}}],
        runtime_verification={'status': 'PENDING', 'steps': []})
    report = {'title': '舊標題', 'facts': [], 'findings': [], 'diagnoses': [
        {'signal_ref': '/diagnostics/0', 'field': 'capsule.render_policy',
         'observation': '未知記憶', 'hypothesis': '措辭過強', 'experiment': '固定路由重播',
         'recommendation': '區分情緒肯定與事實認定',
         'quote': {'ref': '/answers/0', 'text': '原文'}}]}
    text = render_readable(report, store)
    assert text.startswith('# 小安 1 案例評測：1 Subject × 1 Judge')
    assert '| Capsule `n1` | capsule.render_policy | 區分情緒肯定與事實認定 |' in text
    order = ['閱讀覆蓋與限制', '指標與解讀', 'Capsule 與 Wiki 逐鍵位修改建議',
             '重點案例與 Judge 分歧', '技術附錄：證據索引']
    assert [text.index('## '+heading) for heading in order] == sorted(text.index('## '+heading) for heading in order)
    assert '原版評分報告（全文保留）' not in text


def test_hard_label_auroc_keeps_subject_denominators():
    r = result()
    r['aggregates']['routing'] = {
        'interpretation': '逐輪矩陣', 'labels': {'CRISIS':'危機', 'BASELINE':'基礎', 'MISSING':'缺失'},
        'summary': [{'subject_id':'s', 'row_labels':['CRISIS','BASELINE'],
                     'column_labels':['CRISIS','BASELINE','MISSING'],
                     'matrix': {'CRISIS':{'CRISIS':3,'BASELINE':1,'MISSING':1},
                                'BASELINE':{'CRISIS':1,'BASELINE':5,'MISSING':0}},
                     'matrix_turns':11,'planned_turns':11,'accepted_hit_rate':0.5,
                     'accepted_hit_n':5,'accepted_evaluated_n':10,
                     'actual_unknown_turns':0,'actual_missing_turns':1,'excluded_turns':0}]}
    store = SimpleNamespace(result=r,generation='g',exposed={},sources={})
    text = render_readable({'title':'報告','facts':[],'findings':[]},store)
    assert '| s | 3 | 1 | 1 | 5 | 75.00% | 16.67% | 0.7917 |' in text
    assert '排除缺失／未知實際路由' in text
