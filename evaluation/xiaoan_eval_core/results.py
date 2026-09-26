"""Complete frozen evaluation results, validated joins and shared aggregates."""
from collections.abc import Mapping, Sequence
from statistics import fmean


def _rows(stage, *keys):
    if isinstance(stage, Sequence) and not isinstance(stage, (str, bytes)):
        return [x for x in stage if isinstance(x, Mapping)]
    if isinstance(stage, Mapping):
        for key in keys:
            if isinstance(stage.get(key), list):
                return stage[key]
    return []


# Complete canonical contract. Compact legacy helpers above are not its inputs.
def complete_digest(value):
    import hashlib
    import json
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def seal_complete_results(result):
    result.pop("core_digest", None)
    result.pop("result_generation", None)
    result["core_digest"] = complete_digest(result)
    result["result_generation"] = result["core_digest"]
    return result


def _stage_cells(stage):
    return _rows(stage, "cells", "results", "rows")


def build_complete_results(spec, rows, faithfulness, rubric, relevancy, checks, receipts):
    """Serialize complete evidence, with projections strictly downstream."""
    from copy import deepcopy
    inventories = deepcopy((faithfulness or {}).get("inventories", []))
    by_inventory = {i["answer_id"]: i["inventory_id"] for i in inventories}
    envelopes = []
    for row in rows:
        aid = row["answer_id"]
        envelopes.append({"answer_id": aid, "inventory_id": by_inventory.get(aid),
                          "rubric": [deepcopy(c) for c in _stage_cells(rubric) if c.get("answer_id") == aid],
                          "assessments": [deepcopy(c) for c in _stage_cells(faithfulness) if c.get("answer_id") == aid],
                          "checks": [deepcopy(c) for c in _stage_cells(checks) if c.get("answer_id") == aid],
                          "relevancy": next((deepcopy(c) for c in _stage_cells(relevancy) if c.get("answer_id") == aid), {}),
                          "human_review": [], "stage_refs": [s.get("stage_id") for s in receipts if s.get("answer_id") == aid]})
    result = {"schema_version": "xiaoan-results/v2", "contract": "frozen-answer-evaluation/v1",
              "run_ref": spec.get("run_ref"), "manifest": deepcopy(spec.get("manifest", {})),
              "evaluation_config": deepcopy(spec.get("evaluation_config", spec.get("evaluator_config", {}))),
              "plan": deepcopy({**{k: v for k, v in spec.items() if k not in {"rows", "manifest", "plan", "artifacts", "provenance"}}, **spec.get("plan", {})}),
              "answers": deepcopy(rows), "inventories": inventories, "envelopes": envelopes,
              "stages": deepcopy(receipts), "artifacts": deepcopy(spec.get("artifacts", [])),
              "provenance": deepcopy(spec.get("provenance", []))}
    if isinstance(result["artifacts"], dict):
        result["artifacts"] = [{"path": path, **(value if isinstance(value, dict) else {"sha256": value})} for path, value in result["artifacts"].items()]
    if isinstance(result["provenance"], dict):
        result["provenance"] = [result["provenance"]]
    result["aggregates"] = aggregate_complete_results(result)
    from .costs import build_answer_costs
    result['aggregates']['answer_costs']=build_answer_costs(rows)
    seal_complete_results(result)
    validate_complete_results(result)
    return result


def _gate(values):
    if "FAIL" in values:
        return "FAIL"
    if not values or any(v not in {"PASS", "NOT_APPLICABLE"} for v in values):
        return "UNDETERMINED"
    return "PASS" if "PASS" in values else "NOT_APPLICABLE"


def aggregate_complete_results(result):
    """Case-macro aggregates; each Judge, metric and scope owns its denominator."""
    from collections import Counter, defaultdict
    answers = result["answers"]
    envs = {e["answer_id"]: e for e in result["envelopes"]}
    inventories = {i["inventory_id"]: i for i in result["inventories"]}
    judges = {str(j.get("id", j.get("judge_id"))) for j in result["plan"].get("judges", [])}
    for e in envs.values():
        judges.update(c["judge_id"] for branch in ("rubric", "assessments") for c in e[branch])
    cases = defaultdict(list)
    for a in answers:
        cases[(a["subject_id"], a["case_id"])].append(a)
    case_metrics = []
    for (subject, case), turns in sorted(cases.items()):
        for judge in sorted(judges):
            records = [(a, envs[a["answer_id"]]) for a in turns]
            rubric_cells = [next((c for c in e["rubric"] if c["judge_id"] == judge), {}) for _, e in records]
            valid = all(a.get("status", a.get("availability")) == "AVAILABLE" for a, _ in records)
            scored = [c.get("rubric", c) for c in rubric_cells]
            quality_ok = valid and all(c.get("status") == "AVAILABLE" and s.get("weighted_total") is not None for c, s in zip(rubric_cells, scored))
            scores = {}
            if quality_ok:
                dims = set().union(*(s.get("scores", {}).keys() for s in scored))
                scores = {d: fmean(s["scores"][d] for s in scored if d in s.get("scores", {})) for d in dims}
                weights = scored[0].get("final_weights", {})
                quality = sum(scores[d] * weights[d] for d in scores) if weights and all(d in weights for d in scores) else fmean(s["weighted_total"] for s in scored)
            else:
                quality = None
            base = {"subject_id": subject, "judge_id": judge, "case_id": case}
            case_metrics.append({**base, "metric": "rubric", "value": quality, "eligible": quality_ok, "dimensions": scores,
                                 "reason": None if quality_ok else "INCOMPLETE_RUBRIC"})
            assessment_cells = [next((c for c in e["assessments"] if c["judge_id"] == judge), {}) for _, e in records]
            for dimension in ("faithfulness", "correctness"):
                counts = Counter()
                complete = valid
                for (_, e), cell in zip(records, assessment_cells):
                    inv = inventories.get(e.get("inventory_id"))
                    assessed = cell.get("assessment", {}).get("claims", [])
                    by_id = {c["id"]: c for c in assessed}
                    if inv is None or cell.get("status") not in {"AVAILABLE", "PARTIAL"} or cell.get("assessment", {}).get("dimension_status", {}).get(dimension) == "UNAVAILABLE":
                        complete = False
                        continue
                    for claim in inv["claims"]:
                        verdict = by_id.get(claim["id"], {}).get(dimension, {}).get("verdict")
                        if verdict not in {"ENTAILED", "PARTIAL", "CONTRADICTED", "UNSUPPORTED", "UNKNOWN", "NOT_APPLICABLE"}:
                            complete = False
                        else:
                            counts[verdict] += 1
                denominator = sum(v for k, v in counts.items() if k != "NOT_APPLICABLE")
                eligible = complete and denominator > 0
                case_metrics.append({**base, "metric": dimension, "value": counts["ENTAILED"] / denominator if eligible else None,
                                     "unknown_ratio": counts["UNKNOWN"] / denominator if eligible else None,
                                     "numerator": counts["ENTAILED"], "denominator": denominator, "verdict_counts": dict(counts),
                                     "eligible": eligible, "reason": None if eligible else ("NOT_APPLICABLE" if complete else "INCOMPLETE_ASSESSMENT")})
            for gate_type in ("rubric_gate", "requirements_gate"):
                gates = []
                for (answer, _), rc, ac in zip(records, scored, assessment_cells):
                    if gate_type == "rubric_gate":
                        red = rc.get("red_lines", [])
                        gates.append("FAIL" if any(r.get("triggered") for r in red) else (rc.get("gate", "PASS") if rc.get("status") == "AVAILABLE" else "UNDETERMINED"))
                    else:
                        required = [r for r in answer.get("requirements", []) if r.get("critical")]
                        judged = {r["id"]: r for r in ac.get("assessment", {}).get("requirements", [])}
                        values = [{"SATISFIED": "PASS", "VIOLATED": "FAIL", "NOT_APPLICABLE": "NOT_APPLICABLE"}.get(judged.get(r["id"], {}).get("verdict"), "UNDETERMINED") for r in required]
                        gates.append(_gate(values) if values else "NOT_APPLICABLE")
                case_metrics.append({**base, "metric": gate_type, "gate": _gate(gates), "eligible": True})
    summaries = []
    for subject in sorted({a["subject_id"] for a in answers}):
        for judge in sorted(judges):
            for metric in ("rubric", "faithfulness", "correctness", "rubric_gate", "requirements_gate"):
                subset = [c for c in case_metrics if c["subject_id"] == subject and c["judge_id"] == judge and c["metric"] == metric]
                eligible = [c for c in subset if c["eligible"]]
                gate_counts = Counter(c["gate"] for c in subset if "gate" in c)
                if gate_counts:
                    den = sum(n for k, n in gate_counts.items() if k != "NOT_APPLICABLE")
                    value = gate_counts["PASS"] / den if den else None
                else:
                    den = len(eligible)
                    value = fmean(c["value"] for c in eligible) if eligible else None
                summaries.append({"metric": metric, "scope": "own_complete_cases", "subject_id": subject, "judge_id": judge,
                                  "value": value, "effective_cases": len(eligible), "planned_cases": len(subset), "denominator": den,
                                  "case_ids": [c["case_id"] for c in eligible], "excluded": [{"case_id": c["case_id"], "reason": c.get("reason")} for c in subset if not c["eligible"]],
                                  "gate_counts": dict(gate_counts), "unknown_ratio": fmean(c["unknown_ratio"] for c in eligible) if eligible and metric in {"faithfulness", "correctness"} else None,
                                  "formula": "case_equal_weight" if not gate_counts else "PASS/(PASS+FAIL+UNDETERMINED)"})
    for judge in sorted(judges):
        for metric in ("rubric", "faithfulness", "correctness"):
            own = [s for s in summaries if s["judge_id"] == judge and s["metric"] == metric and s["scope"] == "own_complete_cases"]
            common = set.intersection(*(set(s["case_ids"]) for s in own)) if own else set()
            for summary in own:
                subset = [c for c in case_metrics if c["subject_id"] == summary["subject_id"] and c["judge_id"] == judge and c["metric"] == metric and c["case_id"] in common]
                summaries.append({**summary, "scope": "common_complete_cases", "value": fmean(c["value"] for c in subset) if subset else None,
                                  "effective_cases": len(common), "denominator": len(common), "case_ids": sorted(common),
                                  "unknown_ratio": fmean(c["unknown_ratio"] for c in subset) if subset and metric in {"faithfulness", "correctness"} else None,
                                  "excluded": [{"case_id": c["case_id"], "reason": "NOT_COMMON_COMPLETE"} for c in case_metrics if c["subject_id"] == summary["subject_id"] and c["judge_id"] == judge and c["metric"] == metric and c["case_id"] not in common]})
    applicability = []
    for c in case_metrics:
        applicability.append({k: c.get(k) for k in ("subject_id", "judge_id", "case_id", "metric", "eligible", "reason", "verdict_counts", "denominator")})
    usage = []
    seen_attempts = set()
    for stage in result.get("stages", []):
        for attempt in stage.get("attempts", []):
            ident = attempt.get("attempt_id")
            if ident in seen_attempts:
                continue
            seen_attempts.add(ident)
            usage.append({"task": stage.get("task"), "attempt_id": ident, "usage": attempt.get("usage"), "latency_ms": attempt.get("latency_ms"), "reused": bool(stage.get("reused_from"))})
    citation_coverage = []
    for answer in answers:
        envelope = envs[answer["answer_id"]]
        catalog = {u["ref"]: u for u in answer.get("context", [])}
        for cell in envelope["assessments"]:
            available = (answer.get("context_capture") == "EXPOSED" and cell.get("status") in {"AVAILABLE", "PARTIAL"}
                         and cell.get("assessment", {}).get("dimension_status", {}).get("faithfulness") != "UNAVAILABLE")
            refs = {q["ref"] for c in cell.get("assessment", {}).get("claims", []) for q in c.get("faithfulness", {}).get("evidence", [])}
            layers = sorted({u.get("layer") for u in catalog.values() if u.get("layer")})
            for layer in [None, *layers]:
                eligible_refs = {r for r, u in catalog.items() if layer is None or u.get("layer") == layer}
                count = len(refs & eligible_refs)
                citation_coverage.append({"answer_id": answer["answer_id"], "judge_id": cell["judge_id"], "layer": layer,
                                          "cited_occurrences": count if available else None, "provided_occurrences": len(eligible_refs),
                                          "value": count / len(eligible_refs) if available and eligible_refs else None,
                                          "status": "AVAILABLE" if available else "UNAVAILABLE"})
    from .taxonomy import AXES, case_taxonomy
    groups = {}
    for a in answers:
        key = (a["subject_id"], a["case_id"])
        if not any(a.get(axis) is not None for axis in AXES):
            continue
        labels = case_taxonomy(a)
        if key in groups and groups[key] != labels:
            raise ValueError(f"inconsistent case taxonomy for {key}")
        groups[key] = labels
    grouped = []
    for summary in [s for s in summaries if s["scope"] == "own_complete_cases"]:
        for axis, vocabulary in AXES.items():
            for label in vocabulary:
                subset = [c for c in case_metrics if c["subject_id"] == summary["subject_id"] and c["judge_id"] == summary["judge_id"]
                          and c["metric"] == summary["metric"] and (label in groups.get((c["subject_id"], c["case_id"]), {}).get(axis, [])
                          if axis == "scenario_tags" else groups.get((c["subject_id"], c["case_id"]), {}).get(axis) == label)]
                if not subset:
                    continue
                valid_cases = [c for c in subset if c["eligible"]]
                gate_counts = Counter(c["gate"] for c in subset if "gate" in c)
                denominator = sum(n for status, n in gate_counts.items() if status != "NOT_APPLICABLE") if gate_counts else len(valid_cases)
                value = (gate_counts["PASS"] / denominator if denominator else None) if gate_counts else (fmean(c["value"] for c in valid_cases) if valid_cases else None)
                grouped.append({**summary, "scope": f"{axis}:{label}", "value": value,
                                "effective_cases": len(valid_cases), "planned_cases": len(subset), "denominator": denominator,
                                "case_ids": [c["case_id"] for c in valid_cases], "gate_counts": dict(gate_counts),
                                "formula": "PASS/(PASS+FAIL+UNDETERMINED)" if gate_counts else "case_equal_weight",
                                "excluded": [{"case_id": c["case_id"], "reason": c.get("reason")} for c in subset if not c["eligible"]],
                                "unknown_ratio": fmean(c["unknown_ratio"] for c in valid_cases) if valid_cases and summary["metric"] in {"faithfulness", "correctness"} else None})
    from .routing import route_analysis
    return {"case_metrics": case_metrics, "metrics": summaries + grouped, "applicability": applicability, "usage": usage, "citation_coverage": citation_coverage,
            'routing':route_analysis(answers,result.get('plan',{}))}


def validate_complete_results(result):
    if result.get("schema_version") != "xiaoan-results/v2":
        raise ValueError("expected complete xiaoan-results/v2; workbook/legacy inputs unsupported")
    content = {k: v for k, v in result.items() if k not in {"core_digest", "result_generation"}}
    if result.get("core_digest") != complete_digest(content):
        raise ValueError("complete results digest mismatch")
    answers = {a["answer_id"]: a for a in result["answers"]}
    inventories = {i["inventory_id"]: i for i in result["inventories"]}
    if len(answers) != len(result["answers"]) or len(inventories) != len(result["inventories"]):
        raise ValueError("duplicate answer/inventory identity")
    for inv in inventories.values():
        if inv.get("answer_id") not in answers:
            raise ValueError("orphan inventory")
        answer = answers[inv["answer_id"]]
        if not isinstance(answer.get("answer"), str):
            raise ValueError("inventory requires available answer text")
        ids = set()
        for claim in inv["claims"]:
            if claim["id"] in ids:
                raise ValueError("duplicate claim identity")
            ids.add(claim["id"])
            span = claim["answer_span"]
            if answer["answer"][span["start"]:span["end"]] != span["text"]:
                raise ValueError("claim answer span mismatch")
    for envelope in result["envelopes"]:
        aid = envelope["answer_id"]
        if aid not in answers:
            raise ValueError("orphan envelope")
        iid = envelope.get("inventory_id")
        if iid is not None and (iid not in inventories or inventories[iid]["answer_id"] != aid):
            raise ValueError("inventory join mismatch")
        for cell in envelope["assessments"]:
            if cell.get("inventory_id") not in {None, iid}:
                raise ValueError("assessment inventory join mismatch")
            if cell.get("assessment"):
                known = {c["id"] for c in inventories[iid]["claims"]} if iid else set()
                if any(c["id"] not in known for c in cell["assessment"].get("claims", [])):
                    raise ValueError("unknown assessment claim")
                row = answers[aid]
                for claim in cell["assessment"].get("claims", []):
                    for dimension, units in (("faithfulness", row.get("context", [])), ("correctness", row.get("reference_facts", []))):
                        if cell["assessment"].get("dimension_status", {}).get(dimension) == "UNAVAILABLE":
                            continue
                        catalog = {u["ref"]: u for u in units}
                        for quote in claim.get(dimension, {}).get("evidence", []):
                            if quote["ref"] not in catalog:
                                raise ValueError("evidence domain/ref mismatch")
                            content = catalog[quote["ref"]]["content"]
                            if content[quote["start"]:quote["end"]] != quote["text"]:
                                raise ValueError("evidence span mismatch")
    if len(result["envelopes"]) != len(answers) or len({e["answer_id"] for e in result["envelopes"]}) != len(answers):
        raise ValueError("envelope coverage mismatch")
    return result
