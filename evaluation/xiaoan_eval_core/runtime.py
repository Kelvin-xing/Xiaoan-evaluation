"""Bounded execution with extraction barrier and immutable successful checkpoints."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import json
import os
from pathlib import Path
from threading import Lock, BoundedSemaphore
import time
from uuid import uuid4
from . import VERSION
from .contracts import (assessment_request, digest, extraction_request, indexed, text,
                        validate_assessment_parts, validate_inventory)
from .scoring import claim_metrics, inventory_audit, requirement_metrics, summarize


class ResponseStore:
    def __init__(self, directory=None, *, max_workers=4, provider_max_inflight=2, max_attempts=2, provider_options=None, provider_requests_per_second=0, request_filter=None):
        self.directory = Path(directory) if directory is not None else None
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
        self.memory, self.requests, self.receipts = {}, {}, []
        self.partial = {}
        self.completed = {}
        self.failed = {}
        self.lock = Lock()
        self.key_locks = {}
        self.providers = {}
        self.global_limit = BoundedSemaphore(max(1, int(max_workers)))
        self.provider_max_inflight = max(1, int(provider_max_inflight))
        self.max_attempts = max(1, int(max_attempts))
        self.provider_options = deepcopy(provider_options or {})
        self.rate = max(0, float(provider_requests_per_second))
        self.next_request = {}
        self.rate_lock = Lock()
        self.request_filter = request_filter

    def journal(self, key, attempt):
        if self.directory is None:
            return
        content = (json.dumps(attempt, ensure_ascii=False, allow_nan=False) + '\n').encode()
        descriptor = os.open(self.directory / f'{key}.events.jsonl', os.O_CREAT | os.O_APPEND | os.O_WRONLY, 0o600)
        try:
            os.write(descriptor, content)
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def interrupted(self, key):
        path = self.directory / f'{key}.events.jsonl' if self.directory else None
        if path is None or not path.exists():
            return []
        latest = {}
        for line in path.read_text().splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue  # Interrupted final append is not a successful receipt.
            latest[event['attempt_id']] = event
        return [{**event, 'execution_status': 'FAILED', 'error': 'INTERRUPTED_RESULT_UNKNOWN',
                 'usage': None, 'usage_reason': 'PROVIDER_MAY_HAVE_PROCESSED'}
                for event in latest.values() if event.get('execution_status') == 'RUNNING']

    def request_digest(self, request):
        return digest({**request, **({"provider_options": self.provider_options} if self.provider_options else {})})

    def call(self, request, provider, validate, supplied=None):
        request = deepcopy(request)
        if self.provider_options:
            request["provider_options"] = deepcopy(self.provider_options)
        key = digest(request)
        with self.lock:
            lock = self.key_locks.setdefault(key, Lock())
            self.requests[key] = deepcopy(request)
        with lock:
            if key in self.completed:
                result = deepcopy(self.completed[key])
                self.receipts.append({'stage_id': key, 'request_digest': key, 'task': request.get('task'),
                    'answer_id': request.get('answer_id'), 'identity': deepcopy(request.get('identity', {})),
                    'request': deepcopy(request), 'attempts': [], 'execution_status': 'SUCCEEDED',
                    'availability': 'PARTIAL' if isinstance(result, dict) and result.get('status') == 'PARTIAL' else 'AVAILABLE',
                    'output': deepcopy(result), 'reused_from': key,
                    'incremental_usage': {'input_tokens': 0, 'output_tokens': 0}})
                return result
            if key in self.failed:
                raise self.failed[key]('shared in-flight request failed')
            try:
                result = self._call_owned(key, request, provider, validate, supplied)
                self.completed[key] = deepcopy(result)
                return result
            except Exception as exc:
                # Keep a safe exception type only; no provider message/credentials.
                self.failed[key] = type(exc) if type(exc) in {ValueError, LookupError, TimeoutError, ConnectionError, PermissionError} else RuntimeError
                raise

    def _call_owned(self, key, request, provider, validate, supplied):
        path = self.directory / f'{key}.json' if self.directory else None
        cached = self.memory.get(key)
        if cached is None and path is not None and path.exists():
            cached = json.loads(path.read_text())
        if cached is None and self.request_filter is not None and not self.request_filter(request):
            raise LookupError('Stage not selected for retry')
        receipt = {'stage_id': key, 'request_digest': key, 'task': request.get('task'),
                   'answer_id': request.get('answer_id'),
                   'identity': deepcopy(request.get('identity', {})), 'attempts': [],
                   'execution_status': 'RUNNING', 'request': deepcopy(request)}
        receipt['historical_interrupted_attempts'] = self.interrupted(key)
        self.receipts.append(receipt)
        if cached is not None:
            if cached.get('request_hash') != key:
                raise ValueError('checkpoint request binding mismatch')
            result = validate(cached['response'], request)
            receipt.update(execution_status='SUCCEEDED', reused_from=key,
                           incremental_usage={'input_tokens': 0, 'output_tokens': 0}, output=result)
            return result
        if supplied is None and provider is None:
            receipt.update(execution_status='SKIPPED', reason='PROVIDER_NOT_CONFIGURED')
            raise LookupError('provider not configured')
        partial_path = self.directory / f'{key}.partial.json' if self.directory else None
        previous = self.partial.get(key)
        if partial_path is not None and partial_path.exists():
            saved = json.loads(partial_path.read_text())
            if saved.get('request_hash') != key:
                raise ValueError('partial checkpoint binding mismatch')
            previous = validate(saved['response'], request)
        response = None
        for number in range(self.max_attempts if supplied is None else 1):
            attempt = {'attempt_id': uuid4().hex, 'started_at': datetime.now(timezone.utc).isoformat(),
                       'usage': None, 'usage_reason': 'PROVIDER_DID_NOT_REPORT', 'provider_request_id': None,
                       'execution_status': 'RUNNING'}
            start = time.monotonic()
            try:
                if supplied is None:
                    name = request.get('identity', {}).get('provider', 'configured')
                    with self.lock:
                        limit = self.providers.setdefault(name, BoundedSemaphore(self.provider_max_inflight))
                    with self.global_limit, limit:
                        if self.rate:
                            with self.rate_lock:
                                now = time.monotonic()
                                delay = max(0, self.next_request.get(name, now) - now)
                                self.next_request[name] = now + delay + 1/self.rate
                            if delay:
                                time.sleep(delay)
                        receipt['attempts'].append(attempt)
                        self.journal(key, attempt)
                        response = provider(deepcopy(request))
                else:
                    response = deepcopy(supplied)
                    receipt['supplied'] = True
                if isinstance(response, str):
                    response = json.loads(response)
                if isinstance(response, dict) and 'usage' in response:
                    attempt['usage'] = response.get('usage')
                    attempt['usage_reason'] = None if response.get('usage') is not None else 'PROVIDER_DID_NOT_REPORT'
                if isinstance(response, dict) and 'payload' in response:
                    attempt['usage'] = response.get('usage')
                    attempt['usage_reason'] = None if response.get('usage') is not None else 'PROVIDER_DID_NOT_REPORT'
                    attempt['provider_request_id'] = response.get('provider_request_id')
                    response = response['payload']
                if isinstance(response, str):
                    response = json.loads(response)
                receipt['raw_response'] = deepcopy(response)
                result = validate(response, request)
                if previous is not None:
                    response, conflicts = merge_partial(previous, response)
                    result = validate(response, request)
                    if conflicts:
                        result['status'] = 'PARTIAL'
                        result['retry_conflicts'] = conflicts
                attempt['execution_status'] = 'SUCCEEDED'
                attempt['latency_ms'] = (time.monotonic()-start)*1000
                if supplied is None:
                    self.journal(key, attempt)
                receipt['output'] = deepcopy(result)
                partial = isinstance(result, dict) and result.get('status') == 'PARTIAL'
                receipt.update(execution_status='SUCCEEDED', availability='PARTIAL' if partial else 'AVAILABLE')
                # Partial data is retained but never published as a successful cache entry.
                if partial:
                    self.partial[key] = deepcopy(result)
                    if partial_path is not None:
                        temporary_partial = partial_path.with_name(f'.{key}.{uuid4().hex}.partial.tmp')
                        try:
                            temporary_partial.write_text(json.dumps({'request_hash': key, 'response': response}, ensure_ascii=False))
                            os.replace(temporary_partial, partial_path)
                        finally:
                            temporary_partial.unlink(missing_ok=True)
                    return result
                envelope = {'contract': VERSION, 'request_hash': key, 'response': response}
                if path is not None:
                    temporary = path.with_name(f'.{key}.{uuid4().hex}.tmp')
                    try:
                        with temporary.open('x', encoding='utf-8') as handle:
                            json.dump(envelope, handle, ensure_ascii=False, allow_nan=False)
                            handle.flush(); os.fsync(handle.fileno())
                        try:
                            os.link(temporary, path)
                        except FileExistsError:
                            existing = json.loads(path.read_text())
                            if existing.get('request_hash') != key:
                                raise ValueError('checkpoint binding mismatch')
                            other = validate(existing['response'], request)
                            if other != result:
                                raise ValueError('concurrent successful outputs conflict')
                    finally:
                        temporary.unlink(missing_ok=True)
                self.memory[key] = envelope
                return result
            except Exception as exc:
                response = getattr(exc, 'response', None)
                status = getattr(response, 'status_code', None)
                if type(status) is not int:
                    status = getattr(exc, 'status_code', getattr(exc, 'code', None))
                retry_after = None
                if status in {429, 500, 502, 503, 504} and response is not None:
                    header = response.headers.get('Retry-After', '')
                    try:
                        retry_after = float(header)
                    except (TypeError, ValueError):
                        try:
                            retry_after = (parsedate_to_datetime(header) - datetime.now(timezone.utc)).total_seconds()
                        except (TypeError, ValueError, OverflowError):
                            pass
                    if retry_after is not None:
                        retry_after = min(30.0, max(0.0, retry_after))
                attempt.update(execution_status='FAILED', latency_ms=(time.monotonic()-start)*1000,
                               error=type(exc).__name__, retryable=isinstance(exc, (TimeoutError, ConnectionError)) or type(exc).__name__ in {'RemoteProtocolError','ReadTimeout','ConnectTimeout','ConnectError','ReadError','WriteError'} or status in {429, 500, 502, 503, 504})
                if type(status) is int:
                    attempt['http_status_code'] = status
                if retry_after is not None:
                    attempt['retry_after_seconds'] = retry_after
                if supplied is None:
                    self.journal(key, attempt)
                receipt.update(execution_status='FAILED', reason=type(exc).__name__)
                if not attempt['retryable'] or number + 1 >= self.max_attempts:
                    raise
                time.sleep(retry_after if retry_after is not None else min(.2 * (2**number), 2))


def merge_partial(previous, response):
    """Keep validated earlier decisions; fill only missing fields, recording conflicts."""
    merged = deepcopy(response)
    conflicts = []
    latest = {c['id']: c for c in merged['claims']}
    for claim in previous['claims']:
        for dimension in ('faithfulness', 'correctness'):
            if dimension not in claim:
                continue
            if latest[claim['id']].get(dimension) != claim[dimension]:
                conflicts.append({'claim_id': claim['id'], 'dimension': dimension,
                                  'preserved': claim[dimension], 'candidate': latest[claim['id']].get(dimension)})
            latest[claim['id']][dimension] = deepcopy(claim[dimension])
    latest_reqs = {r['id']: r for r in merged['requirements']}
    for req in previous['requirements']:
        if latest_reqs[req['id']] != req:
            conflicts.append({'requirement_id': req['id'], 'preserved': req,
                              'candidate': latest_reqs[req['id']]})
        latest_reqs[req['id']] = deepcopy(req)
    merged['requirements'] = list(latest_reqs.values())
    return merged, conflicts


def identity(value):
    if not isinstance(value, dict):
        raise ValueError("identity must be an object")
    # Never send arbitrary plugin configuration or credentials to another model.
    return {key: text(value.get(key), key) for key in ("id", "provider", "model", "prompt_version")}


def prepare_rows(spec):
    """Expand reviewed persistent constraints only over their declared turn intervals."""
    rows = deepcopy(spec["rows"])
    seen = set()
    for row in rows:
        for key in ("answer_id", "case_id", "subject_id", "subject_provider", "subject_model"):
            text(row.get(key), key)
        if type(row.get("turn")) is not int or row["turn"] < 1:
            raise ValueError("turn must be positive integer")
        key = (row["subject_id"], row["case_id"], row["turn"])
        if key in seen:
            raise ValueError("duplicate subject/case/turn")
        seen.add(key)
        requirements = row.setdefault("requirements", [])
        for constraint in spec.get("conversation_constraints", []):
            if constraint["case_id"] != row["case_id"]:
                continue
            start, end = constraint["start_turn"], constraint.get("end_turn")
            if type(start) is not int or start < 1 or (end is not None and (type(end) is not int or end < start)):
                raise ValueError("invalid constraint interval")
            if start <= row["turn"] and (end is None or row["turn"] <= end):
                if constraint.get("status") != "approved":
                    row["oracle_status"] = "provisional"
                requirements.append({"id": constraint["id"], "kind": "constraint",
                                     "text": constraint["text"], "critical": constraint["critical"]})
        indexed(requirements, "requirements")
    # Missing rows cannot silently disappear from a supposedly complete conversation.
    plans = spec.get("planned_turns")
    if not isinstance(plans, dict) or not plans:
        raise ValueError("planned_turns must declare every case's expected turn numbers")
    groups = {(r["subject_id"], r["case_id"]) for r in rows}
    planned_subjects = spec.get("planned_subjects")
    if (not isinstance(planned_subjects, list) or not planned_subjects or
            any(not isinstance(s, str) or not s for s in planned_subjects) or
            len(set(planned_subjects)) != len(planned_subjects) or
            set(planned_subjects) != {r["subject_id"] for r in rows}):
        raise ValueError("planned_subjects must match all represented subjects, including unavailable lanes")
    for subject in {r["subject_id"] for r in rows}:
        for case, turns in plans.items():
            if (not isinstance(turns, list) or not turns or any(type(t) is not int or t < 1 for t in turns)
                    or len(set(turns)) != len(turns)):
                raise ValueError("invalid planned turn list")
            actual = {r["turn"] for r in rows if r["subject_id"] == subject and r["case_id"] == case}
            if actual != set(turns):
                raise ValueError("every planned turn needs a row, including UNAVAILABLE turns")
    if any(case not in plans for _, case in groups):
        raise ValueError("unplanned case")
    if len({r["answer_id"] for r in rows}) != len(rows):
        raise ValueError("duplicate answer_id")
    return rows



def evaluate(spec, provider=None, *, checkpoint_dir=None, rubric_stage=None,
             relevancy_stage=None, store=None):
    if spec.get('contract') != VERSION:
        raise ValueError(f'contract must be {VERSION}')
    extractor = identity(spec['extractor'])
    judges = [identity(j) for j in spec['judges']]
    if not judges or len({j['id'] for j in judges}) != len(judges):
        raise ValueError('at least one unique judge required')
    rows = prepare_rows(spec)
    workers = max(1, int(spec.get('max_workers', 4)))
    store = store or ResponseStore(checkpoint_dir, max_workers=workers,
                                  provider_max_inflight=spec.get('provider_max_inflight', 2),
                                  max_attempts=spec.get('max_attempts', 2), provider_options=spec.get('provider_options'),
                                  provider_requests_per_second=spec.get('provider_requests_per_second', 0))
    def extract(row):
        if row.get('status') != 'AVAILABLE':
            return {'answer_id': row['answer_id'], 'status': 'UNAVAILABLE', 'reason': 'ANSWER_UNAVAILABLE'}
        try:
            request = extraction_request(row, extractor)
            inventory = store.call(request, provider, validate_inventory, row.get('inventory'))
            audit = inventory_audit(inventory, row.get('inventory_audit'), row.get('human_inventory', []))
            return {'answer_id': row['answer_id'], 'status': 'AVAILABLE',
                    'extraction_request_id': store.request_digest(request), 'audit': audit, **inventory}
        except Exception as exc:
            return {'answer_id': row['answer_id'], 'status': 'UNAVAILABLE', 'reason': type(exc).__name__}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        states = list(pool.map(extract, rows))
        # Materializing map is the all-extraction terminal barrier.
        frozen = {r['answer_id']: r for r in states}
        def assess(pair):
            row, judge = pair
            state = frozen[row['answer_id']]
            cell = {k: row[k] for k in ('answer_id', 'case_id', 'turn', 'subject_id')}
            cell.update(judge_id=judge['id'], judge_identity=judge, status='UNAVAILABLE')
            if state['status'] != 'AVAILABLE':
                return {**cell, 'reason': 'INVENTORY_UNAVAILABLE:'+state['reason']}
            inventory = {k: state[k] for k in ('contract', 'binding', 'extractor', 'claims', 'inventory_id')}
            cell['inventory_id'] = inventory['inventory_id']
            try:
                request = assessment_request(row, inventory, judge)
                assessment = store.call(request, provider, validate_assessment_parts,
                                        row.get('assessments', {}).get(judge['id']))
                metrics = claim_metrics(inventory, assessment)
                catalog = {u['ref']: u for u in row.get('context', [])}
                refs = {e['ref'] for c in assessment['claims'] for e in c.get('faithfulness', {}).get('evidence', [])}
                layers = {}
                for ref, unit in catalog.items():
                    layer = unit['layer']
                    entry = layers.setdefault(layer, {'provided_n': 0, 'cited_n': 0})
                    entry['provided_n'] += 1
                    entry['cited_n'] += ref in refs
                for claim in metrics['layer_attribution']['claims']:
                    claim['layers'] = sorted({catalog[ref]['layer'] for ref in claim['evidence_refs']})
                coverage_available = row.get('context_capture') == 'EXPOSED' and assessment['dimension_status']['faithfulness'] == 'AVAILABLE'
                metrics['evidence_citation_coverage'] = {
                    'status': 'AVAILABLE' if coverage_available else 'UNAVAILABLE',
                    'provided_n': len(catalog), 'cited_n': len(refs) if coverage_available else None,
                    'rate': len(refs)/len(catalog) if coverage_available and catalog else None,
                    'by_layer': layers if coverage_available else {}}
                cell.update(status=assessment['status'], assessment_request_id=store.request_digest(request),
                            assessment=assessment, metrics=metrics, inventory_audit=state['audit'],
                            requirements=requirement_metrics(row, assessment))
            except Exception as exc:
                cell['reason'] = 'ASSESSMENT_UNAVAILABLE:'+type(exc).__name__
            return cell
        cells = list(pool.map(assess, [(row, judge) for row in rows for judge in judges]))
    return {'contract': VERSION, 'inventories': [s for s in states if s['status'] == 'AVAILABLE'],
            'extraction_states': states, 'cells': cells, 'requests': store.requests,
            'receipts': store.receipts, 'summary': summarize(cells),
            'stages': {'extraction': {'planned_n': len(rows), 'available_n': sum(s['status']=='AVAILABLE' for s in states)},
                       'assessment': {'planned_n': len(cells), 'available_n': sum(c['status']=='AVAILABLE' for c in cells)}}}
