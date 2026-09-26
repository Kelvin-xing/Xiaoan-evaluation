"""Offline two-session probe of the actual in-memory ConversationStore.
This proves storage separation only, not model-level semantic non-disclosure.
"""
from pathlib import Path
import sys,json
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tech/chatflow/poc'))
from conversation_store import InMemoryConversationStore


def probe(*, negative_control=False):
    store=InMemoryConversationStore();a,_=store.create();b,_=store.create()
    marker='SYNTHETIC-SESSION-A-7319'
    a.state.record_turn(redacted_user_message='仅会话A的测试标记：'+marker,assistant_response='收到',route_id='baseline',safety_level='normal')
    if negative_control:b.state=a.state
    isolated=marker not in json.dumps(b.state.context_for_router(),ensure_ascii=False)
    a_retained=marker in json.dumps(a.state.context_for_router(),ensure_ascii=False)
    return {'status':'PASS' if isolated and a_retained else 'FAIL','scope':'in_memory_conversation_store_only','session_a_seed_retained':a_retained,'session_b_has_no_a_marker':isolated,'negative_control':negative_control,'model_non_disclosure':'UNAVAILABLE: no subject model called','authorization_boundary':'No network calls; synthetic marker only.'}

if __name__=='__main__':
    result={'positive':probe(),'negative_control':probe(negative_control=True)}
    assert result['positive']['status']=='PASS' and result['negative_control']['status']=='FAIL'
    output=ROOT/'evaluation/runs/2026-09-13-minimal32-oracle-completion/memory-session-probe.json';output.parent.mkdir(exist_ok=True);output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
