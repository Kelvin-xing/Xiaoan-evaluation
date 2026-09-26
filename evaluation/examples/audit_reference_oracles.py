"""Offline reference inventory audit. Does not call providers or approve labels.

Run from repository root:
  python evaluation/examples/audit_reference_oracles.py --output /tmp/oracle-audit.json
"""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'evaluation'))
sys.path.insert(0, str(ROOT / 'tech/chatflow/poc'))
from xiaoan_eval.reference_oracle import parse_reference_oracle
from ground import extract_heading_path_section


def audit(root=ROOT):
    errors, rows, stale = [], [], []
    snapshot_name = 'source-snapshot-2026-09-14.json' if (root/'evaluation/oracles/source-snapshot-2026-09-14.json').exists() else 'source-snapshot-2026-09-13.json'
    snapshot = json.loads((root/'evaluation/oracles'/snapshot_name).read_text())
    expected_id = 'sha256:' + hashlib.sha256(json.dumps(snapshot['files'], sort_keys=True).encode()).hexdigest()
    if snapshot['snapshot_id'] != expected_id:
        errors.append('snapshot manifest digest mismatch')
    for name, digest in snapshot['files'].items():
        p = root/name
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest() != digest:
            errors.append(f'snapshot drift: {name}')
    capsules = {c['id']: c for c in json.loads((root/'tech/chatflow/poc/capsules.json').read_text())}

    def check_ref(ref, location):
        name, _, anchor = ref.partition('#')
        p = root/name
        if not p.is_file():
            errors.append(f'{location}: missing ref {ref}')
        elif name not in snapshot['files']:
            errors.append(f'{location}: ref outside versioned snapshot {ref}')
        elif anchor:
            try:
                extract_heading_path_section(p.read_text(), anchor)
            except ValueError as exc:
                errors.append(f'{location}: {ref}: {exc}')

    for p in sorted((root/'content/knowledge/wiki/nodes').glob('*.md')):
        text = p.read_text()
        frontmatter = yaml.safe_load(text.split('---', 2)[1])
        for ref in frontmatter.get('source_refs', []):
            name = ref.partition('#')[0]
            source_path = root/'content'/name if name.startswith('knowledge/source/') else root/name
            if not source_path.is_file():
                stale.append({'wiki': str(p.relative_to(root)), 'ref': ref})
    for package in ('evaluation', 'evaluation_multimodels'):
        package_root = root/package
        other_snapshot = json.loads((package_root/'oracles'/snapshot_name).read_text())
        if other_snapshot != snapshot:
            errors.append(f'{package}: snapshot differs')
        files = sorted((package_root/'test-cases').glob('TC-*.yaml')) + sorted((package_root/'test-cases/proposed').glob('TC-*.yaml'))
        for p in files:
            case = yaml.safe_load(p.read_text())
            for turn in case['turns']:
                label = f'{package}/{case["id"]}/T{turn["turn"]}'
                e = turn['expected']
                try:
                    c = parse_reference_oracle(e.get('reference_oracle'))
                    if not c:
                        raise ValueError('missing reference_oracle')
                except ValueError as exc:
                    errors.append(f'{label}: {exc}')
                    continue
                if c['snapshot_id'] != snapshot['snapshot_id']:
                    errors.append(f'{label}: wrong snapshot_id')
                if set(e['route_ids']) != set(c['route_contracts']) or e['capsule_ids'] != e['route_ids'] or e['preferred_route_id'] not in e['route_ids']:
                    errors.append(f'{label}: route/capsule contract mismatch')
                if not set(e['safety_levels']) <= {'normal', 'self_harm', 'immediate_danger'} or not e['safety_levels']:
                    errors.append(f'{label}: invalid safety label')
                for route, contract in c['route_contracts'].items():
                    if route in capsules:
                        current = capsules[route]
                        if contract['capsule_ref'] != current['path'] or contract['configured_ground_node_ids'] != current['ground'].get('nodes', []):
                            errors.append(f'{label}: runtime capsule contract drift')
                    elif route not in {'baseline','crisis_sop'}:
                        errors.append(f'{label}: unregistered route {route}')
                    check_ref(contract['capsule_ref'], label)
                    for ref in contract.get('answer_section_refs', []):
                        check_ref(ref, label)
                    if contract['ground_ref']:
                        check_ref(contract['ground_ref'], label)
                for ref in e['source_refs'] + e['wiki_refs'] + c['ground']['background_source_refs']:
                    check_ref(ref, label)
                for node in c['ground']['required_node_ids'] + c['ground']['background_node_ids']:
                    check_ref(f'content/knowledge/wiki/nodes/{node}.md', label)
                if c['ground']['activation'] == 'required' and (not e['source_refs'] or not e['wiki_refs']):
                    errors.append(f'{label}: required evidence lacks refs')
                response = e.get('response_oracle', {})
                if not response.get('required_claims') or not response.get('forbidden_claims'):
                    errors.append(f'{label}: incomplete response oracle')
                if package == 'evaluation':
                    mirror = root/'evaluation_multimodels'/p.relative_to(package_root)
                    if yaml.safe_load(mirror.read_text()) != case:
                        errors.append(f'{label}: mirror differs')
                    rows.append({'case':case['id'],'turn':turn['turn'],'proposal':p.parent.name=='proposed',
                                 'ground':c['ground']['activation'],'source_gaps':c['source_gaps'],
                                 'runtime_ground_gaps':c.get('runtime_ground_gaps',{})})
    canonical = [r for r in rows if not r['proposal']]
    return {'status':'PASS' if not errors else 'FAIL', 'meaning':'Reference integrity only; not legal approval or model correctness.',
            'snapshot_id':snapshot['snapshot_id'], 'case_count':len({r['case'] for r in canonical}), 'turn_count':len(canonical),
            'proposed_turn_count':len(rows)-len(canonical), 'ground_counts':dict(Counter(r['ground'] for r in canonical)),
            'source_gap_turns':[r for r in canonical if r['source_gaps']],
            'runtime_ground_gap_turns':[r for r in canonical if r['runtime_ground_gaps']],
            'stale_wiki_source_refs':stale, 'errors':errors}


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path)
    args=parser.parse_args()
    result=audit()
    body=json.dumps(result,ensure_ascii=False,indent=2)+'\n'
    if args.output:
        args.output.write_text(body)
    print(json.dumps({k:v for k,v in result.items() if k not in {'source_gap_turns','runtime_ground_gap_turns','stale_wiki_source_refs'}},ensure_ascii=False))
    print('source gap turns:',len(result['source_gap_turns']),'runtime ground gap turns:',len(result['runtime_ground_gap_turns']),'stale wiki source refs:',len(result['stale_wiki_source_refs']))
    sys.exit(bool(result['errors']))
