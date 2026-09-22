"""Export readable baseline summaries from the existing checkpoint (no API calls)."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path
from statistics import mean, median

import run
from xiaoan_eval.multimodel import _resume_row, _spec_id, matrix_pair_summary
from xiaoan_eval.oracle_judge import summarize as oracle_summary


def load_rows(path):
    answers, judges, cells = {}, {}, {}
    with path.open() as stream:
        for line in stream:
            event = json.loads(line)
            kind = event["event"]
            if kind == "answer":
                aid = event["answer_id"]
                answers[aid] = event
                judges = {key: value for key, value in judges.items() if key[0] != aid}
                cells = {key: value for key, value in cells.items() if key[0] != aid}
            elif kind == "judgement":
                judges[event["answer_id"], _spec_id(event["judge"])] = event
            elif kind == "cell":
                row = event["row"]
                cells[row["answer_id"], row["judge"]["id"]] = row
    rows = [_resume_row(answers[aid], judges.get((aid, jid)), row)
            for (aid, jid), row in cells.items()]
    return answers, judges, rows


def write_csv(path, headers, records):
    def safe(value):
        return "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(headers)
        writer.writerows([safe(value) for value in row] for row in records)


def display(value):
    return "UNAVAILABLE" if value is None else f"{value:.4f}"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    out = args.directory
    manifest = json.loads((out / "manifest.json").read_text())
    answers, judges, rows = load_rows(out / "checkpoint.jsonl")
    providers = [s["provider"] for s in manifest["subjects"]]
    judge_providers = [s["provider"] for s in manifest["judges"]]
    completed = len(answers) == manifest["subject_calls"] and len(rows) == manifest["judge_calls_upper_bound"]
    status = "完整執行紀錄" if completed else "部分結果（執行未完成）"
    lines = [f"# {len(manifest['cases'])} 案裸模型 {len(providers)}×{len(judge_providers)} 基準：{status}", "",
             "矩陣包含對角線自評；分數為 0–3。每格先計完整案例分數，再對案例取平均。",
             "紅線觸發的完整案例為 0；缺輪／呼叫失敗排除分母，不補零。", "",
             f"回答：{len(answers)}/{manifest['subject_calls']}；評分格：{len(rows)}/{manifest['judge_calls_upper_bound']}。",
             f"回答狀態：{dict(Counter(e['answer']['status'] for e in answers.values()))}。",
             f"評分狀態：{dict(Counter(r['status'] for r in rows))}。", "",
             "## Subject × Judge", "",
             "| 回答模型 / Judge | " + " | ".join(judge_providers) + " |",
             "| --- | " + " | ".join("---:" for _ in judge_providers) + " |"]
    matrix, coverage, oracle_pairs = [], [], []
    for subject in providers:
        values = []
        for judge in judge_providers:
            selected = [r for r in rows if r["subject"]["provider"] == subject and r["judge"]["provider"] == judge]
            score = matrix_pair_summary(selected)
            values.append(score["value"])
            good = [r for r in selected if r["status"] == "PASS"]
            cases = {}
            for row in selected:
                cases.setdefault(row["case_id"], []).append(row)
            complete_cases = sum(len(rs) == len(rs[0]["expected_turns"]) and all(r["status"] == "PASS" for r in rs) for rs in cases.values())
            coverage.append([subject, judge, complete_cases, len(manifest["cases"]), len(good), len(selected), sum(bool(r["triggered_red_lines"]) for r in good)])
            eligible = [r for r in selected if r.get("coverage", {}).get("oracle_approved")]
            semantic = oracle_summary([r.get("oracle_assessment") if r["status"] == "PASS" else None for r in eligible])
            oracle_pairs.append({"subject": subject, "judge": judge, **semantic})
        matrix.append([subject, *values])
        lines.append("| " + subject + " | " + " | ".join(map(display, values)) + " |")
    write_csv(out / "matrix.csv", ["subject / judge", *judge_providers], matrix)
    write_csv(out / "pair_coverage.csv", ["subject", "judge", "complete_cases", "expected_cases", "valid_turns", "recorded_turns", "red_line_turns"], coverage)
    lines += ["", "## 每格有效案例數（滿額 32）", "", "| Subject | " + " | ".join(judge_providers) + " |", "| --- | " + " | ".join("---:" for _ in judge_providers) + " |"]
    for subject in providers:
        lines.append("| " + subject + " | " + " | ".join(str(r[2]) for r in coverage if r[0] == subject) + " |")
    oracle_records = []
    for row in rows:
        assessment = row.get("oracle_assessment") or {}
        for item in assessment.get("items", []):
            oracle_records.append([row["subject"]["provider"], row["judge"]["provider"], row["case_id"], row["turn"], assessment.get("status"), item["id"], item["kind"], item["verdict"], item["reason"], json.dumps(item.get("spans", []), ensure_ascii=False)])
    write_csv(out / "semantic_oracle.csv", ["subject", "judge", "case", "turn", "status", "claim_id", "kind", "verdict", "reason", "answer_spans"], oracle_records)
    (out / "semantic_oracle_summary.json").write_text(json.dumps(oracle_pairs, ensure_ascii=False, indent=2))
    usage = []
    for role, artifacts in [("subject", [e["answer"] for e in answers.values()]), ("judge", [e["judgement"] for e in judges.values()])]:
        for provider in providers:
            selected = [a for a in artifacts if a["provider"] == provider]
            times = [a["elapsed_ms"] / 1000 for a in selected if a.get("elapsed_ms") is not None and a["status"] == "PASS"]
            totals = [a["total_tokens"] for a in selected if a.get("total_tokens") is not None]
            usage.append([role, provider, len(selected), sum(a["status"] == "PASS" for a in selected), sum(totals) if totals else None, len(totals), mean(times) if times else None, median(times) if times else None])
    write_csv(out / "usage_summary.csv", ["role", "provider", "retained_calls", "pass", "reported_tokens", "calls_with_token_data", "mean_success_seconds", "median_success_seconds"], usage)
    lines += ["", "## 其他指標與閱讀位置", "",
              "- `results.xlsx`：七維度、Judge 一致性、紅線一致性、分數分布、原始回答及評分。",
              "- `semantic_oracle.csv`：逐條 required/forbidden claim 的滿足、違反、不確定判定及答案證據。",
              "- `semantic_oracle_summary.json`：各 Subject × Judge 的要求滿足率、禁止內容違反率及缺失數。",
              "- `pair_coverage.csv`：每格有效案例及輪次、紅線輪次數。",
              "- `usage_summary.csv`：目前保留呼叫的 token 及耗時；未回傳用量或被替代重試的消耗不包含，不能當完整帳單。", "",
              "## 解讀限制", "",
              "無 system prompt、capsule、wiki、檢索或工具。僅同案 user/assistant 多輪歷史。",
              "未計算 Faithfulness、Answer Relevancy；沒有獨立查證法律/資源時效。",
              "自評已納入矩陣；一致性統計仍依原框架使用 non-self 觀察。",
              "模型、端點、推理強度、token 預算見 manifest.json 及 run-settings.json；這是這組設定下的描述性基準，不代表一般能力排名。", ""]
    (out / "summary.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved summary and CSV metrics; answers={len(answers)}, cells={len(rows)}, complete={completed}")


if __name__ == "__main__":
    main()
