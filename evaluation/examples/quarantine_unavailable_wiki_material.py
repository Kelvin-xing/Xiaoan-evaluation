"""Quarantine genuinely unavailable material while retaining supported node claims.

Runs on the isolated draft only. No source is deleted or rewritten. This records
loss of support explicitly; it is not a legal approval or accepted Wiki rebuild.
"""
from pathlib import Path
import json,re,sys
ROOT=Path(__file__).resolve().parents[2]
STAGE=Path('/tmp/xiaoan-remediation-stage-20260914')
OUT=ROOT/'evaluation/oracles/minimal32-remediation'
sys.path.insert(0,str(ROOT/'tech/chatflow/poc'))
from ground import extract_heading_path_section
records=[]
p=STAGE/'content/knowledge/wiki/nodes/protection-order-evidence.md';s=p.read_text()
ref='knowledge/source/practice/87-人身安全保护令实务.md#三申请流程'
assert 'legacy-87' in (ROOT/'content/knowledge/source/source-文件处理规范.md').read_text()
section=extract_heading_path_section((ROOT/'content/knowledge/source/045-最高法关于人身安全保护令适用法律规定.md').read_text(),'第六条')
assert '较大可能性' in section and '(十一)' in section
removed=[line for line in s.splitlines() if '87-人身安全保护令实务' in line]
s='\n'.join(line for line in s.splitlines() if '87-人身安全保护令实务' not in line)+'\n'
s += '\n## 来源迁移待审\n\n旧实务资料 legacy-87 已由来源目录登记退役，不能继续作为依据。证明标准和证据类型保留对 canonical 045 第六条及反家暴法第二十条的引用；未恢复上海数据或其他实务补充。此处只核对上述来源关系，不代表整篇法律审核通过。\n'
s=s.replace('status: draft','status: needs-review')
p.write_text(s)
records.append({'node':str(p.relative_to(STAGE)),'reason':'legacy-87 explicitly retired in source handling rules; retained primary-source support independently checked','removed_material':removed,'remaining_basis':'content/knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#第六条','basis_excerpt':section})
p=STAGE/'content/knowledge/wiki/nodes/injury-appraisal-procedure.md';s=p.read_text()
start=s.index('### 就医取证要点');end=s.index('## 适用边界',start)
removed=s[start:end]
s=s[:start]+'### 未核实的医疗操作资料\n\n原医院/法医帮助资料不在当前来源库中，其具体操作建议已移出本节点，保留在迁移审计记录待核验。此缺口不影响下列公安处理规定的独立引用，不得把来源迁移视为医学建议审核通过。\n\n'+s[end:]
s='\n'.join(line for line in s.splitlines() if 'knowledge/source/如何寻求医院及法医鉴定的帮助.md' not in line)+'\n'
# Existing prose already cites these provisions; bind exact sections instead of
# claiming four initial refs support every procedural detail.
for anchor in ('第十二条','第三十一条','第三十九条'):
    extract_heading_path_section((ROOT/'content/knowledge/source/053-公安机关办理伤害案件规定.md').read_text(),anchor)
    s=s.replace('source_refs:\n','source_refs:\n  - "knowledge/source/053-公安机关办理伤害案件规定.md#'+anchor+'"\n',1)
s=s.replace('来源类型：`agency_rule`（tier 2）','来源分类：当前 source frontmatter 为 `G` / `source_tier: 2`（机关规范性文件）')
s=s.replace('status: draft','status: needs-review');p.write_text(s)
records.append({'node':str(p.relative_to(STAGE)),'reason':'named hospital/forensic source absent from current corpus; medical instructions remain unavailable, not replaced by model knowledge','removed_material':removed})
(OUT/'quarantined-material.json').write_text(json.dumps(records,ensure_ascii=False,indent=2)+'\n')
print('quarantined two unavailable dependencies; sources untouched; Wiki approval not advanced')
