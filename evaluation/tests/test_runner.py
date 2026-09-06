from __future__ import annotations

from dataclasses import dataclass, field
import json
from typing import Any

from xiaoan_eval.checkpoint import JsonlCheckpoint
from xiaoan_eval.runner import EvaluationRunner
from xiaoan_eval.manifest import SuiteCaseBinding, SuiteManifest


@dataclass
class FakeTransport:
    conversations: list[str] = field(default_factory=list)
    messages: list[tuple[str, str]] = field(default_factory=list)

    def create_conversation(self) -> str:
        conversation_id = f"conversation-{len(self.conversations) + 1}"
        self.conversations.append(conversation_id)
        return conversation_id

    def send_turn(self, conversation_id: str, user: str) -> dict[str, Any]:
        self.messages.append((conversation_id, user))
        return {
            "response": f"reply to {user}",
            "trace": {
                "safety": {"level": "baseline"},
                "route": {"id": "baseline"},
                "ground": {"resolved_refs": [], "warnings": []},
                "guard": {"passed": True},
                "state": {"active_capsule": None},
                "timings": {"total_ms": 10},
                "tokens": {"input": 3, "output": 4},
            },
        }


def test_runner_keeps_turns_serial_and_cases_isolated() -> None:
    transport = FakeTransport()
    runner = EvaluationRunner(transport)
    cases = [
        {"id": "TC-01", "turns": [{"turn": 1, "user": "a"}, {"turn": 2, "user": "b"}]},
        {"id": "TC-02", "turns": [{"turn": 1, "user": "c"}]},
    ]

    results = runner.run_cases(cases)

    assert transport.messages == [
        ("conversation-1", "a"),
        ("conversation-1", "b"),
        ("conversation-2", "c"),
    ]
    assert [result.case_id for result in results] == ["TC-01", "TC-02"]


def test_runner_checkpoints_each_completed_turn(tmp_path) -> None:
    checkpoint_path = tmp_path / "evaluation-checkpoint.jsonl"

    class InspectingTransport(FakeTransport):
        def send_turn(self, conversation_id: str, user: str) -> dict[str, Any]:
            if user == "b":
                events = [
                    json.loads(line)
                    for line in checkpoint_path.read_text(encoding="utf-8").splitlines()
                ]
                assert [event["turn"] for event in events] == [1]
                assert events[0]["response"] == "reply to a"
            return super().send_turn(conversation_id, user)

    with JsonlCheckpoint(checkpoint_path, "run-1") as checkpoint:
        EvaluationRunner(InspectingTransport(), checkpoint=checkpoint).run_cases(
            [{"id": "TC-01", "turns": [{"turn": 1, "user": "a"}, {"turn": 2, "user": "b"}]}]
        )

    events = [
        json.loads(line)
        for line in checkpoint_path.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["event"] for event in events] == ["subject_turn", "subject_turn"]
    assert [event["turn"] for event in events] == [1, 2]


def test_runner_rejects_incomplete_structured_trace() -> None:
    class IncompleteTransport(FakeTransport):
        def send_turn(self, conversation_id: str, user: str) -> dict[str, Any]:
            return {"response": "unsafe to persist", "trace": {"route": {"id": "baseline"}}}

    runner = EvaluationRunner(IncompleteTransport())

    result = runner.run_cases(
        [{"id": "TC-01", "turns": [{"turn": 1, "user": "hello"}]}]
    )[0]

    assert result.status == "error"
    assert result.turns[0].response is None
    assert "missing trace fields" in result.turns[0].error


def test_runner_records_transport_failure_as_execution_error() -> None:
    class FailingTransport(FakeTransport):
        def send_turn(self, conversation_id: str, user: str):
            raise RuntimeError("provider unavailable")

    result = EvaluationRunner(FailingTransport()).run_cases(
        [{"id": "TC-01", "turns": [{"turn": 1, "user": "hello"}]}]
    )[0]

    assert result.status == "error"
    assert result.turns[0].error == "provider unavailable"


def test_suite_retries_append_and_selects_earliest_success(tmp_path) -> None:
    class FlakyTransport(FakeTransport):
        calls = 0

        def send_turn(self, conversation_id: str, user: str):
            self.calls += 1
            if self.calls == 1:
                raise RuntimeError("provider unavailable")
            return super().send_turn(conversation_id, user)

    suite = SuiteManifest(
        suite_id="canonical", suite_version="1", taxonomy_version="1",
        scoring_contract_version="response-effectiveness/v1",
        cases=(SuiteCaseBinding(
            case_id="TC-01", case_digest="abc", expected_turns=(1,),
            scenario_id="baseline", coverage_axes={}, comparability_group="v1",
            maturity="PROVISIONAL_DESCRIPTIVE",
        ),), retry_policy={"max_attempts": 2},
    )
    ledger = tmp_path / "attempts.jsonl"
    runner = EvaluationRunner(FlakyTransport())

    result = runner.run_suite(
        suite, [{"id": "TC-01", "turns": [{"turn": 1, "user": "hello"}]}],
        ledger_path=ledger,
    )

    assert result.validity == "VALID"
    assert [item.outcome for item in result.attempts] == ["PROVIDER_FAILURE", "ANSWERED"]
    assert result.selected_attempts == {"TC-01": 2}
    assert len(ledger.read_text(encoding="utf-8").splitlines()) == 2
