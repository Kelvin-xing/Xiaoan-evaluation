"""Render and publish the two-file evaluation deliverable pair."""

from __future__ import annotations

from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Mapping, Sequence

from .report_model import ReportModel
from .workbook import read_workbook, write_workbook


PUBLIC_FILES = frozenset({"results.xlsx", "report.md"})


def validate_output_target(output: Path) -> None:
    """Fail before expensive work when an output directory is not safely reusable."""
    _validate_public_directory(output)


def publish_deliverables(model: ReportModel, output: Path, report_text: str) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / f".{output.name}.evaluation.lock"
    journal_path = output.parent / f".{output.name}.evaluation-journal.json"
    with _locked(lock_path):
        _validate_public_directory(output)
        with tempfile.TemporaryDirectory(prefix=f".{output.name}.stage-", dir=output.parent) as temporary:
            staging = Path(temporary)
            workbook_path = staging / "results.xlsx"
            report_path = staging / "report.md"
            write_workbook(model, workbook_path)
            report_path.write_text(report_text, encoding="utf-8")
            facts = read_workbook(workbook_path)
            if facts.generation_id != model.generation_id:
                raise ValueError("rendered workbook generation mismatch")
            if _report_generation(report_path) != model.generation_id:
                raise ValueError("rendered Markdown generation mismatch")
            output.mkdir(parents=True, exist_ok=True)
            journal_path.write_text(json.dumps({"generation_id": model.generation_id, "phase": "prepared"}) + "\n", encoding="utf-8")
            os.chmod(journal_path, 0o600)
            os.replace(workbook_path, output / "results.xlsx")
            journal_path.write_text(json.dumps({"generation_id": model.generation_id, "phase": "workbook_replaced"}) + "\n", encoding="utf-8")
            os.replace(report_path, output / "report.md")
            journal_path.unlink(missing_ok=True)
            os.chmod(output / "results.xlsx", 0o600)
            os.chmod(output / "report.md", 0o600)


def validate_pair(output: Path):
    _validate_public_directory(output, require_pair=True)
    facts = read_workbook(output / "results.xlsx")
    generation = _report_generation(output / "report.md")
    if generation != facts.generation_id:
        raise ValueError("deliverable pair contains mixed generations")
    return facts


def render_decision_report(model: ReportModel) -> str:
    overview = {str(row["metric"]): row.get("value") for row in model.overview}
    lines = [
        "---", f"generation_id: {model.generation_id}", f"schema_version: {model.schema_version}",
        f"artifact_state: {model.artifact_state}", "---", "", "# 評估決策報告", "",
        "## 執行結果", "", f"- 產物狀態：`{_display_status(model.artifact_state)}`",
        f"- 評估結論：`{_display_status(overview.get('Evaluation verdict', 'UNAVAILABLE'))}`",
        f"- 平均案例分（0–3）：`{_display(overview.get('Overall score'))}`",
        f"- 通過率：`{_display(overview.get('Pass rate'))}`",
        f"- 平均總延遲：`{_display(overview.get('Mean total latency (ms)'))}` 毫秒", "",
        "品質與速度分開呈現；缺失的遙測資料會被排除，不會按零分計算。", "",
        "## 快速判讀：路由、策略與證據", "",
        "下表由 `03_Metrics` 聚合而來，先看分流，再看回答是否得到內容支持；不可用表示證據不足，不代表 0 分。", "",
        "| 問題 | 指標 | 結果 | 閱讀方式 |", "| --- | --- | ---: | --- |",
    ]
    decision = {str(row.get("metric")): row for row in model.overview if row.get("section") == "Decision"}
    decision_rows = (
        ("Router 是否分流到可接受路由", "Router accepted accuracy", "查看 `route_acceptance` 的 case/turn PASS/FAIL；可接受集合可包含多個合理路由。"),
        ("Router 是否命中首選路由", "Router preferred accuracy", "查看 `route_preference`；危機案例核對 `crisis_sop`，普通案例核對 capsule/baseline。"),
        ("回答是否有足夠 Capsule 支持", "Capsule claim alignment", "只表示 Judge claims 對齊已注入 Capsule units；屬觀察性證據，不是因果證明。"),
        ("回答整體是否有足夠證據支持", "Overall claim support rate", "查看 semantic attribution，再到 03_Metrics/typed facts 查看 Capsule、Ground、Wiki 分層。"),
    )
    for question, metric, reading in decision_rows:
        row = decision.get(metric, {})
        display_metric = {
            "Router accepted accuracy": "Router 可接受路由準確率",
            "Router preferred accuracy": "Router 首選路由準確率",
            "Capsule claim alignment": "Capsule claim 對齊率",
            "Overall claim support rate": "整體 claim 支持率",
        }[metric]
        lines.append(f"| {_md(question)} | {_md(display_metric)} | {_display(row.get('value'))} | {_md(reading)} |")
    lines.extend([
        "", "**crisis SOP 是否合理**：自動指標只能確認危機 route/安全 hard gate 是否符合 oracle，不能單獨判定 SOP 的步驟、語氣與風險處置是否充分。請在 `03_Metrics` 交叉查看 `route_acceptance`、`route_preference`、`safety`、red-line 與 Judge 的「行動賦權／求助轉介／法律維權」分數；失敗的 case/turn 才是修改位置。",
        "**baseline 是否合理**：baseline route 命中且回答表現良好時，表示不需要 capsule 的案例沒有被過度升級；route 正確但回答缺漏，優先檢查 Composer/ground。若 `04_Baseline` 未附上，不能宣稱相對 baseline 改善。", "",
        "## Capsule／Ground 引用分數", "",
        "以下分數只在對應 oracle 與引用證據可用時計算；不可用不等於零分。", "",
        "| 類別 | 分數 | 定義 |", "| --- | ---: | --- |",
    ])
    capsule_score, ground_score = _citation_scores(model)
    lines.extend([
        f"| Capsule 引用 | {_display(capsule_score)} | Capsule claim alignment；回答 claims 與已注入 Capsule 證據的對齊程度。 |",
        f"| Ground 引用 | {_display(ground_score)} | 目前不使用 `required_ground_refs` / `relevant_ground_refs` 作 oracle 判斷；Ground 是否支持回答請看 semantic attribution 的 layer support。 |",
        "", "## 維度分數", "", "| 維度 | 分數 |", "| --- | ---: |",
    ])
    dimensions = [row for row in model.overview if row.get("section") == "Dimension"]
    lines.extend(f"| {_md(row.get('metric'))} | {_display(row.get('value'))} |" for row in dimensions)
    if not dimensions:
        lines.append("| 沒有已評估維度 | 不可用（UNAVAILABLE） |")
    lines.extend(["", "## 測試案例結果", "", "| 案例 | 狀態 | 最終分數 | 失敗階段 | 人工複核 | 延遲（毫秒） |", "| --- | --- | ---: | --- | --- | ---: |"]) 
    for row in model.cases:
        lines.append(f"| {_md(row.get('case_id'))} | {_md(_display_status(row.get('status')))} | {_display(row.get('final_score'))} | {_md(row.get('failure_stage') or '-')} | {_md(_display_status(row.get('review_status')))} | {_display(row.get('total_ms'))} |")
    lines.extend(["", "## 每個案例／輪次的 Capsule 分流與支持", "", "| 案例 | 輪次 | 實際 route/capsule | route 可接受 | route 首選 | 支持判讀 |", "| --- | ---: | --- | --- | --- | --- |"])
    metrics_by_turn: dict[tuple[str, int], dict[str, Mapping[str, Any]]] = {}
    for metric in model.metrics:
        case_id = str(metric.get("case_id", ""))
        turn = metric.get("turn")
        if case_id == "__RUN__" or not isinstance(turn, int):
            continue
        metrics_by_turn.setdefault((case_id, turn), {})[str(metric.get("metric_id"))] = metric
    for turn in model.turns:
        key = (str(turn.get("case_id")), int(turn.get("turn", 0)))
        facts = metrics_by_turn.get(key, {})
        accepted = facts.get("route_acceptance", {}).get("status")
        preferred = facts.get("route_preference", {}).get("status")
        support = "請查看本報告的 Capsule claim alignment／semantic attribution 聚合；本輪未提供可驗證的 claim 支持分數。"
        lines.append(f"| {_md(key[0])} | {key[1]} | `{_md(turn.get('route_id') or '未記錄')}` | {_display_status(accepted or 'UNAVAILABLE')} | {_display_status(preferred or 'UNAVAILABLE')} | {_md(support)} |")
    lines.extend(["", "## 指標發現", ""])
    failing = [row for row in model.metrics if str(row.get("status", "")).upper() in {"FAIL", "ERROR"}]
    if failing:
        for row in failing[:30]:
            lines.append(f"- `{row.get('case_id')}:T{row.get('turn')}:{row.get('metric_id')}` 狀態=`{_display_status(row.get('status'))}` 分數=`{_display(row.get('raw_score'))}`。{_md(row.get('reason') or '請檢查已連結的證據。')}")
    else:
        lines.append("未記錄失敗或錯誤的指標事實。")
    lines.extend(["", "## 改善建議", ""])
    if model.recommendations:
        for item in model.recommendations:
            lines.extend([
                f"### {_md(item.get('recommendation_id', '建議'))}", "",
                f"- 狀態：`{_display_status(item.get('status', 'hypothesis'))}`",
                f"- 目標：`{_md(item.get('target', '未指定'))}`",
                f"- 證據狀態：`{_display_status(item.get('evidence_state', item.get('status', 'OBSERVATIONAL_HYPOTHESIS')))}`",
                f"- 證據參照：{_md(', '.join(str(value) for value in item.get('trace_evidence_refs', ())) or '未記錄')}",
                "", _md(item.get('rationale', '')), "",
                "在受控實驗章節附上結果之前，此建議仍屬假設。", "",
            ])
    else:
        lines.append("本輪未產生改善行動。")
    lines.extend(["", "## 基準比較", ""])
    lines.append("基準證據已附於工作簿的 `04_Baseline` 工作表。" if model.baseline else "未執行，因此不宣稱相較基準有所改善。")
    lines.extend(["", "## 實驗結果", ""])
    if model.experiments:
        for row in model.experiments:
            lines.extend([
                f"### {_md(row.get('experiment_id', '實驗'))}", "",
                f"- 假設：{_md(row.get('hypothesis', ''))}",
                f"- 對照組：`{_md(row.get('control', ''))}`",
                f"- 候選組：`{_md(row.get('candidate', ''))}`",
                f"- 重複次數：`{_display(row.get('repetitions'))}`",
                f"- 目標結果：`{_md(row.get('target_result', ''))}`",
                f"- 非目標退化：`{_display(row.get('non_target_regression'))}`",
                f"- 防護條件：`{_md(row.get('guardrails', ''))}`",
                f"- 結論：`{_display_status(row.get('verdict', ''))}`",
                f"- 下一步：{_md(row.get('next_action', ''))}", "",
            ])
    else:
        lines.append("未執行；上述改善建議仍屬假設。")
    lines.extend(["", "## 人工複核", ""])
    lines.append(f"待複核項目：`{len(model.human_review)}`。複核者身分僅為作業標籤，不代表已完成身分驗證。")
    lines.extend(["", "## 穩定性", ""])
    if model.stability:
        lines.append("穩定性只表示可重複性，不衡量正確性；穩定的錯誤回答仍然是錯誤回答。")
        for row in model.stability:
            lines.append(f"- {_md(row.get('metric'))}：`{_display(row.get('value'))}`（{_display_status(row.get('status'))}）")
    else:
        lines.append("`未測量（NOT_MEASURED）`。穩定性表示固定控制條件下的可重複性，不衡量正確性。")
    lines.extend(["", "## 類型化證據事實", ""])
    typed = model.manifest.get("typed_facts", {})
    if isinstance(typed, Mapping) and typed:
        for kind, facts in sorted(typed.items()):
            count = len(facts) if isinstance(facts, Sequence) and not isinstance(facts, (str, bytes)) else 0
            lines.append(f"- `{_md(kind)}`：`{count}` 筆事實；身分標識與證據參照保留於工作簿中繼資料。")
    else:
        lines.append("未附上類型化的測試套件、歸因、基準、參數、診斷或實驗事實。")
    lines.extend(["", "## 限制", "", "- 路由命中或相似度分數，不能證明回答在語義上實際使用了相關內容。", "- `UNAVAILABLE`、`NOT_RUN` 與 `NOT_APPLICABLE` 不等於數值零。", "- 只有測量方式與案例／輪次契約相容時，基準差異才有效。", ""])
    return "\n".join(lines)


def _validate_public_directory(output: Path, *, require_pair: bool = False) -> None:
    if not output.exists():
        if require_pair:
            raise ValueError("deliverable directory does not exist")
        return
    if not output.is_dir():
        raise ValueError("deliverable output must be a directory")
    names = {path.name for path in output.iterdir() if path.name not in {".DS_Store"} and not path.name.startswith("~$")}
    if names and names != PUBLIC_FILES:
        raise ValueError(f"deliverable directory contains unknown files: {', '.join(sorted(names - PUBLIC_FILES))}")
    if require_pair and names != PUBLIC_FILES:
        raise ValueError("deliverable directory does not contain a complete pair")


@contextmanager
def _locked(path: Path):
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def _report_generation(path: Path) -> str:
    for line in path.read_text(encoding="utf-8").splitlines()[:10]:
        if line.startswith("generation_id:"):
            return line.partition(":")[2].strip()
    raise ValueError("Markdown report has no generation_id")


def _display(value: Any) -> str:
    return f"{value:.4f}" if isinstance(value, float) else "不可用（UNAVAILABLE）" if value is None else str(value)


def _citation_scores(model: ReportModel) -> tuple[float | None, float | None]:
    aggregate = {str(row.get("metric_id")): row.get("raw_score") for row in model.metrics if row.get("case_id") == "__RUN__"}
    capsule = aggregate.get("v3:capsule_attribution.claim_alignment")
    # Ground citation quality is not derived from case-level oracle lists.
    ground = None
    return (float(capsule) if isinstance(capsule, (int, float)) else None, ground)


def _display_status(value: Any) -> str:
    raw = "UNAVAILABLE" if value is None or str(value).strip() == "" else str(value)
    labels = {
        "PASS": "通過", "FAIL": "未通過", "ERROR": "錯誤", "SKIP": "略過",
        "FINAL": "已完成", "PENDING_REVIEW": "待人工複核", "NEEDS_REVIEW": "需要人工複核",
        "AVAILABLE": "可用", "UNAVAILABLE": "不可用", "NOT_RUN": "未執行",
        "NOT_MEASURED": "未測量", "NOT_APPLICABLE": "不適用", "ATTACHED": "已附上",
        "HYPOTHESIS": "假設", "VALIDATED": "已驗證", "REJECTED": "已否決",
        "COMPLETED": "已完成", "NOT_REQUESTED": "未要求", "AGREED": "一致",
        "OBSERVATIONAL_HYPOTHESIS": "觀察性假設",
    }
    label = labels.get(raw.upper())
    return f"{label}（{raw}）" if label else raw


def _md(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ").replace("<", "&lt;").replace(">", "&gt;")
