from pathlib import Path
import re,yaml,hashlib,json
O=Path(__file__).resolve().parent;C=O/'candidate';K=C/'content/knowledge'
# Retain the statute's real parent hierarchy in the new extract.
p=next((K/'source').glob('087-*'));s=p.read_text();s=s.replace('## 第五章 诉讼参加人','## 第一编 总则\n\n### 第五章 诉讼参加人').replace('### 第二节','#### 第二节').replace('#### 第六十四条','##### 第六十四条').replace('## 第六章','### 第六章').replace('## 第九章','### 第九章');s=re.sub(r'^### (第[^\n]+条)$',r'#### \1',s,flags=re.M);p.write_text(s)
for p in (C/'content').rglob('*.md'):
 if p.name.startswith('087-'):continue
 s=p.read_text();t=s.replace('087-中华人民共和国民事诉讼法.md#中华人民共和国民事诉讼法/','087-中华人民共和国民事诉讼法.md#中华人民共和国民事诉讼法/第一编 总则/')
 if t!=s:p.write_text(t)
for pkg in ['evaluation','evaluation_multimodels']:
 for p in (C/pkg/'test-cases').glob('TC-6[12].yaml'):
  s=p.read_text().replace('087-中华人民共和国民事诉讼法.md#中华人民共和国民事诉讼法/','087-中华人民共和国民事诉讼法.md#中华人民共和国民事诉讼法/第一编 总则/');p.write_text(s)
new=[next((K/'source').glob(n+'-*')) for n in ['087','088','089']]
p=K/'source/目录.md';s=p.read_text();s+='\n## 2026-09-24 新增来源（候选）\n\n| canonical ID | 文件 | source_code | source_tier | 正式标题 | 发布机构 |\n| --- | --- | --- | --- | --- | --- |\n'
for f in new:
 m=yaml.safe_load(f.read_text().split('---',2)[1]);s+=f"| {f.name[:3]} | {f.name[4:]} | {m['source_code']} | {m['source_tier']} | {m['official_title']} | {m['issuer']} |\n"
s+='\n当前候选含87份活跃来源，永久退役055、061不复用；下一新增ID为090。分类确认后方可转为正式入库记录。\n';p.write_text(s)
p=K/'source/source-文件处理规范.md';s=p.read_text().replace('当前共有84份活跃资料','2026-09-24候选新增087—089后共有87份活跃资料').replace('`001`–`086` 中除 `055`、`061` 外的84个编号','`001`–`089` 中除 `055`、`061` 外的87个编号').replace('下一份从 `087` 开始','下一份从 `090` 开始');p.write_text(s)
p=K/'wiki/source-registry.md';s=p.read_text();rows=''
for f in new:
 m=yaml.safe_load(f.read_text().split('---',2)[1]);rows+=f"| {f.name[:3]} | `{f.name}` | {m['source_code']} | {m['source_tier']} | `{hashlib.sha256(f.read_bytes()).hexdigest()}` | `incorporated` | — |\n"
match=re.search(r'^\| 086 \|.*\n',s,re.M);assert match;s=s[:match.end()]+rows+s[match.end():]
s=s.replace('当前共有84份active canonical source','当前候选共有87份active canonical source').replace('updated: 2026-09-20','updated: 2026-09-24')
h=hashlib.sha256()
for f in sorted((K/'source').glob('[0-9][0-9][0-9]-*.md')):
 h.update(f.name.encode());h.update(b'\0');h.update(hashlib.sha256(f.read_bytes()).hexdigest().encode());h.update(b'\n')
s=re.sub(r'当前 source snapshot：`sha256:[a-f0-9]+`','当前 source snapshot：`sha256:'+h.hexdigest()+'`',s)
s+='''\n## 2026-09-24 程序与境外证据增量（候选）

- 087：处理第64、67、70、103—106、108条；调查和保全独立概念进入civil-investigation-and-preservation。第70条暂作上下文保留，不为覆盖而添加无关节点。
- 088：处理第11、14—17、20条；第20条支持调查申请，其余支持foreign-civil-evidence。
- 089：四项通知全文已核对；第二、四项以institutional_implementation挂靠境外证据节点，第16条司法解释承担法律依据，不让通知单独承重。
- 两个新增节点均为needs-review；不增加缺乏必要性的关系边。原有4项开放风险范围与限制不变，manifest未接受。候选分类待确认，正式目录尚未改变。
''';p.write_text(s)
p=K/'index.md';s=p.read_text().replace('84 份 active source','87 份 active source').replace('节点：23','节点：25').replace('23个节点','25个节点').replace('`incorporated`：79份','`incorporated`：82份');pos=s.index('\n## 综合页');s=s[:pos].rstrip()+'\n| [[civil-investigation-and-preservation]] | procedure | 法院调查申请、诉前及诉中保全条件与责任。 |\n| [[foreign-civil-evidence]] | procedure | 境外文书证明手续、中文译本及中美附加证明书边界。 |\n'+s[pos:];p.write_text(s)
p=K/'wiki/legal-mechanism-tree.md';s=p.read_text().replace('## 实施与比较背景','- [[civil-investigation-and-preservation]]\n- [[foreign-civil-evidence]]\n\n## 实施与比较背景');p.write_text(s)
p=K/'log.md';p.write_text(p.read_text()+'''\n## 2026-09-24 程序与境外证据补充候选

新增087—089完整相关条文及通知，新增两个needs-review节点，N5e/N2a条件接入。美国实施通知分支须用户上下文明确材料在美国形成；未知国家只加载通用证据规则。TEXT_ONLY素材与现有Ground配置，无新增工具能力。五轮合同增量另行记录；分类及候选激活状态见本次审核记录。\n''')
print('candidate inventories and statute hierarchy synchronized')
