"""Prepare an isolated, reviewable candidate; never assigns human approval or edits active content."""
from pathlib import Path
import shutil,yaml,json,sys
R=Path(__file__).resolve().parents[3];O=Path(__file__).resolve().parent;C=O/'candidate';P=R/'evaluation_multimodels/oracles/minimal33-completion-2026-09-23'
C.mkdir(exist_ok=True)
for sub in ['content','evaluation/test-cases','evaluation_multimodels/test-cases']:
 shutil.copytree(R/sub,C/sub,dirs_exist_ok=True)
for p in (P/'pending-sources').glob('*.md'):
 text=p.read_text();m=yaml.safe_load(text.split('---',2)[1]);body=text.split('---',2)[2]
 meta={'source_code':m['proposed_source_code'],'source_tier':m['proposed_source_tier'],**{k:m[k] for k in ['official_title','issuer','effective_year','url']}}
 meta['notes']=[s.replace('；待人工确认分类后方可入库','').replace('；分类待人工确认','') for s in m['notes']]
 meta['notes'].append('整理说明：本文件为待确认分类的隔离候选，未获人工法律审核。')
 (C/'content/knowledge/source'/p.name).write_text('---\n'+yaml.safe_dump(meta,allow_unicode=True,sort_keys=False)+'---'+body)
for p in (P/'pending-wiki').glob('*.md'):
 (C/'content/knowledge/wiki/nodes'/p.name).write_text(p.read_text().replace("updated: '2026-09-23'","updated: '2026-09-24'"))
# Split general foreign evidence and US implementation at the branch level.
# Foreign legal rules stay reusable for other countries without injecting US-only instructions.
foreign='foreign-civil-evidence';civil='civil-investigation-and-preservation';property='marital-property-and-debt'
def add_caps(prefix):
 p=next((C/'content/capsule').glob(prefix+' *'));s=p.read_text()
 addition=f'''- if: 用户在家暴相关离婚或财产争议中询问法院、代理律师如何调查银行卡流水、车辆、房产或债务线索，或如何申请诉前、诉中财产保全
  node: {civil}
  source_roles:
    - legal_basis

- if: 用户询问境外出警、就医或其他境外材料在中国内地民事诉讼中的保存、证明手续、中文翻译及证明力，尚未明确材料在美国形成
  node: {foreign}
  source_roles:
    - legal_basis

- if: 当前或既往用户消息已明确证据材料在美国形成，用户询问美国出警、就医记录在中国内地诉讼中的保存、提交、附加证明书或翻译手续
  node: {foreign}
  source_roles:
    - legal_basis
    - institutional_implementation

'''
 if prefix=='N2a':addition+=f'''- if: 用户询问离婚前后夫妻财产被转移、隐匿或伪造共同债务，需先区分财产归属与债务性质
  node: {property}
  source_roles:
    - legal_basis

'''
 s=s.replace('# related_capsules',addition+'# related_capsules')
 material='''## 财产调查与境外材料

- 只有车牌、旧银行卡号等线索时，说明可与代理律师整理书面调查申请：指出证据内容、无法自行取得的客观原因、待证明事实和明确线索，在举证期限届满前提交；不保证法院查到全部财产或全额追回。
- 财产保全须区分诉中与紧急诉前申请；解释担保、范围、紧急裁定及诉前保全后30日内起诉或仲裁的条件，不把所有申请概括为免费、免担保或必然冻结。
- 对境外出警、医疗材料先确认形成国家、出具机构、材料种类及当前婚姻状态，保留原始材料与来源记录，准备中文译本并向受理法院核对手续；不要一概要求领事认证，或保证办妥手续后必然采信。
- 已明确是美国形成、送中国内地使用的材料时，说明公约范围内公文书可走美国附加证明书路径，仍应核对文书类型及法院要求；附加证明书不证明全部事实真实，不把警察记录与医院报告自动当作同类公文书。

'''
 s=s.replace('# act\n','# act\n\n'+material,1)
 if prefix=='N2a':s=s.replace('# triggers\n','# triggers\n\n- "美国的报警和医院记录在国内法院能用吗" / "只有银行卡号和车牌，能不能请法院查"\n',1)
 (C/'content/capsule'/p.name).write_text(s)
for cap in ['N5e','N2a']:add_caps(cap)
print('candidate sources, nodes and 2 capsules prepared; active content untouched')
