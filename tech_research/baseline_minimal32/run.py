#!/usr/bin/env python3
"""Bare-model baseline; reuse the authoritative evaluator and provider adapter."""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import sys
import threading
from types import FunctionType

HERE = Path(__file__).resolve().parent
EVALUATION = HERE.parent.parent / "evaluation_multimodels"
sys.path.insert(0, str(EVALUATION))

# Import first: the existing plugin loads .env before resolving model defaults.
import company_eval_plugins as providers
from xiaoan_eval.cases import load_case
from xiaoan_eval.multimodel import (
    ModelSpec, default_subject_specs, default_judge_specs, normalize_response,
    run_matrix, render_matrix_report, write_matrix_workbook,
)
from xiaoan_eval.rules import load_rating_rule

MINIMAL32 = (1, 4, 5, 9, 10, 11, 12, 14, 15, 17, 18, 21, 22, 23, 24, 26,
             28, 29, 30, 35, 37, 42, 48, 51, 53, 57, 61, 62, 63, 66, 72, 74)


def safe_failure(exc, stage):
    """Keep structured retry/HTTP diagnostics without provider message bodies."""
    errors = tuple(getattr(exc, "retry_errors", ()))
    safe = [e for e in errors if isinstance(e, str) and e.replace("_", "").isalnum()]
    return providers.ProviderCallError(
        f"{stage} failed: {type(exc).__name__}; {','.join(safe)}",
        attempt_count=int(getattr(exc, "attempt_count", 1)), retry_errors=safe,
    )


class BareConversation:
    """Thread-local case history; no system instruction, oracle, RAG or tools.

    Reuse provider settings/retries verbatim, replacing only Request in a private
    copy of the transport's globals. Never patch the shared Judge transport.
    """
    def __init__(self):
        self.local = threading.local()
        original = providers.multimodel_transport
        self.transport = FunctionType(
            original.__code__, {**original.__globals__, "Request": self.request},
            original.__name__, original.__defaults__, original.__closure__,
        )

    def start_case(self, spec, case_id):
        self.local.messages = []
        self.local.failed = False

    def end_case(self, spec, case_id):
        self.local.messages = []

    def request(self, url, data, **kwargs):
        body = json.loads(data)
        # Only model sampling/provider options survive from the adapter.
        for key in ("system", "tools", "tool_choice", "response_format", "prompt_cache_key"):
            body.pop(key, None)
        body["messages"] = list(self.local.messages)
        return providers.Request(url, data=json.dumps(body, ensure_ascii=False).encode(), **kwargs)

    def __call__(self, spec, prompt):
        if self.local.failed:
            raise RuntimeError("previous turn unavailable; remaining case turns skipped")
        self.local.messages.append({"role": "user", "content": prompt})
        try:
            raw = self.transport(spec, prompt)
            answer = normalize_response(spec.provider, spec.model, raw, 0).text
            if not answer.strip():
                raise RuntimeError("empty subject answer")
        except Exception as exc:
            self.local.failed = True
            # Avoid saving provider exception text that could echo credentials.
            raise safe_failure(exc, "subject provider") from None
        self.local.messages.append({"role": "assistant", "content": answer})
        return raw


def judge_transport(spec, prompt):
    try:
        return providers.multimodel_transport(spec, prompt)
    except Exception as exc:
        raise safe_failure(exc, "judge provider") from None


def specs(path, defaults, judge=False):
    result = defaults if path is None else tuple(ModelSpec(**row) for row in json.loads(Path(path).read_text()))
    if not result or len({s.id for s in result}) != len(result):
        raise ValueError("model list must be non-empty with unique IDs")
    if any((s.tier == "judge") != judge for s in result):
        raise ValueError("Judges require tier=judge; subjects must not use tier=judge")
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="execute paid provider calls; otherwise preview only")
    parser.add_argument("--output", type=Path, default=HERE / "runs" / "baseline")
    parser.add_argument("--cases", help="optional comma-separated subset, e.g. TC-01,TC-04")
    parser.add_argument("--subjects", help="optional JSON ModelSpec array")
    parser.add_argument("--judges", help="optional JSON ModelSpec array")
    parser.add_argument("--latest-only", action="store_true", help="use the highest configured tier from each provider")
    parser.add_argument("--include-self-judging", action="store_true", help="include diagonal self-evaluations in primary scores")
    parser.add_argument("--subject-concurrency", type=int, default=2)
    parser.add_argument("--judge-concurrency", type=int, default=3)
    parser.add_argument("--max-in-flight", type=int, default=3)
    parser.add_argument("--per-provider-concurrency", type=int, default=1)
    parser.add_argument("--resume", action="store_true", help="reuse successes and retry failed/partial conversations")
    args = parser.parse_args()
    allowed = [f"TC-{n:02d}" for n in MINIMAL32]
    ids = args.cases.split(",") if args.cases else allowed
    if not ids or len(set(ids)) != len(ids) or set(ids) - set(allowed):
        parser.error("--cases must be a unique subset of the minimal 32")
    rule_path = EVALUATION / "ratings rule.yml"
    rule = load_rating_rule(rule_path)
    paths = [EVALUATION / "test-cases" / f"{cid}.yaml" for cid in ids]
    cases = [load_case(path, rule).case for path in paths]
    if any(case is None or case.id != cid for case, cid in zip(cases, ids)):
        raise ValueError("invalid case or case ID mismatch")
    subjects = specs(args.subjects, default_subject_specs())
    if args.latest_only:
        subjects = tuple(s for s in subjects if s.tier == "latest")
        if not subjects:
            parser.error("--latest-only selected no subjects")
    judges = specs(args.judges, default_judge_specs(), judge=True)
    turns = sum(len(case.turns) for case in cases)
    source_files = [rule_path, *paths, EVALUATION / "company_eval_plugins.py",
                    *sorted((EVALUATION / "xiaoan_eval").glob("*.py"))]
    contract = {
        "mode": "bare-native-conversation/v1", "cases": ids, "turns": turns,
        "subjects": [asdict(s) for s in subjects], "judges": [asdict(s) for s in judges],
        "isolate_self_judging": not args.include_self_judging,
        "source_sha256": {str(p.relative_to(EVALUATION)): hashlib.sha256(p.read_bytes()).hexdigest() for p in source_files},
        "runner_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "subject_calls": turns * len(subjects),
        "judge_calls_upper_bound": turns * len(subjects) * len(judges),
    }
    print(json.dumps({k: v for k, v in contract.items() if not k.endswith("sha256")}, ensure_ascii=False, indent=2))
    if not args.run:
        print("Preview only. Add --run to call providers.")
        return 0
    out = args.output.resolve()
    manifest = out / "manifest.json"
    if args.resume:
        if not manifest.exists() or json.loads(manifest.read_text()) != contract:
            raise ValueError("resume contract changed; use a new output directory")
    else:
        if out.exists() and any(out.iterdir()):
            raise ValueError("output is not empty; use --resume or a new directory")
        out.mkdir(parents=True, exist_ok=True)
        manifest.write_text(json.dumps(contract, ensure_ascii=False, indent=2))
        snapshots = out / "inputs"
        snapshots.mkdir()
        for path in [rule_path, *paths]:
            (snapshots / path.name).write_bytes(path.read_bytes())
    print("Generating answers, then judging frozen answers. Checkpoint: " + str(out / "checkpoint.jsonl"), flush=True)
    rows = run_matrix(
        cases, subjects, judges, subject_transport=BareConversation(),
        judge_transport=judge_transport, rating_rule=rule,
        checkpoint_path=out / "checkpoint.jsonl", resume=args.resume,
        retry_unavailable=args.resume, subject_concurrency=args.subject_concurrency,
        judge_concurrency=args.judge_concurrency, max_in_flight=args.max_in_flight,
        per_provider_concurrency=args.per_provider_concurrency,
        isolate_self_judging=not args.include_self_judging,
    )
    write_matrix_workbook(rows, out / "results.xlsx")
    note = ("# 無 Chatflow 基準\n\n受測模型只收到原始 user/assistant 對話；無 system prompt、分流、檢索或工具。\n"
            "法律／資源真確性未另接 lawwiki 查證，RL-02 為 Judge 判斷，需人工複核。\n"
            "路由與檢索等 Chatflow 指標不適用；不把缺少遙測解讀為能力零分。\n\n")
    (out / "report.md").write_text(note + render_matrix_report(rows), encoding="utf-8")
    print(f"Saved: {out / 'results.xlsx'} and {out / 'report.md'}")
    return 0 if rows and all(row["status"] == "PASS" for row in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
