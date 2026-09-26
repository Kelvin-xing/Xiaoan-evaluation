"""Exercise the frozen pilot's transport without executing its live orchestration."""
import ast
import json
import time
from pathlib import Path
from types import SimpleNamespace

import pytest

from xiaoan_eval_core.contracts import digest


def load_transport(tmp_path, post):
    root = Path(__file__).resolve().parents[1]
    script = root / 'runs/20260923-tc52-gpt6-three-judges/private/run_staged.py'
    tree = ast.parse(script.read_text())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'llm')
    namespace = dict(json=json, time=time, digest=digest, HERE=tmp_path,
                     ROOT=root.parent, GPT_RESPONSES=True,
                     model_config=SimpleNamespace(
                         client_config=lambda model: {'base_url': 'https://example.invalid', 'api_key': 'test'},
                         provider_for_model=lambda model: 'claude'),
                     httpx=SimpleNamespace(post=post))
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(script), 'exec'), namespace)
    return namespace['llm']


@pytest.mark.parametrize('complete', [True, False])
def test_claude_rubric_requires_one_completed_tool(tmp_path, complete):
    captured = []
    payload = {'dimensions': [{'module': 'quality', 'score': 2, 'supporting_evidence': ['含有"引號"'],
                              'deduction_evidence': [], 'uncertainty': 'low'}],
               'red_lines': [{'id': 'R1', 'triggered': False, 'evidence': [], 'uncertainty': 'low'}]}
    def post(url, **kwargs):
        captured.append(kwargs['json'])
        raw = {'stop_reason': 'tool_use' if complete else 'max_tokens',
               'content': [{'type': 'tool_use', 'name': 'submit_judgement', 'input': payload}]}
        return SimpleNamespace(raise_for_status=lambda: None, json=lambda: raw)
    call = load_transport(tmp_path, post)
    request = {'rating_rule': {'modules': [{'name': 'quality'}], 'red_lines': [{'id': 'R1'}],
                              'score_scale': [{'score': n} for n in range(4)]}}
    if complete:
        assert call('claude-test', request, 'rubric') == payload
    else:
        with pytest.raises(ValueError, match='completed judgement'):
            call('claude-test', request, 'rubric')
        assert not any('parsed' in json.loads(p.read_text()) for p in (tmp_path/'calls').glob('*.json'))
    body = captured[0]
    assert body['tool_choice'] == {'type': 'tool', 'name': 'submit_judgement'}
    schema = body['tools'][0]['input_schema']
    assert set(schema['required']) == {'dimensions', 'red_lines'}
    assert schema['properties']['dimensions']['items']['properties']['module']['enum'] == ['quality']
