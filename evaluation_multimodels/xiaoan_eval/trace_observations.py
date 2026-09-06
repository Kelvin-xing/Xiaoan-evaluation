from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class TraceObservation:
    case_id: str
    turn: int
    route_id: str
    resolved_refs: frozenset[str]
    response_sha256: str | None


def iter_trace_observations(
    records: Sequence[Mapping[str, Any]],
) -> tuple[TraceObservation, ...]:
    observations = []
    for record in records:
        case_id = str(record.get("case_id", "unknown"))
        pipeline = record.get("pipeline")
        turns = pipeline.get("turn_traces", ()) if isinstance(pipeline, Mapping) else ()
        if not isinstance(turns, Sequence) or isinstance(turns, (str, bytes)):
            continue
        for item in turns:
            if not isinstance(item, Mapping):
                continue
            turn = item.get("turn")
            trace = item.get("trace")
            if not isinstance(turn, int) or not isinstance(trace, Mapping):
                continue
            observations.append(
                TraceObservation(
                    case_id=case_id,
                    turn=turn,
                    route_id=_route_id(trace),
                    resolved_refs=_resolved_refs(trace),
                    response_sha256=(
                        str(item["response_sha256"])
                        if item.get("response_sha256") is not None
                        else None
                    ),
                )
            )
    return tuple(observations)


def _route_id(trace: Mapping[str, Any]) -> str:
    route = trace.get("route")
    if not isinstance(route, Mapping):
        return "unknown"
    value = route.get("id", route.get("capsule_id"))
    return str(value) if value is not None else "unknown"


def _resolved_refs(trace: Mapping[str, Any]) -> frozenset[str]:
    ground = trace.get("ground")
    values = ground.get("resolved_ground", ()) if isinstance(ground, Mapping) else ()
    if not isinstance(values, Sequence) or isinstance(values, (str, bytes)):
        return frozenset()
    return frozenset(str(item) for item in values)
