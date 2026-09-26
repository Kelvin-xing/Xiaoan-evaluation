"""Minimal33引用与三分支静态可达性核对；不调用模型或授予审核。"""
from pathlib import Path
from itertools import combinations
import hashlib
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'tech/chatflow/poc'))
from ground import extract_heading_path_section

BASE = ROOT / 'evaluation_multimodels/oracles'
index = json.loads((BASE / 'content-index-2026-09-23.json').read_text())
snapshot = json.loads((BASE / 'source-snapshot-2026-09-23.json').read_text())
assert index['snapshot_id'] == snapshot['snapshot_id']
assert snapshot['snapshot_id'] == 'sha256:' + hashlib.sha256(json.dumps(snapshot['files'], sort_keys=True).encode()).hexdigest()
for name, digest in snapshot['files'].items():
    assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name
ids = json.loads((ROOT / 'docs/plans/evaluation-minimal33.selection.json').read_text())['case_ids']
rows = []
errors = []


def physical(ref):
    return 'content/' + ref if ref.startswith('knowledge/') else ref


for cid in ids:
    a = yaml.safe_load((ROOT / 'evaluation/test-cases' / (cid + '.yaml')).read_text())
    b = yaml.safe_load((ROOT / 'evaluation_multimodels/test-cases' / (cid + '.yaml')).read_text())
    if a != b:
        errors.append({'case': cid, 'error': '两套YAML不一致'})
    for turn in b['turns']:
        e = turn['expected']
        r = e['reference_oracle']
        g = r['ground']
        assert r['snapshot_id'] == snapshot['snapshot_id']
        refs = e['source_refs'] + e['wiki_refs'] + g['background_source_refs']
        for c in r['route_contracts'].values():
            refs += [c['capsule_ref']] + c['answer_section_refs']
            if c['ground_ref']:
                refs.append(c['ground_ref'])
        for ref in refs:
            name, _, anchor = physical(ref).partition('#')
            p = ROOT / name
            if not p.is_file():
                errors.append({'case': cid, 'turn': turn['turn'], 'ref': ref, 'error': '文件不存在'})
            elif anchor:
                try:
                    extract_heading_path_section(p.read_text(), anchor)
                except ValueError as exc:
                    errors.append({'case': cid, 'turn': turn['turn'], 'ref': ref, 'error': str(exc)})
        for node in g['required_node_ids'] + g['background_node_ids']:
            assert node in index['nodes'], (cid, node)
        routes = {}
        required_nodes = set(g['required_node_ids'])
        required_refs = set(e['source_refs'])
        for route, c in r['route_contracts'].items():
            if route in index['capsules']:
                actual = index['capsules'][route]
                assert c['configured_ground_node_ids'] == actual['configured_ground_node_ids']
                assert c['ground_branches'] == actual['ground_branches']
            branches = c.get('ground_branches', [])
            loaded = []
            for branch in branches:
                meta = index['nodes'][branch['node_id']]
                loaded.append({physical(ref) for role in branch['source_roles'] for ref in meta['source_roles'].get(role, [])})
            all_refs = set().union(*loaded) if loaded else set()
            candidate = None
            if g['activation'] == 'required':
                for count in range(1, min(3, len(branches)) + 1):
                    for combo in combinations(range(len(branches)), count):
                        ns = {branches[i]['node_id'] for i in combo}
                        rs = set().union(*(loaded[i] for i in combo))
                        if required_nodes <= ns and required_refs <= rs:
                            candidate = [i + 1 for i in combo]
                            break
                    if candidate:
                        break
            routes[route] = {
                'missing_nodes': sorted(required_nodes - set(c['configured_ground_node_ids'])),
                'missing_source_refs_by_roles': sorted(required_refs - all_refs),
                'candidate_branch_numbers': candidate,
            }
        rows.append({'case': cid, 'turn': turn['turn'], 'ground': g['activation'],
                     'source_gaps': r.get('source_gaps', []), 'routes': routes,
                     'no_route_has_structural_coverage': g['activation'] == 'required' and not any(v['candidate_branch_numbers'] for v in routes.values())})
summary = {'case_count': len(ids), 'turn_count': len(rows), 'reference_errors': errors,
           'source_gap_turns': sum(bool(r['source_gaps']) for r in rows),
           'required_turns_without_structural_route': sum(r['no_route_has_structural_coverage'] for r in rows),
           'meaning': '静态检查当前节点/来源角色及最多3分支；if条件是否适用、模型是否选择、8000字符预算实际裁剪及回答质量仍需定向运行。'}
(OUT / 'remaining-work.json').write_text(json.dumps({'summary': summary, 'turns': rows}, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
assert not errors
