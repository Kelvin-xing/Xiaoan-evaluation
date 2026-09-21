"""Retry wrapper for Qwen and Kimi Judge calls with one in-flight call each."""
import threading
import company_eval_plugins

_GATES = {provider: threading.Semaphore(1) for provider in ("qwen", "kimi")}

def judge(spec, prompt):
    gate = _GATES.get(spec.provider)
    if gate is None:
        return company_eval_plugins.multimodel_transport(spec, prompt)
    with gate:
        return company_eval_plugins.multimodel_transport(spec, prompt)
