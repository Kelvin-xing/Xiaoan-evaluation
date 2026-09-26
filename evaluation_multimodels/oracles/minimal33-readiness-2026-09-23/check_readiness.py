"""离线检查当前 Minimal33；保存 loader 状态、逐轮审核状态和引用差异。"""
from pathlib import Path
from collections import Counter
from dataclasses import asdict
import hashlib
import json
import sys
import yaml

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'evaluation'))
from xiaoan_eval.cases import load_case
from xiaoan_eval.rules import load_rating_rule

selection = json.loads((ROOT / 'docs/plans/evaluation-minimal33.selection.json').read_text())
rows = []
for package in ('evaluation', 'evaluation_multimodels'):
    rule = load_rating_rule(ROOT / package / 'ratings rule.yml')
    for cid in selection['case_ids']:
        p = ROOT / package / 'test-cases' / (cid + '.yaml')
        loaded = load_case(p, rule)
        raw = yaml.safe_load(p.read_text())
        dates = raw['oracle_provenance'].get('source_effective_dates', [])
        if dates:
            assert raw['oracle_provenance']['legal_effective_date'] == max(s['effective_date'] for s in dates)
            assert all(s['official_url'].startswith('https://') and s['date_basis'] for s in dates)
        rows.append({'package': package, 'case_id': cid, 'sha256': hashlib.sha256(p.read_bytes()).hexdigest(),
                     'turn_count': len(loaded.case.turns), 'status': loaded.preflight.status,
                     'issues': [asdict(i) for i in loaded.preflight.issues],
                     'maturity': loaded.case.maturity, 'oracle_status': raw['oracle_provenance']['status'],
                     'legal_effective_date': raw['oracle_provenance']['legal_effective_date'],
                     'legal_date_applicability': loaded.case.oracle_provenance.legal_date_applicability,
                     'reference_status_counts': dict(Counter(t['expected']['reference_oracle']['status'] for t in raw['turns']))})
summary = {package: {'loader_status': dict(Counter(r['status'] for r in rows if r['package'] == package)),
                    'maturity': dict(Counter(r['maturity'] for r in rows if r['package'] == package)),
                    'case_count': sum(r['package'] == package for r in rows),
                    'turn_count': sum(r['turn_count'] for r in rows if r['package'] == package)}
           for package in ('evaluation', 'evaluation_multimodels')}
result = {'checked_at': '2026-09-23', 'pii_validator': 'not_configured', 'summary': summary, 'cases': rows}
(OUT / 'preflight.json').write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
current = dict(selection)
current['selected_at'] = '2026-09-23'
current['purpose'] = 'Minimal33 current case selection after user confirmation and reference repair'
current['provisional_case_ids'] = [r['case_id'] for r in rows if r['package'] == 'evaluation' and r['oracle_status'] == 'provisional']
current['coverage_status'] = '33 reviewed case oracles; new reference contracts remain provisional; source and runtime gaps tracked separately.'
current['parent_selection'] = 'docs/plans/evaluation-minimal33.selection.json'
for c in current['cases']:
    c['sha256'] = hashlib.sha256((ROOT / c['source']).read_bytes()).hexdigest()
current['readiness_report'] = 'evaluation_multimodels/oracles/minimal33-readiness-2026-09-23/preflight.json'
(OUT / 'selection.json').write_text(json.dumps(current, ensure_ascii=False, indent=2) + '\n')
print(json.dumps(summary, ensure_ascii=False, indent=2))
