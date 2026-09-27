"""Assemble the full Minimal33 matrix from seven subjects and Gemini Pro shards."""
from __future__ import annotations

import argparse
import json
from copy import deepcopy
from pathlib import Path

from xiaoan_eval.frozen_balanced import assemble_balanced
from xiaoan_eval_core.costs import build_answer_costs
from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results, validate_complete_results


def pro_from_prior_matrix(result):
    result = validate_complete_results(deepcopy(result))
    if len(result['plan']['subjects']) != 8:
        raise ValueError('Prior matrix does not contain eight subjects')
    subject = next((item for item in result['plan']['subjects'] if item['id'] == 'gemini-3.1-pro-preview'), None)
    if subject is None:
        raise ValueError('Prior matrix has no Gemini Pro subject')
    ids = {row['answer_id'] for row in result['answers'] if row['subject_id'] == subject['id']}
    if not ids:
        raise ValueError('No frozen Gemini Pro answers')
    prior_generation = result['result_generation']
    result['plan']['subjects'] = [subject]
    result['plan']['planned_subjects'] = [subject['id']]
    result['answers'] = [row for row in result['answers'] if row['answer_id'] in ids]
    result['envelopes'] = [env for env in result['envelopes'] if env['answer_id'] in ids]
    result['inventories'] = [inv for inv in result['inventories'] if inv['answer_id'] in ids]
    result['stages'] = [stage for stage in result['stages'] if stage.get('answer_id') in ids]
    result['artifacts'] = []
    result['provenance'].append({'operation': 'select_prior_matrix_subject',
                                 'source_generation': prior_generation, 'subject_id': subject['id']})
    result['aggregates'] = aggregate_complete_results(result)
    result['aggregates']['answer_costs'] = build_answer_costs(result['answers'])
    seal_complete_results(result)
    return validate_complete_results(result)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seven', type=Path, required=True)
    parser.add_argument('--prior-eight', type=Path, required=True)
    parser.add_argument('--pro-pilot', type=Path, required=True)
    parser.add_argument('--pro-bulk', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    paths = [args.seven, args.prior_eight, args.pro_pilot, args.pro_bulk]
    sources = [validate_complete_results(json.loads(path.read_text())) for path in paths]
    sources[1] = pro_from_prior_matrix(sources[1])
    result = assemble_balanced(sources, paths, args.output, require_relevancy=False,
                               require_assessment=False, require_rubric=False)
    print(json.dumps({'cases': result['plan']['case_ids'], 'answers': len(result['answers']),
                      'subjects': len(result['plan']['subjects']), 'judges': len(result['plan']['judges']),
                      'generation': result['result_generation']}, ensure_ascii=False))


if __name__ == '__main__':
    main()
