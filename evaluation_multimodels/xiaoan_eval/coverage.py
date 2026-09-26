"""Report authored versus reviewed metric coverage without inventing oracles."""
from __future__ import annotations

from typing import Any, Mapping, Sequence
from .cases import TestCase
from .reference_oracle import field_is_reviewed

MEMORY_TYPES = ("remember", "retrieve", "use", "not_use", "update", "isolation", "stale", "unsafe")


def case_coverage(case: TestCase) -> dict[str, Any]:
    counts = {name: 0 for name in ("route", "safety", "response", "claims", "tools", "goal")}
    for turn in case.turns:
        expected = turn.expected
        if expected is None:
            continue
        counts["route"] += bool(expected.route_ids)
        counts["safety"] += bool(expected.safety_levels)
        response = expected.response_oracle
        counts["response"] += response is not None
        if response is not None:
            counts["claims"] += bool(response.required_claims or response.forbidden_claims)
            counts["tools"] += bool(response.expected_tools)
            counts["goal"] += response.goal_completed is not None
    counts.update({f"memory:{kind}": sum(item.check_type == kind for item in case.memory_checkpoints) for kind in MEMORY_TYPES})
    reviewed = dict(counts) if case.oracle_gate_eligible else {name: 0 for name in counts}
    if case.oracle_gate_eligible:
        for name, field in (("route", "route_ids"), ("safety", "safety_levels")):
            reviewed[name] = sum(bool(getattr(t.expected, field)) and field_is_reviewed(t.expected, field)
                                 for t in case.turns if t.expected is not None)
    return {"case_id": case.id, "expected_turns": len(case.turns), "oracle_approved": case.oracle_gate_eligible,
            "maturity": case.maturity, "authored": counts,
            "reviewed": reviewed}


def coverage_rows(coverage: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    unique = {str(item["case_id"]): item for item in coverage if "case_id" in item}
    names = sorted({name for item in unique.values() for name in item.get("authored", {})})
    output = []
    for name in names:
        authored = sum(item.get("authored", {}).get(name, 0) for item in unique.values())
        reviewed = sum(item.get("reviewed", {}).get(name, 0) for item in unique.values())
        output.append({"section": "Coverage", "metric": f"Oracle {name}", "value": reviewed,
            "status": "AVAILABLE" if reviewed else "UNAVAILABLE",
            "interpretation": f"Authored={authored}; reviewed={reviewed}; cases={len(unique)}. Zero reviewed coverage is not evaluated capability."})
    return output
