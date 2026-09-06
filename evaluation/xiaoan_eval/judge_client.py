"""Provider-neutral structured judge boundary."""

from __future__ import annotations

from typing import Any, Callable, Mapping, Protocol

from .judge import JudgeResult, parse_judge_response, validate_claim_evidence
from .rules import RatingRule


class JudgeProvider(Protocol):
    def __call__(self, request: Mapping[str, Any]) -> str: ...


class JudgeClient:
    def __init__(
        self,
        provider: JudgeProvider | Callable[[Mapping[str, Any]], str],
        rating_rule: RatingRule,
        *,
        checkpoint: Callable[[Mapping[str, Any]], None] | None = None,
        checkpoint_event: str = "judge",
    ) -> None:
        self._provider = provider
        self._rating_rule = rating_rule
        self._checkpoint = checkpoint
        self._checkpoint_event = checkpoint_event

    def judge(self, request: Mapping[str, Any]) -> JudgeResult:
        """Invoke an injected provider once and validate its untrusted output."""
        try:
            raw = _invoke(self._provider, request)
        except Exception as exc:
            self._save_checkpoint(request, None, f"{type(exc).__name__}: {exc}")
            raise
        self._save_checkpoint(request, raw, None)
        try:
            result = parse_judge_response(raw, self._rating_rule)
            catalog = request.get("evidence_catalog", [])
            if not isinstance(catalog, list):
                raise TypeError("judge request evidence_catalog must be an array")
            validate_claim_evidence(result, catalog)
        except Exception as exc:
            self._save_validation(request, "ERROR", f"{type(exc).__name__}: {exc}")
            raise
        self._save_validation(request, "PASS", None)
        return result

    def _save_checkpoint(
        self, request: Mapping[str, Any], raw_response: str | None, error: str | None
    ) -> None:
        if self._checkpoint is None:
            return
        self._checkpoint(
            {
                "event": self._checkpoint_event,
                "case_id": request.get("case_id"),
                "turn": request.get("turn"),
                "raw_response": raw_response,
                "provider_usage": dict(getattr(raw_response, "usage", {}) or {}),
                "error": error,
            }
        )

    def _save_validation(
        self, request: Mapping[str, Any], status: str, error: str | None
    ) -> None:
        if self._checkpoint is None:
            return
        self._checkpoint(
            {
                "event": f"{self._checkpoint_event}_validation",
                "case_id": request.get("case_id"),
                "turn": request.get("turn"),
                "status": status,
                "error": error,
            }
        )


def _invoke(provider: Any, request: Mapping[str, Any]) -> str:
    if callable(provider):
        return provider(request)
    for method_name in ("generate", "complete"):
        method = getattr(provider, method_name, None)
        if callable(method):
            return method(request)
    raise TypeError("judge provider must be callable or expose generate/complete")
