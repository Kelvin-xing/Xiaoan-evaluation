"""Provider-neutral structured judge boundary."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from .judge import JudgeResult, parse_judge_response, validate_claim_evidence
from .rules import RatingRule


class JudgeProvider(Protocol):
    def __call__(self, request: Mapping[str, Any]) -> str: ...


class JudgeClient:
    def __init__(self, provider: JudgeProvider | Callable[[Mapping[str, Any]], str],
                 rating_rule: RatingRule) -> None:
        self._provider = provider
        self._rating_rule = rating_rule

    def judge(self, request: Mapping[str, Any]) -> JudgeResult:
        """Invoke an injected provider once and validate its untrusted output."""
        result = parse_judge_response(_invoke(self._provider, request), self._rating_rule)
        catalog = request.get("evidence_catalog", [])
        if not isinstance(catalog, list):
            raise TypeError("judge request evidence_catalog must be an array")
        validate_claim_evidence(result, catalog)
        return result


def _invoke(provider: Any, request: Mapping[str, Any]) -> str:
    if callable(provider):
        return provider(request)
    for method_name in ("generate", "complete"):
        method = getattr(provider, method_name, None)
        if callable(method):
            return method(request)
    raise TypeError("judge provider must be callable or expose generate/complete")
