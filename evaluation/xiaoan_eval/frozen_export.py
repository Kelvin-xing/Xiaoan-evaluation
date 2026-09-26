"""Human-readable workbook views of a validated complete result; no model calls."""
from pathlib import Path
import json
from collections import defaultdict
from statistics import mean
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.table import Table, TableStyleInfo
from openpyxl.utils import get_column_letter
from xiaoan_eval_core.results import validate_complete_results
from xiaoan_eval_core.taxonomy import AXES

SHEETS = (
    "Overview", "Score Summary", "Routing Summary", "Coverage & Usage",
    "Case Eligibility", "Spec", "Answers", "Scores",
    "Claims", "Requirements", "Rating Details", "Human Review",
)

_DETAIL_SHEETS = ("Spec", "Answers", "Scores", "Claims", "Requirements", "Rating Details", "Human Review")
_SCORE_SCOPES = {"own_complete_cases"}
_SCORE_METRICS = {"rubric", "faithfulness", "correctness", "rubric_gate", "requirements_gate"}
_NAVY = "1F4E78"
_LIGHT = "F3F6F9"
_GREEN = "E2F0D9"
_YELLOW = "FFF2CC"
_RED = "F4CCCC"
_WHITE = "FFFFFF"
_BORDER = Side(style="thin", color="D9E1F2")


def _encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else value


def _config_summary(value):
    """Reader configuration excludes raw prompt/schema/context text recursively."""
    hidden = {"content", "instructions", "prompt", "schema", "context", "history", "raw", "response", "request", "aggregation_policy"}
    if isinstance(value, dict):
        return {k: _config_summary(v) for k, v in value.items() if k not in hidden}
    if isinstance(value, list):
        return [_config_summary(v) for v in value]
    return value


def _telemetry_columns(value):
    """Flatten call telemetry for the human-facing Scores sheet.

    The complete receipt remains in the source result/checkpoint.  Excel only
    needs the fields people compare while reviewing latency and usage.
    """
    if not isinstance(value, dict):
        return {
            "attempt_count": None,
            "attempt_ids": None,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "total_tokens": None,
            "reused_from": None,
        }
    attempts = value.get("attempts")
    attempts = attempts if isinstance(attempts, list) else []
    latencies = [item.get("latency_ms") for item in attempts if isinstance(item, dict) and item.get("latency_ms") is not None]
    usage = [item.get("usage", {}) for item in attempts if isinstance(item, dict) and isinstance(item.get("usage"), dict)]

    def total(name):
        values = [item.get(name) for item in usage if isinstance(item.get(name), (int, float))]
        return sum(values) if values else None

    return {
        "attempt_count": len(attempts),
        "attempt_ids": "; ".join(str(item.get("attempt_id")) for item in attempts if isinstance(item, dict) and item.get("attempt_id")),
        "latency_ms": "; ".join(f"{float(item):.0f}" for item in latencies) if latencies else None,
        "input_tokens": total("input_tokens"),
        "output_tokens": total("output_tokens"),
        "total_tokens": total("total_tokens"),
        "reused_from": value.get("reused_from"),
    }


def _count_statuses(value, statuses):
    if not isinstance(value, (dict, list)):
        return None
    items = value.values() if isinstance(value, dict) else value
    return sum(1 for item in items if isinstance(item, dict) and item.get("status") in statuses)


def project_results(result):
    validate_complete_results(result)
    if result["answers"] and "routing" not in result["aggregates"]:
        raise ValueError("routing aggregate missing; use refresh-derived-results before exporting")
    from .frozen_review import build_review_rows
    tables = {s: [] for s in SHEETS}
    tables["Human Review"] = build_review_rows(result)
    tables["Spec"].append({"section": "result", "field": "core_digest", "value": result["core_digest"], "json_pointer": "/core_digest"})
    receipts = {s.get("request_digest"): s for s in result.get("stages", [])}
    def telemetry(cell):
        receipt = receipts.get(cell.get("request_id", cell.get("assessment_request_id")), {})
        return {"attempts": [{"attempt_id": a.get("attempt_id"), "usage": a.get("usage"), "latency_ms": a.get("latency_ms")} for a in receipt.get("attempts", [])],
                "reused_from": receipt.get("reused_from")}

    for key in ("manifest", "plan"):
        for field, value in result[key].items():
            if "prompt" not in field and "schema" not in field and field != "aggregation_policy":
                tables["Spec"].append({"section": key, "field": field, "value": _config_summary(value), "json_pointer": f"/{key}/{field}"})
    answers = {a["answer_id"]: a for a in result["answers"]}
    inventories = {i["inventory_id"]: i for i in result["inventories"]}
    tables["Overview"] = list(result["aggregates"].get("metrics", []))
    routing=result['aggregates'].get('routing',{})
    routes={r['answer_id']:r for r in routing.get('details',[])}
    labels = routing.get('labels', {})
    for item in routing.get('summary', []):
        tables['Overview'].append({
            'section': '路由模式統計',
            **{k: v for k, v in item.items() if k not in ('matrix', 'row_labels', 'column_labels')},
        })
    costs=result['aggregates'].get('answer_costs',{})
    by_cost={r['answer_id']:r for r in costs.get('rows',[])}
    tables['Overview'].extend({'section':'官方定價回答成本估算',**r} for r in costs.get('summary',[]))
    for section in ("applicability", "usage", "citation_coverage"):
        tables["Overview"].extend({"section": section, **item} for item in result["aggregates"].get(section, []))

    # Keep the original wide Overview as a lossless audit view.  These rows are
    # projected into the narrow presentation sheets below, but never into
    # Score Summary unless they are one of the explicit score metrics.
    metrics = result["aggregates"].get("metrics", [])
    for scope, metric in sorted({(m.get("scope"), m.get("metric")) for m in metrics if m.get("scope") and m.get("metric")}):
        subset = [m for m in metrics if m.get("scope") == scope and m.get("metric") == metric]
        judges = sorted({m.get("judge_id") for m in subset if m.get("judge_id")})
        for kind in ("score", "effective/planned cases"):
            tables["Overview"].append({})
            header = {"metric": f"{scope} / {metric} / {kind}"}
            header.update(dict(zip(("scope", "subject_id", "judge_id", "value", "effective_cases"), judges)))
            tables["Overview"].append(header)
            for subject in sorted({m.get("subject_id") for m in subset if m.get("subject_id")}):
                lookup = {m.get("judge_id"): m for m in subset if m.get("subject_id") == subject}
                values = [
                    lookup[j].get("value") if kind == "score"
                    else f"{lookup[j].get('effective_cases')}/{lookup[j].get('planned_cases')}"
                    for j in judges
                ]
                row = {"metric": subject}
                row.update(dict(zip(("scope", "subject_id", "judge_id", "value", "effective_cases"), values)))
                tables["Overview"].append(row)

    tables["Overview"].append({})
    for item in routing.get('summary', []):
        columns = item.get('column_labels', [])
        values = [labels.get(column, column) for column in columns]
        header = {"metric": f"路由模式混淆矩陣｜{item.get('subject_id')}｜列：預期；欄：實際"}
        header.update(dict(zip(("scope", "subject_id", "judge_id", "value", "effective_cases", "excluded"), values)))
        tables['Overview'].append(header)
        for expected in item.get('row_labels', []):
            row = {"metric": labels.get(expected, expected)}
            counts = [item.get('matrix', {}).get(expected, {}).get(actual, 0) for actual in columns]
            row.update(dict(zip(("scope", "subject_id", "judge_id", "value", "effective_cases", "excluded"), counts)))
            tables['Overview'].append(row)
        footer = {
            "metric": "允許路由命中率",
            "scope": item.get('accepted_hit_rate'),
            "subject_id": "命中／可判定輪次",
            "judge_id": f"{item.get('accepted_hit_n')}/{item.get('accepted_evaluated_n')}",
            "value": "矩陣／計劃輪次",
            "effective_cases": f"{item.get('matrix_turns')}/{item.get('planned_turns')}",
        }
        tables['Overview'].append(footer)
    for index, envelope in enumerate(result["envelopes"]):
        a = answers[envelope["answer_id"]]
        base = {k: a.get(k) for k in ("case_id", "turn", "subject_id", "answer_id")}
        pointer = f"/envelopes/{index}"
        cost=by_cost.get(a['answer_id'],{})
        route=routes.get(a['answer_id'],{})
        tables["Answers"].append({**base, "question": a.get("question"), "answer": a.get("answer"), "status": a.get("status", a.get("availability")),
                                  "test_type": a.get("test_type"), "scenario_category": a.get("scenario_category"),
                                  "scenario_tags": a.get("scenario_tags"),
                                  "route": route.get('actual_route',a.get("route")),
                                  'expected_route':route.get('expected_route'),'expected_mode':route.get('expected_mode'),
                                  'actual_mode':route.get('actual_mode'),'accepted_route_hit':route.get('accepted_hit'),
                                  'route_exclusion_reason':route.get('exclusion_reason'),
                                  "time": a.get("telemetry", {}).get("started_at", a.get("started_at")),
                                  "latency_ms": a.get("telemetry", {}).get("elapsed_ms", a.get("latency_ms")),
                                  "input_tokens": a.get("usage", {}).get("input_tokens"), "output_tokens": a.get("usage", {}).get("output_tokens"),
                                  "total_tokens": a.get("usage", {}).get("total_tokens"), "relevancy": envelope["relevancy"].get("score"),
                                  "relevancy_status": envelope["relevancy"].get("status", "UNAVAILABLE"),
                                  'official_input_cost':cost.get('input_cost'),'official_output_cost':cost.get('output_cost'),
                                  'official_answer_cost':cost.get('total_cost'),'cost_currency':cost.get('currency'),
                                  'cost_status':cost.get('status'),'cost_reason':cost.get('reason'),
                                  'price_source':cost.get('rate',{}).get('source_url'),
                                  'cost_notes':cost.get('notes'), 'json_pointer': pointer})
        for j, cell in enumerate(envelope["rubric"]):
            r = cell.get("rubric", cell)
            tables["Scores"].append({**base, "judge_id": cell["judge_id"], "role": "rubric", "status": cell.get("status"), **{f"score:{dimension}": score for dimension, score in r.get("scores", {}).items()},
                                     "weighted_total": r.get("weighted_total"), **_telemetry_columns(telemetry(cell)), "gate": r.get("gate"), "reason": cell.get("reason"), "json_pointer": f"{pointer}/rubric/{j}"})
            for kind, details in (("dimension", r.get("dimension_details", [])), ("red_line", r.get("red_lines", []))):
                if isinstance(details, dict):
                    details = [{"id": k, **v} for k, v in details.items()]
                for detail in details:
                    tables["Rating Details"].append({**base, "judge_id": cell["judge_id"], "detail_type": kind, **detail, "json_pointer": f"{pointer}/rubric/{j}/rubric"})
        inventory = inventories.get(envelope.get("inventory_id"))
        for j, cell in enumerate(envelope["assessments"]):
            common = {**base, "judge_id": cell["judge_id"], "status": cell.get("status"), "reason": cell.get("reason"), "json_pointer": f"{pointer}/assessments/{j}"}
            metrics = cell.get("metrics")
            requirements = cell.get("requirements")
            tables["Scores"].append({
                **common,
                "role": "assessment",
                **_telemetry_columns(telemetry(cell)),
                "metrics_available_n": _count_statuses(metrics, {"AVAILABLE", "PASS", "ENTAILED", "SUPPORTED"}),
                "metrics_unknown_n": _count_statuses(metrics, {"UNKNOWN", "UNAVAILABLE", "NOT_APPLICABLE"}),
                "requirements_satisfied_n": _count_statuses(requirements, {"SATISFIED", "PASS"}),
                "requirements_unknown_n": _count_statuses(requirements, {"UNKNOWN", "UNAVAILABLE", "NOT_APPLICABLE"}),
            })
            assessment = cell.get("assessment", {})
            judged = {c["id"]: c for c in assessment.get("claims", [])}
            context = {u["ref"]: u for u in a.get("context", [])}
            truths = {u["ref"]: u for u in a.get("reference_facts", [])}
            if inventory:
                for claim in inventory["claims"]:
                    item = judged.get(claim["id"], {})
                    row = {**common, "inventory_id": inventory["inventory_id"], "claim_id": claim["id"], "claim": claim["proposition"], "kind": claim["kind"],
                           "conditions": claim.get("conditions"), "answer_quote": claim["answer_span"]["text"]}
                    for dim, catalog in (("faithfulness", context), ("correctness", truths)):
                        decision = item.get(dim, {})
                        row[dim] = decision.get("verdict")
                        row[dim + "_reason"] = decision.get("reason")
                        row[dim + "_evidence"] = [{**ev, "layer": catalog.get(ev["ref"], {}).get("layer")} for ev in decision.get("evidence", [])]
                    tables["Claims"].append(row)
            reqs = {r["id"]: r for r in a.get("requirements", [])}
            verdicts = {r["id"]: r for r in assessment.get("requirements", [])}
            for rid, req in reqs.items():
                tables["Requirements"].append({**common, **req, **verdicts.get(rid, {}), "source": "assessment"})
        for check in envelope["checks"]:
            tables["Requirements"].append({**base, **check, "source": "deterministic", "json_pointer": pointer + "/checks"})
    return tables


def _clean_excel_value(value):
    if isinstance(value, float):
        return float(format(value, ".6g"))
    return _encoded(value)


def _raw_rows(rows):
    fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status", "json_pointer"]
    return fields, [[_encoded(row.get(field)) for field in fields] for row in rows]


def _write_table(sheet, start_row, headers, rows, table_name, widths):
    for column, header in enumerate(headers, 1):
        cell = sheet.cell(start_row, column, header)
        cell.font = Font(bold=True, color=_WHITE)
        cell.fill = PatternFill("solid", fgColor=_NAVY)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for row_number, row in enumerate(rows, start_row + 1):
        for column, value in enumerate(row, 1):
            cell = sheet.cell(row_number, column, _clean_excel_value(value))
            if isinstance(cell.value, str):
                cell.data_type = "s"
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.border = Border(bottom=_BORDER)
            if row_number % 2 == 0:
                cell.fill = PatternFill("solid", fgColor=_LIGHT)
    if rows:
        end_row = start_row + len(rows)
        table = Table(displayName=table_name, ref=f"A{start_row}:{get_column_letter(len(headers))}{end_row}")
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
        sheet.add_table(table)
    for index, width in enumerate(widths, 1):
        sheet.column_dimensions[get_column_letter(index)].width = width


def _presentation_sheet(sheet, title, subtitle, freeze="A5"):
    sheet.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    sheet.cell(1, 1, title).font = Font(size=16, bold=True, color=_NAVY)
    sheet.cell(1, 1).alignment = Alignment(vertical="center")
    sheet.row_dimensions[1].height = 26
    sheet.merge_cells(start_row=2, start_column=1, end_row=2, end_column=5)
    sheet.cell(2, 1, subtitle).font = Font(size=10, color="666666", italic=True)
    sheet.cell(2, 1).alignment = Alignment(vertical="top", wrap_text=True)
    sheet.row_dimensions[2].height = 30
    sheet.freeze_panes = freeze
    sheet.sheet_view.showGridLines = False
    sheet.print_title_rows = "1:3"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True


def _style_detail_sheet(sheet):
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    sheet.print_title_rows = "1:1"
    sheet.page_setup.orientation = "landscape"
    sheet.page_setup.fitToWidth = 1
    sheet.page_setup.fitToHeight = 0
    sheet.sheet_properties.pageSetUpPr.fitToPage = True
    for cell in sheet[1]:
        cell.font = Font(bold=True, color=_WHITE)
        cell.fill = PatternFill("solid", fgColor=_NAVY)
        cell.alignment = Alignment(vertical="center", wrap_text=True)
    for column in range(1, sheet.max_column + 1):
        header = sheet.cell(1, column).value
        width = 48 if header in {"question", "answer", "evaluation_summary", "reason", "claim", "answer_quote", "faithfulness_reason", "correctness_reason", "text", "content"} else 18
        sheet.column_dimensions[get_column_letter(column)].width = width
        for row in range(2, sheet.max_row + 1):
            sheet.cell(row, column).alignment = Alignment(vertical="top", wrap_text=True)


def _presentation_rows(tables, result):
    raw_headers, raw_values = _raw_rows(tables["Overview"])
    aggregates = result["aggregates"]
    metric_rows = [row for row in aggregates.get("metrics", [])
                   if row.get("scope") in _SCORE_SCOPES or str(row.get("scope", "")).split(":", 1)[0] in AXES
                   if row.get("metric") in _SCORE_METRICS]
    routing_data = result["aggregates"].get("routing") or {"summary": []}
    route_stats = routing_data["summary"]
    applicability = aggregates.get("applicability", [])
    citation = aggregates.get("citation_coverage", [])
    usage = aggregates.get("usage", [])
    route_matrix = []
    for row in route_stats:
        for expected, actual in row.get("matrix", {}).items():
            route_matrix.append([row.get("subject_id"), routing_data.get("labels", {}).get(expected, expected), *(actual.get(mode, 0) for mode in
                                 ("CRISIS", "BASELINE", "CAPSULE", "SAFETY_CLARIFICATION", "UNKNOWN", "MISSING"))])

    answer_headers, answer_values = _raw_rows(tables["Answers"])
    answers = [dict(zip(answer_headers, row)) for row in answer_values]
    subjects = sorted({str(row.get("subject_id")) for row in answers if row.get("subject_id")})
    case_ids = sorted({str(row.get("case_id")) for row in answers if row.get("case_id")})
    judges = sorted({j["id"] for j in result["plan"].get("judges", [])})
    judges = sorted(set(judges) | {row["judge_id"] for row in metric_rows if row.get("judge_id")})
    suite = result["plan"].get("suite_id") or result["manifest"].get("suite_id") or "Evaluation"
    scope_name = case_ids[0] if len(case_ids) == 1 else suite
    title = f"{scope_name}｜{len(case_ids)} 案例｜{len(subjects)} Subject × {len(judges)} Judge 評估總覽"
    planned_judgements = sum(len(env["rubric"]) for env in result["envelopes"])
    summary = [
        ["案例範圍", ", ".join(case_ids) if len(case_ids) <= 4 else f"{len(case_ids)} 個選定案例（完整選集見 Spec）", f"{suite}；{len(answers)} 個 subject 回答輪次"],
        ["Subject", ", ".join(subjects), f"{sum(a.get('status') == 'AVAILABLE' for a in result['answers'])}/{len(answers)} 回答可用"],
        ["Judge", ", ".join(judges), f"{sum(c.get('status') == 'AVAILABLE' for env in result['envelopes'] for c in env['rubric'])}/{planned_judgements} rubric 可用"],
        ["Assessment", f"{sum(c.get('status') == 'AVAILABLE' for env in result['envelopes'] for c in env['assessments'])}/{sum(len(env['assessments']) for env in result['envelopes'])}", "可用／計劃 Judge assessment 格位"],
    ]
    by_metric = {(row["scope"], row["metric"], row["subject_id"], row["judge_id"]): row for row in metric_rows}
    def shown_score(row):
        if row is None:
            return "UNAVAILABLE"
        gates = row.get("gate_counts") or {}
        if row["metric"].endswith("_gate") and not (gates.get("PASS") or gates.get("FAIL")):
            return "NOT_APPLICABLE" if gates.get("NOT_APPLICABLE") == row.get("planned_cases") else "UNAVAILABLE"
        return row["value"] if row.get("value") is not None else "UNAVAILABLE"

    matrices = []
    metric_order = {name: index for index, name in enumerate(("rubric", "faithfulness", "correctness", "rubric_gate", "requirements_gate"))}
    def axis_detail(scope):
        return ("總體", "全部案例") if scope == "own_complete_cases" else tuple(scope.split(":", 1))

    def scope_sort(pair):
        axis, detail = axis_detail(pair[0])
        return (0 if axis == "總體" else list(AXES).index(axis) + 1,
                0 if axis == "總體" else AXES[axis].index(detail), metric_order[pair[1]])

    for scope, metric in sorted({(row["scope"], row["metric"]) for row in metric_rows},
                                key=scope_sort):
        scores, counts = [], []
        for subject in subjects:
            cells = [by_metric.get((scope, metric, subject, judge)) for judge in judges]
            scores.append([subject, *(shown_score(cell) for cell in cells)])
            counts.append([subject, *(f"{cell.get('effective_cases')}/{cell.get('planned_cases')}" if cell else "UNAVAILABLE" for cell in cells)])
        matrices.append((*axis_detail(scope), metric, scores, counts))
    score = [[row.get("subject_id"), row.get("judge_id"),
              *axis_detail(row["scope"]), row.get("metric"), shown_score(row),
              "AVAILABLE" if isinstance(shown_score(row), (int, float)) else shown_score(row),
              f"{row.get('effective_cases')}/{row.get('planned_cases')}", row.get("unknown_ratio"), _encoded(row.get("gate_counts")), row.get("formula")] for row in metric_rows]
    routing_summary = [[row.get("subject_id"), row.get("planned_turns"), row.get("matrix_turns"), row.get("accepted_hit_n"), row.get("accepted_evaluated_n"), row.get("accepted_hit_rate"), row.get("preferred_mode_accuracy"), row.get("actual_unknown_turns"), row.get("actual_missing_turns")] for row in route_stats]
    eligible = defaultdict(lambda: [0, 0])
    for row in applicability:
        pair = (row.get("subject_id"), row.get("judge_id"), row.get("metric"))
        eligible[pair][0] += row.get("eligible") is True
        eligible[pair][1] += 1
    coverage = [[subject, judge, metric, available, planned, f"{available}/{planned}"]
                for (subject, judge, metric), (available, planned) in sorted(eligible.items())]
    answer_subject = {row.get("answer_id"): row.get("subject_id") for row in answers}
    citation_groups = defaultdict(lambda: [0, 0, 0, 0])
    for row in citation:
        group = citation_groups[(answer_subject.get(row.get("answer_id")), row.get("judge_id"), row.get("layer") or "總計")]
        group[3] += 1
        if row.get("status") == "AVAILABLE":
            group[0] += 1
            group[1] += row.get("cited_occurrences") or 0
            group[2] += row.get("provided_occurrences") or 0
    citation_rows = [[subject, judge, layer, f"{available}/{planned}", cited if available else None,
                      provided if available else None, cited/provided if available and provided else None,
                      "AVAILABLE" if available == planned else "PARTIAL" if available else "UNAVAILABLE"]
                     for (subject, judge, layer), (available, cited, provided, planned) in sorted(citation_groups.items())]
    receipts = {attempt.get("attempt_id"): {"answer_id": receipt.get("answer_id"),
                "judge_id": receipt.get("identity", {}).get("id") if receipt.get("task") in {"rubric", "assess_claims"} else None}
                for receipt in result["stages"] for attempt in receipt.get("attempts", [])}
    usage_groups = defaultdict(lambda: {"attempts": 0, "reported": 0, "input": 0, "output": 0, "total": 0, "latency": []})
    for row in usage:
        receipt = receipts.get(row.get("attempt_id"), {})
        group = usage_groups[(answer_subject.get(receipt.get("answer_id")), receipt.get("judge_id"), row.get("task"))]
        group["attempts"] += 1
        values = row.get("usage") or {}
        if all(isinstance(values.get(name), (int, float)) for name in ("input_tokens", "output_tokens", "total_tokens")):
            group["reported"] += 1
            for name, key in (("input_tokens", "input"), ("output_tokens", "output"), ("total_tokens", "total")):
                group[key] += values[name]
        if isinstance(row.get("latency_ms"), (int, float)):
            group["latency"].append(row["latency_ms"])
    for answer in result["answers"]:
        group = usage_groups[(answer["subject_id"], None, "subject_answer")]
        group["attempts"] += 1
        values = answer.get("usage") or {}
        if all(isinstance(values.get(name), (int, float)) for name in ("input_tokens", "output_tokens", "total_tokens")):
            group["reported"] += 1
            for name, key in (("input_tokens", "input"), ("output_tokens", "output"), ("total_tokens", "total")):
                group[key] += values[name]
        latency = answer.get("telemetry", {}).get("elapsed_ms")
        if isinstance(latency, (int, float)):
            group["latency"].append(latency)
    usage_rows = [[subject, judge, task, group["attempts"], f"{group['reported']}/{group['attempts']}",
                   group["input"] if group["reported"] else None, group["output"] if group["reported"] else None,
                   group["total"] if group["reported"] else None,
                   mean(group["latency"]) if group["latency"] else None,
                   "AVAILABLE" if group["reported"] == group["attempts"] else "PARTIAL" if group["reported"] else "UNAVAILABLE"]
                  for (subject, judge, task), group in sorted(usage_groups.items(), key=lambda item: tuple(str(x or "") for x in item[0]))]
    taxonomy_by_case = {a["case_id"]: a for a in result["answers"]}
    eligibility = [[row.get("case_id"), taxonomy_by_case.get(row.get("case_id"), {}).get("test_type"),
                    taxonomy_by_case.get(row.get("case_id"), {}).get("scenario_category"),
                    taxonomy_by_case.get(row.get("case_id"), {}).get("scenario_tags"),
                    row.get("metric"), row.get("subject_id"), row.get("judge_id"), row.get("eligible"), row.get("denominator"), row.get("verdict_counts")] for row in applicability]
    return {
        "raw_headers": raw_headers, "raw_values": raw_values, "title": title, "summary": summary,
        "subjects": subjects, "judges": judges, "matrices": matrices,
        "score": score, "routing_summary": routing_summary, "matrix": route_matrix,
        "coverage": coverage, "citation": citation_rows, "usage": usage_rows, "eligibility": eligibility,
    }


def _build_presentation_workbook(tables, result):
    from .frozen_review import excel_display

    presentation = _presentation_rows(tables, result)
    book = Workbook()
    book.remove(book.active)

    overview = book.create_sheet("Overview")
    _presentation_sheet(overview, presentation["title"], "各指標按 Subject × Judge 展示；數值與有效／計劃案例分開，未取得結果保留 UNAVAILABLE。")
    _write_table(overview, 4, ["範圍", "內容", "覆蓋情況"], presentation["summary"], "tbl_overview_summary", [28, 52, 48])
    overview.row_dimensions[6].height = 44
    overview.row_dimensions[7].height = 32
    row = 4 + len(presentation["summary"]) + 3
    for index, (axis, detail, metric, values, counts) in enumerate(presentation["matrices"], 1):
        for column, value in enumerate((axis, detail, metric), 1):
            overview.cell(row, column, value).font = Font(size=12, bold=True, color=_NAVY)
        headers = ["Subject", *presentation["judges"]]
        widths = [28, *([24] * len(presentation["judges"]))]
        _write_table(overview, row + 1, headers, values, f"tbl_overview_value_{index}", widths)
        for value_row in range(row + 2, row + 2 + len(values)):
            for column in range(2, len(headers) + 1):
                if overview.cell(value_row, column).value == "UNAVAILABLE":
                    overview.cell(value_row, column).fill = PatternFill("solid", fgColor=_YELLOW)
        coverage_start = row + len(values) + 4
        overview.cell(coverage_start, 1, "有效／計劃案例").font = Font(bold=True, color=_NAVY)
        _write_table(overview, coverage_start + 1, headers, counts, f"tbl_overview_coverage_{index}", widths)
        row = coverage_start + len(counts) + 4

    score = book.create_sheet("Score Summary")
    _presentation_sheet(score, "評分摘要", "只展示品質 metric；其他診斷請查看主題工作表。")
    _write_table(score, 4, ["Subject", "Judge", "軸", "細分", "指標", "分數／比例", "狀態", "有效／計劃案例", "未知比例", "Gate 計數", "計算方式"], presentation["score"], "tbl_score_summary", [24, 24, 24, 28, 20, 16, 16, 18, 14, 20, 34])

    routing = book.create_sheet("Routing Summary")
    _presentation_sheet(routing, "路由摘要", "整體命中率、模式混淆矩陣與計劃覆蓋分開呈現。")
    _write_table(routing, 4, ["模型", "計劃輪次", "矩陣輪次", "允許命中", "可判定輪次", "允許命中率", "首選準確率", "未知路由", "缺失路由"], presentation["routing_summary"], "tbl_routing_summary", [24, 12, 12, 12, 14, 16, 16, 12, 12])
    matrix_start = 4 + len(presentation["routing_summary"]) + 3
    _write_table(routing, matrix_start, ["Subject", "預期模式／實際模式", "危機模式", "基礎回應", "場景膠囊", "安全澄清", "未知路由", "缺失路由"], presentation["matrix"], "tbl_routing_matrix", [24, 24, 16, 16, 16, 16, 16, 16])

    coverage = book.create_sheet("Coverage & Usage")
    _presentation_sheet(coverage, "覆蓋率與執行用量", "按 Subject／Judge 彙總；逐案例資料見 Case Eligibility、Answers 與 Scores。")
    _write_table(coverage, 4, ["Subject", "Judge", "指標", "可納入案例", "計劃案例", "覆蓋"], presentation["coverage"], "tbl_applicability", [24, 24, 22, 18, 18, 18])
    citation_start = 4 + len(presentation["coverage"]) + 3
    _write_table(coverage, citation_start, ["Subject", "Judge", "層", "可用／計劃", "已引用", "可引用", "覆蓋率", "狀態"], presentation["citation"], "tbl_citation_coverage", [24, 24, 20, 18, 14, 14, 14, 16])
    usage_start = citation_start + len(presentation["citation"]) + 3
    _write_table(coverage, usage_start, ["Subject", "Judge", "任務", "呼叫／回答數", "Token 記錄數", "已報告輸入", "已報告輸出", "已報告總量", "平均延遲（毫秒）", "用量狀態"], presentation["usage"], "tbl_usage", [24, 24, 24, 18, 18, 18, 18, 18, 22, 16])

    eligibility = book.create_sheet("Case Eligibility")
    _presentation_sheet(eligibility, "案例納入與可評資格", "這張表回答哪些案例被納入哪個指標；不可用、未知或不適用不轉成低分。")
    _write_table(eligibility, 4, ["案例", "test_type", "scenario_category", "scenario_tags", "指標", "Subject", "Judge", "可納入", "分母", "Verdict 計數"], presentation["eligibility"], "tbl_case_eligibility", [16, 20, 24, 48, 20, 24, 24, 14, 12, 48])

    for name in _DETAIL_SHEETS:
        sheet = book.create_sheet(name)
        rows = tables[name]
        fields = list(dict.fromkeys(key for row in rows for key in row)) or ["status", "json_pointer"]
        sheet.append(fields)
        for record in rows:
            sheet.append([
                excel_display(_encoded(record.get(field)), record.get("json_pointer", "/"))
                for field in fields
            ])

    for sheet in book.worksheets:
        for row in sheet.iter_rows():
            for cell in row:
                if isinstance(cell.value, str):
                    cell.data_type = "s"

    for sheet in book.worksheets:
        if sheet.title in {"Overview", "Score Summary", "Routing Summary", "Coverage & Usage", "Case Eligibility"}:
            continue
        _style_detail_sheet(sheet)
    book.properties.title = presentation["title"]
    book.properties.description = "Readable evaluation workbook; routing diagnostics are separate from score summary."
    return book


def export_results_workbook(result, path):
    path = Path(path)
    if path.exists():
        old = load_workbook(path, read_only=True, data_only=False)
        try:
            if "Human Review" in old:
                it = old["Human Review"].iter_rows(values_only=True)
                headers = next(it, ())
                editable = [i for i, h in enumerate(headers) if h in {"decision", "notes", "reviewer", "reviewed_at", "revisions_json"}]
                if any(any(row[i] is not None for i in editable) for row in it):
                    raise ValueError("existing workbook contains human edits; preserve/import it before rebuilding")
        finally:
            old.close()
    tables = project_results(result)
    book = _build_presentation_workbook(tables, result)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp.xlsx")
    book.save(temp)
    verified = load_workbook(temp, read_only=True)
    if tuple(verified.sheetnames) != SHEETS:
        raise ValueError("workbook sheet verification failed")
    verified.close()
    temp.replace(path)
    return path
