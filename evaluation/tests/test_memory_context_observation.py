from xiaoan_eval.memory_metrics import conversation_context_observation
from test_evidence import _runtime_history_window


def test_router_memory_does_not_prove_composer_memory():
    snapshot=_runtime_history_window()
    snapshot['invocations']['composer']['provider_continuation_used']=False
    trace={'effective_context_snapshot':snapshot,'router_context':{'supplied_completed_turns':2}}
    result=conversation_context_observation(['older','user-0','user-1'],trace)
    assert result['router_history_matches_window'] is True
    assert result['composer_explicit_history_matches'] is False


def test_uncaptured_provider_continuation_stays_unknown():
    snapshot=_runtime_history_window()
    snapshot['invocations']['composer']['provider_continuation_used']=True
    result=conversation_context_observation(['user-0','user-1'],{'effective_context_snapshot':snapshot})
    assert result['composer_explicit_history_matches'] is None
    assert result['composer_history_reason'].startswith('TRACE_MISSING')
