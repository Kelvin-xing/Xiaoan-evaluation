import json
from concurrent.futures import ThreadPoolExecutor

import pytest

from xiaoan_eval.checkpoint import JsonlCheckpoint


def test_checkpoint_flushes_each_event_and_allows_same_run_append(tmp_path) -> None:
    path = tmp_path / "private" / "evaluation-checkpoint.jsonl"
    with JsonlCheckpoint(path, "run-1") as checkpoint:
        checkpoint({"event": "subject_turn", "turn": 1})
        assert json.loads(path.read_text(encoding="utf-8"))["turn"] == 1

    with JsonlCheckpoint(path, "run-1") as checkpoint:
        checkpoint({"event": "primary_judge", "turn": 1})

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["subject_turn", "primary_judge"]
    assert {event["run_fingerprint"] for event in events} == {"run-1"}
    assert path.parent.stat().st_mode & 0o777 == 0o700
    assert path.stat().st_mode & 0o777 == 0o600


def test_checkpoint_rejects_events_from_another_run(tmp_path) -> None:
    path = tmp_path / "evaluation-checkpoint.jsonl"
    with JsonlCheckpoint(path, "run-1") as checkpoint:
        checkpoint({"event": "subject_turn"})

    with pytest.raises(ValueError, match="different run manifest"):
        with JsonlCheckpoint(path, "run-2"):
            pass


def test_checkpoint_discards_only_an_incomplete_trailing_event(tmp_path) -> None:
    path = tmp_path / "evaluation-checkpoint.jsonl"
    path.write_bytes(
        b'{"event":"subject_turn","run_fingerprint":"run-1"}\n{"event":'
    )

    with JsonlCheckpoint(path, "run-1") as checkpoint:
        checkpoint({"event": "primary_judge"})

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["subject_turn", "primary_judge"]


def test_checkpoint_repairs_a_valid_final_event_without_newline(tmp_path) -> None:
    path = tmp_path / "evaluation-checkpoint.jsonl"
    path.write_text(
        '{"event":"subject_turn","run_fingerprint":"run-1"}', encoding="utf-8"
    )

    with JsonlCheckpoint(path, "run-1") as checkpoint:
        checkpoint({"event": "primary_judge"})

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert [event["event"] for event in events] == ["subject_turn", "primary_judge"]


def test_checkpoint_serializes_concurrent_writes_and_keeps_attempt_per_worker(tmp_path) -> None:
    path = tmp_path / "evaluation-checkpoint.jsonl"
    with JsonlCheckpoint(path, "run-1") as checkpoint:
        def write_case(case_number: int) -> None:
            checkpoint.set_attempt(case_number)
            for turn in range(20):
                checkpoint({"event": "subject_turn", "case_id": f"TC-{case_number}", "turn": turn})

        with ThreadPoolExecutor(max_workers=4) as executor:
            list(executor.map(write_case, range(1, 5)))

    events = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert len(events) == 80
    assert all(event["attempt"] == int(event["case_id"].split("-")[1]) for event in events)
