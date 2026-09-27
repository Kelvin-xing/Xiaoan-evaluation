"""Human-facing labels and metric interpretation from frozen result metadata."""
import re
import yaml

PRESENTATION_VERSION = 'integrated-case-report/v1'

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
        if parts[0]=='diagnostics':return '異常案例診斷摘要'
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


def render_judge_matrices(result):
    metrics = result.get('aggregates', {}).get('metrics', [])
    own = {(row.get('subject_id'), row.get('judge_id'), row.get('metric')): (i, row)
           for i, row in enumerate(metrics) if row.get('scope') == 'own_complete_cases'}
    subjects = list(dict.fromkeys(row['subject_id'] for row in result.get('answers', [])))
    judges = [row['id'] for row in result.get('plan', {}).get('judges', [])]
    if not own or not subjects or not judges:
        return []
    names = [('rubric', 'Rubric 品質分數'), ('rubric_gate', '品質紅線 gate 通過率'),
             ('faithfulness', '忠實度已確認支持率'), ('correctness', '正確性已確認支持率'),
             ('requirements_gate', '關鍵要求 gate 通過率')]
    lines = ['', f'## {len(subjects)} Subject × {len(judges)} Judge 指標矩陣', '',
             '每格為本組完整案例指標；括號為有效／計劃案例數。缺值與不適用保持無法計算，UNKNOWN 並非錯誤。各 Judge 分開呈現，不合併成單一分數。']
    for metric, label in names:
        if not any(key[2] == metric for key in own):
            continue
        lines.extend(['', '### '+label, '', '| 被測模型 | '+' | '.join(escape_cell(j) for j in judges)+' |',
                      '| --- | '+' | '.join('---:' for _ in judges)+' |'])
        for subject in subjects:
            cells = []
            for judge in judges:
                entry = own.get((subject, judge, metric))
                if entry is None:
                    cells.append('無法計算')
                    continue
                index, row = entry
                display = metric_view(result, {'pointer':f'/aggregates/metrics/{index}/value',
                                               'value':row['value']})[1]
                cells.append(escape_cell(display)+f"（{row.get('effective_cases',0)}／{row.get('planned_cases','?')}）")
            lines.append('| '+escape_cell(subject)+' | '+' | '.join(cells)+' |')
    return lines


def render_chatflow_audit(result, link):
    answers = result.get('answers', [])
    traced = [(i, a, a.get('trace') or {}) for i, a in enumerate(answers) if (a.get('trace') or {}).get('route')]
    if not traced:
        return []
    total = len(traced)
    route = lambda t: t[2]['route'].get('capsule_id')
    crisis = sum(route(t) == 'crisis_sop' for t in traced)
    clarification = sum(route(t) == 'safety_clarification' for t in traced)
    baseline = sum(route(t) == 'baseline' for t in traced)
    capsule = [t for t in traced if route(t) not in {'crisis_sop', 'safety_clarification', 'baseline'}]
    loaded = [t for t in capsule if t[2].get('ground', {}).get('loaded')]
    source = [t for t in loaded if any(u.get('layer') == 'SOURCE' for u in t[2].get('effective_context_snapshot', {}).get('invocations', {}).get('composer', {}).get('context_units', []))]
    without_intent = sum('no global Ground intent' in t[2].get('ground', {}).get('loading_reason', '') for t in capsule)
    without_branch = sum('no conditional Ground branch matched' in t[2].get('ground', {}).get('loading_reason', '') for t in capsule)
    warnings = sum(bool(t[2].get('output_guard', {}).get('warnings')) for t in traced)
    over_limit = sum(t[2].get('output_guard', {}).get('character_count', 0) > t[2].get('output_guard', {}).get('length_limit', float('inf')) for t in traced)
    continued = sum(bool(t[2]['route'].get('should_continue_active_capsule')) for t in traced)
    tagged = sum(bool(t[2].get('redaction', {}).get('pii_tags')) for t in traced)
    invoked = sum(t[2].get('effective_context_snapshot', {}).get('invocations', {}).get('composer', {}).get('status') == 'INVOKED' for t in traced)
    ground_example = next((link(f'/answers/{i}') for i, _, _ in source), '案例待核對')
    lines = ['', '## Chatflow 逐步改善清單', '',
             f'以下執行計數由凍結的 {total} 條回答 trace 直接計算；是步驟覆蓋與異常線索，不是逐條語意品質審查。現行程式的行為與歷史生成版本仍須對照。',
             '', '| 步驟 | 已觀察到的能力與缺口 | 定位與改動 | 驗證方式 |', '| --- | --- | --- | --- |']
    rows = [
        ('輸入與 PII', f'{total} 條中 {tagged} 條有 PII tag；tag 計數不能證明文字已遮蔽。',
         '在 PII 前處理加入經授權的偵測／遮蔽，令 Safety、Router、Composer 與日誌都使用一致的安全輸入；不要以空 tag 表示已完成遮蔽。', '用姓名、地址、電話及不該遮蔽的普通詞作對照測試；先核對歷史程式版本。'),
        ('Safety 與危機 SOP', f'{crisis} 條進 crisis_sop，{clarification} 條進安全澄清；安全澄清會跳過 Router、Ground 與 Composer。',
         '依核准 oracle 逐條校對 UNCLEAR 與 CRISIS 的邊界，為模糊敘述保留安全回應而避免攔掉普通求助。', '對三類邊界案例重播分類與回應，分別記錄漏判危機、過度澄清與後續對話。'),
        ('Router 與跨輪狀態', f'正常路由中 {baseline} 條落 baseline、{len(capsule)} 條選 capsule；{continued} 條要求沿用活躍 capsule。',
         '在 Router 的 triggers/use_when/do_not_use_when 與 state 交接處比較核准路由；針對不合理 baseline、錯配 capsule、跨輪代詞補測，不把 Safety 改動算成 Router 改動。', '按模型對照報告的混淆矩陣及允許路由命中率，再做跨輪路由回歸。'),
        ('Capsule 內容與選擇', f'{len(capsule)} 條進入具體 capsule；這只證明被選用，不能證明 recognize/act/render_policy 已在回答中用得恰當。',
         '對低品質案例比對被選 capsule 的 recognize、act、render_policy 與用戶任務；拆開「選錯膠囊」和「選對但回覆不合用」兩類修訂。', '固定 Router 輸出做 Composer A/B；另固定 Composer 比較 capsule 選擇。'),
        ('Ground 觸發與分支', f'{len(capsule)} 條 capsule 中 {len(loaded)} 條 loaded；{without_intent} 條未命中全域意圖，{without_branch} 條未匹配條件分支（原因可能重疊）。',
         '按案例核對 capsule.ground 的意圖詞與條件分支，優先挑有法律／機構事實需求卻未載入依據的表述；不能把所有未載入一概判錯。', '按 capsule 分組比較應載入率、分支召回、誤載入率與延遲。'),
        ('Wiki 與來源解析', f'{len(source)} 條在 Composer 上下文帶有 SOURCE 單元；如 {ground_example} 可追到 resolved_ground 與來源。提供了單元不等於回答引用或使用了它。',
         '逐條檢查應引證案例的 resolved_ground 是否包含正確條文／知識節點、版本與可引用片段；缺失時先定位 Ground 分支或 Wiki 解析，再改節點映射。', '對應有來源的案例比較「應有→解析→提供→回答明示／忠實支持」四個狀態；抽查原文與有效日期。'),
        ('Composer、Prompt 與 SOP', f'{invoked} 條真正呼叫 Composer；安全澄清走固定回應。提供 PROMPT、CAPSULE 或 SOURCE 的 trace 只能證明輸入，不能證明回答遵循或實際使用。',
         '把有來源而缺少應有引證的案例分給 Composer prompt 的引用指令、capsule.render_policy 或 Wiki 供給三處排查；無來源時禁止補造法條或機構能力。', '固定同一來源與模型比較修改前後的主張支持、明示引證、同理與單輪推進。'),
        ('輸出檢查與收尾', f'{warnings} 條有 output_guard 警告，{over_limit} 條超過建議字數限制；實際攔截行為須核對當次版本。',
         '先區分安全違規與風格警告；針對可檢測的高風險違規設拒送／再生成條件，風格以 prompt 與回歸測試優化，不直接截斷危機回應。', '量測警告、實際攔截及誤攔截；對照最終發給使用者的文本。'),
    ]
    lines.extend('| '+' | '.join(escape_cell(c) for c in row)+' |' for row in rows)
    lines.extend(['', '優先順序：先核對 Safety 漏判與 PII 透傳，再對應有法律／機構依據的案例檢查 Ground→Wiki→Composer 鏈條；Router、Capsule 與 Prompt 各做單變量回歸。Judge 的 citation_coverage 衡量評委引用了哪些已提供單元，不能當作 Composer 的實際引用率。'])
    return lines


REPORT_ORDER = (
    '閱讀覆蓋與限制', '指標與解讀', '指標矩陣', '路由模式混淆矩陣',
    '法律、行動與心理支持診斷線索', 'Chatflow 逐步改善清單',
    'Capsule 與 Wiki 逐鍵位修改建議', '重點案例與 Judge 分歧',
    '回答模型成本（官方定價估算）', '執行路徑核對', '技術附錄：證據索引',
)


def order_report_sections(text):
    """Keep generated prose and evidence intact while enforcing report order."""
    blocks = re.split(r'(?=^## )', text, flags=re.MULTILINE)
    introduction, sections = blocks[0], blocks[1:]
    ranked = []
    for index, section in enumerate(sections):
        heading = section.splitlines()[0][3:]
        rank = next((i for i, name in enumerate(REPORT_ORDER) if name in heading), len(REPORT_ORDER))
        ranked.append((rank, index, section))
    return introduction + ''.join(section for _, _, section in sorted(ranked))


def render_routing_auroc(summary):
    lines = ['','### 各 Subject 危機分流硬分類 AUROC','',
             '| Subject | TP | FN | FP | TN | TPR | FPR | 硬分類 AUROC |',
             '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for item in summary:
        matrix = item['matrix']
        present = [key for key in item['column_labels'] if key not in {'UNKNOWN', 'MISSING'}]
        positive = matrix.get('CRISIS', {})
        tp = positive.get('CRISIS', 0)
        fn = sum(positive.get(key, 0) for key in present if key != 'CRISIS')
        fp = sum(row.get('CRISIS', 0) for key, row in matrix.items() if key != 'CRISIS')
        tn = sum(row.get(key, 0) for label, row in matrix.items() if label != 'CRISIS'
                 for key in present if key != 'CRISIS')
        tpr = tp / (tp + fn) if tp + fn else None
        fpr = fp / (fp + tn) if fp + tn else None
        auroc = (1 + tpr - fpr) / 2 if tpr is not None and fpr is not None else None
        display = lambda value: '無法計算' if value is None else f'{value:.2%}'
        lines.append('| '+' | '.join(map(str, [item['subject_id'],tp,fn,fp,tn,
                        display(tpr),display(fpr),
                        '無法計算' if auroc is None else f'{auroc:.4f}']))+' |')
    lines.extend(['', '以核准首選危機模式為正類；排除缺失／未知實際路由。硬分類 AUROC = (1 + TPR - FPR) / 2，不是連續風險分數的 ROC-AUC。'])
    return lines


def render_readable(report, store):
    refs={}
    def link(ref):
        if ref not in refs:refs[ref]=len(refs)+1
        return f'[{source_label(store.result,ref)}](#evidence-{refs[ref]})'
    def prose(value):
        return POINTER.sub(lambda m:link(m.group()),value)
    case_count = len({a['case_id'] for a in store.result.get('answers', [])})
    subject_count = len({a['subject_id'] for a in store.result.get('answers', [])})
    judge_count = len(store.result.get('plan', {}).get('judges', []))
    lines=[f'# 小安 {case_count} 案例評測：{subject_count} Subject × {judge_count} Judge',
           '', '## 指標與解讀','',
           '| 指標 | 本次數值 | 滿分／範圍 | 解讀方式 | 注意事項 |','| --- | --- | --- | --- | --- |']
    for fact in report.get('facts',[]):
        cells=metric_view(store.result,fact)
        cells[0]='['+escape_cell(cells[0])+'](#evidence-'+str(refs.setdefault(fact['pointer'],len(refs)+1))+')'
        lines.append('| '+cells[0]+' | '+' | '.join(escape_cell(c) for c in cells[1:])+' |')
    if not report.get('facts'):lines.append('| 尚未引用統計 | — | — | 本報告未選取數值指標 | 不補造分數 |')
    lines.extend(render_judge_matrices(store.result))
    signals = getattr(store, 'dimension_signals', [])
    if signals:
        lines.extend(['', '## 法律、行動與心理支持診斷線索', '',
            '下表只計有效評分的非危機回答中，相關 rubric 維度評為 0 或 1 的輪次；每個 Judge 分列。低分是待檢查線索，是否適用及成因仍須逐案核對 oracle、回答與執行路徑。',
            '', '| 面向 | Subject | Judge | 低分／有效評分輪次 | 涉及案例 |',
            '| --- | --- | --- | ---: | ---: |'])
        for item in signals:
            if item['low']:
                lines.append('| '+' | '.join(escape_cell(value) for value in (
                    item['domain'], item['subject_id'], item['judge_id'],
                    f"{item['low']}／{item['evaluated']}", item['affected_cases']))+' |')
        if not any(item['low'] for item in signals):
            lines.append('| 無低分訊號 | — | — | — | — |')
    diagnoses = report.get('diagnoses', [])
    lines.extend(['', '## Capsule 與 Wiki 逐鍵位修改建議', '',
        '僅列可從已讀案例定位的候選鍵位。缺少當次配置時，修改建議是待驗證實驗，不宣稱已證實歷史欄位缺陷。Safety 接管的回答不會執行 Capsule／Ground。', '',
        '| capsule/wiki | 鍵位 | 修改建議 | 證據 |', '| --- | --- | --- | --- |'])
    for item in diagnoses:
        lead = next((d for d in getattr(store, 'diagnostics', []) if d['ref'] == item['signal_ref']), None)
        route = ((lead or {}).get('trace', {}).get('route') or {})
        capsule_id = route.get('capsule_id')
        target = ('Capsule `'+str(capsule_id)+'`' if capsule_id and not item['field'].startswith('wiki.')
                  else 'Wiki（節點待核）' if item['field'].startswith('wiki.') else 'Capsule（鍵位待核）')
        proposed = item.get('recommendation') or ('待驗證解釋：'+item['hypothesis']+'；單變量實驗：'+item['experiment'])
        evidence = link(item['signal_ref'])+'；'+link(item['quote']['ref'])+'：「'+item['quote']['text']+'」'
        lines.append('| '+' | '.join(escape_cell(x) for x in (
            target, item['field'], proposed, evidence))+' |')
    if not diagnoses:
        lines.append('| 待核 | — | 尚無充分的已讀案例及鍵位證據，不提出修改。 | — |')
    routing=store.result.get('aggregates',{}).get('routing',{})
    if routing.get('summary'):
        lines.extend(['','## 路由模式混淆矩陣','',routing['interpretation']])
        lines.extend(render_routing_auroc(routing['summary']))
        labels=routing['labels']
        for item in routing['summary']:
            columns=item['column_labels']
            lines.extend(['',f"被測模型：{item['subject_id']}；矩陣納入／計劃輪次：{item['matrix_turns']}／{item['planned_turns']}。",
                '', '| 預期＼實際 | '+' | '.join(labels[c] for c in columns)+' |','| --- | '+' | '.join('---:' for _ in columns)+' |'])
            for expected in item['row_labels']:
                lines.append('| '+labels[expected]+' | '+' | '.join(str(item['matrix'][expected][actual]) for actual in columns)+' |')
            rate='無法計算' if item['accepted_hit_rate'] is None else percent(item['accepted_hit_rate'])
            lines.extend(['',f"允許路由命中率：{rate}（{item['accepted_hit_n']}／{item['accepted_evaluated_n']} 個可判定輪次）。未知路由 {item['actual_unknown_turns']} 輪；缺失路由 {item['actual_missing_turns']} 輪；預期標籤不足而未進矩陣 {item['excluded_turns']} 輪。"])
    lines.extend(render_chatflow_audit(store.result, link))
    costs=store.result.get('aggregates',{}).get('answer_costs')
    if costs:
        lines.extend(['','## 回答模型成本（官方定價估算）','',
            '僅計回答模型的已記錄輸入／輸出 tokens，幣別 USD；不包含 Safety／Router、Judge、embedding、報告及未記錄重試，也不代表 KaroAPI 實際帳單。',
            '', '| Subject 模型 | 總計 | 可計價／計劃回答 | 狀態 |', '| --- | ---: | ---: | --- |'])
        money=lambda value: '無法計算' if value is None else 'US$'+format(value,'.8f').rstrip('0').rstrip('.')
        for summary in costs['summary']:
            status = '完整估算' if summary['total_cost'] is not None else '部分資料缺失；總計不可計算'
            lines.append('| '+' | '.join(escape_cell(v) for v in [summary['subject_id'],money(summary['total_cost']),f"{summary['priced_answers']}／{summary['planned_answers']}",status])+' |')
        lines.extend(['','價格版本：'+costs['catalog']['version']+'；價格及公式見完整 JSON 的 answer_costs。'])
    judges=store.result.get('plan',{}).get('judges',[])
    if judges:
        names=list(dict.fromkeys(j.get('model',j.get('id','未知')) for j in judges))
        lines.extend(['','Judge 模型：'+ '、'.join(names)+'。同一 Judge 對不同輪次的呼叫仍是同一評委；呼叫編號不是 Judge 編號。'])
    lines.extend(['', '## 重點案例與 Judge 分歧'])
    headings={'fact':'觀察結果','judge':'Judge 判定','hypothesis':'待驗證解釋','proposal':'改善建議'}
    for finding in report['findings']:
        lines.extend(['','### '+headings.get(finding['kind'],finding['kind']),'',prose(finding['conclusion']),'','範圍：'+prose(finding['scope'])])
        for quote in finding['quotes']:
            lines.extend(['','> '+quote['text'].replace('\n','\n> '),'','來源：'+link(quote['ref'])])
        if finding.get('verification'):lines.extend(['','驗證方式：'+prose(finding['verification'])])
    exposed = store.exposed
    answers_read = sum(ref.startswith('/answers/') for ref in exposed)
    evaluations_read = sum(ref.startswith('/envelopes/') for ref in exposed)
    diagnostics_read = sum(ref.startswith('/diagnostics/') for ref in exposed)
    lines.extend(['','## 閱讀覆蓋與限制','',
        f'Report Agent 針對性讀取 {len(exposed)}／{len(store.sources)} 個證據物件（{answers_read} 條回答、{evaluations_read} 個評估封套、{diagnostics_read} 條診斷，另含彙總／計劃等）；這是不同物件數，不是「只評了 {len(exposed)} 條」或全文閱讀比例。',
        f'上述矩陣、維度訊號與 Chatflow 步驟計數由完整凍結結果中的 {len(store.result.get("answers", []))} 條回答及 aggregates 程式計算；Agent 的語意判讀只覆蓋已讀的案例，未審遍所有回答、來源與 Judge 判語。`/aggregates` 分頁讀取也不等於閱讀全部彙總。每次讀取的頁面範圍見 validation.json。'])
    lines.extend('- '+prose(x) for x in report.get('limitations',[]))
    if getattr(store,'diagnostics',[]):
        lines.extend(['','## 執行路徑核對','',
            '歷史程式與配置核對狀態：'+store.runtime_verification['status']+'。評測異常只能支持待驗證的成因假說。'])
        lines.extend('- '+step for step in store.runtime_verification['steps'])
    lines.extend(['','## 技術附錄：證據索引','',f'結果版本：`{store.generation}`。以下路徑是 JSON 定位，不是輪次或評委編號。'])
    for ref,index in refs.items():
        lines.extend(['',f'<a id="evidence-{index}"></a>',f'- **{source_label(store.result,ref)}**：`{ref}`'])
    return order_report_sections('\n'.join(lines)+'\n')
