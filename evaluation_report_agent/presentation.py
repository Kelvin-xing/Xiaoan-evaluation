"""Human-facing labels and metric interpretation from frozen result metadata."""
import re
import yaml

PRESENTATION_VERSION = 'human-readable-metrics/v1'

TASKS = {'extract_claims':'主張抽取','assess_claims':'主張與要求評估','rubric':'品質評分',
         'relevancy_generation':'相關性：反向問題生成','relevancy_embedding':'相關性：向量比較'}
METRICS = {'rubric':'Rubric 品質分數','faithfulness':'忠實度已確認支持率',
           'correctness':'正確性已確認支持率','rubric_gate':'品質紅線 gate 已確認通過率',
           'requirements_gate':'關鍵要求 gate 已確認通過率'}
LAYERS = {'CURRENT_INPUT':'本輪使用者輸入','PRIOR_USER':'先前使用者陳述','PRIOR_ASSISTANT':'先前助手回答',
          'PROMPT':'系統指令','CAPSULE':'場景膠囊','WIKI':'知識內容','SOURCE':'來源文件'}
POINTER = re.compile(r'/(?:answers|stages|envelopes|aggregates|inventories|manifest|plan)(?:/[A-Za-z0-9_.~-]+)*')


def resolve(result, pointer):
    value=result
    for key in pointer.lstrip('/').split('/'):
        key=key.replace('~1','/').replace('~0','~')
        value=value[int(key)] if isinstance(value,list) else value[key]
    return value


def turn_label(answer):
    n=answer.get('turn')
    word={1:'一',2:'二',3:'三',4:'四',5:'五',6:'六',7:'七',8:'八',9:'九',10:'十'}.get(n,str(n))
    return f"{answer.get('case_id','案例')} 第{word}輪"


def source_label(result, ref):
    parts=ref.strip('/').split('/')
    try:
        if parts[0]=='answers' and len(parts)>1:
            return turn_label(result['answers'][int(parts[1])])+'回答'
        if parts[0] in ('stages','envelopes','inventories') and len(parts)>1:
            item=result[parts[0]][int(parts[1])]
            answer=next((a for a in result['answers'] if a['answer_id']==item.get('answer_id')),None)
            prefix=turn_label(answer) if answer else '評估工作'
            name=TASKS.get(item.get('task'),{'envelopes':'完整評估','inventories':'主張清單'}.get(parts[0],'執行紀錄'))
            model=item.get('identity',{}).get('model')
            return prefix+'｜'+name+(f'（{model}）' if model else '')
        if parts[0]=='aggregates':
            if len(parts)>2:
                item=result['aggregates'][parts[1]][int(parts[2])]
                if parts[1]=='citation_coverage':return '評估證據引用覆蓋｜'+LAYERS.get(item.get('layer'),item.get('layer') or '全部來源層')
                label=METRICS.get(item.get('metric'),item.get('metric','統計'))
                if parts[-1]=='unknown_ratio':label=label.replace('已確認支持率','未知比例')
                return label
            return '程式計算的統計'
        return {'manifest':'版本與配置','plan':'評估計劃'}.get(parts[0],'證據紀錄')
    except (KeyError,ValueError,IndexError,TypeError):
        return '證據紀錄（名稱未提供）'


def number(value):
    return f'{value:.4g}' if isinstance(value,(int,float)) else str(value)


def percent(value):
    return number(value*100)+'%'


def rubric_scale(result):
    config=result.get('evaluation_config') or result.get('manifest',{}).get('evaluator_config',{})
    entry=config.get('rating-rule.yml',{})
    content=entry.get('content') if isinstance(entry,dict) else entry
    if not content:return None
    values=[x['score'] for x in yaml.safe_load(content).get('score_scale',[]) if isinstance(x.get('score'),(int,float))]
    return (min(values),max(values)) if values else None


def metric_view(result, fact):
    """Return display cells without changing a stored metric or its denominator."""
    ref,value=fact['pointer'],fact['value']
    parts=ref.strip('/').split('/')
    item=resolve(result,'/'+ '/'.join(parts[:-1]))
    metric=item.get('metric') if isinstance(item,dict) else None
    label=source_label(result,ref)
    notes=[]
    if 'answer_costs' in parts:
        label={'total_cost':'回答模型官方估算合計','known_subtotal':'回答模型已知成本小計','input_cost':'回答模型輸入成本','output_cost':'回答模型輸出成本'}.get(parts[-1],'回答模型成本統計')
        monetary=parts[-1] in {'total_cost','known_subtotal','input_cost','output_cost'}
        display='無法計算' if value is None else ('US$'+format(value,'.8f').rstrip('0').rstrip('.') if monetary else number(value))
        scale='USD；無滿分' if monetary else '回答數；無滿分'
        meaning='按已記錄回答 tokens 及保存的官方價目表計算。'
        notes.append('官方定價估算，不是中介帳單；不含其他模型角色、儲存或未記錄重試。')
        if item.get('reason'):notes.append('原因：'+item['reason'])
        if 'priced_answers' in item:notes.append(f"可計價／計劃回答：{item['priced_answers']}／{item['planned_answers']}。")
    elif parts[-1]=='unknown_ratio':
        display='無法計算' if value is None else percent(value)
        scale='0–100%（比例上限）'
        meaning='表示適用主張中有多少仍無法確定；越低表示未知越少。'
        notes.append('未知不是已證實錯誤；與已確認支持率使用相同案例集合及適用分母。')
    elif 'citation_coverage' in parts:
        display='無法計算' if value is None else percent(value)
        scale='0–100%（比例上限）'
        meaning='Judge 引用的唯一內容單元 ÷ 提供給 Composer 的單元。'
        notes.append('可用於支持或指出矛盾；不是模型實際使用率、品質分數或因果貢獻。')
        notes.append(f"引用／提供單元：{item.get('cited_occurrences','未知')}／{item.get('provided_occurrences','未知')}。")
        if value is None:notes.append('資料不可用或分母為零；不當作零引用。')
    elif metric=='rubric':
        limits=rubric_scale(result)
        display='無法計算' if value is None else number(value)+(f'／{number(limits[1])}' if limits else '')
        scale=f'{number(limits[0])}–{number(limits[1])}；滿分 {number(limits[1])}' if limits else '來源未提供量尺'
        meaning='各維度依凍結規則加權，完整案例等權平均；越高表示越符合 rubric。'
        notes.append('不是正確率；紅線／gate 獨立展示，不強制將品質分數歸零。')
    elif metric in ('faithfulness','correctness'):
        display='無法計算' if value is None else percent(value)
        scale='0–100%；100% 表示所有適用主張均已確認支持'
        meaning='依'+('當時提供的上下文內容' if metric=='faithfulness' else '獨立核准事實')+'判定；每案已確認支持主張數 ÷ 適用主張數，再對案例等權平均。'
        unknown=item.get('unknown_ratio')
        if unknown is not None:notes.append('未知比例：'+percent(unknown)+'。')
        notes.append('UNKNOWN 留在分母，NOT_APPLICABLE 排除；比例低需連同未知比例解讀。')
        if metric=='correctness' and unknown==1:
            notes.append('全部適用主張尚無法確定；本數值不表示全部已被判錯。')
            truth_missing=all(not a.get('reference_facts') for a in result.get('answers',[]) if a.get('subject_id')==item.get('subject_id'))
            if truth_missing:notes.append('本組答案未提供獨立核准真值。')
        if value is None:notes.append('沒有符合完整性／適用分母條件的案例，並非零分。')
    elif metric in ('rubric_gate','requirements_gate'):
        display='無法計算（不適用）' if value is None and item.get('gate_counts',{}).get('NOT_APPLICABLE') else '無法計算' if value is None else percent(value)
        scale='0–100%；100% 表示分母內案例均確認通過'
        meaning='PASS ÷（PASS＋FAIL＋UNDETERMINED），不適用案例排除。'
        notes.append('待確認不是已證實失敗；gate 與品質分數分開。')
        counts=item.get('gate_counts',{})
        if counts:notes.append('案例狀態：'+ '、'.join(f'{k}={v}' for k,v in counts.items())+'。')
        if value is None:notes.append('沒有可計算的適用分母，並非零分。')
    else:
        display='無法計算' if value is None else number(value)
        scale='依來源指標定義'
        meaning='此項尚未登記專用解讀；見證據索引，避免假定量尺。'
    if isinstance(item,dict):
        if item.get('answer_id'):
            answer=next((a for a in result.get('answers',[]) if a['answer_id']==item['answer_id']),None)
            if answer:label+='（'+turn_label(answer)+'）'
        if item.get('case_id'):label+='（'+item['case_id']+'）'
        subject,judge=item.get('subject_id'),item.get('judge_id')
        if subject:label+=f'｜被測 {subject}'
        if judge:label+=f'｜Judge {judge}'
        scope=item.get('scope')
        if scope:notes.append('範圍：'+{'own_complete_cases':'本組完整案例','common_complete_cases':'共同完整案例'}.get(scope,scope)+'。')
        if 'effective_cases' in item:
            count_label='有 gate 紀錄／計劃案例' if metric in ('rubric_gate','requirements_gate') else '有效／計劃案例'
            notes.append(f"{count_label}：{item['effective_cases']}／{item.get('planned_cases','未知')}。")
    return [label,display,scale,meaning,' '.join(notes)]


def escape_cell(value):
    return str(value).replace('|','\\|').replace('\n','<br>')


def render_readable(report, store):
    refs={}
    def link(ref):
        if ref not in refs:refs[ref]=len(refs)+1
        return f'[{source_label(store.result,ref)}](#evidence-{refs[ref]})'
    def prose(value):
        return POINTER.sub(lambda m:link(m.group()),value)
    lines=['# '+report['title'],'','## 指標與解讀','',
           '| 指標 | 本次數值 | 滿分／範圍 | 解讀方式 | 注意事項 |','| --- | --- | --- | --- | --- |']
    for fact in report.get('facts',[]):
        cells=metric_view(store.result,fact)
        cells[0]='['+escape_cell(cells[0])+'](#evidence-'+str(refs.setdefault(fact['pointer'],len(refs)+1))+')'
        lines.append('| '+cells[0]+' | '+' | '.join(escape_cell(c) for c in cells[1:])+' |')
    if not report.get('facts'):lines.append('| 尚未引用統計 | — | — | 本報告未選取數值指標 | 不補造分數 |')
    routing=store.result.get('aggregates',{}).get('routing',{})
    if routing.get('summary'):
        lines.extend(['','## 路由模式混淆矩陣','',routing['interpretation']])
        labels=routing['labels']
        for item in routing['summary']:
            columns=item['column_labels']
            lines.extend(['',f"被測模型：{item['subject_id']}；矩陣納入／計劃輪次：{item['matrix_turns']}／{item['planned_turns']}。",
                '', '| 預期＼實際 | '+' | '.join(labels[c] for c in columns)+' |','| --- | '+' | '.join('---:' for _ in columns)+' |'])
            for expected in item['row_labels']:
                lines.append('| '+labels[expected]+' | '+' | '.join(str(item['matrix'][expected][actual]) for actual in columns)+' |')
            rate='無法計算' if item['accepted_hit_rate'] is None else percent(item['accepted_hit_rate'])
            lines.extend(['',f"允許路由命中率：{rate}（{item['accepted_hit_n']}／{item['accepted_evaluated_n']} 個可判定輪次）。未知路由 {item['actual_unknown_turns']} 輪；缺失路由 {item['actual_missing_turns']} 輪；預期標籤不足而未進矩陣 {item['excluded_turns']} 輪。"])
    costs=store.result.get('aggregates',{}).get('answer_costs')
    if costs:
        lines.extend(['','## 回答模型成本（官方定價估算）','',
            '僅計回答模型的已記錄輸入／輸出 tokens，幣別 USD；不包含 Safety／Router、Judge、embedding、報告及未記錄重試，也不代表 KaroAPI 實際帳單。',
            '', '| 回答 | 模型 | 輸入成本 | 輸出成本 | 合計 | 狀態／注意事項 |', '| --- | --- | --- | --- | --- | --- |'])
        money=lambda value: '無法計算' if value is None else 'US$'+format(value,'.8f').rstrip('0').rstrip('.')
        for row in costs['rows']:
            label=f"{row['case_id']} 第{row['turn']}輪"
            note=row.get('reason') or ' '.join(row.get('notes',[]))
            note={'ANSWER_TOKEN_USAGE_MISSING':'未保存回答模型 token 用量，無法回算。','OFFICIAL_PRICE_NOT_FOUND':'缺少精確模型／服務層的官方價格。','NO_ANSWER_MODEL_CALL':'未呼叫回答模型。','PRICING_PERIOD_REQUIRED':'缺少已確認的峰／谷計價時段。'}.get(note,note)
            lines.append('| '+' | '.join(escape_cell(v) for v in [label,row['subject_model'],money(row['input_cost']),money(row['output_cost']),money(row['total_cost']),note])+' |')
        for summary in costs['summary']:
            lines.extend(['',f"{summary['subject_id']}：可計價回答 {summary['priced_answers']}／{summary['planned_answers']}；已知小計 {money(summary['known_subtotal'])}；完整合計 {money(summary['total_cost'])}。"])
        lines.extend(['','價格版本：'+costs['catalog']['version']+'；價格及公式見完整 JSON 的 answer_costs。'])
    judges=store.result.get('plan',{}).get('judges',[])
    if judges:
        names=list(dict.fromkeys(j.get('model',j.get('id','未知')) for j in judges))
        lines.extend(['','Judge 模型：'+ '、'.join(names)+'。同一 Judge 對不同輪次的呼叫仍是同一評委；呼叫編號不是 Judge 編號。'])
    headings={'fact':'觀察結果','judge':'Judge 判定','hypothesis':'待驗證解釋','proposal':'改善建議'}
    for finding in report['findings']:
        lines.extend(['','## '+headings.get(finding['kind'],finding['kind']),'',prose(finding['conclusion']),'','範圍：'+prose(finding['scope'])])
        for quote in finding['quotes']:
            lines.extend(['','> '+quote['text'].replace('\n','\n> '),'','來源：'+link(quote['ref'])])
        if finding.get('verification'):lines.extend(['','驗證方式：'+prose(finding['verification'])])
    lines.extend(['','## 閱讀覆蓋與限制','',f'已讀證據紀錄 {len(store.exposed)}／{len(store.sources)}；這是紀錄覆蓋，不等於案例閱讀比例。逐頁範圍見 validation.json。'])
    lines.extend('- '+prose(x) for x in report.get('limitations',[]))
    lines.extend(['','## 技術附錄：證據索引','',f'結果版本：`{store.generation}`。以下路徑是 JSON 定位，不是輪次或評委編號。'])
    for ref,index in refs.items():
        lines.extend(['',f'<a id="evidence-{index}"></a>',f'- **{source_label(store.result,ref)}**：`{ref}`'])
    return '\n'.join(lines)+'\n'
