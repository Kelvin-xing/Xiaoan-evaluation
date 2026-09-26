from __future__ import annotations

import json
import io
import os
from types import SimpleNamespace
from email.message import Message
from urllib.error import HTTPError

import company_eval_plugins
import pytest
from xiaoan_eval.multimodel import ModelSpec, default_subject_specs, invoke


@pytest.fixture(autouse=True)
def shared_file(monkeypatch, tmp_path):
    from xiaoan_eval_core import model_config
    path = tmp_path / ".env"
    values = {"GLOBALAI_API_BASE": "https://globalai.vip/v1", "XIAOAN_JUDGE_MODEL": "gpt-test",
              "XIAOAN_OPENAI_WIRE_API": "chat_completions", "XIAOAN_CLAUDE_API_MODE": "anthropic",
              "XIAOAN_OPENAI_API_KEY": "test-key", "XIAOAN_CLAUDE_API_KEY": "test-key", "XIAOAN_GEMINI_API_KEY": "test-key"}
    for provider in ("CLAUDE", "GPT", "GEMINI", "DEEPSEEK"):
        values.update({f"XIAOAN_{provider}_LATEST_MODEL": "subject", f"XIAOAN_{provider}_SECOND_MODEL": "latest", f"XIAOAN_{provider}_JUDGE_MODEL": "judge"})
    def write(**updates):
        values.update(updates)
        path.write_text("".join(f"{k}={v}\n" for k,v in values.items()))
    values["XIAOAN_MAX_RETRIES"] = "1"
    write()
    monkeypatch.setattr(company_eval_plugins.time, "sleep", lambda _: None)
    monkeypatch.setattr(model_config, "ENV_PATH", path)
    monkeypatch.setattr(company_eval_plugins, "EVALUATION_ENV_PATH", path)
    return write


def test_local_env_model_settings_override_stale_process_values(
    monkeypatch, tmp_path
) -> None:
    env_path = tmp_path / ".env"
    original = company_eval_plugins.EVALUATION_ENV_PATH.read_text()
    env_path.write_text(
        original + "XIAOAN_GPT_LATEST_MODEL=gpt-file-current\n"
        "XIAOAN_JUDGE_MODEL=judge-file-current\n"
        "GLOBALAI_API_KEY=file-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(company_eval_plugins, "EVALUATION_ENV_PATH", env_path)
    monkeypatch.setattr(company_eval_plugins.model_config, "ENV_PATH", env_path)
    monkeypatch.setenv("XIAOAN_GPT_LATEST_MODEL", "gpt-process-old")
    monkeypatch.setenv("XIAOAN_JUDGE_MODEL", "judge-process-old")
    monkeypatch.setenv("GLOBALAI_API_KEY", "process-key")

    company_eval_plugins._load_local_env()

    assert os.environ["XIAOAN_GPT_LATEST_MODEL"] == "gpt-file-current"
    assert os.environ["XIAOAN_JUDGE_MODEL"] == "judge-file-current"
    assert os.environ["GLOBALAI_API_KEY"] == "process-key"
    assert default_subject_specs()[2].model == "gpt-file-current"
    assert company_eval_plugins._evaluation_env()["XIAOAN_JUDGE_MODEL"] == "judge-file-current"
    assert company_eval_plugins._evaluation_env()["GLOBALAI_API_KEY"] == "file-key"


SCORE_SCALE = [
    {"score": score, "description": f"anchor {score}"} for score in range(4)
]
























def test_second_judge_uses_independent_model(monkeypatch) -> None:
    seen = []
    monkeypatch.setattr(
        company_eval_plugins,
        "_judge_with_model",
        lambda request, model: seen.append((request, model)) or "{}",
    )
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {"XIAOAN_SECONDARY_JUDGE_MODEL": "second-model"})
    monkeypatch.setenv("XIAOAN_SECONDARY_JUDGE_MODEL", "second-model")

    assert company_eval_plugins.second_judge({"case_id": "TC-01"}) == "{}"
    assert seen == [({"case_id": "TC-01"}, "second-model")]


def test_primary_judge_requires_file_model(monkeypatch):
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {})
    with pytest.raises(ValueError, match="XIAOAN_JUDGE_MODEL"):
        company_eval_plugins.judge({})


def test_recommendation_prompt_requests_chinese_user_visible_text() -> None:
    assert "繁體中文" in company_eval_plugins.RECOMMENDATION_INSTRUCTIONS
    assert "problem_statement" in company_eval_plugins.RECOMMENDATION_INSTRUCTIONS


def test_chatflow_transport_uses_separate_long_outer_timeout(monkeypatch) -> None:
    captured = {}

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return b'{"conversation_id":"conv-1"}'

    class Opener:
        def open(self, _request, timeout):
            captured["timeout"] = timeout
            return Response()

    transport = company_eval_plugins.XiaoAnChatflowTransport()
    transport._state().opener = Opener()
    monkeypatch.setenv("XIAOAN_PROVIDER_TIMEOUT", "120")
    monkeypatch.delenv("XIAOAN_CHATFLOW_TIMEOUT", raising=False)

    transport._json("POST", "http://test.invalid/v1/conversations")

    assert captured["timeout"] == 600.0




def test_authoritative_context_resolves_only_trace_refs(monkeypatch) -> None:
    monkeypatch.setattr(
        company_eval_plugins,
        "_resolve_ref",
        lambda ref: [{"ref": ref, "title": "Title", "text": "Evidence"}],
    )

    context = company_eval_plugins.authoritative_context(
        case=object(),
        turn=object(),
        trace={"ground": {"resolved_ground": ["node-a", "node-a", "node-b"]}},
    )

    assert [item["ref"] for item in context["items"]] == ["node-a", "node-b"]
    assert context["unresolved_refs"] == []


def test_authoritative_context_accepts_large_ground_ref_sets_when_configured(monkeypatch) -> None:
    """The resolver preserves large sets when an explicit higher cap is configured."""
    monkeypatch.setattr(company_eval_plugins, "MAX_CONTEXT_ITEMS", 42)
    monkeypatch.setattr(
        company_eval_plugins,
        "_resolve_ref",
        lambda ref: [{"ref": ref, "title": "Title", "text": "Evidence"}],
    )

    refs = [f"node-{index}" for index in range(42)]
    context = company_eval_plugins.authoritative_context(
        case=object(),
        turn=object(),
        trace={"ground": {"resolved_ground": refs}},
    )

    assert [item["ref"] for item in context["items"]] == refs


def test_authoritative_context_rejects_unsupported_legacy_capsule_evidence() -> None:
    with pytest.raises(
        company_eval_plugins.AuthoritativeContextError,
        match="not supported by the current Chatflow trace contract",
    ):
        company_eval_plugins.authoritative_context(
            case=object(),
            turn=object(),
            trace={
                "route": {"capsule_id": "n3"},
                "ground": {"resolved_ground": []},
                "capsule": {"available_refs": ["capsule:n3:recognize:0"]},
            },
        )


def test_authoritative_context_fails_closed_for_unresolved_refs(monkeypatch) -> None:
    def fail(_ref: str):
        raise ValueError("missing")

    monkeypatch.setattr(company_eval_plugins, "_resolve_ref", fail)

    with pytest.raises(
        company_eval_plugins.AuthoritativeContextError,
        match="could not be resolved: missing",
    ):
        company_eval_plugins.authoritative_context(
            case=object(), turn=object(), trace={"ground": {"resolved_ground": ["missing"]}}
        )


def test_captured_ground_is_complete_bounded_and_never_reresolved(monkeypatch):
    import hashlib
    def unit(index):
        text = "Captured clause " + str(index)
        return {"occurrence_id": f"source:{index}", "unit_id": f"source:{index}",
                "layer": "SOURCE", "source_turn": 1, "content": text,
                "content_sha256": "sha256:" + hashlib.sha256(text.encode()).hexdigest(), "policy_ids": []}
    snapshot = {"schema_version": "effective-context-snapshot/v1", "snapshot_id": "frozen",
                "turn": 1, "context_kind": "ordinary",
                "router": {"status": "INVOKED", "units": [unit(99)]},
                "composer": {"status": "INVOKED", "units": [unit(i) for i in range(37)]}}
    def forbidden(_):
        raise AssertionError("must not resolve frozen evidence against current repository")
    monkeypatch.setattr(company_eval_plugins, "_resolve_ref", forbidden)
    context = company_eval_plugins.authoritative_context(object(), object(),
        {"effective_context_snapshot": snapshot, "ground": {"resolved_ground": [str(i) for i in range(37)]}})
    assert len(context["items"]) == 37
    assert context["items"][-1]["text"] == "Captured clause 36"
    assert all(item["snapshot_id"] == "frozen" for item in context["items"])
    monkeypatch.setattr(company_eval_plugins, "MAX_CAPTURED_CONTEXT_CHARS", 1)
    with pytest.raises(company_eval_plugins.AuthoritativeContextError, match="budget"):
        company_eval_plugins.authoritative_context(object(), object(), {"effective_context_snapshot": snapshot})
    snapshot["composer"]["units"][0]["content"] = "changed"
    with pytest.raises(company_eval_plugins.AuthoritativeContextError, match="invalid"):
        company_eval_plugins.authoritative_context(object(), object(), {"effective_context_snapshot": snapshot})


@pytest.mark.parametrize("provider", ["qwen", "kimi"])
def test_unconfigured_provider_rejected_before_network(monkeypatch, provider):
    monkeypatch.setattr(company_eval_plugins, "urlopen", lambda *a, **k: pytest.fail("must not send"))
    with pytest.raises(ValueError, match="仅支持"):
        company_eval_plugins.multimodel_transport(ModelSpec(provider, "old", "latest"), "synthetic")







@pytest.mark.parametrize('content', ['{"ok":true}', '```json\n{"ok":true}\n```'])
def test_canonical_provider_preserves_config_prompt_and_decodes_json(monkeypatch, tmp_path, content):
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    from xiaoan_eval_core import llm_adapter
    captured = []
    async def fake(body, config, **kwargs):
        captured.append(body)
        return {'id': 'request1', 'choices': [{'message': {'content': content}}],
                'usage': {'prompt_tokens': 8, 'completion_tokens': 2}}
    monkeypatch.setattr(llm_adapter, 'arequest', fake)
    provider = ConfiguredProvider(tmp_path / 'requests')
    reply = provider({'task': 'rubric', 'identity': {'model': 'judge'},
                      'instructions': 'EXTERNAL CONFIG PROMPT', 'answer': 'frozen'})
    assert reply['payload'] == {'ok': True}
    assert reply['usage']['total_tokens'] == 10
    assert captured[0]['messages'][0]['content'] == 'EXTERNAL CONFIG PROMPT'
    assert 'frozen' in captured[0]['messages'][1]['content']
    assert captured[0]['store'] is False


def test_canonical_provider_uses_strict_schema_when_supplied(monkeypatch, tmp_path):
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    from xiaoan_eval_core import llm_adapter
    captured = []
    async def fake(body, config, **kwargs):
        captured.append(body)
        return {'choices': [{'message': {'content': '{"ok":true}'}}]}
    monkeypatch.setattr(llm_adapter, 'arequest', fake)
    ConfiguredProvider(tmp_path / 'requests')({'task': 'rubric', 'identity': {'model': 'judge'},
        'instructions': 'prompt', 'response_schema': {'type': 'object', 'properties': {'ok': {'type': 'boolean'}},
        'required': ['ok'], 'additionalProperties': False}, 'answer': 'frozen'})
    fmt = captured[0]['response_format']
    assert fmt['type'] == 'json_schema'
    assert fmt['json_schema']['strict'] is True

@pytest.mark.parametrize('status', ['failed', 'incomplete'])
def test_canonical_provider_rejects_incomplete_response(status):
    from xiaoan_eval.frozen_provider import response_text
    with pytest.raises(ValueError, match='failed/incomplete'):
        response_text({'status': status, 'output_text': 'partial'})


def test_canonical_provider_uses_shared_credentials_without_serializing_them(monkeypatch, tmp_path):
    from xiaoan_eval.frozen_provider import ConfiguredProvider
    from xiaoan_eval_core import llm_adapter
    async def fake(body, config, **kwargs):
        assert config['XIAOAN_OPENAI_API_KEY'] == 'test-key'
        assert 'API_KEY' not in json.dumps(body)
        return {'choices': [{'message': {'content': 'answer'}}]}
    monkeypatch.setattr(llm_adapter, 'arequest', fake)
    provider = ConfiguredProvider(tmp_path / 'requests')
    provider.subject({'model': 'subject'}, 'question', [], [])
    assert all('test-key' not in p.read_text() for p in (tmp_path / 'requests').glob('*.json'))

@pytest.mark.parametrize('model,family,wire', [('gpt-test','OPENAI','chat_completions'), ('claude-test','CLAUDE','messages'), ('gemini-test','GEMINI','chat_completions')])
def test_shared_async_transport_endpoint_credentials_and_usage(monkeypatch, model, family, wire):
    import asyncio
    import httpx
    from xiaoan_eval_core import llm_adapter
    captured = []
    def handle(request):
        captured.append(request)
        raw = {'content': [{'type':'text', 'text':'hello'}], 'usage':{'input_tokens':8,'output_tokens':2}} if wire == 'messages' else {'choices':[{'message':{'content':'hello'}}], 'usage':{'prompt_tokens':8,'completion_tokens':2}}
        return httpx.Response(200, json=raw)
    original = httpx.AsyncClient
    monkeypatch.setattr(httpx, 'AsyncClient', lambda **kw: original(transport=httpx.MockTransport(handle), **kw))
    config = {f'XIAOAN_{family}_BASE_URL':'https://fixture.invalid/v1', f'XIAOAN_{family}_API_KEY':'fixture-key', 'XIAOAN_OPENAI_WIRE_API':'chat_completions'}
    result = asyncio.run(llm_adapter.arequest({'model':model,'messages':[{'role':'system','content':'stable'},{'role':'user','content':'dynamic'}]}, config, provider=family))
    assert str(captured[0].url).endswith('/messages' if wire == 'messages' else '/chat/completions')
    assert captured[0].headers['x-api-key' if wire == 'messages' else 'Authorization'] == ('fixture-key' if wire == 'messages' else 'Bearer fixture-key')
    assert result['usage']


def test_canonical_retry_empty_json_and_usage_receipts(monkeypatch, tmp_path):
    from xiaoan_eval_core.runtime import ResponseStore
    calls=[]
    def call(request):
        calls.append(request)
        if len(calls) == 1:
            raise TimeoutError('transient')
        return {'payload': {'ok':True}, 'usage':{'input_tokens':8,'output_tokens':2}}
    store = ResponseStore(tmp_path, max_attempts=2)
    request={'task':'fixture','identity':{'provider':'fixture'},'binding':'frozen'}
    assert store.call(request, call, lambda payload,req: payload) == {'ok':True}
    assert store.call(request, call, lambda payload,req: payload) == {'ok':True}
    assert len(calls)==2
