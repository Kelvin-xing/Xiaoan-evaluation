"""Selective retries from a sealed frozen result into a new immutable generation."""
from __future__ import annotations

from copy import deepcopy
from collections import Counter
from pathlib import Path
import json
import os

from xiaoan_eval_core.configuration import snapshot, workflow
from xiaoan_eval_core.contracts import digest
from xiaoan_eval_core.results import (aggregate_complete_results, seal_complete_results,
                                      validate_complete_results)
from xiaoan_eval_core.runtime import ResponseStore
from xiaoan_eval_core.orchestration import run_orchestration
from .frozen_ingress import file_hash, validate_frozen_spec
from .frozen_provider import ConfiguredProvider, transport_options
from .frozen_cli import write_json
from .frozen_export import export_results_workbook


STAGES = {'extraction', 'rubric', 'assessment', 'relevancy'}


def extend_judges(spec, additions):
    result = validate_frozen_spec(spec)
    if not additions:
        return result
    old = result['judges']
    if len({j['id'] for j in old + additions}) != len(old) + len(additions):
        raise ValueError('Judge identity already planned or duplicated')
    prior = result.get('judge_extension', {}).get('added_judges', [])
    result['plan'] = deepcopy(result['plan'])
    result['judges'] = deepcopy(old + additions)
    result['plan']['judges'] = deepcopy(result['judges'])
    result['judge_extension'] = {
        'source_manifest_digest':result['manifest']['manifest_digest'],
        'added_judges':deepcopy(prior + additions)}
    return validate_frozen_spec(result)


def import_successful_checkpoints(output, sources):
    destination = Path(output)/'checkpoint'
    for source in sources:
        folder = Path(source)/'checkpoint'
        if not folder.is_dir():
            raise ValueError(f'Checkpoint directory missing: {folder}')
        for path in sorted(folder.glob('*.json')):
            partial = path.name.endswith('.partial.json')
            key = path.name.removesuffix('.partial.json') if partial else path.stem
            payload = json.loads(path.read_text())
            if (payload.get('request_hash') != key or 'response' not in payload or
                    (partial and (not isinstance(payload['response'], dict) or
                                  not isinstance(payload['response'].get('claims'), list) or
                                  not isinstance(payload['response'].get('requirements'), list)))):
                raise ValueError(f'Invalid checkpoint: {path}')
            destination.mkdir(parents=True, exist_ok=True)
            target = destination/path.name
            if partial and (destination/(key+'.json')).exists():
                continue
            if target.exists():
                if target.read_bytes() != path.read_bytes():
                    raise ValueError(f'Conflicting checkpoint: {target}')
            else:
                try:
                    os.link(path, target)
                except FileExistsError:
                    if target.read_bytes() != path.read_bytes():
                        raise ValueError(f'Conflicting checkpoint: {target}')


def compatible_schema_update(previous, current):
    """Allow only strict object closure and missing array-item shape completion."""
    def is_refinement(before, after):
        if before == after:
            return True
        if not isinstance(before, dict) or not isinstance(after, dict):
            return False
        old = deepcopy(before)
        new = deepcopy(after)
        if old.get('type') == 'object' and 'additionalProperties' not in old:
            if new.pop('additionalProperties', None) is not False:
                return False
        if old.get('type') == 'array' and 'items' not in old:
            item = new.pop('items', None)
            if not isinstance(item, dict):
                return False
        old_props = old.pop('properties', None)
        new_props = new.pop('properties', None)
        if old != new or (old_props is None) != (new_props is None):
            return False
        return old_props is None or (old_props.keys() == new_props.keys() and
                all(is_refinement(old_props[k], new_props[k]) for k in old_props))

    if previous.keys() != current.keys():
        return False
    for name, old in previous.items():
        new = current[name]
        if old == new:
            continue
        if not name.startswith('schemas/') or not name.endswith('.json'):
            return False
        import json
        from hashlib import sha256
        before = json.loads(old['content'])
        after = json.loads(new['content'])
        # Definitions are new structural constraints, never a changed old contract.
        definitions = after.pop('$defs', {})
        if any(not isinstance(item, dict) for item in definitions.values()) or not is_refinement(before, after):
            return False
        if sha256(old['content'].encode()).hexdigest() != old['sha256'] or sha256(new['content'].encode()).hexdigest() != new['sha256']:
            return False
    return True


def retry_evaluation(spec, parent, output, *, stages=None, answer_ids=None,
                     judge_ids=None, provider=None, execute=False, max_workers=2,
                     new_evaluator_cohort=False, adopt_current_runtime=False, dry_run=False,
                     provider_max_inflight=None, checkpoint_sources=None):
    spec = validate_frozen_spec(spec)
    parent = validate_complete_results(parent)
    if parent['manifest'] != spec['manifest']:
        raise ValueError('Parent manifest differs from frozen input')
    old = {row['answer_id']:row for row in parent['answers']}
    new = {row['answer_id']:row for row in spec['rows']}
    current_config = snapshot()
    if adopt_current_runtime:
        if new_evaluator_cohort or not compatible_schema_update(parent['evaluation_config'], current_config):
            raise ValueError('Current evaluator changes are not the compatible schema-only update')
        spec['evaluation_config'] = current_config
        spec['evaluation_provider_options'] = transport_options(ConfiguredProvider().values)
    if not new_evaluator_cohort and (parent['evaluation_config'] != current_config or
            spec.get('evaluation_config', spec['manifest']['evaluator_config']) != current_config) and not adopt_current_runtime:
        raise ValueError('Evaluator configuration changed; start a new evaluation cohort')
    if not new_evaluator_cohort and not adopt_current_runtime and parent['plan'].get('provider_options') != spec.get('provider_options'):
        raise ValueError('Evaluator provider options differ from parent')
    if any(env.get('human_review') for env in parent['envelopes']):
        raise ValueError('Export and reconcile Human Review before changing automatic evaluations')
    for aid in old.keys() & new.keys():
        if old[aid] != new[aid]:
            raise ValueError('Frozen answer changed without a new answer_id')
    changed = new.keys() - old.keys()
    removed = old.keys() - new.keys()
    if removed and {old[aid]['planned_unit_id'] for aid in removed} != {new[aid]['planned_unit_id'] for aid in changed}:
        raise ValueError('Subject retry must replace exactly the selected planned rows')
    if len(new) != len(old) or {r['planned_unit_id'] for r in new.values()} != {r['planned_unit_id'] for r in old.values()}:
        raise ValueError('Subject retry changed the planned matrix')
    if new_evaluator_cohort:
        if stages or answer_ids or judge_ids or changed:
            raise ValueError('New evaluator cohort requires every frozen answer and stage')
        spec['evaluation_config'] = current_config
        spec['evaluation_provider_options'] = transport_options(ConfiguredProvider().values)
    requested = set(stages or STAGES)
    if not requested or requested - STAGES:
        raise ValueError('Unknown retry stage')
    selected_answers = set(answer_ids or new)
    if selected_answers - new.keys():
        raise ValueError('Unknown answer_id')
    judges = {j['id'] for j in spec['judges']}
    selected_judges = set(judge_ids or judges)
    if selected_judges - judges:
        raise ValueError('Unknown judge_id')
    old_env = {env['answer_id']:env for env in parent['envelopes']}
    selected = set()
    for aid in selected_answers | changed:
        if new[aid]['status'] != 'AVAILABLE':
            continue
        env = old_env.get(aid, {})
        if new_evaluator_cohort or aid in changed or 'extraction' in requested and env.get('inventory_id') is None:
            selected.add(('extract_claims', aid, None))
        for name, task in (('rubric', 'rubric'), ('assessment', 'assess_claims')):
            if name not in requested and aid not in changed:
                continue
            branch = 'rubric' if name == 'rubric' else 'assessments'
            cells = {cell['judge_id']:cell for cell in env.get(branch, [])}
            for judge in selected_judges if aid not in changed else judges:
                if new_evaluator_cohort or aid in changed or cells.get(judge, {}).get('status') != 'AVAILABLE':
                    selected.add((task, aid, judge))
                    if task == 'assess_claims' and env.get('inventory_id') is None:
                        selected.add(('extract_claims', aid, None))
        if (new_evaluator_cohort or 'relevancy' in requested or aid in changed) and (new_evaluator_cohort or aid in changed or env.get('relevancy', {}).get('status') != 'AVAILABLE'):
            selected.update({('relevancy_generation', aid, None), ('relevancy_embedding', aid, None)})
        if 'extraction' in requested and ('extract_claims', aid, None) in selected:
            selected.update(('assess_claims', aid, judge) for judge in judges)
    if not selected and not changed:
        raise ValueError('No unavailable selected stage cells to retry')
    out = Path(output)
    if (out/'results.json').exists():
        raise ValueError('Retry output already sealed; choose a new directory')
    call = provider or (ConfiguredProvider(None if dry_run else out/'provider-artifacts') if execute else None)
    if isinstance(call, ConfiguredProvider) and transport_options(call.values) != spec.get('evaluation_provider_options',spec.get('provider_options', {})):
        raise ValueError('Provider options differ from frozen input')
    if dry_run:
        return {'parent_generation':parent['result_generation'],
                'new_evaluator_cohort':new_evaluator_cohort,
                'adopt_current_runtime':adopt_current_runtime,
                'judges':[j['id'] for j in spec['judges']],
                'selected':dict(sorted(Counter(task for task,_,_ in selected).items()))}
    import_successful_checkpoints(out, checkpoint_sources or [])
    selection={'parent_generation':parent['result_generation'],
               'new_evaluator_cohort':new_evaluator_cohort,
               'selected':sorted([list(x) for x in selected],key=str)}
    write_json(out/'retry-selection.json',selection)
    settings = workflow()
    def selected_request(request):
        task = request['task']
        judge = request.get('identity', {}).get('id') if task in {'rubric', 'assess_claims'} else None
        return (task,request.get('answer_id'),judge) in selected
    store = ResponseStore(out/'checkpoint',max_workers=max_workers,
                          provider_max_inflight=(provider_max_inflight if provider_max_inflight is not None else
                              spec.get('provider_max_inflight',settings['provider_max_inflight'])),
                          max_attempts=spec.get('max_attempts',settings['max_attempts']),
                          provider_options=spec.get('evaluation_provider_options',spec.get('provider_options')),
                          provider_requests_per_second=spec.get('provider_requests_per_second',settings.get('provider_requests_per_second',0)),
                          request_filter=selected_request)
    for receipt in ([] if new_evaluator_cohort else parent['stages']):
        if (receipt.get('execution_status') == 'SUCCEEDED' and
                receipt.get('answer_id') in new and 'raw_response' in receipt):
            key = receipt['request_digest']
            if digest(receipt['request']) != key or receipt.get('stage_id') != key:
                raise ValueError('Parent stage request digest mismatch')
            if receipt.get('availability') == 'PARTIAL':
                if receipt.get('task') == 'assess_claims':
                    previous = store.partial.get(key)
                    if previous is not None and previous != receipt['output']:
                        raise ValueError('Conflicting partial parent stage outputs')
                    store.partial[key] = deepcopy(receipt['output'])
                continue
            cached = {'request_hash':key, 'response':receipt['raw_response']}
            if key in store.memory and store.memory[key] != cached:
                raise ValueError('Conflicting successful parent stage outputs')
            store.memory[key] = cached

    def allowed(request):
        if not selected_request(request):
            raise LookupError('Stage not selected for retry')
        if call is None:
            raise LookupError('Provider not configured')
        return call(request)

    def embed(texts, task):
        if ('relevancy_embedding', task['answer_id'], None) not in selected:
            raise LookupError('Stage not selected for retry')
        if call is None or not hasattr(call, 'embeddings'):
            raise LookupError('Embedding provider not configured')
        return call.embeddings(texts,task)

    write_json(out/'frozen-input.json', spec)
    try:
        result = run_orchestration(spec, faithfulness_provider=allowed, rubric_provider=allowed,
                                   generation_provider=allowed, embedding_provider=embed,
                                   checkpoint_dir=out/'checkpoint', max_workers=max_workers, store=store)
    finally:
        if provider is None and isinstance(call, ConfiguredProvider):
            call.close()
    for env in result['envelopes']:
        aid = env['answer_id']
        prior = old_env.get(aid)
        if prior is None or new_evaluator_cohort:
            continue
        if ('extract_claims', aid, None) not in selected:
            env['inventory_id'] = prior['inventory_id']
        for branch, task in (('rubric','rubric'), ('assessments','assess_claims')):
            attempted = {cell['judge_id'] for cell in env[branch]}
            preserved = {cell['judge_id']:deepcopy(cell) for cell in prior[branch]
                         if (task, aid, cell['judge_id']) not in selected}
            env[branch] = [preserved.get(cell['judge_id'],cell) for cell in env[branch]]
            if attempted != judges:
                raise ValueError('Retry dropped a planned Judge cell')
        if ('relevancy_generation', aid, None) not in selected:
            env['relevancy'] = deepcopy(prior['relevancy'])
        env['checks'] = deepcopy(prior['checks'])
    preserved_inventories = [inv for inv in ([] if new_evaluator_cohort else parent['inventories'])
                             if inv['answer_id'] in new and ('extract_claims',inv['answer_id'],None) not in selected]
    result['inventories'] = [*preserved_inventories,
                             *(inv for inv in result['inventories']
                               if ('extract_claims',inv['answer_id'],None) in selected)]
    result['stages'] = [r for r in ([] if new_evaluator_cohort else parent['stages']) if r.get('answer_id') in new] + [
        r for r in result['stages'] if (r.get('task'),r.get('answer_id'),
              r.get('identity',{}).get('id') if r.get('task') in {'rubric','assess_claims'} else None) in selected]
    for env in result['envelopes']:
        env['stage_refs'] = list(dict.fromkeys(r['stage_id'] for r in result['stages'] if r.get('answer_id') == env['answer_id']))
    result['provenance'] = [*parent.get('provenance', []),
                            {'operation':'new_evaluator_cohort' if new_evaluator_cohort else 'selective_retry',
                             'parent_generation':parent['result_generation'],
                             'judge_extension':deepcopy(spec.get('judge_extension')),
                             'checkpoint_sources':[str(Path(path).resolve()) for path in checkpoint_sources or []],
                             'runtime_migration': {'prior_evaluator_config': parent['evaluation_config'],
                                                   'prior_provider_options': parent['plan'].get('provider_options'),
                                                   'current_provider_options': spec['evaluation_provider_options'],
                                                   'rule': 'strict_object_closure_and_array_item_shape_only'} if adopt_current_runtime else None,
                             'selected':sorted([list(x) for x in selected], key=str)}]
    result['provenance'][-1]['execution_limits'] = {
        'max_workers':max_workers, 'provider_max_inflight':store.provider_max_inflight}
    for folder in ('provider-artifacts','subject-checkpoint','checkpoint'):
        for artifact in sorted((out/folder).glob('*')):
            if artifact.is_file() and artifact.suffix in ('.json','.jsonl'):
                result['artifacts'].append({'id':file_hash(artifact),
                    'path':str(artifact.relative_to(out)),'sha256':file_hash(artifact),'type':folder})
    result['aggregates'] = aggregate_complete_results(result)
    from xiaoan_eval_core.costs import build_answer_costs
    result['aggregates']['answer_costs'] = build_answer_costs(result['answers'])
    seal_complete_results(result)
    validate_complete_results(result)
    write_json(out/'results.json',result)
    export_results_workbook(result,out/'results.xlsx')
    return result
