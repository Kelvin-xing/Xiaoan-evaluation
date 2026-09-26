"""Offline calibration datasets, comparisons and explicit adoption receipts.

This module never invokes an agent, sends gold to a Judge, or activates a
candidate configuration. Human decisions are inputs, not inferred approval.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

from xiaoan_eval_core.contracts import digest
from .frozen_review import _evaluation, _resolve


def freeze_split(case_ids, *, metadata=None, seed=33):
    """Freeze exactly 22 development and 11 holdout cases, stratified by scenario.

    IDs alone are safe to expose to development; holdout labels/content are not.
    Metadata records scenario, red-line/error categories and selection rationale.
    """
    if len(case_ids) != 33 or len(set(case_ids)) != 33:
        raise ValueError('initial calibration requires exactly 33 unique case IDs')
    metadata = metadata or {}
    groups = {}
    for case in case_ids:
        groups.setdefault(metadata.get(case, {}).get('scenario_id', 'unspecified'), []).append(case)
    groups = {key: sorted(values, key=lambda c: hashlib.sha256(f'{seed}:{c}'.encode()).hexdigest())
              for key, values in sorted(groups.items())}
    counts = {key: len(values) // 3 for key, values in groups.items()}
    remaining = 11 - sum(counts.values())
    for key in sorted(groups, key=lambda key: (-(len(groups[key]) % 3), key))[:remaining]:
        counts[key] += 1
    validation = [case for key, values in groups.items() for case in values[:counts[key]]]
    calibration = [case for case in case_ids if case not in validation]
    result = {'schema_version': 'frozen-calibration-split/v1', 'seed': seed,
              'calibration_case_ids': calibration, 'validation_case_ids': validation,
              'case_metadata': deepcopy(metadata), 'selection_basis': 'scenario-stratified seeded hash; case grouping',
              'validation_status': 'INDEPENDENT', 'case_source_digest': digest(list(case_ids))}
    result['split_digest'] = digest(result)
    return result


def validate_split(split):
    actual = {k: v for k, v in split.items() if k != 'split_digest'}
    if digest(actual) != split.get('split_digest'):
        raise ValueError('split digest mismatch')
    train, test = split['calibration_case_ids'], split['validation_case_ids']
    if len(train) != 22 or len(test) != 11 or len(set(train + test)) != 33:
        raise ValueError('case partition leakage or invalid 22/11 split')


def mark_validation_used_for_development(split, *, reason):
    if not reason:
        raise ValueError('development reuse requires reason')
    validate_split(split)
    out = deepcopy(split)
    out['validation_status'] = 'USED_FOR_DEVELOPMENT'
    out['reuse_reason'] = reason
    out.pop('split_digest')
    out['split_digest'] = digest(out)
    return out


def build_benchmark(results, split, *, partition='calibration', purpose='development'):
    """Export only the requested partition; independent holdout needs final-validation purpose."""
    from xiaoan_eval_core.results import validate_complete_results
    validate_complete_results(results)
    validate_split(split)
    if partition not in {'calibration', 'validation'}:
        raise ValueError('unknown calibration partition')
    if partition == 'validation' and purpose != 'final-validation':
        raise ValueError('holdout labels are excluded from prompt-development exports')
    if partition == 'validation' and split['validation_status'] != 'INDEPENDENT':
        raise ValueError('validation set has been used for development; supply new independent cases')
    selected = set(split[partition + '_case_ids'])
    answers = {a['answer_id']: a for a in results['answers']}
    items = []
    for envelope in results['envelopes']:
        answer = answers[envelope['answer_id']]
        if answer['case_id'] not in selected:
            continue
        # Latest human submission per judge determines eligibility, not any old approval.
        latest = {r['judge_id']: r for r in envelope.get('human_review', [])}
        for judge, review in latest.items():
            if not review.get('confirmed_by') or not review.get('gold_eligible'):
                continue
            automatic = deepcopy(_evaluation(envelope, judge))
            actual_hash = hashlib.sha256(answer['answer'].encode()).hexdigest() if isinstance(answer.get('answer'), str) else None
            if review.get('assessment_digest') != digest(automatic) or review.get('answer_sha256') != actual_hash:
                raise ValueError('human benchmark binding mismatch')
            labels = deepcopy(automatic)
            if review['decision'] == 'REJECT':
                for revision in review['revisions']:
                    parts = revision['pointer'].rsplit('/', 1)
                    target = _resolve(labels, parts[0])
                    key = parts[1].replace('~1', '/').replace('~0', '~')
                    target[int(key) if isinstance(target, list) else key] = deepcopy(revision['value'])
                    if '/dimension_details/' in revision['pointer'] and key == 'score':
                        rubric = labels['rubric']['rubric']
                        module = target.get('module', target.get('id'))
                        if module in rubric.get('scores', {}):
                            rubric['scores'][module] = revision['value']
                            weights = rubric.get('final_weights', {})
                            if weights and all(k in rubric['scores'] for k in weights):
                                rubric['weighted_total'] = sum(rubric['scores'][k] * v for k, v in weights.items())
            elif review['decision'] != 'APPROVE':
                continue
            items.append({'answer_id': answer['answer_id'], 'case_id': answer['case_id'],
                          'turn': answer['turn'], 'subject_id': answer['subject_id'], 'judge_id': judge,
                          'row_digest': answer.get('row_digest'), 'frozen_input_digest': digest(answer), 'answer_sha256': review['answer_sha256'],
                          'automatic': automatic, 'gold': labels, 'review_id': review['review_id'],
                          'revisions': deepcopy(review.get('revisions', [])),
                          'confirmed_by': review['confirmed_by']})
    result = {'schema_version': 'frozen-calibration-benchmark/v1', 'partition': partition,
              'split_digest': split['split_digest'], 'source_core_digest': results['core_digest'],
              'planned_case_ids': sorted(selected), 'labelled_case_ids': sorted({i['case_id'] for i in items}),
              'items': items}
    result['benchmark_digest'] = digest(result)
    return result


def judge_inputs(results, case_ids):
    """Only frozen answer inputs: never human labels, scores or final overlays."""
    keys = {'answer_id', 'case_id', 'turn', 'subject_id', 'subject_model', 'question', 'answer',
            'history', 'context', 'reference_facts', 'truth_status', 'truth_version', 'requirements',
            'quality_focus', 'status', 'answer_sha256', 'row_digest', 'observations'}
    selected = set(case_ids)
    return [{k: deepcopy(v) for k, v in a.items() if k in keys}
            for a in results['answers'] if a['case_id'] in selected]


def snapshot_calibration(directory, baseline_config, candidate_config, split, *, changes):
    """Create immutable config snapshots. A new directory is required for each candidate."""
    validate_split(split)
    if not changes.strip():
        raise ValueError('candidate changes require rationale')
    target = Path(directory)
    if target.exists():
        raise ValueError('calibration directory exists; use a new candidate version')
    snapshots = {}
    for role, root in [('baseline-config', Path(baseline_config)), ('candidate-config', Path(candidate_config))]:
        if not root.is_dir():
            raise ValueError('configuration directory missing')
        content = {}
        for file in sorted(root.rglob('*')):
            if file.is_symlink():
                raise ValueError('config snapshots cannot follow symlinks')
            if file.is_file():
                if file.name.startswith('.') or file.suffix.lower() not in {'.md', '.json', '.yaml', '.yml', '.txt'}:
                    raise ValueError('only explicit text configuration artifacts may be snapshotted')
                content[file.relative_to(root).as_posix()] = file.read_bytes()
        if not content:
            raise ValueError('empty configuration snapshot')
        snapshots[role] = content
    target.mkdir(parents=True)
    artifacts = {}
    for role, files in snapshots.items():
        for name, content in files.items():
            destination = target / role / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(content)
            artifacts[f'{role}/{name}'] = hashlib.sha256(content).hexdigest()
    manifest = {'schema_version': 'frozen-calibration-run/v1', 'split': split,
                'config_artifacts': artifacts, 'status': 'CANDIDATE_NOT_ADOPTED'}
    manifest['manifest_digest'] = digest(manifest)
    (target / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    (target / 'changes.md').write_text(changes)
    return manifest


def _labels(value, prefix=''):
    result = {}
    if isinstance(value, dict):
        for key, child in value.items():
            path = prefix + '/' + str(key)
            if key in {'score', 'verdict', 'triggered', 'reason', 'evidence'}:
                result[path] = child
            elif key == 'scores' and isinstance(child, dict):
                result.update({path + '/' + str(k): v for k, v in child.items()})
            else:
                result.update(_labels(child, path))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            key = child.get('id', child.get('module', index)) if isinstance(child, dict) else index
            result.update(_labels(child, prefix + '/' + str(key)))
    return result


def compare_calibration(benchmark, baseline, candidate):
    """Compare each Judge independently to approved labels; missing results stay missing."""
    from xiaoan_eval_core.results import validate_complete_results
    validate_complete_results(baseline)
    validate_complete_results(candidate)
    expected = {k: v for k, v in benchmark.items() if k != 'benchmark_digest'}
    if digest(expected) != benchmark.get('benchmark_digest'):
        raise ValueError('benchmark digest mismatch')
    indexes = []
    for result in (baseline, candidate):
        indexes.append(({a['answer_id']: a for a in result['answers']},
                        {e['answer_id']: e for e in result['envelopes']}))
    comparisons = []
    for item in benchmark['items']:
        payloads = []
        for answers, envelopes in indexes:
            answer = answers.get(item['answer_id'])
            if answer and (item.get('frozen_input_digest') != digest(answer) or item.get('row_digest') != answer.get('row_digest') or (hashlib.sha256(answer['answer'].encode()).hexdigest() if isinstance(answer.get('answer'), str) else None) != item.get('answer_sha256')):
                raise ValueError('calibration must compare identical frozen answer inputs')
            payloads.append(_labels(_evaluation(envelopes.get(item['answer_id'], {}), item['judge_id'])))
        for path, gold in _labels(item['gold']).items():
            old, new = (payload.get(path) for payload in payloads)
            record = {'case_id': item['case_id'], 'answer_id': item['answer_id'], 'judge_id': item['judge_id'],
                      'path': path, 'gold': gold, 'baseline': old, 'candidate': new,
                      'baseline_available': path in payloads[0], 'candidate_available': path in payloads[1],
                      'baseline_agrees': path in payloads[0] and old == gold,
                      'candidate_agrees': path in payloads[1] and new == gold}
            if isinstance(gold, (float, int)) and not isinstance(gold, bool):
                for role, value in [('baseline', old), ('candidate', new)]:
                    record[role + '_absolute_error'] = abs(value - gold) if isinstance(value, (int, float)) else None
                    record[role + '_severe_difference'] = abs(value - gold) >= 2 if isinstance(value, (int, float)) else None
            comparisons.append(record)
    judges = {}
    for judge in sorted({r['judge_id'] for r in comparisons}):
        rows = [r for r in comparisons if r['judge_id'] == judge]
        judges[judge] = {'items': len(rows), 'improved': sum(not r['baseline_agrees'] and r['candidate_agrees'] for r in rows),
                        'regressed': sum(r['baseline_agrees'] and not r['candidate_agrees'] for r in rows),
                        'candidate_missing': sum(not r['candidate_available'] for r in rows)}
    by_item = {}
    for row in comparisons:
        key = (row['judge_id'], row['path'])
        summary = by_item.setdefault(key, {'judge_id': key[0], 'path': key[1], 'n': 0, 'baseline_agrees': 0, 'candidate_agrees': 0, 'candidate_missing': 0, 'baseline_severe_difference': 0, 'candidate_severe_difference': 0, 'candidate_confusion': []})
        summary['n'] += 1
        for field in ('baseline_agrees', 'candidate_agrees', 'baseline_severe_difference', 'candidate_severe_difference'):
            summary[field] += bool(row.get(field))
        summary['candidate_missing'] += not row['candidate_available']
        if row['path'].endswith(('/verdict', '/triggered')):
            summary['candidate_confusion'].append({'gold': row['gold'], 'predicted': row['candidate'], 'available': row['candidate_available']})
    return {'benchmark_digest': benchmark['benchmark_digest'], 'by_judge': judges, 'by_item': list(by_item.values()), 'details': comparisons,
            'adoption': 'REQUIRES_USER_CONFIRMATION',
            'usage': {'baseline': _benchmark_usage(baseline, {i['answer_id'] for i in benchmark['items']}), 'candidate': _benchmark_usage(candidate, {i['answer_id'] for i in benchmark['items']})}}


def _benchmark_usage(results, answer_ids):
    """Allowlisted numeric telemetry only; no requests, outputs, labels or raw usage."""
    rows = []
    fields = {'input_tokens', 'output_tokens', 'total_tokens', 'cached_input_tokens', 'latency_ms', 'elapsed_ms'}
    for stage in results.get('stages', []):
        if stage.get('answer_id') not in answer_ids:
            continue
        for attempt in stage.get('attempts', []):
            usage = attempt.get('usage') or {}
            numeric = {k: v for k, v in usage.items() if k in fields and (v is None or type(v) in {int, float})}
            numeric.update({k: v for k, v in attempt.items() if k in {'latency_ms', 'elapsed_ms'} and (v is None or type(v) in {int, float})})
            rows.append({'answer_id': stage['answer_id'], 'task': stage.get('task'), 'usage': numeric})
    return rows


def record_adoption(directory, *, confirmed_by, scope, reason, comparison_digest):
    """Record a human choice; deliberately does not copy candidate over active config."""
    if not all((confirmed_by, scope, reason, comparison_digest)):
        raise ValueError('manual adoption requires confirmer, scope, reason and comparison digest')
    target = Path(directory)
    manifest = json.loads((target / 'manifest.json').read_text())
    for name, expected in manifest['config_artifacts'].items():
        if hashlib.sha256((target / name).read_bytes()).hexdigest() != expected:
            raise ValueError('candidate snapshot changed after freeze')
    receipt = {'confirmed_by': confirmed_by, 'scope': scope, 'reason': reason,
               'comparison_digest': comparison_digest, 'manifest_digest': manifest['manifest_digest'],
               'confirmed_at': datetime.now(timezone.utc).isoformat(), 'activation': 'EXPLICIT_SEPARATE_ACTION'}
    with (target / 'adoption.json').open('x') as stream:
        json.dump(receipt, stream, ensure_ascii=False, indent=2)
    return receipt
