"""Refresh descriptive inventories from cases, never author or approve labels."""
from pathlib import Path
import json,csv,re,yaml
ROOT=Path(__file__).resolve().parents[2]
from audit_reference_oracles import audit

def refresh():
    result=audit(ROOT)
    assert not result['errors'],result['errors']
    directory=ROOT/'evaluation/oracles'
    (directory/'reference-integrity-2026-09-14.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    rows=[];brief=[]
    files=sorted((ROOT/'evaluation/test-cases').glob('TC-*.yaml'))+sorted((ROOT/'evaluation/test-cases/proposed').glob('TC-*.yaml'))
    for p in files:
        c=yaml.safe_load(p.read_text())
        for t in c['turns']:
            e=t['expected'];r=e['reference_oracle'];proposal=p.parent.name=='proposed'
            brief.append({'case':c['id'],'proposal':proposal,'turn':t['turn'],'routes':e['route_ids'],'safety':e['safety_levels'],'ground':r['ground']['activation'],'source_refs':e['source_refs'],'wiki_refs':e['wiki_refs'],'gaps':r['source_gaps']})
            if proposal:continue
            rows.append({'case':c['id'],'turn':t['turn'],'user':t['user'],'prior_capsule_ids':' | '.join(r['prior_labels'].get('capsule_ids',[])),'route_ids':' | '.join(e['route_ids']),'preferred_route_id':e['preferred_route_id'],'safety_levels':' | '.join(e['safety_levels']),'ground_activation':r['ground']['activation'],'required_node_ids':' | '.join(r['ground']['required_node_ids']),'source_refs':' | '.join(e['source_refs']),'wiki_refs':' | '.join(e['wiki_refs']),'source_gaps':' | '.join(r['source_gaps']),'runtime_ground_gaps':json.dumps(r['runtime_ground_gaps'],ensure_ascii=False),'status':r['status']})
    with (directory/'reference-review-2026-09-14.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(rows[0]));w.writeheader();w.writerows(rows)
    (directory/'reference-refresh-2026-09-14.json').write_text(json.dumps(brief,ensure_ascii=False,indent=2)+'\n')
    p=directory/'README.zh-CN.md';s=p.read_text()
    for k,v in result['ground_counts'].items():s=re.sub(r'\| '+k+r' \| \d+ \|',f'| {k} | {v} |',s)
    s=re.sub(r'\*\*\d+ 轮\*\*的待审核必需节点',f'**{len(result["runtime_ground_gap_turns"])} 轮**的待审核必需节点',s)
    s=s.replace('Ground recall/precision 在原框架仍为未实现','Ground recall/precision 在原框架仍为未实现')
    if '2026-09-14 后续' not in s:
        s+='\n\n## 2026-09-14 后续：原32案96轮完整复审\n\n逐轮必要/禁止行为、允许替代、争议及独立风险依据见 [完整复审包](minimal32-completion/README.zh-CN.md)。新增标签仍待人工审阅。上方引用统计已按复审后的标签刷新；25轮的相关专题有来源缺口，其中部分本轮只需支持/澄清，不再强制检索。原先关于没有统一长度约束的描述需以实际捕获prompt修正：普通回答有300字硬上限，明确展开有500字上限，危机另按其合同。\n'
    p.write_text(s)
    for name in ['reference-integrity-2026-09-14.json','reference-review-2026-09-14.csv','reference-refresh-2026-09-14.json','README.zh-CN.md']:(ROOT/'evaluation_multimodels/oracles'/name).write_bytes((directory/name).read_bytes())
    print(result['status'],result['ground_counts'],'runtime gaps',len(result['runtime_ground_gap_turns']))
if __name__=='__main__':refresh()
