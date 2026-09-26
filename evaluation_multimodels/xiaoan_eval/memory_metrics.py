"""Shared memory lifecycle observations; absence of telemetry is never failure."""
from __future__ import annotations

from typing import Any, Mapping, Sequence

from .cases import MemoryCheckpoint


def memory_observation(checkpoint: MemoryCheckpoint, trace: Mapping[str, Any]) -> dict[str, Any]:
    state = trace.get("state")
    state = state if isinstance(state, Mapping) else {}
    kind = checkpoint.check_type
    expected = set(checkpoint.facts)

    def facts(field: str) -> set[str] | None:
        value = state.get(field)
        return set(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) and all(isinstance(item, str) for item in value) else None

    def flag(field: str) -> bool | None:
        value = state.get(field)
        return value if isinstance(value, bool) else None

    retained = facts("memory_facts")
    retrieved_facts = facts("memory_retrieved_facts")
    used_facts = facts("memory_used_facts")
    contamination = facts("memory_contamination_candidates")
    remembered = expected <= retained if retained is not None else None
    retrieved = expected <= retrieved_facts if retrieved_facts is not None else None
    used = expected <= used_facts if used_facts is not None else flag("memory_used")
    decision: bool | None = None
    if kind == "remember":
        decision = remembered
    elif kind == "retrieve":
        decision = retrieved
    elif kind == "use":
        # Explicit per-fact use evidence is sufficient. A generic flag additionally
        # needs retention evidence; an absent flag is not False.
        decision = used if used_facts is not None else (
            remembered and used if remembered is not None and used is not None else None
        )
    elif kind == "not_use":
        decision = not bool(expected & used_facts) if used_facts is not None else (
            not used if used is not None else None
        )
    elif kind == "update":
        decision = flag("memory_updated_correctly")
    elif kind == "isolation":
        isolated = flag("memory_isolated")
        decision = False if contamination else isolated
    elif kind in {"stale", "unsafe"}:
        violation = flag(f"memory_{kind}")
        if violation is None:
            violation = flag("memory_stale_or_unsafe")
        decision = not violation if violation is not None else None
    else:
        raise ValueError(f"unsupported memory checkpoint type: {kind}")
    return {
        "status": "skip" if decision is None else "pass" if decision else "fail",
        "reason": "memory telemetry unavailable or invalid" if decision is None else f"memory {kind} {'passed' if decision else 'failed'}",
        "check_type": kind, "expected_facts": sorted(expected),
        "retrieved_facts": sorted(retrieved_facts) if retrieved_facts is not None else None,
        "remembered": remembered, "retrieved": retrieved,
        "used_when_required": decision if kind == "use" else None,
        "not_used_when_forbidden": decision if kind == "not_use" else None,
        "updated_correctly": decision if kind == "update" else None,
        "isolated": decision if kind == "isolation" else None,
        "stale_or_unsafe": not decision if kind in {"stale", "unsafe"} and decision is not None else None,
        "contamination_candidates": sorted(contamination) if kind == "isolation" and contamination is not None else None,
    }


def conversation_context_observation(prior_user_inputs, trace):
    """Observe Router and Composer separately; never invent semantic memory flags."""
    from .evidence import validate_effective_context_snapshot
    if not prior_user_inputs:
        return {'status':'NOT_APPLICABLE','reason':'first turn has no prior inputs'}
    try:
        snapshot=validate_effective_context_snapshot(trace['effective_context_snapshot'])
    except (KeyError,ValueError,TypeError):
        return {'status':'UNAVAILABLE','reason':'TRACE_MISSING'}
    router_texts=[u.content for u in snapshot.router.units if u.layer=='PRIOR_USER']
    composer_texts=[u.content for u in snapshot.composer.units if u.layer=='PRIOR_USER']
    raw=trace['effective_context_snapshot'].get('invocations',{}).get('composer',{})
    continuation=raw.get('provider_continuation_used')
    expected=list(prior_user_inputs)
    supplied=trace.get('router_context',{}).get('supplied_completed_turns')
    router_expected=expected[-supplied:] if type(supplied) is int and supplied>0 else [] if supplied==0 else expected
    router_matches=router_texts==router_expected if snapshot.router.status=='INVOKED' else None
    # Unknown/implicit continuation needs its own captured parent evidence, not a guessed pass.
    composer_matches=composer_texts==expected if continuation is False else None
    return {'status':'AVAILABLE','router_history_matches_window':router_matches,
            'composer_explicit_history_matches':composer_matches,
            'composer_history_reason':'EXPLICIT_HISTORY_CHECK' if continuation is False else 'TRACE_MISSING: implicit provider parent context not captured',
            'provider_continuation_used':continuation,'router_history_count':len(router_texts),
            'composer_history_count':len(composer_texts),'expected_history_count':len(expected),
            'semantic_use':'UNAVAILABLE: requires answer-to-fact evidence; context presence alone is insufficient'}
