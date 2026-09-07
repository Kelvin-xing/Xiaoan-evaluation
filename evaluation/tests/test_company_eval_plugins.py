from __future__ import annotations

import json
from types import SimpleNamespace

import company_eval_plugins
import pytest


SCORE_SCALE = [
    {"score": score, "description": f"anchor {score}"} for score in range(4)
]


def test_judge_requests_schema_constrained_json(monkeypatch) -> None:
    captured = {}
    expected = {
        "red_lines": [
            {"id": "R1", "triggered": False, "evidence": [], "uncertainty": "low"}
        ],
        "dimensions": [
            {
                "module": "行动赋权",
                "score": 2,
                "supporting_evidence": ["answer"],
                "deduction_evidence": [],
                "uncertainty": "low",
            }
        ],
        "legal_claims": [],
        "faithfulness_claims": [],
    }

    class FakeCompletions:
        def create(self, **kwargs):
            captured.update(kwargs)
            return SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(expected)))]
            )

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(company_eval_plugins, "_openai_client", lambda: fake_client)
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {"XIAOAN_JUDGE_MODEL": "judge-model"})
    monkeypatch.setenv("XIAOAN_JUDGE_MODEL", "judge-model")
    monkeypatch.setenv("XIAOAN_JUDGE_REASONING_EFFORT", "medium")
    monkeypatch.setenv("XIAOAN_DISABLE_RESPONSE_STORAGE", "true")

    result = company_eval_plugins.judge(
        {
            "assistant_answer": "answer",
            "rating_rule": {
                "schema_version": "1.1",
                "score_scale": SCORE_SCALE,
                "red_lines": [{"id": "R1", "description": "unsafe"}],
                "quality_rubric": [{"name": "行动赋权", "description": "useful"}],
            },
        }
    )

    assert json.loads(result) == expected
    assert captured["model"] == "judge-model"
    assert captured["reasoning_effort"] == "medium"
    assert captured["store"] is False
    schema = captured["response_format"]["json_schema"]["schema"]
    assert schema["properties"]["red_lines"]["items"]["properties"]["id"]["enum"] == ["R1"]
    assert schema["properties"]["dimensions"]["items"]["properties"]["module"]["enum"] == ["行动赋权"]
    assert schema["properties"]["dimensions"]["items"]["properties"]["score"] == {
        "type": "integer",
        "enum": [0, 1, 2, 3],
    }


def test_responses_judge_uses_explicit_stable_prefix_cache_breakpoint(monkeypatch) -> None:
    captured = {}

    class FakeResponses:
        def create(self, **kwargs):
            captured.update(kwargs)
            payload = json.dumps({"red_lines": [], "dimensions": [], "legal_claims": [], "faithfulness_claims": []})
            usage = SimpleNamespace(model_dump=lambda: {"input_tokens": 100, "input_tokens_details": {"cached_tokens": 80, "cache_write_tokens": 10}})
            return [SimpleNamespace(type="response.output_text.delta", delta=payload), SimpleNamespace(type="response.completed", response=SimpleNamespace(usage=usage))]

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(company_eval_plugins, "_openai_client", lambda: fake_client)
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {
        "XIAOAN_OPENAI_WIRE_API": "responses",
        "XIAOAN_PROMPT_CACHE_MODE": "explicit",
    })
    monkeypatch.setenv("XIAOAN_DISABLE_RESPONSE_STORAGE", "true")

    result = company_eval_plugins.judge({
        "case_id": "TC-01",
        "rating_rule": {"score_scale": SCORE_SCALE, "red_lines": [], "quality_rubric": []},
    })

    assert captured["prompt_cache_options"] == {"mode": "explicit", "ttl": "30m"}
    assert captured["prompt_cache_key"].startswith("xiaoan-eval-v1:")
    assert captured["input"][0]["content"][0]["prompt_cache_breakpoint"] == {}
    assert "rating_rule" in captured["input"][0]["content"][0]["text"]
    assert "TC-01" in captured["input"][1]["content"][0]["text"]
    assert result.usage["input_tokens_details"]["cached_tokens"] == 80


def test_judge_accepts_provider_returning_structured_content_as_a_string(
    monkeypatch,
) -> None:
    expected = {
        "red_lines": [],
        "dimensions": [],
        "legal_claims": [],
        "faithfulness_claims": [],
    }

    class FakeCompletions:
        def create(self, **_kwargs):
            return json.dumps(expected)

    fake_client = SimpleNamespace(
        chat=SimpleNamespace(completions=FakeCompletions())
    )
    monkeypatch.setattr(company_eval_plugins, "_openai_client", lambda: fake_client)

    result = company_eval_plugins.judge(
        {
                "rating_rule": {
                    "score_scale": SCORE_SCALE,
                    "red_lines": [],
                "quality_rubric": [],
            }
        }
    )

    assert json.loads(result) == expected


def test_judge_unwraps_markdown_fenced_json_from_compatible_provider(
    monkeypatch,
) -> None:
    expected = {
        "red_lines": [],
        "dimensions": [],
        "legal_claims": [],
        "faithfulness_claims": [],
    }

    class FakeCompletions:
        def create(self, **_kwargs):
            return "```json\n" + json.dumps(expected) + "\n```"

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(company_eval_plugins, "_openai_client", lambda: fake_client)

    result = company_eval_plugins.judge(
        {"rating_rule": {"score_scale": SCORE_SCALE, "red_lines": [], "quality_rubric": []}}
    )

    assert json.loads(result) == expected


def test_judge_reports_non_json_provider_text_with_a_bounded_preview(
    monkeypatch,
) -> None:
    class FakeCompletions:
        def create(self, **_kwargs):
            return "Service Unavailable: model quota exhausted"

    fake_client = SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions()))
    monkeypatch.setattr(company_eval_plugins, "_openai_client", lambda: fake_client)

    with pytest.raises(RuntimeError, match="Service Unavailable: model quota exhausted"):
        company_eval_plugins.judge(
                {"rating_rule": {"score_scale": SCORE_SCALE, "red_lines": [], "quality_rubric": []}}
        )


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


def test_primary_judge_defaults_to_documented_model(monkeypatch) -> None:
    captured = {}
    monkeypatch.delenv("XIAOAN_JUDGE_MODEL", raising=False)
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {})
    monkeypatch.setattr(
        company_eval_plugins,
        "_judge_with_model",
        lambda request, model: captured.update(model=model) or "{}",
    )

    assert company_eval_plugins.judge({"case_id": "TC-01"}) == "{}"
    assert captured["model"] == "gpt-5.5"


def test_evaluation_env_falls_back_to_project_local_file(tmp_path, monkeypatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "XIAOAN_JUDGE_MODEL=file-model\nOPENAI_API_KEY=file-key\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(company_eval_plugins, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(company_eval_plugins, "EVALUATION_ENV_PATH", env_file)
    monkeypatch.setenv("XIAOAN_JUDGE_MODEL", "shell-model")
    monkeypatch.setenv("OPENAI_API_KEY", "shell-key")

    values = company_eval_plugins._evaluation_env()

    assert values["XIAOAN_JUDGE_MODEL"] == "file-model"
    assert values["OPENAI_API_KEY"] == "shell-key"


def test_recommendation_prompt_requests_chinese_user_visible_text() -> None:
    assert "繁體中文" in company_eval_plugins.RECOMMENDATION_INSTRUCTIONS
    assert "problem_statement" in company_eval_plugins.RECOMMENDATION_INSTRUCTIONS


def test_openai_client_uses_shared_custom_base_url(monkeypatch) -> None:
    captured = {}
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setenv("XIAOAN_OPENAI_BASE_URL", "https://api.karoapi.com/v1")
    monkeypatch.delenv("XIAOAN_JUDGE_BASE_URL", raising=False)
    monkeypatch.setattr(
        company_eval_plugins,
        "OpenAI",
        lambda **kwargs: captured.update(kwargs) or object(),
    )
    monkeypatch.setattr(company_eval_plugins, "_evaluation_env", lambda: {
        "OPENAI_API_KEY": "test-key",
        "XIAOAN_OPENAI_BASE_URL": "https://api.karoapi.com/v1",
    })

    company_eval_plugins._openai_client()

    assert captured == {
        "api_key": "test-key",
        "base_url": "https://api.karoapi.com/v1",
        "timeout": 600.0,
    }


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
