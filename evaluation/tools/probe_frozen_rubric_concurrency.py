"""Bounded live rubric probe; successful calls become reusable retry checkpoints."""
from __future__ import annotations

import argparse
from collections import Counter, deque
from concurrent.futures import ThreadPoolExecutor, as_completed
from itertools import islice
import json
from pathlib import Path
from threading import Lock
import time
from uuid import uuid4

from xiaoan_eval.frozen_cli import write_json
from xiaoan_eval.frozen_provider import ConfiguredProvider, transport_options
from xiaoan_eval.rules import load_rating_rule
from xiaoan_eval_core.configuration import ROOT, snapshot
from xiaoan_eval_core.orchestration import build_rubric_request
from xiaoan_eval_core.rubric import evaluate_rubric
from xiaoan_eval_core.runtime import ResponseStore


def candidates(spec, store):
    rule = load_rating_rule(ROOT / 'rating-rule.yml')
    pending = {judge['id']: deque() for judge in spec['judges']}
    for row in spec['rows']:
        if row['status'] != 'AVAILABLE':
            continue
        for judge in spec['judges']:
            request = build_rubric_request(row, rule, judge=judge)
            key = store.request_digest(request)
            # Never append an event to, or replay, an existing checkpoint key.
            if any((store.directory / (key + suffix)).exists()
                   for suffix in ('.json', '.partial.json', '.events.jsonl')):
                continue
            pending[judge['id']].append((row, request))
    while any(pending.values()):
        for group in pending.values():
            if group:
                yield group.popleft(), rule


def probe(spec, output, count, level):
    if count < 1 or level < 1:
        raise ValueError('count and level must be positive')
    if spec['evaluation_config'] != snapshot():
        raise ValueError('Frozen evaluator config differs from current config')
    provider = ConfiguredProvider(output / 'provider-artifacts')
    if transport_options(provider.values) != spec['evaluation_provider_options']:
        raise ValueError('Provider options differ from frozen evaluator input')
    store = ResponseStore(output / 'checkpoint', max_workers=level,
                          provider_max_inflight=level, max_attempts=1,
                          provider_options=spec['evaluation_provider_options'])
    selected = list(islice(candidates(spec, store), count))
    if len(selected) != count:
        raise ValueError('Not enough untouched rubric cells for this probe')
    lock = Lock()
    inflight = peak = 0
    errors = Counter()
    def one(item):
        nonlocal inflight, peak
        (row, request), rule = item
        def timed_provider(value):
            nonlocal inflight, peak
            with lock:
                inflight += 1
                peak = max(peak, inflight)
            try:
                return provider(value)
            finally:
                with lock:
                    inflight -= 1
        return store.call(request, timed_provider,
                          lambda response, _: evaluate_rubric(row, response, rule))
    started = time.monotonic()
    try:
        with ThreadPoolExecutor(max_workers=level) as pool:
            futures = [pool.submit(one, item) for item in selected]
            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as exc:
                    status = getattr(getattr(exc, 'response', None), 'status_code', None)
                    errors[f'{type(exc).__name__}:{status}' if status else type(exc).__name__] += 1
    finally:
        provider.close()
    elapsed = time.monotonic() - started
    report = {'level': level, 'requests': count, 'peak_inflight': peak,
              'succeeded': count - sum(errors.values()), 'errors': dict(errors),
              'elapsed_seconds': round(elapsed, 2),
              'successful_per_minute': round((count-sum(errors.values())) * 60 / elapsed, 2)}
    write_json(output / 'concurrency-probes' / f'level-{level}-count-{count}-{uuid4().hex}.json', report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen-input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--level', type=int, required=True)
    parser.add_argument('--count', type=int, required=True)
    args = parser.parse_args()
    spec = json.loads(args.frozen_input.read_text())
    print(json.dumps(probe(spec, args.output, args.count, args.level), ensure_ascii=False))


if __name__ == '__main__':
    main()
