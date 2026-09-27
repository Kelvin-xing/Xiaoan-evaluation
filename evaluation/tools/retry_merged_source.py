"""Retry a source cohort whose original run was retained only in a sealed merge."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from xiaoan_eval.frozen_ingress import validate_frozen_spec
from xiaoan_eval.frozen_retry import retry_evaluation
from xiaoan_eval_core.costs import build_answer_costs
from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results, validate_complete_results


def recover_source(merged, index):
    merged = validate_complete_results(merged)
    events = [item for item in merged['provenance'] if item.get('operation') == 'merge_subject_results']
    if len(events) != 1 or len(events[0]['source_manifests']) != 2:
        raise ValueError('Expected exactly two embedded source manifests')
    manifest = deepcopy(events[0]['source_manifests'][index])
    subjects = {subject['id'] for subject in manifest['plan']['subjects']}
    rows = [deepcopy(row) for row in merged['answers'] if row['subject_id'] in subjects]
    if (len(rows) != sum(len(merged['plan']['planned_turns'][case]) for case in manifest['plan']['case_ids']) * len(subjects)
            or {row['manifest_digest'] for row in rows} != {manifest['manifest_digest']}):
        raise ValueError('Source row coverage or manifest bindings differ')
    ids = {row['answer_id'] for row in rows}
    judges = deepcopy(merged['plan']['judges'])
    plan = deepcopy(manifest['plan'])
    original_judges = plan['judges']
    if judges[:len(original_judges)] != original_judges or len(judges) != len(original_judges) + 1:
        raise ValueError('Cannot reconstruct original Judge extension')
    plan['judges'] = judges
    spec = {'schema_version': 'evaluation-methods/v3', 'contract': merged['contract'],
            'manifest': manifest, 'plan': plan, 'judges': judges,
            'judge_extension': {'source_manifest_digest': manifest['manifest_digest'],
                                'added_judges': judges[len(original_judges):]},
            'rows': rows, 'planned_subjects': [subject['id'] for subject in plan['subjects']],
            'planned_turns': {case: merged['plan']['planned_turns'][case] for case in plan['case_ids']},
            'extractor': deepcopy(plan['extractor']),
            'relevancy_generator': deepcopy(plan['relevancy_generator']),
            'provider_options': deepcopy(manifest['provider_options']),
            'evaluation_config': deepcopy(merged['evaluation_config']),
            'audit_sample_fraction': 0}
    validate_frozen_spec(spec)
    parent = deepcopy(merged)
    parent['manifest'] = deepcopy(manifest)
    parent['plan']['subjects'] = deepcopy(plan['subjects'])
    parent['plan']['planned_subjects'] = spec['planned_subjects']
    parent['answers'] = rows
    parent['envelopes'] = [env for env in parent['envelopes'] if env['answer_id'] in ids]
    parent['inventories'] = [inv for inv in parent['inventories'] if inv['answer_id'] in ids]
    parent['stages'] = [stage for stage in parent['stages'] if stage.get('answer_id') in ids]
    parent['artifacts'] = []
    parent['provenance'].append({'operation': 'recover_source_cohort_from_sealed_merge',
                                 'merged_generation': merged['result_generation'],
                                 'source_manifest_digest': manifest['manifest_digest']})
    parent['aggregates'] = aggregate_complete_results(parent)
    parent['aggregates']['answer_costs'] = build_answer_costs(rows)
    seal_complete_results(parent)
    validate_complete_results(parent)
    return spec, parent


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--from-results', type=Path, required=True)
    parser.add_argument('--cohort', choices=('six', 'flash'), required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--execute', action='store_true')
    parser.add_argument('--max-workers', type=int, default=10)
    parser.add_argument('--provider-max-inflight', type=int, default=10)
    parser.add_argument('--provider-requests-per-second', type=float)
    parser.add_argument('--reuse-checkpoints', type=Path, nargs='*')
    parser.add_argument('--defer-relevancy', action='store_true')
    args = parser.parse_args()
    spec, parent = recover_source(json.loads(args.from_results.read_text()), 0 if args.cohort == 'six' else 1)
    stages = ['extraction', 'rubric', 'assessment'] if args.defer_relevancy else ['extraction', 'rubric', 'assessment', 'relevancy']
    outcome = retry_evaluation(spec, parent, args.output, stages=stages,
                               execute=args.execute, dry_run=not args.execute, adopt_current_runtime=True,
                               max_workers=args.max_workers, provider_max_inflight=args.provider_max_inflight,
                               provider_requests_per_second=args.provider_requests_per_second,
                               checkpoint_sources=args.reuse_checkpoints)
    if not args.execute:
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
    else:
        print(json.dumps({'answers': len(outcome['answers']), 'generation': outcome['result_generation']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
