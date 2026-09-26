"""Readable second-pass reports; semantic results and missingness stay separate."""
from __future__ import annotations

import json


def tables(result):
    evaluation = result.get("evaluation", result)
    cells, claims, requirements = [], [], []
    for cell in evaluation["cells"]:
        base = {k: cell[k] for k in ("subject_id", "judge_id", "case_id", "turn", "answer_id")}
        metrics = cell.get("metrics", {})
        gates = cell.get("requirements", {})
        cells.append({**base, "status": cell["status"],
                      "inventory_id": cell.get("inventory_id"), "reason": cell.get("reason"),
                      "safety_gate": gates.get("safety_gate"), "task_gate": gates.get("task_gate"),
                      "release_gate": gates.get("release_gate"),
                      **{f"{dim}_{key}": metrics.get(dim, {}).get(key)
                         for dim in ("faithfulness", "correctness")
                         for key in ("strict_rate", "known_support_rate", "known_coverage", "unknown_n", "eligible_n")}})
        for claim in cell.get("assessment", {}).get("claims", []):
            claims.append({**base, "inventory_id": cell["inventory_id"], "claim_id": claim["id"],
                           **{f"{dim}_{key}": claim.get(dim, {}).get(key) for dim in ("faithfulness", "correctness")
                              for key in ("verdict", "evidence", "reason")}})
        for req in gates.get("items", []):
            requirements.append({**base, **req})
    inventories = [{"inventory_id": inventory["inventory_id"], "answer_id": inventory["answer_id"], **claim}
                   for inventory in evaluation["inventories"] for claim in inventory["claims"]]
    return {"Cells": cells, "Inventory": inventories, "Claims": claims, "Requirements": requirements,
            "Conversations": evaluation["summary"]["conversations"], "Ablation": result.get("pairs", [])}


def markdown(result):
    evaluation = result.get("evaluation", result)
    summary = evaluation["summary"]
    lines = ["# XiaoAn unified evaluation", "", f'Contract: `{evaluation["contract"]}`', "",
             "Versioned second pass; not comparable to legacy binary or weighted attribution scores.", "",
             f'Planned cells: {summary["planned_cells"]}; available cells: {summary["available_cells"]}.', "",
             "Strict support uses all applicable claims, including UNKNOWN. Known support must be read with known coverage. "
             "SUPPORTIVE is excluded; recommendation/action truth is not applicable. Missing values are not zero.", ""]
    for name, rows in tables(result).items():
        if name not in {"Cells", "Conversations", "Ablation"} or not rows:
            continue
        columns = (["subject_id", "judge_id", "case_id", "turn", "status", "safety_gate", "task_gate",
                    "faithfulness_strict_rate", "correctness_known_coverage"] if name == "Cells"
                   else list(rows[0]))
        def show(value):
            if value is None: return "—"
            return str(value).replace("|", "\\|").replace("\n", " ")
        lines += [f"## {name}", "", "| " + " | ".join(columns) + " |",
                  "| " + " | ".join("---" for _ in columns) + " |"]
        lines += ["| " + " | ".join(show(row.get(k)) for k in columns) + " |" for row in rows]
        lines.append("")
    lines += ["Claim/evidence and requirement details are retained in measurement.json and measurement.xlsx.", "",
              "Release gates cover supplied approved requirements only. Extraction completeness, semantic validity, "
              "and real-world safety require independent human calibration. A higher support score is not proof of capsule causality.", ""]
    return "\n".join(lines)


def workbook(result, path):
    from openpyxl import Workbook
    wb = Workbook()
    wb.remove(wb.active)
    for name, rows in tables(result).items():
        sheet = wb.create_sheet(name)
        columns = list(dict.fromkeys(k for row in rows for k in row))
        if not columns:
            sheet.append(["No available observations"])
            continue
        sheet.append(columns)
        for row in rows:
            values = []
            for key in columns:
                value = row.get(key)
                if isinstance(value, (dict, list)):
                    value = json.dumps(value, ensure_ascii=False, allow_nan=False)
                if isinstance(value, str):
                    # Workbook text is untrusted model/user content, never formulas.
                    value = "".join(c for c in value if ord(c) >= 32 or c in "\n\t\r")
                    if value.startswith(("=", "+", "-", "@")):
                        value = "'" + value
                    value = value[:32767]  # JSON remains the complete source of record.
                values.append(value)
            sheet.append(values)
        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions
    wb.save(path)
