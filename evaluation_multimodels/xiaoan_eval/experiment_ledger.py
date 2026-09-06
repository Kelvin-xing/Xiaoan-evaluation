"""Durable append-only lifecycle ledger for paired experiments."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Mapping


STATES = frozenset(
    {"PREPARED", "RUNNING_CONTROL", "RUNNING_CANDIDATE", "PARTIAL", "COMPLETE", "FAILED", "ABANDONED", "CLEANED"}
)
TRANSITIONS: Mapping[str | None, frozenset[str]] = {
    None: frozenset({"PREPARED"}),
    "PREPARED": frozenset({"RUNNING_CONTROL", "RUNNING_CANDIDATE", "FAILED", "ABANDONED"}),
    "RUNNING_CONTROL": frozenset({"PARTIAL", "FAILED"}),
    "RUNNING_CANDIDATE": frozenset({"PARTIAL", "FAILED"}),
    "PARTIAL": frozenset({"RUNNING_CONTROL", "RUNNING_CANDIDATE", "COMPLETE", "ABANDONED", "FAILED"}),
    "COMPLETE": frozenset({"CLEANED"}),
    "FAILED": frozenset({"CLEANED"}),
    "ABANDONED": frozenset({"CLEANED"}),
    "CLEANED": frozenset(),
}


@dataclass(frozen=True)
class LedgerEvent:
    sequence: int
    experiment_id: str
    state: str
    experiment_digest: str
    occurred_at: str
    detail: Mapping[str, object]


class ExperimentLedger:
    def __init__(self, path: Path, experiment_id: str, experiment_digest: str) -> None:
        self.path = path
        self.experiment_id = experiment_id
        self.experiment_digest = experiment_digest

    def read(self) -> tuple[LedgerEvent, ...]:
        if not self.path.exists():
            return ()
        events = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            event = LedgerEvent(**raw)
            if event.experiment_id != self.experiment_id or event.experiment_digest != self.experiment_digest:
                raise ValueError("experiment ledger identity or digest conflict")
            events.append(event)
        if [event.sequence for event in events] != list(range(1, len(events) + 1)):
            raise ValueError("experiment ledger sequence is not append-only")
        previous = None
        for event in events:
            if event.state not in TRANSITIONS.get(previous, frozenset()):
                raise ValueError(f"invalid persisted experiment transition: {previous} -> {event.state}")
            previous = event.state
        return tuple(events)

    def append(self, state: str, detail: Mapping[str, object] | None = None) -> LedgerEvent:
        if state not in STATES:
            raise ValueError("unsupported experiment state")
        events = self.read()
        current = events[-1].state if events else None
        if state not in TRANSITIONS[current]:
            raise ValueError(f"invalid experiment transition: {current} -> {state}")
        event = LedgerEvent(
            sequence=len(events) + 1,
            experiment_id=self.experiment_id,
            state=state,
            experiment_digest=self.experiment_digest,
            occurred_at=datetime.now(timezone.utc).isoformat(),
            detail=dict(detail or {}),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True))
            handle.write("\n")
        return event
