"""Offline examples only. This module never contacts the SUT or a provider."""
def allow_synthetic(request):
    return request.get('question') == 'Which answer is correct?' or request.get('probe_id', '').startswith('synthetic-')

def pairwise(request):
    return {'winner': 'LEFT' if request['left'] == 'correct' else 'RIGHT', 'reason': 'Synthetic fixture: the literal word correct wins.'}

def harness(request):
    return {**{k: request[k] for k in ('probe_id', 'arm', 'session_id')}, 'status': 'AVAILABLE', 'control_hash': request['control_hash'], 'facts': request['scenario']['synthetic_facts']}
