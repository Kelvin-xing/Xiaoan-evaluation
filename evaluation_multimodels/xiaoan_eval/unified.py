"""Adapters from existing snapshots and configured providers to the common core."""
from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

from xiaoan_eval_core.runtime import evaluate
from xiaoan_eval_core.ablation import run as run_ablation

from .evidence import validate_effective_context_snapshot, build_evidence_catalog


def attach_records(spec, records):
    """Attach immutable answers from single-run records or matrix cells.

    Rows in the plan still declare identities, the exact conversation prefix and
    approved requirements. Repeated judge cells reuse the same subject answer;
    conflicting answers/snapshots are rejected, never silently selected.
    """
    from xiaoan_eval_core.contracts import digest
    indexed = {}
    subjects = spec["planned_subjects"]

    def add(key, answer, snapshot, question=None):
        value = {"answer": answer, "effective_context_snapshot": snapshot, "question": question}
        if key in indexed and digest(indexed[key]) != digest(value):
            raise ValueError("conflicting immutable answers for subject/case/turn")
        indexed[key] = value

    for record in records:
        if "subject" in record and "answer" in record:
            answer = record["answer"]
            if answer.get("status") == "PASS" and answer.get("text"):
                add((record["subject"]["id"], record["case_id"], record["turn"]),
                    answer["text"], answer.get("trace", {}).get("effective_context_snapshot"))
        else:
            subject = record.get("subject_id") or (subjects[0] if len(subjects) == 1 else None)
            if subject is None:
                raise ValueError("single-run record needs subject_id for a multi-subject plan")
            traces = {t["turn"]: t.get("trace", {}) for t in record.get("pipeline", {}).get("turn_traces", [])}
            for turn in record.get("conversation", {}).get("turns", []):
                if turn.get("assistant_response"):
                    add((subject, record["case_id"], turn["turn"]), turn["assistant_response"],
                        traces.get(turn["turn"], {}).get("effective_context_snapshot"), turn.get("user_input"))
    spec = deepcopy(spec)
    for row in spec["rows"]:
        selected = indexed.get((row["subject_id"], row["case_id"], row["turn"]))
        if selected is None:
            row.update(status="UNAVAILABLE", answer=None)
            continue
        if selected["question"] is not None and selected["question"] != row["question"]:
            raise ValueError("record question does not match the curated turn plan")
        row.update(status="AVAILABLE", answer=selected["answer"])
        # No synthetic evidence fallback: missing snapshots make support unavailable.
        row.pop("context", None)
        row.pop("context_capture", None)
        row["effective_context_snapshot"] = selected["effective_context_snapshot"]
    return spec


def load_records(spec, input_path):
    filename = spec.get("records_file")
    if filename is None:
        return spec
    path = Path(input_path).resolve().parent / filename
    content = path.read_text(encoding="utf-8")
    records = json.loads(content) if content.lstrip().startswith("[") else [json.loads(line) for line in content.splitlines() if line.strip()]
    from xiaoan_eval_core.contracts import digest
    prepared = attach_records(spec, records)
    prepared["source_artifact_hash"] = digest(records)
    return prepared


def prepare(spec):
    spec = deepcopy(spec)
    for row in spec.get("rows", []):
        snapshot = row.pop("effective_context_snapshot", None)
        if snapshot is not None:
            validated = validate_effective_context_snapshot(snapshot)
            if validated.turn != row["turn"]:
                raise ValueError("snapshot turn does not match answer turn")
            if validated.composer.status != "INVOKED":
                raise ValueError("unified context requires an invoked composer snapshot")
            row["context"] = [{k: u[k] for k in ("ref", "content", "layer")}
                              for u in build_evidence_catalog(validated)]
            row["context_version"] = validated.snapshot_id
            row["context_capture"] = "EXPOSED"
        # Only explicit fields are passed to the engine. Arbitrary traces and
        # environment/provider configuration cannot enter a judge request.
        row.pop("trace", None)
    return spec


def run(spec, provider=None, *, checkpoint_dir=None, ablation=False, subject_provider=None):
    prepared = prepare(spec)
    if ablation:
        return run_ablation(prepared, provider, checkpoint_dir=checkpoint_dir,
                            subject_provider=subject_provider)
    return evaluate(prepared, provider, checkpoint_dir=checkpoint_dir,
                    rubric_stage=prepared.get("rubric_stage"),
                    relevancy_stage=prepared.get("relevancy_stage"))


def validate_evaluation_request(request):
    """Structural egress allowlist for the owner's authorized test evaluation.

    Does not authorize arbitrary subject adapters or claim that case text has
    been anonymized. Rebuild requests from canonical fields to reject extras.
    """
    from xiaoan_eval_core.contracts import extraction_request, assessment_request, validate_inventory
    from xiaoan_eval_core.runtime import identity
    try:
        if request.get("task") == "extract_claims":
            return request == extraction_request(request, identity(request["identity"]))
        if request.get("task") == "assess_claims":
            inv = request["inventory"]
            extraction = extraction_request(request, identity(inv["extractor"]))
            canonical = validate_inventory(inv, extraction)
            if canonical != inv:
                return False
            row = {**request, "context_capture": "EXPOSED", "truth_status": "approved"}
            return request == assessment_request(row, canonical, identity(request["identity"]))
        return False
    except (KeyError, TypeError, ValueError):
        return False


def configured_provider(request):
    """Use the configured evaluator endpoint; identity.provider must be configured.

    Credentials remain inside the existing client. This plugin never reads a
    provider or endpoint from untrusted evidence. It evaluates, not generates subjects.
    """
    from company_eval_plugins import _openai_client
    if request["task"] not in {"extract_claims", "assess_claims"}:
        raise ValueError("configured_provider only supports evaluation tasks")
    identity = request["identity"]
    if identity["provider"] != "configured":
        raise ValueError("use provider=configured for the configured endpoint plugin")
    from xiaoan_eval_core import model_config
    role = "XIAOAN_CLAIM_EXTRACTOR_MODEL" if request["task"] == "extract_claims" else "XIAOAN_CLAIM_ASSESSOR_MODEL"
    selected = model_config.model(role, identity["model"])
    response = _openai_client(selected).complete(
        model=selected,
        store=False,
        messages=[{"role": "system", "content": request["instructions"]},
                  {"role": "user", "content": json.dumps(
                      {k: v for k, v in request.items() if k != "instructions"}, ensure_ascii=False)}],
        response_format={"type": "json_object"},
    )
    return response.choices[0].message.content
