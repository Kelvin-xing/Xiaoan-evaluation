"""Bounded trial: known failing Judge endpoints are circuit-open; no payload changes."""
import company_eval_plugins

def judge(spec, prompt):
    if spec.provider in {'kimi', 'qwen'}:
        raise RuntimeError('TRIAL_CIRCUIT_OPEN_NOT_ATTEMPTED: ' + spec.provider + ' Judge paused after observed repeated rate limits/timeouts or incomplete streams; prior successful judgements preserved; not a quality zero')
    return company_eval_plugins.multimodel_transport(spec, prompt)
