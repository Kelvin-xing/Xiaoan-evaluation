"""Inventory sealed Minimal33 runs without conflating frozen experiment versions."""
from __future__ import annotations

from collections import Counter, defaultdict
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))
from xiaoan_eval_core.results import validate_complete_results  # noqa: E402
from xiaoan_eval_core.contracts import digest as contract_digest  # noqa: E402


def count(values):
    return dict(sorted(Counter(values).items()))


def audit(runs):
    groups = defaultdict(lambda: {"answers": {}, "rubric": {}, "assessments": {},
                                  "relevancy": {}, "inventories": {}, "runs": [], "judges": set()})
    summaries = []
    positions = defaultdict(list)
    for folder in sorted(runs.glob("minimal33*")):
        path = folder / "results.json"
        if not path.is_file() and not (folder / "plan.json").is_file() and not (folder / "subject-checkpoint").is_dir():
            continue
        if not path.is_file():
            plan_path = folder / "plan.json"
            plan = json.loads(plan_path.read_text(encoding="utf-8")) if plan_path.is_file() else None
            lanes = list((folder / "subject-checkpoint").glob("[0-9a-f]" * 64 + ".json"))
            saved = []
            for lane in lanes:
                rows = json.loads(lane.read_text(encoding="utf-8"))
                if not isinstance(rows, list) or not rows:
                    raise ValueError(f"Invalid subject lane: {lane}")
                for row in rows:
                    if row.get("manifest_digest") != plan["manifest"]["manifest_digest"]:
                        raise ValueError(f"Subject lane manifest mismatch: {lane}")
                    import hashlib
                    expected = hashlib.sha256(row["answer"].encode()).hexdigest() if isinstance(row.get("answer"), str) else None
                    if row.get("answer_sha256") != expected:
                        raise ValueError(f"Subject lane answer hash mismatch: {lane}")
                    if row.get("row_digest") != contract_digest({k: v for k, v in row.items() if k != "row_digest"}):
                        raise ValueError(f"Subject lane row digest mismatch: {lane}")
                saved.extend(rows)
            if len({row["answer_id"] for row in saved}) != len(saved):
                raise ValueError(f"Duplicate subject lane answer: {folder}")
            summaries.append({"run": folder.name, "sealed_results": False,
                              "manifest_digest": plan["manifest"]["manifest_digest"] if plan else None,
                              "checkpoint_files": sum(1 for _ in folder.glob("checkpoint/*.json")),
                              "verified_subject_lanes": len(lanes),
                              "verified_subject_rows": count(row["status"] for row in saved),
                              "subject_progress_files": sum(1 for _ in folder.glob("subject-checkpoint/*.progress.json")),
                              "raw_subject_files": sum(1 for _ in folder.glob("subject-checkpoint/*.raw.json"))})
            for row in saved:
                if row["status"] == "AVAILABLE":
                    positions[(row["case_id"], row["turn"], row["subject_id"])].append(
                        (row["manifest_digest"], row["answer_id"], row["answer_sha256"]))
            continue
        result = validate_complete_results(json.loads(path.read_text(encoding="utf-8")))
        digest = result["manifest"]["manifest_digest"]
        group = groups[digest]
        group["runs"].append(folder.name)
        group["judges"].update(x["id"] for x in result["plan"]["judges"])
        answers = result["answers"]
        rubric = [cell for env in result["envelopes"] for cell in env["rubric"]]
        assessments = [cell for env in result["envelopes"] for cell in env["assessments"]]
        relevancy = [env["relevancy"] for env in result["envelopes"]]
        summaries.append({"run": folder.name, "sealed_results": True,
                          "manifest_digest": digest, "generation": result["result_generation"],
                          "subjects": [x["id"] for x in result["plan"]["subjects"]],
                          "judges": [x["id"] for x in result["plan"]["judges"]],
                          "answers": count(x["status"] for x in answers),
                          "inventories": len(result["inventories"]),
                          "rubric": count(x["status"] for x in rubric),
                          "assessments": count(x["status"] for x in assessments),
                          "relevancy": count(x.get("status") for x in relevancy)})
        for answer in answers:
            key = answer["answer_id"]
            previous = group["answers"].get(key)
            if previous is not None and previous["row_digest"] != answer["row_digest"]:
                raise ValueError(f"Conflicting frozen answer: {key}")
            group["answers"][key] = answer
            if answer["status"] == "AVAILABLE":
                positions[(answer["case_id"], answer["turn"], answer["subject_id"])].append(
                    (digest, key, answer["answer_sha256"]))
        for inventory in result["inventories"]:
            key = inventory["answer_id"]
            previous = group["inventories"].get(key)
            if previous is not None and previous != inventory["inventory_id"]:
                raise ValueError(f"Conflicting inventory: {key}")
            group["inventories"][key] = inventory["inventory_id"]
        for name, cells in (("rubric", rubric), ("assessments", assessments), ("relevancy", relevancy)):
            for cell in cells:
                if cell.get("status") not in {"AVAILABLE", "PARTIAL"}:
                    continue
                key = (cell["answer_id"], cell.get("judge_id"))
                previous = group[name].get(key)
                if previous is not None and previous != cell:
                    raise ValueError(f"Conflicting {name} cell: {key}")
                group[name][key] = cell
    cohorts = []
    for manifest, group in groups.items():
        answers = group["answers"]
        available = {key for key, row in answers.items() if row["status"] == "AVAILABLE"}
        cohorts.append({"manifest_digest": manifest, "runs": group["runs"],
                        "answers_available": len(available), "answers_planned": len(answers),
                        "inventories": len(group["inventories"]),
                        "rubric_available": len(group["rubric"]),
                        "assessments_available": len(group["assessments"]),
                        "relevancy_available": len(group["relevancy"]),
                        "complete_judge_cells": sum(
                            (key in group["rubric"] and key in group["assessments"])
                            for key in group["rubric"].keys() | group["assessments"].keys()),
                        "missing_subjects": count(row["subject_id"] for row in answers.values()
                                                  if row["status"] != "AVAILABLE"),
                        "missing_rubric_by_judge": {
                            judge: sum((aid, judge) not in group["rubric"] for aid in available)
                            for judge in sorted(group["judges"])},
                        "missing_assessments_by_judge": {
                            judge: sum((aid, judge) not in group["assessments"] for aid in available)
                            for judge in sorted(group["judges"])}})
    cross = {key: entries for key, entries in positions.items()
             if len({entry[0] for entry in entries}) > 1}
    return {"runs": summaries, "cohorts": sorted(cohorts, key=lambda x: x["manifest_digest"]),
            "cross_manifest": {"overlapping_positions": len(cross),
                               "different_answer_text": sum(len({e[2] for e in entries}) > 1
                                                            for entries in cross.values())}}


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--runs", type=Path, default=ROOT / "evaluation_multimodels/runs")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        parser.error("output exists; choose a new immutable path")
    report = audit(args.runs)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
