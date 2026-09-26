from pathlib import Path
import yaml,json,hashlib,html,collections
R=Path('/Users/mingjiexing/xiaoan');O=R/'evaluation_multimodels/oracles/minimal33-update-2026-09-24';O.mkdir(exist_ok=True)
ids=json.loads((R/'docs/plans/evaluation-minimal33.selection.json').read_text())['case_ids'];rows=[]
for cid in ids:
 p=R/'evaluation_multimodels/test-cases'/(cid+'.yaml');d=yaml.safe_load(p.read_text());mirror=yaml.safe_load((R/'evaluation/test-cases'/p.name).read_text());assert d==mirror
 for t in d['turns']:
  rows.append({'case_id':cid,'turn':t['turn'],'user':t['user'],'case_maturity':d.get('maturity'),'scenario_id':d.get('scenario_id','unclassified'),'comparability_group':d.get('comparability_group','default'),'case_oracle_provenance':d['oracle_provenance'],'expected':t['expected'],'case_file':str(p.relative_to(R)),'case_sha256':hashlib.sha256(p.read_bytes()).hexdigest()})
assert len(rows)==100 and len(ids)==33
artifact={'scope':'Minimal33 current contracts after source classification and grouping approval; 33 cases approved for aggregate by user on 2026-09-24','case_count':33,'turn_count':100,'cases':rows}
(O/'contracts-100.json').write_text(json.dumps(artifact,ensure_ascii=False,indent=2)+'\n')
intro='''# Minimal33：100轮引用合同审阅

这是当前两套测试一致的33案、100轮合同导出。每轮均展示用户原话、回答要求、路由、安全标签、来源、Ground条件及完整reference_oracle。当前100轮引用合同均为reviewed；33案成熟度均为APPROVED_AGGREGATE。用户已批准六组、案例等权及minimal33_2026_09_content_v2版本。

## 怎样审阅

检查“允许/优先路由”是否适合该轮及此前用户上下文；required Ground是否确为完成本轮所需；optional表示允许加载，not_applicable表示不要求，unavailable表示证据链尚缺。每条来源需支持实际主张，不能只检查路径存在。route_contracts列出胶囊可配置的全部分支，并不要求全部在该轮注入。semantic_alignment是合同说明，主Judge可见但尚非独立硬评分项。

完整机器版见 `contracts-100.json`；交互版见 `contracts-100.html`。本Markdown按案例顺序包含全部100轮，未抽样。

## 100轮索引

| 轮次 | 用户输入 | 优先路由 | Ground | 必需节点 | 来源缺口 |
| --- | --- | --- | --- | --- | --- |
'''
lines=[intro]
for x in rows:
 e=x['expected'];r=e['reference_oracle'];g=r['ground'];label=f"{x['case_id']}/T{x['turn']}"
 vals=[label,x['user'],e.get('preferred_route_id') or '未指定',g['activation'],'、'.join(g['required_node_ids']) or '—','；'.join(r.get('source_gaps',[])) or '无已记录缺口']
 lines.append('| '+' | '.join(str(v).replace('|','\\|').replace('\n',' ') for v in vals)+' |')
for x in rows:
 e=x['expected'];lines+=['',f"## {x['case_id']}/T{x['turn']}",'',x['user'],'',f"案例成熟度：{x['case_maturity']}；场景：{x['scenario_id']}；可比组：{x['comparability_group']}。",'',f"[原始测试文件]({R/x['case_file']})",'', '```yaml',yaml.safe_dump(e,allow_unicode=True,sort_keys=False,width=120).rstrip(),'```']
(O/'contracts-100.md').write_text('\n'.join(lines)+'\n')
# Self-contained searchable reader, no network/assets or embedded scripts from corpus.
payload=json.dumps(rows,ensure_ascii=False).replace('<','\\u003c')
page='''<!doctype html><html lang="zh-CN"><meta charset="utf-8"><title>Minimal33 100轮引用合同</title><style>body{font:16px/1.65 system-ui;margin:auto;max-width:1150px;padding:28px;color:#172b3a;background:#f5f7fa}header{position:sticky;top:0;background:#f5f7fa;padding:10px 0}input,select,button{font:inherit;padding:7px;margin:4px}details{background:white;border:1px solid #ccd6e0;border-radius:8px;margin:12px 0;padding:14px}summary{cursor:pointer;font-weight:600}pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#f0f4f7;padding:14px;font-size:13px}small{color:#546579}h1{font-size:26px}mark{background:#ffe9b4}.summary{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}.tag{background:#e8eef5;padding:3px 8px;border-radius:5px}</style><h1>Minimal33 · 100轮引用合同</h1><p>完整导出，33案 / 100轮。每轮保留完整 expected，包括回答期待与 reference_oracle。当前100轮 reviewed，33案 APPROVED_AGGREGATE；六组、案例等权及 minimal33_2026_09_content_v2 已获批准。</p><header><input id="q" placeholder="搜索案例、用户原话、来源或条文" size="40"><select id="g"><option value="">全部Ground状态</option><option>required</option><option>optional</option><option>not_applicable</option><option>unavailable</option></select><label><input type="checkbox" id="gap">仅显示来源缺口</label><button id="expand">展开当前全部</button><p id="count"></p></header><main id="rows"></main><script type="application/json" id="data">PAYLOAD</script><script>const data=JSON.parse(document.getElementById('data').textContent);const q=document.getElementById('q'),g=document.getElementById('g'),gap=document.getElementById('gap');function add(p,t,s){let e=document.createElement(t);e.textContent=s;p.append(e);return e}function render(){let rows=data.filter(x=>(!q.value||JSON.stringify(x).toLowerCase().includes(q.value.toLowerCase()))&&(!g.value||x.expected.reference_oracle.ground.activation===g.value)&&(!gap.checked||x.expected.reference_oracle.source_gaps.length));document.getElementById('count').textContent=`显示 ${rows.length} / 100 轮`;const out=document.getElementById('rows');out.replaceChildren();rows.forEach(x=>{let e=x.expected,r=e.reference_oracle,d=add(out,'details','');add(d,'summary',`${x.case_id}/T${x.turn} · ${r.ground.activation} · ${e.preferred_route_id||'未指定优先路由'} — ${x.user}`);add(d,'p',`允许路由：${e.route_ids.join('、')}；安全标签：${e.safety_levels.join('、')}；审核：${r.status}`);add(d,'p',`必需节点：${r.ground.required_node_ids.join('、')||'无'}；来源缺口：${r.source_gaps.join('；')||'无已记录缺口'}`);add(d,'h3','回答要求');add(d,'pre',JSON.stringify(e.response_oracle,null,2));add(d,'h3','完整 expected / reference_oracle');add(d,'pre',JSON.stringify(e,null,2));add(d,'small',`原始文件：${x.case_file}；SHA256：${x.case_sha256}`)})}q.oninput=g.onchange=gap.onchange=render;document.getElementById('expand').onclick=()=>document.querySelectorAll('details').forEach(d=>d.open=true);render();</script></html>'''.replace('PAYLOAD',payload)
(O/'contracts-100.html').write_text(page)
print(collections.Counter(x['expected']['reference_oracle']['ground']['activation'] for x in rows));print('33 cases;100 exact rows; all mirrors equal')
