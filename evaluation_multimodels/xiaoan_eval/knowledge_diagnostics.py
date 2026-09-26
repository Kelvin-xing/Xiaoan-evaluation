"""Pure, offline diagnostics for capsule knowledge use and reviewed gaps.

This module deliberately does not infer corpus coverage from an answer.  A
verified gap requires a binding review record that explicitly says the need
was reviewed and that a capsule was required.
"""
from __future__ import annotations

import json
from collections import Counter
from typing import Any, Mapping, Sequence

SCHEMA_VERSION = "knowledge-diagnostics/v1"
REVIEW_VERSION = "knowledge-review/v1"
_FULL = {"ENTAILS"}
_PARTIAL = {"PARTIAL"}


def _map(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _seq(value: Any) -> list[Any]:
    return list(value) if isinstance(value, Sequence) and not isinstance(value, (str, bytes)) else []


def _identity(row: Mapping[str, Any]) -> tuple[Any, ...]:
    binding = _map(row.get("binding"))
    return (row.get("case_id"), row.get("turn"), row.get("subject_id"),
            binding.get("answer_sha256"), binding.get("context_sha256"))


def _relations(claim: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    return [r for r in _seq(claim.get("relations")) if isinstance(r, Mapping)]


def _capsule_state(claim: Mapping[str, Any]) -> tuple[str, list[Mapping[str, Any]]]:
    capsule = [r for r in _relations(claim) if r.get("layer") == "CAPSULE"]
    names = {r.get("relation") for r in capsule}
    if names & _FULL:
        return "FULL", capsule
    if names & _PARTIAL:
        return "PARTIAL", capsule
    return "NONE", capsule


def _claim_row(claim: Mapping[str, Any], turn: Mapping[str, Any]) -> dict[str, Any]:
    state, capsule = _capsule_state(claim)
    rels = _relations(claim)
    other_layers = sorted({str(r.get("layer")) for r in rels
                           if r.get("layer") and r.get("layer") != "CAPSULE"})
    unsupported = not any(r.get("relation") in ("ENTAILS", "PARTIAL") for r in rels)
    if state == "NONE" and unsupported:
        attribution = "UNSUPPORTED_WITHOUT_CAPSULE_EVIDENCE"
    elif state == "NONE":
        attribution = "SUPPORTED_BY_OTHER_OR_PROVIDED_EVIDENCE"
    else:
        attribution = "CAPSULE_FULL" if state == "FULL" else "CAPSULE_PARTIAL"
    return {
        "case_id": turn.get("case_id"), "turn": turn.get("turn"),
        "subject_id": turn.get("subject_id"), "judge_id": turn.get("judge_id"),
        "binding": dict(_map(turn.get("binding"))),
        "claim_id": claim.get("claim_id"), "claim_text": _map(claim.get("answer_span")).get("text", claim.get("text")),
        "claim_kind": claim.get("kind"), "capsule_support": state,
        "capsule_evidence": [dict(r) for r in capsule], "other_evidence_layers": other_layers,
        "all_evidence_refs": [r.get("evidence_ref") for r in rels if r.get("evidence_ref")],
        "unsupported_category": claim.get("unsupported_category"),
        "attribution": attribution,
        "interpretation": "Capsule evidence is explicit in validated attribution; other evidence does not prove capsule use."
    }


def _review_index(reviews: Any) -> dict[tuple[Any, ...], list[Mapping[str, Any]]]:
    if reviews is None:
        return {}
    root = reviews if isinstance(reviews, Mapping) else {"schema_version": REVIEW_VERSION, "reviews": reviews}
    if root.get("schema_version") != REVIEW_VERSION or not isinstance(root.get("reviews"), list):
        raise ValueError(f"expected {REVIEW_VERSION} reviews array")
    result: dict[tuple[Any, ...], list[Mapping[str, Any]]] = {}
    for row in root["reviews"]:
        if not isinstance(row, Mapping):
            raise ValueError("review rows must be objects")
        if not all(row.get(k) is not None for k in ("case_id", "turn", "subject_id", "binding")):
            raise ValueError("review row missing identity")
        needs = row.get("need_to_capsule", [])
        if not isinstance(needs, list):
            raise ValueError("need_to_capsule must be an array")
        for need in needs:
            if not isinstance(need, Mapping) or not isinstance(need.get("requirement_id"), str) or not isinstance(need.get("text"), str):
                raise ValueError("review need requires requirement_id and text")
            if need.get("review_status") not in ("REVIEWED", "UNCERTAIN"):
                raise ValueError("review_status must be REVIEWED or UNCERTAIN")
            if need.get("status") not in ("REQUIRED", "OPTIONAL"):
                raise ValueError("need status must be REQUIRED or OPTIONAL")
            if need.get("adoption_status", "UNKNOWN") not in ("ADOPTED", "OMITTED", "UNKNOWN"):
                raise ValueError("adoption_status must be ADOPTED, OMITTED, or UNKNOWN")
        result.setdefault(_identity(row), []).append(row)
    return result


def _requirements(turn: Mapping[str, Any], reviews: list[Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    gaps: list[dict[str, Any]] = []
    for review in reviews:
        for need in _seq(review.get("need_to_capsule")):
            need = _map(need)
            row = {"case_id": turn.get("case_id"), "turn": turn.get("turn"), "subject_id": turn.get("subject_id"),
                   "binding": dict(_map(turn.get("binding"))), "requirement_id": need.get("requirement_id"),
                   "requirement": need.get("text"), "requiredness": need.get("status"),
                   "review_status": need.get("review_status"), "capsule_id": need.get("capsule_id"),
                   "adoption": need.get("adoption_status", "UNKNOWN"),
                   "evidence": list(need.get("adoption_evidence", [])) if isinstance(need.get("adoption_evidence", []), list) else [],
                   "interpretation": "Adoption requires explicit requirement evidence; this row is not inferred from answer absence."}
            rows.append(row)
            if need.get("review_status") == "REVIEWED" and need.get("status") == "REQUIRED" and need.get("capsule_id"):
                gaps.append({**row, "gap": "VERIFIED_CAPSULE_GAP"})
    return rows, gaps


def build_knowledge_diagnostics(analysis: Mapping[str, Any], reviews: Any = None) -> dict[str, Any]:
    """Build JSON-compatible diagnostics from an existing ``build_analysis`` result."""
    if not isinstance(analysis, Mapping):
        raise ValueError("analysis must be a mapping")
    review_index = _review_index(reviews)
    claim_rows: list[dict[str, Any]] = []
    requirement_rows: list[dict[str, Any]] = []
    gap_rows: list[dict[str, Any]] = []
    turn_rows: list[dict[str, Any]] = []
    for turn in _seq(analysis.get("turns")):
        if not isinstance(turn, Mapping):
            continue
        identity = _identity(turn)
        matched_reviews = [r for r in review_index.get(identity, [])
                           if dict(_map(r.get("binding"))) == dict(_map(turn.get("binding")))]
        claims = [c for c in _seq(analysis.get("claims"))
                  if isinstance(c, Mapping) and _identity(c) == identity]
        # Some parent analyses keep claims nested only under the turn.
        if not claims:
            claims = _seq(turn.get("claims"))
        local_claims = [_claim_row(c, turn) for c in claims if isinstance(c, Mapping)]
        reqs, gaps = _requirements(turn, matched_reviews)
        claim_rows.extend(local_claims); requirement_rows.extend(reqs); gap_rows.extend(gaps)
        capsule_n = sum(c["capsule_support"] in ("FULL", "PARTIAL") for c in local_claims)
        turn_rows.append({"case_id": turn.get("case_id"), "turn": turn.get("turn"), "subject_id": turn.get("subject_id"),
                          "judge_id": turn.get("judge_id"), "binding": dict(_map(turn.get("binding"))),
                          "answer_status": turn.get("answer_status"), "claims": len(local_claims),
                          "capsule_supported_claims": capsule_n,
                          "capsule_supported_claim_share": capsule_n / len(local_claims) if local_claims else None,
                          "reviewed_need_count": sum(r.get("review_status") == "REVIEWED" for r in reqs),
                          "requirement_adoption": "UNKNOWN_WITHOUT_EXPLICIT_REVIEW_EVIDENCE" if reqs else "NOT_REVIEWED",
                          "corpus_coverage": "VERIFIED_GAP_REVIEWED" if gaps else "UNKNOWN"})
    counts = Counter(c["capsule_support"] for c in claim_rows)
    summary = {"claim_count": len(claim_rows), "capsule_full": counts["FULL"], "capsule_partial": counts["PARTIAL"],
               "capsule_supported_claim_share": (counts["FULL"] + counts["PARTIAL"]) / len(claim_rows) if claim_rows else None,
               "required_count": sum(r["requiredness"] == "REQUIRED" for r in requirement_rows),
               "verified_capsule_gap_count": len(gap_rows),
               "unknown_corpus_coverage": not bool(gap_rows) and not bool(requirement_rows),
               "interpretation": "Unsupported or source-supported claims do not establish model internal knowledge or a capsule corpus gap."}
    result = {"schema_version": SCHEMA_VERSION, "turns": turn_rows, "claims": claim_rows,
              "requirements": requirement_rows, "gaps": gap_rows, "summary": summary}
    result["markdown"] = render_knowledge_diagnostics(result)
    return result


def detail_rows(diagnostics: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Flatten diagnostics for a parent workbook detail sheet."""
    return [{"detail_type": kind[:-1], **dict(row)} for kind in ("turns", "claims", "requirements", "gaps")
            for row in _seq(diagnostics.get(kind))]


def render_knowledge_diagnostics(diagnostics: Mapping[str, Any]) -> str:
    s = _map(diagnostics.get("summary"))
    lines = ["## 膠囊知識診斷（離線、描述性）", "",
             "膠囊支持只按逐 claim 的驗證 attribution evidence 計算；其他來源或 unsupported 不代表模型內部知識。缺少回答證據不等於 corpus gap。", "",
             f"- Claim 數：{s.get('claim_count', 0)}；膠囊完整／部分：{s.get('capsule_full', 0)}／{s.get('capsule_partial', 0)}；支持比例：{s.get('capsule_supported_claim_share', 'UNAVAILABLE')}",
             f"- 已驗證膠囊缺口：{s.get('verified_capsule_gap_count', 0)}；corpus coverage：{'UNKNOWN' if s.get('unknown_corpus_coverage') else 'REVIEWED'}", "",
             "| Case/Turn | Claim | 膠囊支持 | 其他證據 | 判讀 |", "| --- | --- | --- | --- | --- |"]
    for row in _seq(diagnostics.get("claims")):
        claim_text = str(row.get("claim_text", "")).replace("|", "\\|")
        other = ", ".join(row.get("other_evidence_layers", [])) or "無"
        lines.append(f"| {row.get('case_id')} T{row.get('turn')} | {claim_text} | {row.get('capsule_support')} | {other} | {row.get('attribution')} |")
    lines += ["", "需求採用與缺口只有在 review 明確記錄需求時才可判定；未有 reviewed need-to-capsule evidence 的部分標為 UNKNOWN。", ""]
    return "\n".join(lines)
