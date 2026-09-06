from __future__ import annotations

import io
import json
from email.message import Message
from urllib.error import HTTPError, URLError

import pytest

from xiaoan_eval.transport import (
    FastAPITransport,
    RetryPolicy,
    TransportError,
)


class FakeResponse:
    def __init__(
        self,
        status: int,
        payload: dict | None = None,
        raw_body: bytes | None = None,
    ) -> None:
        self.status = status
        self._body = (
            raw_body
            if raw_body is not None
            else json.dumps(payload).encode()
            if payload is not None
            else b""
        )
        self._lines = iter(self._body.splitlines(keepends=True))

    def read(self) -> bytes:
        return self._body

    def readline(self) -> bytes:
        return next(self._lines, b"")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *_args: object) -> None:
        return None


class FakeOpener:
    def __init__(self, outcomes: list[object]) -> None:
        self.outcomes = outcomes
        self.requests = []

    def open(self, request, timeout: float):
        self.requests.append((request, timeout))
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def http_error(status: int) -> HTTPError:
    return HTTPError(
        "http://test.invalid",
        status,
        "failure",
        Message(),
        io.BytesIO(b'{"detail":"failure"}'),
    )


def debug_payload() -> dict:
    return {
        "safety": {"level": "normal", "reason": "none"},
        "route": {"capsule_id": "baseline", "confidence": 0.9},
        "capsule": {
            "available_refs": ["capsule:n3:act:0"],
            "content_unit_count": 1,
        },
        "ground": {"loaded": True, "resolved_ground": ["wiki:a"]},
        "output_guard": {"passed": True, "warnings": []},
        "state": {"active_capsule_id": "baseline", "ttl_turns": 2},
        "timings": {
            "response_ttft_ms": 2.0,
            "response_generation_ms": 8.0,
            "total_ms": 12.5,
        },
    }


def stream_body(*, answer: str = "你好", debug: dict | None = None) -> bytes:
    events = [
        ("start", {"response_id": "r1"}),
        ("delta", {"delta": answer}),
        ("debug", {"debug": debug or debug_payload()}),
        ("completed", {"safety_level": "normal"}),
    ]
    return "".join(
        f"id: r1:{index}\nevent: {event}\ndata: {json.dumps(data)}\n\n"
        for index, (event, data) in enumerate(events, 1)
    ).encode()


def test_create_and_send_turn_use_json_api_and_normalize_debug() -> None:
    opener = FakeOpener(
        [
            FakeResponse(201, {"conversation_id": "conv/1"}),
            FakeResponse(200, raw_body=stream_body()),
        ]
    )
    transport = FastAPITransport("http://test.invalid/", opener=opener)

    conversation_id = transport.create_conversation()
    result = transport.send_turn(conversation_id, "求助")

    assert conversation_id == "conv/1"
    assert result == {
        "response": "你好",
        "trace": {
            "safety": {"level": "normal", "reason": "none"},
            "route": {"capsule_id": "baseline", "confidence": 0.9, "id": "baseline"},
            "capsule": {
                "available_refs": ["capsule:n3:act:0"],
                "content_unit_count": 1,
            },
            "ground": {
                "loaded": True,
                "resolved_ground": ["wiki:a"],
                "resolved_refs": ["wiki:a"],
            },
            "guard": {"passed": True, "warnings": []},
            "state": {"active_capsule_id": "baseline", "ttl_turns": 2},
            "timings": {
                "response_ttft_ms": 2.0,
                "response_generation_ms": 8.0,
                "total_ms": 12.5,
                "ttft_ms": 2.0,
                "generation_ms": 8.0,
            },
            "tokens": {},
        },
    }
    create_request, create_timeout = opener.requests[0]
    turn_request, turn_timeout = opener.requests[1]
    assert create_request.full_url == "http://test.invalid/v1/conversations"
    assert create_request.method == "POST"
    assert create_timeout == 600.0
    assert turn_request.full_url.endswith("/v1/conversations/conv%2F1/responses/stream")
    assert json.loads(turn_request.data) == {"message": "求助", "debug": True}
    assert turn_request.get_header("Content-type") == "application/json"
    assert turn_request.get_header("Accept") == "text/event-stream"
    assert turn_timeout == 600.0


def test_stream_errors_are_reported_and_incomplete_stream_fails_closed() -> None:
    error_body = (
        b"event: error\ndata: {\"code\":\"generation_failed\",\"message\":\"provider failed\"}\n\n"
    )
    transport = FastAPITransport(
        "http://test.invalid",
        opener=FakeOpener([FakeResponse(200, raw_body=error_body)]),
    )
    with pytest.raises(TransportError, match="provider failed"):
        transport.send_turn("conv", "message")

    incomplete_body = b"event: delta\ndata: {\"delta\":\"partial\"}\n\n"
    transport = FastAPITransport(
        "http://test.invalid",
        opener=FakeOpener([FakeResponse(200, raw_body=incomplete_body)]),
    )
    with pytest.raises(TransportError, match="without completion"):
        transport.send_turn("conv", "message")


@pytest.mark.parametrize("stream", [
    b"event: completed\ndata: {\"safety_level\":\"normal\"}\n\n",
    b"event: debug\ndata: {\"debug\":{\"route\":{}}}\n\nevent: completed\ndata: {}\n\n",
])
def test_send_turn_fails_closed_when_debug_is_missing_or_incomplete(stream: bytes) -> None:
    transport = FastAPITransport(
        "http://test.invalid",
        opener=FakeOpener([FakeResponse(200, raw_body=stream)]),
    )

    with pytest.raises(TransportError, match="debug"):
        transport.send_turn("conv", "message")


def test_transient_network_and_5xx_failures_are_retried_with_bound() -> None:
    opener = FakeOpener(
        [
            URLError("temporary"),
            http_error(503),
            FakeResponse(201, {"conversation_id": "conv"}),
        ]
    )
    delays: list[float] = []
    transport = FastAPITransport(
        "http://test.invalid",
        retry_policy=RetryPolicy(retries=2, backoff_seconds=0.25),
        opener=opener,
        sleep=delays.append,
    )

    assert transport.create_conversation() == "conv"
    assert len(opener.requests) == 3
    assert delays == [0.25, 0.5]


@pytest.mark.parametrize("failure", [http_error(400), http_error(403), http_error(422)])
def test_client_errors_are_never_retried(failure: HTTPError) -> None:
    opener = FakeOpener([failure, FakeResponse(201, {"conversation_id": "wrong"})])
    transport = FastAPITransport("http://test.invalid", retries=3, opener=opener)

    with pytest.raises(TransportError, match=str(failure.code)):
        transport.create_conversation()

    assert len(opener.requests) == 1


def test_close_is_idempotent_when_no_current_conversation_exists() -> None:
    opener = FakeOpener([http_error(404)])
    transport = FastAPITransport("http://test.invalid", opener=opener)

    transport.close()

    assert len(opener.requests) == 1
    assert opener.requests[0][0].method == "DELETE"


def test_schema_errors_are_never_retried() -> None:
    opener = FakeOpener(
        [
            FakeResponse(201, {"expires_in_seconds": 10}),
            FakeResponse(201, {"conversation_id": "wrong"}),
        ]
    )
    transport = FastAPITransport("http://test.invalid", retries=3, opener=opener)

    with pytest.raises(TransportError, match="conversation_id"):
        transport.create_conversation()

    assert len(opener.requests) == 1


def test_close_deletes_current_conversation() -> None:
    opener = FakeOpener([FakeResponse(204)])
    transport = FastAPITransport("http://test.invalid", opener=opener)

    transport.close()

    request, _ = opener.requests[0]
    assert request.method == "DELETE"
    assert request.full_url == "http://test.invalid/v1/conversations/current"
