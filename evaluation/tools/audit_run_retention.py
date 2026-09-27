"""Audit Minimal33 run generations before pruning intermediate artifacts."""
from __future__ import annotations

from collections import Counter
from hashlib import sha256
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))
from xiaoan_eval_core.results import validate_complete_results  # noqa: E402


def digest_file(path):
    value = sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def inventory(folder):
    kinds = Counter()
    bytes_used = 0
    files = 0
    for root, _, names in os.walk(folder):
        for name in names:
            path = Path(root) / name
            if path.is_symlink():
                raise ValueError(f"Symlink in run: {path}")
            size = path.stat().st_size
            bytes_used += size
            files += 1
            kinds[f"{path.relative_to(folder).parts[0] if len(path.relative_to(folder).parts) > 1 else name}"] += 1
    return {"files": files, "bytes": bytes_used, "file_groups": dict(sorted(kinds.items()))}


def available_cells(result):
    answers = {row["answer_id"]: row["row_digest"] for row in result["answers"]}
    cells = {}
    for env in result["envelopes"]:
        aid = env["answer_id"]
        for branch in ("rubric", "assessments"):
            cells.update({(branch, aid, cell["judge_id"]): cell["status"] for cell in env[branch]
                          if cell["status"] in {"AVAILABLE", "PARTIAL"}})
        if env["relevancy"].get("status") == "AVAILABLE":
            cells[("relevancy", aid, "")] = "AVAILABLE"
    return answers, cells


def audit(runs, keep):
    folders = sorted(folder for folder in runs.iterdir() if folder.is_dir())
    entries = {}
    retained = {}
    for folder in folders:
        entry = inventory(folder)
        result_path = folder / "results.json"
        if result_path.exists():
            result = validate_complete_results(json.loads(result_path.read_text()))
            entry.update({"sealed": True, "result_sha256": digest_file(result_path),
                          "generation": result["result_generation"],
                          "manifest": result["manifest"]["manifest_digest"],
                          "cases": result["plan"]["case_ids"],
                          "subjects": [item["id"] for item in result["plan"]["subjects"]],
                          "judges": [item["id"] for item in result["plan"]["judges"]],
                          "answer_status": dict(Counter(row["status"] for row in result["answers"])),
                          "rubric_status": dict(Counter(cell["status"] for env in result["envelopes"]
                                                        for cell in env["rubric"])),
                          "assessment_status": dict(Counter(cell["status"] for env in result["envelopes"]
                                                            for cell in env["assessments"]))})
            if folder.name in keep:
                retained[folder.name] = available_cells(result)
        else:
            entry["sealed"] = False
        entries[folder.name] = entry

    for folder in folders:
        if folder.name in keep or not entries[folder.name]["sealed"]:
            continue
        result = validate_complete_results(json.loads((folder / "results.json").read_text()))
        answers, cells = available_cells(result)
        preserved_answers = {}
        preserved_cells = {}
        for retained_answers, retained_cells in retained.values():
            preserved_answers.update(retained_answers)
            for key, status in retained_cells.items():
                if status == "AVAILABLE" or key not in preserved_cells:
                    preserved_cells[key] = status
        conflicts = sorted(aid for aid in answers.keys() & preserved_answers.keys()
                           if answers[aid] != preserved_answers[aid])
        entry = entries[folder.name]
        entry["same_answer_conflicts"] = conflicts[:8]
        entry["unique_answer_ids"] = len(answers.keys() - preserved_answers.keys())
        entry["unique_available_cells"] = sum(status == "AVAILABLE" and
                                                preserved_cells.get(key) != "AVAILABLE"
                                                for key, status in cells.items())
        entry["unique_partial_cells"] = sum(status == "PARTIAL" and key not in preserved_cells
                                              for key, status in cells.items())
    return {"retained": sorted(keep), "runs": entries}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, required=True)
    parser.add_argument("--keep", nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists")
    report = audit(args.runs, set(args.keep))
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(f"Validated {sum(v['sealed'] for v in report['runs'].values())} sealed results; "
          f"indexed {len(report['runs'])} run directories")
