from __future__ import annotations

import json
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from http.cookiejar import CookieJar
from typing import Any, Protocol
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import HTTPCookieProcessor, Request, build_opener


class TransportError(RuntimeError):
    """The chatflow API could not provide a trustworthy evaluator response."""


@dataclass(frozen=True)
class RetryPolicy:
    retries: int = 2
    backoff_seconds: float = 0.25

    def __post_init__(self) -> None:
        if self.retries < 0:
            raise ValueError("retries must be non-negative")
        if self.backoff_seconds < 0:
            raise ValueError("backoff_seconds must be non-negative")


class _Response(Protocol):
    status: int

    def read(self) -> bytes: ...

    def readline(self) -> bytes: ...

    def __enter__(self) -> "_Response": ...

    def __exit__(self, *args: object) -> object: ...


class _Opener(Protocol):
    def open(self, request: Request, timeout: float) -> _Response: ...


class FastAPITransport:
    """Synchronous HTTP adapter for the XiaoAn FastAPI conversation API."""

    def __init__(
        self,
        base_url: str,
        timeout: float = 600.0,
        retry_policy: RetryPolicy | None = None,
        *,
        retries: int | None = None,
        backoff_seconds: float | None = None,
        opener: _Opener | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be positive")
        policy = retry_policy or RetryPolicy()
        if retries is not None or backoff_seconds is not None:
            policy = RetryPolicy(
                retries=policy.retries if retries is None else retries,
                backoff_seconds=(
                    policy.backoff_seconds
                    if backoff_seconds is None
                    else backoff_seconds
                ),
            )

        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._retries = policy.retries
        self._backoff_seconds = policy.backoff_seconds
        self._opener = opener or build_opener(HTTPCookieProcessor(CookieJar()))
        self._sleep = sleep

    def create_conversation(self) -> str:
        payload = self._request_json("POST", "/v1/conversations")
        conversation_id = payload.get("conversation_id")
        if not isinstance(conversation_id, str) or not conversation_id:
            raise TransportError("response schema missing conversation_id")
        return conversation_id

    def send_turn(self, conversation_id: str, user: str) -> Mapping[str, Any]:
        encoded_id = quote(conversation_id, safe="")
        answer, debug = self._request_stream(
            f"/v1/conversations/{encoded_id}/responses/stream",
            {"message": user, "debug": True},
        )
        trace = self._normalize_debug(debug)
        return {"response": answer, "trace": trace}

    def close(self) -> None:
        self._request_json(
            "DELETE",
            "/v1/conversations/current",
            allow_empty=True,
            allow_not_found=True,
        )

    def __enter__(self) -> "FastAPITransport":
        return self

    def __exit__(self, *_args: object) -> None:
        self.close()

    def _normalize_debug(self, debug: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
        aliases = {
            "safety": "safety",
            "route": "route",
            "ground": "ground",
            "guard": "output_guard",
            "state": "state",
            "timings": "timings",
        }
        trace: dict[str, Mapping[str, Any]] = {}
        for target, source in aliases.items():
            section = debug.get(source)
            if not isinstance(section, Mapping):
                raise TransportError(f"response debug payload missing {source}")
            trace[target] = dict(section)

        route = dict(trace["route"])
        if "id" not in route and isinstance(route.get("capsule_id"), str):
            route["id"] = route["capsule_id"]
        trace["route"] = route

        ground = dict(trace["ground"])
        if "resolved_refs" not in ground and isinstance(ground.get("resolved_ground"), list):
            ground["resolved_refs"] = list(ground["resolved_ground"])
        trace["ground"] = ground

        # Preserve XiaoAn's layered debug contract.  Older chatflow builds only
        # expose route/ground; derive a minimal capsule identity while retaining
        # richer source/wiki sections when newer builds provide them.
        capsule = debug.get("capsule")
        if isinstance(capsule, Mapping):
            trace["capsule"] = dict(capsule)
        else:
            trace["capsule"] = {
                "id": route.get("id", route.get("capsule_id", "")),
                "title": route.get("capsule_title", ""),
            }
        for section_name in ("source", "sources", "wiki", "llm_wiki"):
            section = debug.get(section_name)
            if isinstance(section, Mapping):
                target = "source" if section_name in {"source", "sources"} else "wiki"
                trace[target] = dict(section)

        timings = dict(trace["timings"])
        timing_aliases = {
            "ttft_ms": "response_ttft_ms",
            "generation_ms": "response_generation_ms",
        }
        for target, source in timing_aliases.items():
            if target not in timings and source in timings:
                timings[target] = timings[source]
        trace["timings"] = timings

        token_data = debug.get("tokens", debug.get("usage", {}))
        if not isinstance(token_data, Mapping):
            raise TransportError("response debug tokens must be an object")
        trace["tokens"] = dict(token_data)
        for optional in (
            "redaction",
            "router_context",
            "models",
            "telemetry",
            "capsule",
        ):
            value = debug.get(optional)
            if isinstance(value, Mapping):
                trace[optional] = dict(value)
        return trace

    def _request_json(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
        *,
        allow_empty: bool = False,
        allow_not_found: bool = False,
    ) -> dict[str, Any]:
        encoded = json.dumps(body).encode("utf-8") if body is not None else None
        request = Request(
            f"{self._base_url}{path}",
            data=encoded,
            method=method,
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

        for attempt in range(self._retries + 1):
            try:
                with self._opener.open(request, timeout=self._timeout) as response:
                    raw = response.read()
            except HTTPError as exc:
                if allow_not_found and exc.code == 404:
                    return {}
                if exc.code < 500 or attempt == self._retries:
                    raise TransportError(f"chatflow HTTP error {exc.code}") from exc
                self._backoff(attempt)
                continue
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == self._retries:
                    raise TransportError("chatflow network request failed") from exc
                self._backoff(attempt)
                continue

            if not raw and allow_empty:
                return {}
            try:
                payload = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise TransportError("chatflow response is not valid JSON") from exc
            if not isinstance(payload, dict):
                raise TransportError("chatflow response must be a JSON object")
            return payload

        raise AssertionError("retry loop exhausted")

    def _request_stream(
        self,
        path: str,
        body: Mapping[str, Any],
    ) -> tuple[str, Mapping[str, Any]]:
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = Request(
            f"{self._base_url}{path}",
            data=encoded,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
                "Cache-Control": "no-cache",
            },
        )

        for attempt in range(self._retries + 1):
            try:
                with self._opener.open(request, timeout=self._timeout) as response:
                    answer, debug = self._read_sse(response)
                return answer, debug
            except HTTPError as exc:
                if exc.code < 500 or attempt == self._retries:
                    raise TransportError(f"chatflow HTTP error {exc.code}") from exc
                self._backoff(attempt)
            except (URLError, TimeoutError, OSError) as exc:
                if attempt == self._retries:
                    raise TransportError("chatflow network request failed") from exc
                self._backoff(attempt)

        raise AssertionError("retry loop exhausted")

    @staticmethod
    def _read_sse(response: _Response) -> tuple[str, Mapping[str, Any]]:
        event_name = ""
        data_lines: list[str] = []
        answer_parts: list[str] = []
        debug: Mapping[str, Any] | None = None
        completed = False

        def dispatch() -> None:
            nonlocal event_name, data_lines, debug, completed
            if not event_name and not data_lines:
                return
            try:
                payload = json.loads("\n".join(data_lines))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise TransportError("chatflow stream event is not valid JSON") from exc
            if not isinstance(payload, Mapping):
                raise TransportError("chatflow stream event must be a JSON object")
            if event_name == "delta":
                delta = payload.get("delta")
                if not isinstance(delta, str):
                    raise TransportError("chatflow stream delta is missing")
                answer_parts.append(delta)
            elif event_name == "debug":
                candidate = payload.get("debug")
                if not isinstance(candidate, Mapping):
                    raise TransportError("chatflow stream debug payload is missing")
                debug = candidate
            elif event_name == "error":
                message = payload.get("message") or payload.get("code") or "unknown"
                stage = payload.get("stage") or "unknown"
                error_type = payload.get("error_type") or "unknown"
                raise TransportError(
                    f"chatflow stream error: {message} "
                    f"(stage={stage}, error_type={error_type})"
                )
            elif event_name == "completed":
                completed = True
            event_name = ""
            data_lines = []

        while True:
            raw_line = response.readline()
            if not raw_line:
                break
            line = raw_line.decode("utf-8").rstrip("\r\n")
            if not line:
                dispatch()
            elif line.startswith(":") or line.startswith("id:"):
                continue
            elif line.startswith("event:"):
                event_name = line[6:].strip()
            elif line.startswith("data:"):
                data_lines.append(line[5:].lstrip())

        dispatch()
        if not completed:
            raise TransportError("chatflow stream ended without completion event")
        if debug is None:
            raise TransportError("chatflow stream debug payload is missing")
        return "".join(answer_parts), debug

    def _backoff(self, attempt: int) -> None:
        self._sleep(self._backoff_seconds * (2**attempt))
