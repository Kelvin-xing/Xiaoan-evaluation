"""Combine separately sealed subject cohorts without rewriting frozen answers."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results, validate_complete_results
from xiaoan_eval_core.costs import build_answer_costs
from .frozen_cli import write_json
from .frozen_export import export_results_workbook


def merge_subject_results(base, addition, output, *, base_path=None, addition_path=None):
    base = validate_complete_results(deepcopy(base))
    addition = validate_complete_results(deepcopy(addition))
    if base['contract'] != addition['contract'] or base['plan']['suite_id'] != addition['plan']['suite_id']:
        raise ValueError('Different evaluation contracts or suites')
    for field in ('case_ids', 'judges', 'extractor', 'relevancy_generator', 'subject_mode'):
        if base['plan'].get(field) != addition['plan'].get(field):
            raise ValueError(f'Incompatible subject cohorts: {field}')
    if base['evaluation_config'] != addition['evaluation_config']:
        raise ValueError('Different evaluator configurations; reconcile cohorts first')
    old_subjects = {s['id'] for s in base['plan']['subjects']}
    new_subjects = {s['id'] for s in addition['plan']['subjects']}
    if old_subjects & new_subjects or not new_subjects:
        raise ValueError('Subject cohorts overlap or addition is empty')
    if {r['subject_id'] for r in base['answers']} != old_subjects or {r['subject_id'] for r in addition['answers']} != new_subjects:
        raise ValueError('Answer subjects differ from plans')
    for field in ('answers', 'inventories', 'envelopes', 'stages'):
        base[field].extend(addition[field])
    base['plan']['subjects'].extend(addition['plan']['subjects'])
    base['plan']['planned_subjects'] = [s['id'] for s in base['plan']['subjects']]
    base['provenance'].append({
        'operation': 'merge_subject_results',
        'source_generations': [base['result_generation'], addition['result_generation']],
        'source_results': [str(Path(p).resolve()) if p is not None else None for p in (base_path, addition_path)],
        'source_manifests': [base['manifest'], addition['manifest']],
        'rule': 'disjoint_subjects_same_suite_judges_and_evaluator_config',
    })
    base['aggregates'] = aggregate_complete_results(base)
    base['aggregates']['answer_costs'] = build_answer_costs(base['answers'])
    seal_complete_results(base)
    validate_complete_results(base)
    out = Path(output)
    if (out / 'results.json').exists():
        raise ValueError('Merged output already sealed; choose a new directory')
    write_json(out / 'results.json', base)
    export_results_workbook(base, out / 'results.xlsx')
    return base
