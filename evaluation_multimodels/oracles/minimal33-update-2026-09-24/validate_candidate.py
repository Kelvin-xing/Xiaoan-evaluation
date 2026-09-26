"""Validate the isolated source integration and propose five turn-level changes."""
from pathlib import Path
import sys,yaml,json,copy
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;C=O/'candidate';sys.path.insert(0,str(R/'tech/chatflow/poc'))
import ground
from capsule_loader import parse_capsule
from capsule_content import parse_ground_branches
from dataclasses import asdict
# Resolve the candidate corpus, not active content.
ground.REPO_ROOT=C;ground.KNOWLEDGE_DIR=C/'content/knowledge';ground.SOURCE_DIR=ground.KNOWLEDGE_DIR/'source';ground.WIKI_NODE_DIR=ground.KNOWLEDGE_DIR/'wiki/nodes'
def nmeta(n):return yaml.safe_load((ground.WIKI_NODE_DIR/(n+'.md')).read_text().split('---',2)[1])
def refs(n,parts):return ['content/'+r for r in nmeta(n)['source_refs'] if any(r.endswith('/'+p) or r.endswith('#'+p) for p in parts)]
P='marital-property-and-debt';J='civil-investigation-and-preservation';F='foreign-civil-evidence'
plan={('TC-61',1):([P,J],refs(P,['第一千零九十二条'])+refs(J,['第一百零三条','第一百零四条','第一百零五条'])),('TC-61',2):([J],refs(J,['第六十四条','第六十七条','第二十条'])),('TC-61',3):([P,J],refs(P,['第一千零六十四条','第一千零九十二条'])+refs(J,['第二十条'])),('TC-62',1):([],[]),('TC-62',2):([F],refs(F,['第十六条','第十七条','二、','四、']))}
changes=[];checks=[]
for cid in ['TC-61','TC-62']:
 d=yaml.safe_load((R/'evaluation_multimodels/test-cases'/(cid+'.yaml')).read_text())
 for t in d['turns']:
  key=cid,t['turn']
  if key not in plan:continue
  e=t['expected'];before=copy.deepcopy(e);r=e['reference_oracle'];g=r['ground'];nodes,rr=plan[key]
  r['previous_review']={k:r.get(k) for k in ['status','reviewed_by','reviewed_at','snapshot_id']};r.update(status='provisional',reviewed_by=None,reviewed_at=None,authored_at='2026-09-24')
  r['review_basis']='2026-09-24用户接受的旧版本保存在accepted-contracts-receipt.json；本轮补齐来源后新增必需集合尚未包含在该接受中。'
  g.update(activation='required' if nodes else 'optional',required_node_ids=nodes,background_node_ids=[] if nodes else [F],background_source_refs=[] if nodes else refs(F,['第十一条','第十四条','第十五条']))
  g['reason']='由已核对的民事财产调查或境外证据规则承载本轮法律问题，保留程序条件及结果不保证。' if nodes else '本轮为披露已持材料，允许保存与来源说明；不强迫展开全部提交手续。'
  e['source_refs']=rr;e['wiki_refs']=['content/knowledge/wiki/nodes/'+n+'.md' for n in nodes];r['source_gaps']=[]
  r['revision_note']='五轮来源补充；回答期待、路由和安全标签保持用户已接受内容。'
  changes.append({'case':cid,'turn':t['turn'],'accepted_expected':before,'proposed_expected':copy.deepcopy(e)})
  for route in e['route_ids']:
   if route not in ['n5e','n2a']:continue
   cap=parse_capsule(next((C/'content/capsule').glob(('N5e' if route=='n5e' else 'N2a')+' *')));bs=parse_ground_branches(cap.ground)
   selected=[]
   for n in nodes or [F]:
    available=[i+1 for i,b in enumerate(bs) if b.node_id==n]
    selected.append(next(i for i in available if n!=F or 'institutional_implementation' in bs[i-1].source_roles))
   items,warning=ground.resolve_ground_branches(bs,tuple(selected));actual={x.ref for x in items}|{x.source_ref for x in items};want={s.removeprefix('content/') for s in rr or g['background_source_refs']}
   assert want<=actual,(key,route,want-actual)
   checks.append({'case':cid,'turn':t['turn'],'route':route,'branches':selected,'chars':sum(ground.ground_item_size(x) for x in items),'required_refs_present':True,'omitted':warning})
 # Effective date sources bind the new physical files; case-level response review stays intact.
 dates=d['oracle_provenance']['source_effective_dates']
 for x in dates:
  if '民事诉讼法' in x['title'] and '证据' not in x['title']:
   x['local_source']='content/knowledge/source/087-中华人民共和国民事诉讼法.md';x['text_url']='https://www.szgm.gov.cn/gmsfj/gkmlpt/content/11/11422/post_11422196.html'
  if '证据的若干规定' in x['title']:x['local_source']='content/knowledge/source/088-最高人民法院关于民事诉讼证据的若干规定.md'
  if '取消外国' in x['title']:x['local_source']='content/knowledge/source/089-驻美使领馆停办领事认证业务通知.md';x['relevance']+='；本地收录使馆实施通知，非公约全文'
 if cid=='TC-61':dates.append({'title':'最高人民法院关于民事诉讼证据的若干规定（2019年修正）','effective_date':'2020-05-01','official_url':'https://www.court.gov.cn/zixun/xiangqing/212721.html','date_basis':'最高法修改决定公告','local_source':'content/knowledge/source/088-最高人民法院关于民事诉讼证据的若干规定.md','relevance':'第二十条，法院调查申请的时点和内容'})
 for pkg in ['evaluation','evaluation_multimodels']:(C/pkg/'test-cases'/(cid+'.yaml')).write_text(yaml.safe_dump(d,allow_unicode=True,sort_keys=False,width=120))
(O/'five-turn-contract-changes.json').write_text(json.dumps(changes,ensure_ascii=False,indent=2)+'\n')
(O/'candidate-validation.json').write_text(json.dumps({'status':'PASS_CANDIDATE_ONLY','classification':'proposed_not_confirmed','source_gaps_after_integration':0,'checks':checks},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(checks,ensure_ascii=False,indent=2))
