"""Provider-neutral structured judge boundary."""

from __future__ import annotations

import os
from collections.abc import Callable as ABCCallable
from typing import Any, Callable, Mapping, Protocol

from .judge import JudgeResult, parse_judge_response, validate_claim_evidence
from .rules import RatingRule


class JudgeProvider(Protocol):
    def __call__(self, request: Mapping[str, Any]) -> str: ...


class JudgeClient:
    def __init__(self, provider: JudgeProvider | Callable[[Mapping[str, Any]], str],
                 rating_rule: RatingRule, *, judge_id: str | None = None,
                 provider_id: str | None = None, model: str | None = None,
                 checkpoint: ABCCallable[[Mapping[str, Any]], None] | None = None,
                 checkpoint_event: str = "judge") -> None:
        self._provider = provider
        self._rating_rule = rating_rule
        self.judge_id = judge_id or os.getenv("XIAOAN_JUDGE_ID", "judge:configured")
        self.provider_id = provider_id or os.getenv("XIAOAN_JUDGE_PROVIDER", "configured")
        self.model = model or os.getenv("XIAOAN_JUDGE_MODEL", "configured")
        self._checkpoint = checkpoint
        self._checkpoint_event = checkpoint_event

    def judge(self, request: Mapping[str, Any]) -> JudgeResult:
        """Invoke an injected provider once and validate its untrusted output."""
        raw = _invoke(self._provider, request)
        usage = getattr(raw, "usage", {})
        if self._checkpoint is not None:
            self._checkpoint({"event": self._checkpoint_event, **{key: request[key] for key in ("case_id", "turn") if key in request}, "raw_response": str(raw), "provider_usage": usage if isinstance(usage, Mapping) else {}, "error": None})
        try:
            result = parse_judge_response(raw, self._rating_rule)
        except Exception as exc:
            if self._checkpoint is not None:
                self._checkpoint({"event": f"{self._checkpoint_event}_validation", "status": "ERROR", "error": f"{type(exc).__name__}: {exc}"})
            raise
        if self._checkpoint is not None:
            self._checkpoint({"event": f"{self._checkpoint_event}_validation", "status": "OK", "error": None})
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
