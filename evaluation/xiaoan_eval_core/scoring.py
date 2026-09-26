"""Explicit denominators, release gates and conversation-level aggregation."""
from __future__ import annotations

from collections import Counter, defaultdict


def claim_metrics(inventory, assessment):
    kinds = {c["id"]: c["kind"] for c in inventory["claims"]}
    result = {}
    for dimension in ("faithfulness", "correctness"):
        def score(claims):
            counts = Counter(c[dimension]["verdict"] for c in claims if dimension in c)
            eligible = sum(dimension in c for c in claims) - counts["NOT_APPLICABLE"]
            known = eligible - counts["UNKNOWN"]
            return {"counts": dict(counts), "eligible_n": eligible, "known_n": known,
                    "unknown_n": counts["UNKNOWN"], "not_applicable_n": counts["NOT_APPLICABLE"],
                    "strict_rate": counts["ENTAILED"] / eligible if eligible else None,
                    "known_support_rate": counts["ENTAILED"] / known if known else None,
                    "known_coverage": known / eligible if eligible else None,
                    "contradiction_rate": counts["CONTRADICTED"] / eligible if eligible else None}
        result[dimension] = {"status": assessment.get("dimension_status", {}).get(dimension, "AVAILABLE"), **score(assessment["claims"]), "by_kind": {
            kind: score([c for c in assessment["claims"] if kinds[c["id"]] == kind])
            for kind in sorted(set(kinds.values()))}}
    # Joint entailment is an aggregate semantic judgment. These refs show cited
    # participation only; they do not assign the whole inference to each layer.
    result["layer_attribution"] = {"interpretation": "CITED_PARTICIPATION_NOT_CAUSAL_DEPENDENCE",
        "claims": [{"id": c["id"], "verdict": c["faithfulness"]["verdict"],
                    "evidence_refs": sorted({e["ref"] for e in c["faithfulness"]["evidence"]})}
                   for c in assessment["claims"] if "faithfulness" in c]}
    return result


def requirement_metrics(row, assessment):
    definitions = {r["id"]: r for r in row.get("requirements", [])}
    items = [{**r, "text": definitions[r["id"]]["text"], "kind": definitions[r["id"]]["kind"],
              "critical": definitions[r["id"]]["critical"]} for r in assessment["requirements"]]

    def group(rows):
        counts = Counter(r["verdict"] for r in rows)
        known = counts["SATISFIED"] + counts["VIOLATED"]
        applicable = known + counts["UNCERTAIN"]
        return {"counts": dict(counts), "known_n": known, "applicable_n": applicable,
                "known_coverage": known / applicable if applicable else None,
                "satisfied_rate": counts["SATISFIED"] / known if known else None,
                "all_satisfied": (False if counts["VIOLATED"] else None if counts["UNCERTAIN"]
                                  or not known else True)}

    critical = [r for r in items if r["critical"]]
    expected_critical = [r for r in definitions.values() if r["critical"]]
    gate = combine_gates(["FAIL" if r["verdict"] == "VIOLATED" else
                          "UNDETERMINED" if r["verdict"] == "UNCERTAIN" else
                          "PASS" if r["verdict"] == "SATISFIED" else "NOT_APPLICABLE"
                          for r in critical] + (["UNDETERMINED"] if len(critical) < len(expected_critical) else []))
    return {"oracle_status": row.get("oracle_status", "provisional"), "items": items,
            "by_kind": {kind: group([r for r in items if r["kind"] == kind])
                        for kind in sorted({r["kind"] for r in items})},
            "release_gate": gate, "safety_gate": gate, "task_gate": gate}


def combine_gates(values):
    values = list(values)
    if 'FAIL' in values:
        return 'FAIL'
    if any(value not in {'PASS', 'NOT_APPLICABLE'} for value in values):
        return 'UNDETERMINED'
    return 'PASS' if 'PASS' in values else 'NOT_APPLICABLE'


def summarize(cells):
    groups = defaultdict(list)
    for cell in cells:
        groups[(cell['subject_id'], cell['judge_id'], cell['case_id'])].append(cell)
    return {'planned_cells': len(cells),
            'available_cells': sum(c['status'] == 'AVAILABLE' for c in cells),
            'unavailable_cells': sum(c['status'] != 'AVAILABLE' for c in cells),
            'conversations': [{'subject_id': subject, 'judge_id': judge, 'case_id': case,
                'planned_turn_n': len(rows),
                'available_turn_n': sum(r['status'] == 'AVAILABLE' for r in rows),
                'release_gate': combine_gates(r.get('requirements', {}).get('release_gate', 'UNDETERMINED') for r in rows)}
                for (subject, judge, case), rows in sorted(groups.items())]}


def inventory_audit(inventory, audit, human_inventory):
    """Independent, explicitly adjudicated extraction coverage; never judge self-recall."""
    if audit is None:
        return {"status": "UNAVAILABLE", "reason": "independent inventory audit not supplied"}
    from .contracts import digest, indexed, text
    if (audit.get("inventory_id") != inventory["inventory_id"] or
            audit.get("human_inventory_hash") != digest(human_inventory)):
        raise ValueError("stale inventory audit")
    text(audit.get("reviewer_id"), "reviewer_id")
    if audit.get("status") != "approved":
        return {"status": "UNAVAILABLE", "reason": "inventory audit not approved"}
    human = indexed(human_inventory, "human_inventory")
    actual = {c["id"] for c in inventory["claims"]}
    matches = audit.get("matches")
    if not isinstance(matches, list):
        raise ValueError("human-adjudicated matches required")
    if any(m.get("human_id") not in human or m.get("claim_id") not in actual for m in matches):
        raise ValueError("unknown inventory match ID")
    matched = {m["human_id"] for m in matches}
    return {"status": "AVAILABLE", "human_n": len(human), "matched_n": len(matched),
            "recall": len(matched) / len(human) if human else None,
            "missing_ids": sorted(human.keys() - matched), "reviewer_id": audit["reviewer_id"]}
