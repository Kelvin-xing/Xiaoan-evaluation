"""Export verified frozen minimal32 metrics for the normal report CLI (offline).

This is a diagnostic selection, not a new run. Historical artifacts are read-only.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "evaluation"))
from xiaoan_eval.scenario_analysis import binding, digest


def read(path):
    return json.loads(path.read_text())


def main():
    runs = ROOT / "evaluation/runs"
    metric_dir = runs / "2026-09-15-minimal32-answer-metrics"
    output = runs / "2026-09-21-minimal32-scenario-analysis"
    selected = read(runs / "2026-09-14-minimal32-regression/diagnostic-selected-turns.json")
    tasks = {(x["task"]["case_id"], x["task"]["turn"]): x for x in read(metric_dir / "relevancy-tasks.json")}
    scores = {(x["case_id"], x["turn"]): x for x in read(metric_dir / "answer-relevancy-scores.json")}
    sources = {}
    for name in sorted({x["answer_attempt"] for x in selected}):
        sources[name] = {x["case_id"]: x for x in read(runs / name / "case-results.json")}
    records, results = {}, []
    for row in selected:
        case, turn = row["case_id"], row["turn"]
        key = case, turn
        if case not in records:
            records[case] = copy.deepcopy(sources[row["answer_attempt"]][case])
            manifest = read(runs / ("." + row["answer_attempt"] + ".private") / "manifest.json")
            records[case]["subject_id"] = manifest["models"]["XIAOAN_RESPONSE_MODEL"]
            records[case]["analysis_provenance"] = {
                "selection": "frozen_case_coherent_diagnostic",
                "answer_attempt": row["answer_attempt"],
                "analysis_date": "2026-09-21",
            }
            records[case]["pipeline"]["planned_turns"] = [
                {"turn": r["turn"], "user_input": r["user"]}
                for r in selected if r["case_id"] == case
            ]
        record = records[case]
        assert record["analysis_provenance"]["answer_attempt"] == row["answer_attempt"]
        if row["execution"] != "ANSWERED":
            continue
        conversation = next(t for t in record["conversation"]["turns"] if t["turn"] == turn)
        assert conversation["assistant_response"] == row["answer"]
        trace = next(t["trace"] for t in record["pipeline"]["turn_traces"] if t["turn"] == turn)
        snapshot = trace["effective_context_snapshot"]
        assert snapshot["snapshot_id"] == row["snapshot_id"]
        subject = trace["models"]["response"]
        assert subject == record["subject_id"]
        task, score = tasks[key]["task"], scores[key]
        assert tasks[key]["binding"] == score["binding"] == digest(task)
        assert task["original_question"] == row["user"]
        assert task["generation_input"]["answer"] == row["answer"]
        assert task["answer_sha256"] == hashlib.sha256(row["answer"].encode()).hexdigest()
        assert task["snapshot_id"] == snapshot["snapshot_id"]
        generation = read(runs / ".2026-09-15-minimal32-answer-relevancy.private" / f"{case}-T{turn}.json")
        assert generation["binding"] == score["binding"]
        assert score["status"] == "AVAILABLE" and len(generation["questions"]) == task["n"]
        results.append({
            "case_id": case, "turn": turn, "subject_id": subject,
            "binding": binding(case, turn, subject, row["answer"], snapshot),
            "provenance": {"answer_attempt": row["answer_attempt"], "generation_binding": score["binding"]},
            "answer_relevancy": {
                **score, "questions": generation["questions"],
                "generator_model": task["generator_model"],
                "prompt_version": task["generator_prompt_version"],
                "query_mode": task["query_mode"],
            },
        })
        attribution = read(runs / ("." + row["answer_attempt"] + "-attribution.private") / f"{case}-T{turn}.json")
        assert row["judge_validated"] and row["independent_attribution_valid"]
        assert attribution["status"] == "AVAILABLE"
        assert attribution["snapshot_id"] == snapshot["snapshot_id"]
        assert attribution["answer_sha256"] == task["answer_sha256"]
        for claim in attribution["assessment"]["claims"]:
            span = claim["answer_span"]
            assert row["answer"][span["start"]:span["end"]] == span["text"]
        observation = next(x for x in record["pipeline"]["observations"] if x["turn"] == turn)
        observation["judge"]["faithfulness_claims"] = row["faithfulness_claims"]
        observation["judge"]["oracle_assessment"] = row["oracle_assessment"]
        observation["attribution"] = {
            **attribution["assessment"], "status": "AVAILABLE",
            "snapshot_id": attribution["snapshot_id"], "answer_sha256": attribution["answer_sha256"],
            "provenance": "frozen_validated_independent_attribution",
        }
    assert len(results) == 89 and len(records) == 32
    output.mkdir(parents=True, exist_ok=True)
    (output / "answer-analysis.json").write_text(json.dumps({"schema_version": "answer-analysis/v1", "results": results}, ensure_ascii=False, indent=2))
    (output / "diagnostic-case-results.jsonl").write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records.values()))
    print(f"Exported {len(results)} bound scores and {len(records)} frozen case records to {output}")


if __name__ == "__main__":
    main()
