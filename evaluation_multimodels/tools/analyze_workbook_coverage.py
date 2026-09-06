"""Emit privacy-safe aggregate topic signals from the consultation workbook."""
from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import re

import openpyxl


TOPIC_PATTERNS = {
    "immediate_danger_or_injury": r"报警|110|殴打|打伤|掐|刀|威胁|生命|危险",
    "protection_order": r"保护令|人身安全",
    "divorce_procedure": r"离婚|起诉|诉讼|调解|冷静期",
    "evidence_preservation": r"证据|录音|录像|病历|报警记录|伤情|鉴定|告诫书",
    "child_custody_or_visitation": r"抚养|孩子|子女|探望|监护",
    "property_or_asset_transfer": r"财产|房产|存款|转移|共同财产|债务",
    "economic_control_or_support": r"生活费|经济|收入|扶养|不给钱",
    "compensation": r"赔偿|损害赔偿|补偿",
    "sexual_violence": r"强奸|性暴力|强迫.*性|性侵",
    "mental_violence_or_control": r"精神暴力|辱骂|侮辱|控制|冷暴力|威胁",
    "cohabiting_or_unmarried": r"同居|未婚|恋爱关系|男友|女友",
    "cross_border": r"国外|境外|外国|跨国|英文|公证|认证",
    "sexual_or_gender_minority": r"LGBT|同性|跨性别|性取向",
    "minor": r"未成年|学校|老师|学生|儿童|孩子",
    "older_person": r"老人|老年|七十|六十|退休",
    "disability_or_illness": r"残疾|残障|精神病|疾病|抑郁",
    "referral": r"妇联|法律援助|律师|派出所|公安|法院|社区|庇护",
}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    payload = analyze(args.workbook)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    if args.output:
        args.output.write_text(text, encoding="utf-8")
    else:
        print(text, end="")
    return 0


def analyze(path: Path) -> dict[str, object]:
    workbook = openpyxl.load_workbook(path, read_only=True, data_only=True)
    sheet = workbook.active
    rows = sheet.iter_rows(values_only=True)
    headers = {str(value): index for index, value in enumerate(next(rows))}
    required = {"案由", "咨询内容", "法律建议"}
    missing = required - set(headers)
    if missing:
        raise ValueError(f"workbook missing columns: {sorted(missing)}")

    visitor = Counter()
    advice = Counter()
    row_count = 0
    compiled = {
        topic: re.compile(pattern, re.IGNORECASE)
        for topic, pattern in TOPIC_PATTERNS.items()
    }
    for row in rows:
        row_count += 1
        visitor_text = " ".join(
            str(row[headers[column]] or "") for column in ("案由", "咨询内容")
        )
        advice_text = str(row[headers["法律建议"]] or "")
        for topic, pattern in compiled.items():
            visitor[topic] += bool(pattern.search(visitor_text))
            advice[topic] += bool(pattern.search(advice_text))

    return {
        "schema_version": "1.0",
        "row_count": row_count,
        "method": {
            "visitor_signal_columns": ["案由", "咨询内容"],
            "advice_signal_columns": ["法律建议"],
            "counts_are_overlapping": True,
            "row_content_emitted": False,
        },
        "visitor_topic_signals": dict(visitor),
        "advice_topic_signals": dict(advice),
    }


if __name__ == "__main__":
    raise SystemExit(main())
