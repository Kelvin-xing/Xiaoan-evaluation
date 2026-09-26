"""Immutable claim inventories and evidence-bound semantic assessments.

Authentic spans establish provenance, not the correctness of semantic labels.
Extraction completeness remains an independent human-calibration question.
"""
from __future__ import annotations

import hashlib
import json
from copy import deepcopy

from . import VERSION
from .configuration import prompt, schema

KINDS = {"FACTUAL", "INTERPRETIVE", "RECOMMENDATION", "ACTION", "SUPPORTIVE"}
VERDICTS = {"ENTAILED", "PARTIAL", "CONTRADICTED", "UNSUPPORTED", "UNKNOWN", "NOT_APPLICABLE"}
REQUIREMENT_KINDS = {"safety", "task", "constraint", "interaction", "route", "evidence"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def text(value, name):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be non-empty text")
    return value


def indexed(rows, name, key="id"):
    if not isinstance(rows, list):
        raise ValueError(f"{name} must be an array")
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{name} entries must be objects")
        ident = text(row.get(key), f"{name}.{key}")
        if ident in result:
            raise ValueError(f"duplicate {name} ID: {ident}")
        result[ident] = row
    return result


def span(value, content):
    if not isinstance(value, dict):
        raise ValueError("span must be an object")
    start, end = value.get("start"), value.get("end")
    if (type(start) is not int or type(end) is not int or
            not 0 <= start < end <= len(content) or content[start:end] != value.get("text")):
        raise ValueError("span must match exact Unicode code-point offsets and text")


def canonical_history(history):
    if not isinstance(history, list) or any(
        not isinstance(h, dict) or h.get("role") not in {"user", "assistant"}
        or not isinstance(h.get("content"), str) for h in history
    ):
        raise ValueError("history must contain completed user/assistant messages only")
    return [{"role": h["role"], "content": h["content"]} for h in history]


def canonical_context(context):
    units = indexed(context, "context", "ref")
    return [{k: text(u.get(k), k) for k in ("ref", "content", "layer")} for u in units.values()]


def extraction_request(row, extractor):
    history = canonical_history(row.get("history", []))
    payload = {"answer_id": text(row.get("answer_id"), "answer_id"), "answer": text(row.get("answer"), "answer"),
               "question": text(row.get("question"), "question"), "history": history}
    return {"contract": VERSION, "task": "extract_claims", "response_schema": schema("claim-extraction"), "validator_version": "frozen/v2", "identity": extractor,
            "binding": digest(payload), **payload,
            "instructions": (
                prompt("claim-extraction.md")
            )}


def validate_inventory(payload, request):
    if not isinstance(payload, dict) or payload.get("binding") != request["binding"]:
        raise ValueError("inventory has a missing or stale answer binding")
    claims = indexed(payload.get("claims"), "claims")
    fingerprints = set()
    for claim in claims.values():
        if claim.get("kind") not in KINDS:
            raise ValueError("invalid claim kind")
        text(claim.get("proposition"), "proposition")
        if not isinstance(claim.get("conditions"), list):
            raise ValueError("claim conditions must be an array")
        for condition in claim["conditions"]:
            text(condition, "condition")
        span(claim.get("answer_span"), request["answer"])
        fingerprint = digest({k: claim[k] for k in ("proposition", "conditions", "answer_span")})
        if fingerprint in fingerprints:
            raise ValueError("duplicate proposition and span")
        fingerprints.add(fingerprint)
    frozen = {"contract": VERSION, "binding": request["binding"],
              "extractor": request["identity"], "claims": deepcopy([
                  {**{k: c[k] for k in ("id", "kind", "proposition", "conditions")},
                   "answer_span": {k: c["answer_span"][k] for k in ("start", "end", "text")}}
                  for c in claims.values()])}
    frozen["inventory_id"] = digest(frozen)
    return frozen


def assessment_request(row, inventory, judge):
    context = indexed(row.get("context", []) if row.get("context_capture") == "EXPOSED" else [], "context", "ref")
    truth = indexed(row.get("reference_facts", []), "reference_facts", "ref")
    for unit in [*context.values(), *truth.values()]:
        text(unit.get("content"), "evidence content")
        text(unit.get("layer"), "evidence layer")
    if truth and row.get("truth_status") != "approved":
        raise ValueError("independent truth evidence requires approved provenance")
    if truth:
        text(row.get("truth_version"), "truth_version")
    # Truth is independent curated material, never an assistant or policy assertion.
    if any(u["layer"] not in {"SOURCE", "REFERENCE"} for u in truth.values()):
        raise ValueError("truth evidence must be SOURCE or REFERENCE")
    requirements = indexed(row.get("requirements", []), "requirements")
    for req in requirements.values():
        text(req.get("text"), "requirement text")
        if req.get("kind") not in REQUIREMENT_KINDS or type(req.get("critical")) is not bool:
            raise ValueError("requirement requires kind and explicit critical boolean")
    observations = row.get("observations", {})
    if not isinstance(observations, dict) or observations.keys() - requirements.keys():
        raise ValueError("observations must bind requirement IDs")
    for observation in observations.values():
        if not isinstance(observation, dict) or observation.get("status") not in {"AVAILABLE", "UNAVAILABLE", "NOT_APPLICABLE"}:
            raise ValueError("observation status required")
        if type(observation.get("value")) not in {bool, str, type(None)}:
            raise ValueError("observation value must be boolean, string or null")
    data = {"answer_id": row["answer_id"], "answer": row["answer"], "question": row["question"], "history": canonical_history(row.get("history", [])),
            "inventory": inventory, "context": [{k: u[k] for k in ("ref", "content", "layer")} for u in context.values()],
            "context_version": row.get("context_version"),
            "context_capture": row.get("context_capture", "UNAVAILABLE"),
            "reference_facts": [{k: u[k] for k in ("ref", "content", "layer")} for u in truth.values()], "truth_version": row.get("truth_version"),
            "requirements": [{k: r[k] for k in ("id", "kind", "text", "critical", "runtime_check", "expected", "scope", "policy_id", "abstention") if k in r} for r in requirements.values()],
            "oracle_status": row.get("oracle_status", "provisional"),
            "observations": {ident: {"status": obs["status"], "value": obs.get("value")}
                             for ident, obs in observations.items()}}
    return {"contract": VERSION, "task": "assess_claims", "response_schema": schema("claim-assessment"), "validator_version": "frozen/v2", "identity": judge,
            "binding": digest(data), **data,
            "instructions": (
                prompt("claim-assessment.md")
            )}


def validate_assessment(payload, request):
    if not isinstance(payload, dict) or payload.get("binding") != request["binding"]:
        raise ValueError("assessment has a missing or stale binding")
    claims = indexed(payload.get("claims"), "assessed claims")
    expected = indexed(request["inventory"]["claims"], "inventory")
    if claims.keys() != expected.keys():
        raise ValueError("assessment must cover exactly the frozen claim IDs")
    for ident, claim in claims.items():
        kind = expected[ident]["kind"]
        for dimension, field in (("faithfulness", "context"), ("correctness", "reference_facts")):
            label = claim.get(dimension)
            if not isinstance(label, dict) or label.get("verdict") not in VERDICTS:
                raise ValueError("invalid claim verdict")
            verdict = label["verdict"]
            text(label.get("reason"), "semantic reason")
            evidence = label.get("evidence")
            if not isinstance(evidence, list):
                raise ValueError("evidence must be an array")
            catalog = indexed(request[field], field, "ref")
            for quote in evidence:
                if quote.get("ref") not in catalog:
                    raise ValueError("unknown or wrong-domain evidence ref")
                span(quote, catalog[quote["ref"]]["content"])
            not_applicable = kind == "SUPPORTIVE" or (
                dimension == "correctness" and kind in {"RECOMMENDATION", "ACTION"})
            if not_applicable != (verdict == "NOT_APPLICABLE"):
                raise ValueError("claim type and applicability disagree")
            if verdict in {"ENTAILED", "PARTIAL", "CONTRADICTED"} and not evidence:
                raise ValueError("semantic support/contradiction requires evidence")
            if verdict == "NOT_APPLICABLE" and evidence:
                raise ValueError("non-applicable claims cannot carry support evidence")
            if dimension == "faithfulness" and request.get("context_capture") != "EXPOSED" and not not_applicable and verdict != "UNKNOWN":
                raise ValueError("missing context must remain UNKNOWN")
            if dimension == "correctness" and not catalog and not not_applicable and verdict != "UNKNOWN":
                raise ValueError("missing truth must remain UNKNOWN")
    requirements = indexed(payload.get("requirements"), "assessed requirements")
    expected_requirements = indexed(request["requirements"], "requirements")
    if requirements.keys() != expected_requirements.keys():
        raise ValueError("assessment must cover exactly all requirements")
    for ident, req in requirements.items():
        if req.get("verdict") not in {"SATISFIED", "VIOLATED", "UNCERTAIN", "NOT_APPLICABLE"}:
            raise ValueError("invalid requirement verdict")
        text(req.get("reason"), "requirement reason")
        if not isinstance(req.get("answer_spans"), list):
            raise ValueError("requirement answer_spans must be an array")
        for quote in req["answer_spans"]:
            span(quote, request["answer"])
        if (req["verdict"] == "SATISFIED" and expected_requirements[ident]["kind"] in {"task", "interaction"}
                and not req["answer_spans"]):
            raise ValueError("task/interaction fulfilment needs answer evidence")
        if ((expected_requirements[ident]["kind"] in {"route", "evidence"} or expected_requirements[ident].get("runtime_check"))
                and request["observations"].get(ident, {}).get("status") != "AVAILABLE"
                and req["verdict"] in {"SATISFIED", "VIOLATED"}):
            raise ValueError("route/evidence judgment needs a bound observation")
        observation = request["observations"].get(ident, {})
        if expected_requirements[ident].get("runtime_check") or expected_requirements[ident]["kind"] in {"route", "evidence"}:
            if observation.get("status") == "NOT_APPLICABLE" and req["verdict"] != "NOT_APPLICABLE":
                raise ValueError("explicit non-applicability must be retained")
            if observation.get("status") == "AVAILABLE" and type(observation.get("value")) is bool:
                expected_verdict = "SATISFIED" if observation["value"] else "VIOLATED"
                if req["verdict"] != expected_verdict:
                    raise ValueError("runtime requirement contradicts deterministic observation")
    return deepcopy({"binding": payload["binding"], "claims": list(claims.values()),
                     "requirements": list(requirements.values())})


def validate_assessment_parts(payload, request):
    """Validate binding first, then preserve independently valid dimensions/requirements."""
    if not isinstance(payload, dict) or payload.get('binding') != request['binding']:
        raise ValueError('assessment has a missing or stale binding')
    claims = indexed(payload.get('claims'), 'assessed claims')
    expected = indexed(request['inventory']['claims'], 'inventory')
    if claims.keys() != expected.keys():
        raise ValueError('assessment must cover exactly frozen claim IDs')
    requirements = indexed(payload.get('requirements'), 'assessed requirements')
    wanted = indexed(request['requirements'], 'requirements')
    if requirements.keys() != wanted.keys():
        raise ValueError('assessment must cover exactly requirements')
    output = {'binding': payload['binding'], 'claims': [], 'requirements': [],
              'validation_errors': [], 'dimension_status': {}}
    for ident, definition in expected.items():
        accepted = {'id': ident}
        for dimension in ('faithfulness', 'correctness'):
            subrequest = deepcopy(request)
            subrequest['inventory']['claims'] = [definition]
            subrequest['requirements'] = []
            kind = definition['kind']
            dummy = {'id': ident}
            for axis in ('faithfulness', 'correctness'):
                na = kind == 'SUPPORTIVE' or (axis == 'correctness' and kind in {'RECOMMENDATION', 'ACTION'})
                dummy[axis] = {'verdict': 'NOT_APPLICABLE' if na else 'UNKNOWN', 'evidence': [], 'reason': 'validation placeholder'}
            dummy[dimension] = claims[ident].get(dimension)
            try:
                validate_assessment({'binding': request['binding'], 'claims': [dummy], 'requirements': []}, subrequest)
                accepted[dimension] = deepcopy(claims[ident][dimension])
            except ValueError as exc:
                output['validation_errors'].append({'claim_id': ident, 'dimension': dimension, 'error': str(exc)})
        output['claims'].append(accepted)
    for ident, definition in wanted.items():
        subrequest = deepcopy(request)
        subrequest['inventory']['claims'] = []
        subrequest['requirements'] = [definition]
        try:
            validate_assessment({'binding': request['binding'], 'claims': [], 'requirements': [requirements[ident]]}, subrequest)
            output['requirements'].append(deepcopy(requirements[ident]))
        except ValueError as exc:
            output['validation_errors'].append({'requirement_id': ident, 'error': str(exc)})
    for dimension in ('faithfulness', 'correctness'):
        output['dimension_status'][dimension] = 'AVAILABLE' if all(dimension in c for c in output['claims']) else 'UNAVAILABLE'
    output['requirements_status'] = 'AVAILABLE' if len(output['requirements']) == len(wanted) else 'UNAVAILABLE'
    output['status'] = 'PARTIAL' if output['validation_errors'] else 'AVAILABLE'
    return output
