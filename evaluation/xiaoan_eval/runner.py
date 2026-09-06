from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Callable, Mapping, Protocol, Sequence

from .manifest import SuiteManifest, canonical_digest


REQUIRED_TRACE_FIELDS = frozenset(
    {"safety", "route", "ground", "guard", "state", "timings", "tokens"}
)


class EvaluationTransport(Protocol):
    """Boundary implemented by an HTTP adapter or an offline test double."""

    def create_conversation(self) -> str: ...

    def send_turn(self, conversation_id: str, user: str) -> Mapping[str, Any]: ...


@dataclass(frozen=True)
class TurnRunResult:
    turn: int
    response: str | None
    trace: Mapping[str, Any]
    error: str | None = None


@dataclass(frozen=True)
class CaseRunResult:
    case_id: str
    status: str
    conversation_id: str
    turns: list[TurnRunResult] = field(default_factory=list)


@dataclass(frozen=True)
class AttemptRecord:
    suite_fingerprint: str
    case_id: str
    attempt: int
    outcome: str
    conversation_id: str
    expected_turns: tuple[int, ...]
    completed_turns: tuple[int, ...]
    logical_lineage_valid: bool
    provider_lineage_valid: bool | None
    result_digest: str
    error: str | None = None

    @property
    def successful(self) -> bool:
        return (
            self.outcome == "ANSWERED"
            and self.completed_turns == self.expected_turns
            and self.logical_lineage_valid
            and self.provider_lineage_valid is not False
        )


@dataclass(frozen=True)
class SuiteRunResult:
    suite_fingerprint: str
    validity: str
    attempts: tuple[AttemptRecord, ...]
    selected_attempts: Mapping[str, int]
    completed_cases: int
    expected_cases: int
    exclusion_reasons: Mapping[str, str]


class EvaluationRunner:
    def __init__(
        self,
        transport: EvaluationTransport,
        *,
        checkpoint: Callable[[Mapping[str, Any]], None] | None = None,
    ) -> None:
        self._transport = transport
        self._checkpoint = checkpoint

    def run_cases(self, cases: Sequence[Mapping[str, Any]]) -> list[CaseRunResult]:
        return [self._run_case(case) for case in cases]

    def run_suite(
        self,
        manifest: SuiteManifest,
        cases: Sequence[Mapping[str, Any]],
        *,
        ledger_path: Path | None = None,
    ) -> SuiteRunResult:
        """Run a manifest-bound suite with retained, deterministic attempts.

        Completed attempts from a matching append-only ledger may be reused.
        The first successful eligible numbered attempt is always selected.
        """
        case_by_id = {str(case["id"]): case for case in cases}
        if tuple(case_by_id) != tuple(binding.case_id for binding in manifest.cases):
            raise ValueError("cases must match suite manifest order exactly")
        attempts = self._read_attempts(ledger_path, manifest.fingerprint)
        maximum = int(manifest.retry_policy.get("max_attempts", 1))
        for binding in manifest.cases:
            existing = [item for item in attempts if item.case_id == binding.case_id]
            if any(item.successful for item in existing):
                continue
            for attempt_number in range(len(existing) + 1, maximum + 1):
                record = self._attempt_suite_case(
                    manifest.fingerprint,
                    binding.expected_turns,
                    case_by_id[binding.case_id],
                    attempt_number,
                )
                attempts.append(record)
                self._append_attempt(ledger_path, record)
                if record.successful:
                    break
        selected: dict[str, int] = {}
        exclusions: dict[str, str] = {}
        for binding in manifest.cases:
            eligible = sorted(
                (
                    item
                    for item in attempts
                    if item.case_id == binding.case_id and item.successful
                ),
                key=lambda item: item.attempt,
            )
            if eligible:
                selected[binding.case_id] = eligible[0].attempt
            else:
                exclusions[binding.case_id] = "NO_SUCCESSFUL_ELIGIBLE_ATTEMPT"
        completed = len(selected)
        if completed == len(manifest.cases):
            validity = "VALID"
        elif completed:
            validity = "PARTIAL"
        else:
            validity = "INVALID"
        return SuiteRunResult(
            suite_fingerprint=manifest.fingerprint,
            validity=validity,
            attempts=tuple(attempts),
            selected_attempts=selected,
            completed_cases=completed,
            expected_cases=len(manifest.cases),
            exclusion_reasons=exclusions,
        )

    def _attempt_suite_case(
        self,
        suite_fingerprint: str,
        expected_turns: tuple[int, ...],
        case: Mapping[str, Any],
        attempt: int,
    ) -> AttemptRecord:
        result = self._run_case(case)
        completed = tuple(
            turn.turn for turn in result.turns if turn.response is not None and turn.error is None
        )
        if result.status == "pass" and completed == expected_turns:
            outcome = "ANSWERED"
        elif any(turn.error and "provider" in turn.error.lower() for turn in result.turns):
            outcome = "PROVIDER_FAILURE"
        else:
            outcome = "RUNTIME_FAILURE"
        provider_lineage = all(
            turn.trace.get("effective_context_snapshot", {})
            .get("lineage", {})
            .get("provider_lineage_valid", True)
            is not False
            for turn in result.turns
        )
        payload = {
            "case_id": result.case_id,
            "attempt": attempt,
            "outcome": outcome,
            "conversation_id": result.conversation_id,
            "completed_turns": completed,
            "errors": [turn.error for turn in result.turns if turn.error],
        }
        return AttemptRecord(
            suite_fingerprint=suite_fingerprint,
            case_id=result.case_id,
            attempt=attempt,
            outcome=outcome,
            conversation_id=result.conversation_id,
            expected_turns=expected_turns,
            completed_turns=completed,
            logical_lineage_valid=bool(result.conversation_id),
            provider_lineage_valid=provider_lineage,
            result_digest=canonical_digest(payload),
            error=next((turn.error for turn in result.turns if turn.error), None),
        )

    @staticmethod
    def _read_attempts(path: Path | None, fingerprint: str) -> list[AttemptRecord]:
        if path is None or not path.exists():
            return []
        records: list[AttemptRecord] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            raw = json.loads(line)
            if raw.get("suite_fingerprint") != fingerprint:
                raise ValueError("ledger belongs to a different suite manifest")
            raw["expected_turns"] = tuple(raw["expected_turns"])
            raw["completed_turns"] = tuple(raw["completed_turns"])
            records.append(AttemptRecord(**raw))
        identities = [(item.case_id, item.attempt) for item in records]
        if len(identities) != len(set(identities)):
            raise ValueError("ledger contains duplicate case attempts")
        return records

    @staticmethod
    def _append_attempt(path: Path | None, record: AttemptRecord) -> None:
        if path is None:
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record.__dict__, ensure_ascii=False, sort_keys=True))
            handle.write("\n")

    def _run_case(self, case: Mapping[str, Any]) -> CaseRunResult:
        try:
            conversation_id = self._transport.create_conversation()
        except RuntimeError as exc:
            return CaseRunResult(
                case_id=str(case["id"]),
                status="error",
                conversation_id="",
                turns=[TurnRunResult(turn=0, response=None, trace={}, error=str(exc))],
            )
        results: list[TurnRunResult] = []
        status = "pass"

        for turn in case["turns"]:
            try:
                payload = self._transport.send_turn(conversation_id, str(turn["user"]))
            except RuntimeError as exc:
                status = "error"
                result = TurnRunResult(
                    turn=int(turn["turn"]), response=None, trace={}, error=str(exc)
                )
                results.append(result)
                self._checkpoint_turn(str(case["id"]), conversation_id, result)
                break
            trace = payload.get("trace")
            missing = REQUIRED_TRACE_FIELDS - set(trace or {})
            if missing:
                status = "error"
                result = TurnRunResult(
                    turn=int(turn["turn"]),
                    response=None,
                    trace={},
                    error=f"missing trace fields: {', '.join(sorted(missing))}",
                )
                results.append(result)
                self._checkpoint_turn(str(case["id"]), conversation_id, result)
                break

            result = TurnRunResult(
                turn=int(turn["turn"]),
                response=str(payload["response"]),
                trace=trace,
            )
            results.append(result)
            self._checkpoint_turn(str(case["id"]), conversation_id, result)

        return CaseRunResult(
            case_id=str(case["id"]),
            status=status,
            conversation_id=conversation_id,
            turns=results,
        )

    def _checkpoint_turn(
        self, case_id: str, conversation_id: str, result: TurnRunResult
    ) -> None:
        if self._checkpoint is None:
            return
        self._checkpoint(
            {
                "event": "subject_turn",
                "case_id": case_id,
                "turn": result.turn,
                "conversation_id": conversation_id,
                "response": result.response,
                "trace": result.trace,
                "error": result.error,
            }
        )
