"""Retry only selected Judge cells over the frozen baseline answers."""
import hashlib
import json
import os
import shutil
import subprocess
import sys
from collections import Counter
from pathlib import Path

import continue_three_judges as previous


HERE = Path(__file__).resolve().parent
SOURCE = HERE / os.environ.get(
    "XIAOAN_SELECTED_RETRY_SOURCE",
    "runs/minimal32-three-judges-retry-20260923",
)
OUT = HERE / os.environ.get(
    "XIAOAN_SELECTED_RETRY_OUT",
    "runs/minimal32-three-judges-retry-42-20260923",
)
TARGET_SUBJECTS = {"claude", "gpt", "gemini"}
EXPECTED_SELECTED = int(os.environ.get("XIAOAN_EXPECTED_SELECTED", "42"))


def _event_key(event):
    if event["event"] == "cell":
        row = event["row"]
        return row["answer_id"], row["judge"]["id"]
    if event["event"] == "judgement":
        return event["answer_id"], previous.old.mm._spec_id(event["judge"])
    return None


def prepare():
    source_checkpoint = SOURCE / "checkpoint.jsonl"
    target_checkpoint = OUT / "checkpoint.jsonl"
    events = [json.loads(line) for line in source_checkpoint.read_text().splitlines()]
    answers = {
        event["answer_id"]: event
        for event in events
        if event["event"] == "answer"
    }
    cells = {
        _event_key(event): event["row"]
        for event in events
        if event["event"] == "cell"
    }
    selected = {
        key
        for key, row in cells.items()
        if row["status"] != "PASS"
        and answers[key[0]]["answer"]["status"] == "PASS"
        and row["subject"]["provider"] in TARGET_SUBJECTS
    }
    if len(answers) != 480 or len(cells) != 1440 or len(selected) != EXPECTED_SELECTED:
        raise RuntimeError(
            f"unexpected checkpoint shape answers={len(answers)} cells={len(cells)} selected={len(selected)}"
        )

    if not target_checkpoint.exists():
        OUT.mkdir(parents=True, exist_ok=True)
        shutil.copytree(SOURCE / "inputs", OUT / "inputs", dirs_exist_ok=True)
        retained = [
            event
            for event in events
            if _event_key(event) not in selected
        ]
        manifest = json.loads((SOURCE / "manifest.json").read_text())
        manifest["retry_selected"] = {
            "parent_run": str(SOURCE),
            "source_sha256": hashlib.sha256(source_checkpoint.read_bytes()).hexdigest(),
            "selected_cells": len(selected),
            "subjects": sorted(TARGET_SUBJECTS),
            "subject_calls_enabled": False,
            "timeout_seconds": 300,
            "max_retries": 1,
        }
        (OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
        with target_checkpoint.open("x") as stream:
            for event in retained:
                stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        print(f"Selected {len(selected)} Judge cells; all 480 answers retained.", flush=True)

    cases, subjects, judges, rule, _ = previous.prepare()
    return cases, subjects, judges, rule, target_checkpoint


def main():
    cases, subjects, judges, rule, checkpoint = prepare()
    os.environ["XIAOAN_PROVIDER_TIMEOUT"] = "300"
    os.environ["GLOBALAI_MAX_RETRIES"] = "1"
    rows = previous.old.mm.run_matrix(
        cases,
        subjects,
        judges,
        rating_rule=rule,
        subject_transport=previous.no_generation,
        judge_transport=previous.judge,
        checkpoint_path=checkpoint,
        resume=True,
        retry_unavailable=False,
        subject_concurrency=12,
        judge_concurrency=3,
        max_in_flight=12,
        per_provider_concurrency=2,
        isolate_self_judging=False,
    )
    previous.old.mm.write_matrix_workbook(rows, OUT / "results.xlsx")
    note = (
        "# 42 格 Judge 補評\n\n"
        "只補評 Claude/GPT/Gemini Subject 的 42 個 unavailable Judge cells；"
        "Qwen/Kimi 不呼叫，480 個 answers 凍結保留。\n\n"
    )
    (OUT / "report.md").write_text(note + previous.old.mm.render_matrix_report(rows))
    subprocess.run([sys.executable, str(HERE / "summarize.py"), str(OUT)], check=True)
    print(dict(Counter(row["status"] for row in rows)), flush=True)


if __name__ == "__main__":
    main()
