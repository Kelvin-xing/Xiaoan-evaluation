from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Callable, Iterable, Mapping

from .runner import CaseRunResult


class UnsafeReportData(ValueError):
    pass


@dataclass(frozen=True)
class RedactionVerifiedRecord:
    payload: Mapping[str, Any]


def verify_for_report(
    result: CaseRunResult, contains_pii: Callable[[str], bool]
) -> RedactionVerifiedRecord:
    payload = asdict(result)
    for text in _strings(payload):
        if contains_pii(text):
            raise UnsafeReportData("report record failed PII validation")
    return RedactionVerifiedRecord(payload)


def write_jsonl(
    destination: str | Path, records: Iterable[RedactionVerifiedRecord]
) -> None:
    path = Path(destination)
    serialized: list[str] = []
    for record in records:
        if not isinstance(record, RedactionVerifiedRecord):
            raise UnsafeReportData(
                "write_jsonl accepts only records that passed PII validation"
            )
        serialized.append(
            json.dumps(
                record.payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        )
    path.write_text("\n".join(serialized) + ("\n" if serialized else ""), encoding="utf-8")


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    if isinstance(value, Mapping):
        for child in value.values():
            yield from _strings(child)
    elif isinstance(value, (list, tuple)):
        for child in value:
            yield from _strings(child)
