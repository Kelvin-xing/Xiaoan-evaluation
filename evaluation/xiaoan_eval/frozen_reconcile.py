"""Recover verified successful cells lost across same-manifest generations."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from pathlib import Path

from xiaoan_eval_core.costs import build_answer_costs
from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results, validate_complete_results
from .frozen_cli import write_json
from .frozen_export import export_results_workbook


def reconcile_generations(base, addition, output, *, base_path, addition_path):
    base = validate_complete_results(deepcopy(base))
    addition = validate_complete_results(addition)
    if (base['manifest'] != addition['manifest'] or
            base['evaluation_config'] != addition['evaluation_config'] or
            base['plan']['subjects'] != addition['plan']['subjects'] or
            base['plan']['judges'] != addition['plan']['judges'] or
            base['plan']['case_ids'] != addition['plan']['case_ids']):
        raise ValueError('Different frozen evaluation cohorts')
    original = {row['answer_id']: row for row in base['answers']}
    incoming = {row['answer_id']: row for row in addition['answers']}
    if original != incoming:
        raise ValueError('Frozen answers differ')
    by_env = {env['answer_id']: env for env in addition['envelopes']}
    inventories = {inv['inventory_id']: inv for inv in base['inventories']}
    incoming_inventory = {inv['inventory_id']: inv for inv in addition['inventories']}
    receipts = {stage['stage_id']: stage for stage in base['stages']}
    incoming_receipts = {stage['stage_id']: stage for stage in addition['stages']}
    recovered = Counter()
    for env in base['envelopes']:
        other = by_env[env['answer_id']]
        for branch in ('rubric', 'assessments'):
            target = {cell['judge_id']: cell for cell in env[branch]}
            source = {cell['judge_id']: cell for cell in other[branch]}
            if target.keys() != source.keys():
                raise ValueError('Different Judge cells')
            for judge, cell in target.items():
                candidate = source[judge]
                if cell['status'] == 'AVAILABLE' and candidate['status'] == 'AVAILABLE' and cell != candidate:
                    raise ValueError(f'Conflicting successful {branch}: {env["answer_id"]} {judge}')
                if (candidate['status'] == 'AVAILABLE' and cell['status'] != 'AVAILABLE' or
                        candidate['status'] == 'PARTIAL' and cell['status'] == 'UNAVAILABLE'):
                    env[branch][next(i for i, item in enumerate(env[branch]) if item['judge_id'] == judge)] = deepcopy(candidate)
                    recovered[(branch, candidate['status'])] += 1
        if other.get('inventory_id'):
            if env.get('inventory_id') not in (None, other['inventory_id']):
                raise ValueError('Conflicting claim inventories')
            iid = other['inventory_id']
            if iid in inventories and inventories[iid] != incoming_inventory[iid]:
                raise ValueError('Conflicting claim inventory content')
            if iid not in inventories:
                inventory = deepcopy(incoming_inventory[iid])
                base['inventories'].append(inventory)
                inventories[iid] = inventory
                recovered[('inventory', 'AVAILABLE')] += 1
            env['inventory_id'] = iid
        relevance = other.get('relevancy', {})
        if env['relevancy'].get('status') != 'AVAILABLE' and relevance.get('status') == 'AVAILABLE':
            env['relevancy'] = deepcopy(relevance)
            recovered[('relevancy', 'AVAILABLE')] += 1
        for stage_id in other['stage_refs']:
            if stage_id in receipts:
                continue
            if stage_id in incoming_receipts:
                stage = deepcopy(incoming_receipts[stage_id])
                base['stages'].append(stage)
                receipts[stage_id] = stage
                env['stage_refs'].append(stage_id)
    base['provenance'].append({'operation': 'reconcile_same_manifest_generation',
                               'source_results': [str(Path(base_path).resolve()), str(Path(addition_path).resolve())],
                               'source_generations': [base['result_generation'], addition['result_generation']],
                               'recovered': {f'{branch}:{status}': count for (branch, status), count in recovered.items()}})
    base['aggregates'] = aggregate_complete_results(base)
    base['aggregates']['answer_costs'] = build_answer_costs(base['answers'])
    seal_complete_results(base)
    validate_complete_results(base)
    out = Path(output)
    if (out / 'results.json').exists():
        raise ValueError('Output already sealed')
    write_json(out / 'results.json', base)
    export_results_workbook(base, out / 'results.xlsx')
    return dict(recovered)
