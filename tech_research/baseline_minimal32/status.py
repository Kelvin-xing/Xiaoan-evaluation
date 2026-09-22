"""Read a live checkpoint without showing private prompts or answers."""
import argparse
from collections import Counter
from datetime import datetime
import json
from pathlib import Path


def status(directory):
    answers, cells = {}, {}
    last = None
    path = directory / "checkpoint.jsonl"
    if path.exists():
        with path.open() as stream:
            for line in stream:
                try:
                    event = json.loads(line)
                except ValueError:
                    continue  # The writer may not yet have finished its last line.
                last = event.get("completed_at", last)
                if event["event"] == "answer":
                    aid = event["answer_id"]
                    answers[aid] = event["answer"]
                    cells = {key: row for key, row in cells.items() if key[0] != aid}
                elif event["event"] == "cell":
                    row = event["row"]
                    cells[(row["answer_id"], row["judge"]["id"])] = row
    def count(items):
        return dict(Counter(items))
    return {
        "answer_count": len(answers), "answer_status": count(a["status"] for a in answers.values()),
        "answers_by_provider": count(a["provider"] + ":" + a["status"] for a in answers.values()),
        "cell_count": len(cells), "cell_status": count(c["status"] for c in cells.values()),
        "judges_by_provider": count(c["judge"]["provider"] + ":" + c["status"] for c in cells.values()),
        "answer_errors": count(str(a.get("error")) for a in answers.values() if a["status"] != "PASS"),
        "judge_errors": count(str(c.get("judgement_error")) for c in cells.values() if c.get("judgement_error")),
        "last_checkpoint": datetime.fromtimestamp(last).isoformat(timespec="seconds") if last else None,
        "reports_written": (directory / "results.xlsx").exists() and (directory / "report.md").exists(),
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    print(json.dumps(status(args.directory), ensure_ascii=False, indent=2))
