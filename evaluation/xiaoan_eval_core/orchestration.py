"""Single Frozen Answer Evaluation engine; independent branches share a request store."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from pathlib import Path
from typing import Any, Mapping
from .configuration import prompt, snapshot, workflow, schema
from .contracts import digest, text
from .relevancy import build_request, evaluate_relevancy
from .rubric import evaluate_rubric
from .runtime import evaluate, ResponseStore, prepare_rows

def build_rubric_request(row: Mapping[str, Any], rating_rule: Any,
                         *, judge_id: str = "rubric:configured", judge=None) -> dict[str, Any]:
    """Build the allowlisted request for one rubric judgement."""
    answer = text(row.get("answer"), "answer")
    question = text(row.get("question"), "question")
    history = row.get("history", [])
    if not isinstance(history, list):
        raise ValueError("history must be an array")
    identity = {"id": judge_id, "provider": "configured", "model": "configured",
                "prompt_version": "ratings-rule/v1"}
    if judge is not None:
        identity = {k: judge[k] for k in ("id", "provider", "model", "prompt_version")}
    payload = {
        "answer_id": text(row.get("answer_id"), "answer_id"),
        "question": question, "answer": answer, "history": deepcopy(history),
        "quality_focus": list(row.get("quality_focus", ())),
        "rating_rule": {
            "schema_version": rating_rule.schema_version,
            "score_scale": [{"score": a.score, "description": a.description}
                            for a in rating_rule.score_scale],
            "red_lines": [{"id": r.id, "name": r.name, "description": r.description}
                          for r in rating_rule.red_lines],
            "modules": [{"name": m.name, "weight": m.weight, "positive": list(m.positive),
                         "negative": list(m.negative)} for m in rating_rule.modules],
            "dynamic_weight_multiplier": rating_rule.dynamic_weight_multiplier,
        },
    }
    return {"contract": "frozen-answer-evaluation/v1", "task": "rubric", "response_schema": schema("rubric"), "validator_version": "frozen/v2",
            "identity": identity, "binding": digest(payload), **payload,
            "instructions": prompt("rubric.md")}



def deterministic_checks(row):
    output = []
    observations = row.get('observations', {})
    for requirement in row.get('requirements', []):
        if not requirement.get('runtime_check') and requirement.get('kind') not in {'route', 'evidence'}:
            continue
        obs = observations.get(requirement['id'], {})
        expected = requirement.get('expected')
        if obs.get('status') == 'NOT_APPLICABLE':
            verdict = 'NOT_APPLICABLE'
        elif obs.get('status') != 'AVAILABLE':
            verdict = 'UNCERTAIN'
        elif isinstance(obs.get('value'), bool):
            verdict = 'SATISFIED' if obs['value'] else 'VIOLATED'
        elif expected is None:
            verdict = 'UNCERTAIN'
        else:
            verdict = 'SATISFIED' if obs.get('value') == expected else 'VIOLATED'
        output.append({'answer_id': row['answer_id'], 'requirement_id': requirement['id'],
                       'status': 'UNAVAILABLE' if verdict == 'UNCERTAIN' else 'AVAILABLE',
                       'verdict': verdict, 'expected': expected, 'observation': deepcopy(obs),
                       'reason': 'BOUND_OBSERVATION_COMPARISON' if verdict != 'UNCERTAIN' else 'OBSERVATION_OR_EXPECTATION_MISSING'})
    return output


def run_orchestration(spec: Mapping[str, Any], *, faithfulness_provider=None,
                      rubric_provider=None, generation_provider=None,
                      embedding_provider=None, rating_rule=None, checkpoint_dir=None,
                      rubric_stage=None, relevancy_stage=None, max_workers=None, store=None):
    from .results import build_complete_results
    spec = deepcopy(spec)
    rows = prepare_rows(spec)
    settings = workflow()
    workers = max(1, int(max_workers or spec.get('max_workers', settings['max_workers'])))
    branches = spec.get('branches', spec.get('plan', {}).get('branches', settings['branches']))
    if isinstance(branches, dict):
        branches = [key for key, enabled in branches.items() if enabled]
    if 'requirements' in branches and 'claims' not in branches:
        branches = [*branches, 'claims']
    spec['max_workers'] = workers
    current_config = snapshot()
    frozen_config = spec.get('evaluation_config', spec.get('manifest', {}).get('evaluator_config'))
    if frozen_config is not None and frozen_config != current_config:
        raise ValueError('selected evaluator configuration differs from frozen evaluation snapshot')
    # Ad-hoc direct Python callers also retain exact executable assets without changing a sealed manifest.
    spec['evaluation_config'] = current_config
    if rating_rule is None and 'rubric' in branches:
        from xiaoan_eval.rules import load_rating_rule
        from .configuration import ROOT
        rating_rule = load_rating_rule(ROOT / 'rating-rule.yml')
    store = store or ResponseStore(checkpoint_dir, max_workers=workers,
                                  provider_max_inflight=spec.get('provider_max_inflight', settings['provider_max_inflight']),
                                  max_attempts=spec.get('max_attempts', settings['max_attempts']),
                                  provider_options=spec.get('evaluation_provider_options',spec.get('provider_options')),
                                  provider_requests_per_second=spec.get('provider_requests_per_second', settings.get('provider_requests_per_second', 0)))
    supplied_rubric = {(r['answer_id'], r.get('judge_id')): r for r in rubric_stage or []}
    supplied_relevancy = {r['answer_id']: r for r in relevancy_stage or []}
    def rubric_one(pair):
        row, judge = pair
        result = {'answer_id': row['answer_id'], 'judge_id': judge['id'], 'evaluator_role': 'rubric', 'status': 'UNAVAILABLE'}
        if 'rubric' not in branches:
            return {**result, 'execution_status': 'NOT_PLANNED', 'reason': 'NOT_PLANNED'}
        if row.get('status') != 'AVAILABLE':
            return {**result, 'execution_status': 'SKIPPED', 'reason': 'ANSWER_UNAVAILABLE'}
        try:
            request = build_rubric_request(row, rating_rule, judge=judge)
            supplied = supplied_rubric.get((row['answer_id'], judge['id']), supplied_rubric.get((row['answer_id'], None), {}))
            payload = supplied.get('payload', supplied.get('rubric'))
            value = store.call(request, rubric_provider, lambda value, _: evaluate_rubric(row, value, rating_rule), payload)
            return {**result, 'status': 'AVAILABLE', 'execution_status': 'SUCCEEDED', 'rubric': value, 'request_id': store.request_digest(request)}
        except Exception as exc:
            return {**result, 'execution_status': 'FAILED', 'reason': 'RUBRIC_'+type(exc).__name__}
    def relevancy_one(row):
        result = {'answer_id': row['answer_id'], 'evaluator_role': 'relevancy', 'status': 'UNAVAILABLE'}
        if 'relevancy' not in branches:
            return {**result, 'execution_status': 'NOT_PLANNED', 'reason': 'NOT_PLANNED'}
        if row.get('status') != 'AVAILABLE':
            return {**result, 'execution_status': 'SKIPPED', 'reason': 'ANSWER_UNAVAILABLE'}
        task = build_request(row['answer_id'], row['question'], row['answer'], generator=spec.get('relevancy_generator'))
        saved = supplied_relevancy.get(row['answer_id'], {})
        generation_request = {'answer_id': row['answer_id'], **task['generation_input'], 'identity': task['generator'], 'binding': task['binding']}
        def generate(_):
            def validate(value, request):
                questions = value.get('questions') if isinstance(value, dict) else None
                if not isinstance(questions, list) or len(questions) != task['n'] or any(not isinstance(q,str) or not q.strip() for q in questions):
                    raise ValueError('invalid reverse questions')
                return {'binding': task['binding'], 'questions': questions}
            return store.call(generation_request, generation_provider, validate)
        def embed(texts, current_task):
            request = {'task': 'relevancy_embedding', 'answer_id': row['answer_id'], 'texts': texts, 'identity': spec.get('embedding_identity', {}), 'binding': current_task['binding']}
            def validate(value, _):
                from .relevancy import _cosine
                if not isinstance(value, dict) or not value.get('model_id') or not value.get('revision'):
                    raise ValueError('embedding identity missing')
                for content in texts:
                    vector = value.get('vectors', {}).get(content)
                    _cosine(vector, vector)
                return value
            return store.call(request, (lambda _: embedding_provider(texts, current_task)) if embedding_provider else None, validate)
        value = evaluate_relevancy(task, generation_provider=generate, embedding_provider=embed,
                                    supplied_generation=saved.get('generation'), supplied_embeddings=saved.get('embeddings'))
        return {**result, **value, 'execution_status': 'SUCCEEDED' if value['status']=='AVAILABLE' else 'FAILED'}
    with ThreadPoolExecutor(max_workers=3) as branches_pool:
        semantic_spec = deepcopy(spec)
        if 'requirements' not in branches:
            semantic_spec['conversation_constraints'] = []
            for row in semantic_spec['rows']:
                row['requirements'] = []
                row['observations'] = {}
        faith_future = branches_pool.submit(evaluate, semantic_spec, faithfulness_provider, store=store) if 'claims' in branches else None
        def parallel(function, items):
            with ThreadPoolExecutor(max_workers=workers) as pool:
                return list(pool.map(function, items))
        rubric_future = branches_pool.submit(parallel, rubric_one, [(r,j) for r in rows for j in spec['judges']])
        relevance_future = branches_pool.submit(parallel, relevancy_one, rows)
        faithfulness = faith_future.result() if faith_future else {
            'inventories': [], 'extraction_states': [],
            'cells': [{**{k: row[k] for k in ('answer_id','case_id','turn','subject_id')},
                       'judge_id': judge['id'], 'status':'UNAVAILABLE', 'execution_status':'NOT_PLANNED',
                       'reason':'NOT_PLANNED'} for row in rows for judge in spec['judges']]}
        rubric, relevancy = rubric_future.result(), relevance_future.result()
    checks = [item for row in rows for item in deterministic_checks(row)] if 'checks' in branches else []
    return build_complete_results(spec, rows, faithfulness, rubric, relevancy, checks, store.receipts)


__all__ = ['build_rubric_request', 'run_orchestration', 'deterministic_checks']
