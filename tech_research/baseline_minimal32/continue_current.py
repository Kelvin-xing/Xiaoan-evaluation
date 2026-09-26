"""Frozen continuation for the user-approved Qwen/Kimi request migration."""
import argparse
from dataclasses import asdict, replace
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import time
import threading
from types import FunctionType

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs/minimal32-current-qwen-kimi-20260921"
sys.path.insert(0, str(OUT / "runtime"))
import company_eval_plugins as providers
# Credentials stay in their existing file, never in the source snapshot.
providers.EVALUATION_ENV_PATH = HERE.parent.parent / "evaluation_multimodels/.env"
providers._load_local_env()
# Freeze the approved request routing, independent of subsequent shared edits.
os.environ["XIAOAN_QWEN_ENDPOINT"] = "https://maas.qwencloudapi.com/compatible-mode/v1"
os.environ["XIAOAN_KIMI_ENDPOINT"] = "https://api.moonshot.cn/v1"
os.environ["GLOBALAI_MAX_RETRIES"] = "1"
os.environ["XIAOAN_PROVIDER_TIMEOUT"] = "120"

from xiaoan_eval import multimodel as mm
from xiaoan_eval.cases import load_case
from xiaoan_eval.rules import load_rating_rule

spec = importlib.util.spec_from_file_location("baseline_snapshot", OUT / "baseline_runner_snapshot.py")
base = importlib.util.module_from_spec(spec)
spec.loader.exec_module(base)

audit_lock = threading.Lock()


def normalize_official(raw, provider):
    """Lossless scalar-to-array correction; never change scores or verdicts."""
    text = mm.normalize_response(provider, "", raw, 0).text
    try:
        value = json.loads(text)
    except (ValueError, TypeError):
        return raw
    changes = []
    if isinstance(value, dict) and isinstance(value.get("red_lines"), list):
        for item in value["red_lines"]:
            if isinstance(item, dict) and isinstance(item.get("evidence"), str):
                item["evidence"] = [item["evidence"]] if item["evidence"] else []
                changes.append(item.get("id"))
    if not changes:
        return raw
    with audit_lock, (OUT / "format-normalization.jsonl").open("a") as stream:
        stream.write(json.dumps({"provider": provider, "original_text": text,
            "original_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "correction": "red_line_evidence_string_to_array", "red_line_ids": changes,
            "time": time.time()}, ensure_ascii=False) + "\n")
    return {**raw, "text": json.dumps(value, ensure_ascii=False)}


def current_judge(spec, prompt):
    if spec.provider not in {"qwen", "kimi"}:
        return base.judge_transport(spec, prompt)
    original = providers.multimodel_transport
    def open_long(request, **kwargs):
        return providers.urlopen(request, **{**kwargs, "timeout": 600})
    # Validate the lossless normalized shape before any transport-level retry.
    def shape_check(payload, native, names, ids):
        normalized = normalize_official(payload, spec.provider)
        if "text" in normalized:
            normalized = {**normalized, "choices": [{"message": {"content": normalized["text"]}}]}
        return providers._judge_response_error(normalized, native, names, ids)
    adapted = FunctionType(original.__code__, {**original.__globals__,
        "urlopen": open_long, "_judge_response_error": shape_check},
        original.__name__, original.__defaults__, original.__closure__)
    try:
        return normalize_official(adapted(spec, prompt), spec.provider)
    except Exception as exc:
        raise base.safe_failure(exc, "official judge") from None


def contract_hash(cases, subjects, judges, rule):
    value = {
        "judge_evidence_schema": mm.JUDGE_EVIDENCE_SCHEMA_VERSION,
        "judge_request_schema": mm.MATRIX_JUDGE_REQUEST_SCHEMA_VERSION,
        "judge_prompt_schema": mm.MATRIX_JUDGE_PROMPT_SCHEMA_VERSION,
        "cases": [mm._json_value(c) for c in cases],
        "subjects": [asdict(s) for s in subjects], "judges": [asdict(j) for j in judges],
        "rating_rule": mm._json_value(rule),
        "attribution": {"enabled": False, "judge_version": "attribution-judge/v1"},
        "isolate_self_judging": False, "scoring_contract_version": mm.SCORING_CONTRACT_VERSION,
    }
    return "sha256:" + hashlib.sha256(mm._canonical_json(value).encode()).hexdigest()


def migrate(destination, sources, digest, subjects, judges, rule):
    """Explicit new-run import with source hashes; never alter the parent run."""
    if destination.exists():
        return
    answers, judgments = {}, {}
    subject_ids = {s.id for s in subjects}
    judge_ids = {j.id for j in judges}
    origins = []
    for path, changed_allowed in sources:
        if not path.exists():
            continue
        origins.append({"path": str(path), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
        for line in path.read_text().splitlines():
            event = json.loads(line)
            aid = event.get("answer_id")
            if event["event"] == "answer":
                if event["subject"]["provider"] in {"qwen", "kimi"} and not changed_allowed:
                    continue
                if mm._spec_id(event["subject"]) not in subject_ids:
                    continue
                if event["answer"]["status"] == "PASS" and aid not in answers:
                    answers[aid] = event
            elif event["event"] == "judgement" and aid in answers:
                judge = event["judge"]
                if judge["provider"] in {"qwen", "kimi"} and not changed_allowed:
                    continue
                jid = mm._spec_id(judge)
                if jid not in judge_ids:
                    continue
                raw = mm._provider_response_from_mapping(event["judgement"])
                valid, _, _, _ = mm._validated_scores(raw, rule)
                if valid.status == "PASS":
                    judgments[aid, jid] = event
    with destination.open("x") as stream:
        for event in [*answers.values(), *judgments.values()]:
            stream.write(json.dumps({**event, "contract_sha256": digest,
                "imported_from_contract": event["contract_sha256"], "imported_at": time.time()}, ensure_ascii=False) + "\n")
    receipt = {"sources": origins, "answers_reused": len(answers), "judgments_reused": len(judgments),
               "new_contract": digest, "approval": "User requested current Qwen/Kimi requests and unchanged other three models."}
    destination.with_suffix(".migration.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2))
    print(json.dumps(receipt, ensure_ascii=False), flush=True)


def main():
    if (OUT / "CANCELLED_QWEN_KIMI.md").exists():
        raise SystemExit("Qwen/Kimi calls cancelled by user. Use continue_three_judges.py; do not restart this run.")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe", action="store_true")
    parser.add_argument("--kimi-check", action="store_true")
    args = parser.parse_args()
    manifest = json.loads((OUT / "manifest.json").read_text())
    rule = load_rating_rule(OUT / "inputs/ratings rule.yml")
    cases = [load_case(OUT / "inputs" / f"{cid}.yaml", rule).case for cid in manifest["cases"]]
    subjects = [mm.ModelSpec(**s) for s in manifest["subjects"]]
    judges = [mm.ModelSpec(**s) for s in manifest["judges"]]
    subject_transport = base.BareConversation()
    if args.kimi_check:
        os.environ["XIAOAN_PROVIDER_TIMEOUT"] = "600"
        os.environ["GLOBALAI_MAX_RETRIES"] = "0"
        cases = [replace(cases[0], turns=cases[0].turns[:1])]
        subjects = [s for s in subjects if s.provider == "qwen"]
        judges = [j for j in judges if j.provider == "kimi"]
        checkpoint = OUT / "kimi-check.jsonl"
        events = [json.loads(line) for line in (OUT / "probe.jsonl").read_text().splitlines()]
        answer = next(e["answer"] for e in events if e["event"] == "answer" and e["subject"]["provider"] == "qwen" and e["turn"] == 1)
        subject_transport = lambda *_: {"text": answer["text"], "usage": {}}
    elif args.probe:
        cases = cases[:1]
        subjects = [s for s in subjects if s.provider in {"qwen", "kimi"}]
        judges = [j for j in judges if j.provider in {"qwen", "kimi"}]
        checkpoint = OUT / "probe.jsonl"
    else:
        checkpoint = OUT / "checkpoint.jsonl"
        migrate(checkpoint, [(Path(manifest["parent_run"]) / "checkpoint.jsonl", False),
                             (OUT / "probe.jsonl", True), (OUT / "kimi-check.jsonl", True)],
                contract_hash(cases, subjects, judges, rule), subjects, judges, rule)
    print(f"Starting {'probe' if args.probe else 'full continuation'}; frozen runtime; {len(cases)} cases", flush=True)
    rows = mm.run_matrix(cases, subjects, judges, rating_rule=rule,
        subject_transport=subject_transport, judge_transport=current_judge,
        checkpoint_path=checkpoint, resume=checkpoint.exists(), retry_unavailable=checkpoint.exists(),
        subject_concurrency=10, judge_concurrency=5, max_in_flight=10,
        per_provider_concurrency=1 if args.kimi_check else 2, isolate_self_judging=False)
    prefix = "kimi-check-" if args.kimi_check else "probe-" if args.probe else ""
    mm.write_matrix_workbook(rows, OUT / f"{prefix}results.xlsx")
    (OUT / f"{prefix}report.md").write_text(mm.render_matrix_report(rows))
    from collections import Counter
    print(json.dumps({"cells": len(rows), "status": dict(Counter(r["status"] for r in rows)),
        "by_judge": dict(Counter(r["judge"]["provider"] + ":" + r["status"] for r in rows))}), flush=True)


if __name__ == "__main__":
    main()
