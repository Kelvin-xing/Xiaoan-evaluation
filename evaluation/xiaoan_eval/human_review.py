"""File-based human review workflow with immutable AI evaluation evidence."""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from typing import Any, Mapping, Sequence

from .rules import RatingRule


SCHEMA_VERSION = "1.0"
CONFIDENCE_LEVELS = frozenset({"low", "medium", "high"})
TEMPLATE_PLACEHOLDER_PREFIX = "<待填写："


def export_review_queue(
    records: Sequence[Mapping[str, Any]],
    run_fingerprint: str,
    rule: RatingRule,
) -> list[dict[str, Any]]:
    if not run_fingerprint.strip():
        raise ValueError("manifest fingerprint must be non-empty")
    packets: list[dict[str, Any]] = []
    for record in records:
        case_id = _text(record.get("case_id"), "case_id")
        review = _mapping(record.get("review"), f"{case_id}.review")
        per_turn = review.get("per_turn")
        if not isinstance(per_turn, list):
            continue
        traces = _turn_traces(record, case_id)
        conversations = _conversation_turns(record, case_id)
        evidence_refs = _string_list(record.get("evidence_refs", []), f"{case_id}.evidence_refs")
        for index, status in enumerate(per_turn):
            if status != "NEEDS_REVIEW":
                continue
            turn = index + 1
            trace = traces.get(turn)
            if trace is None:
                raise ValueError(f"{case_id} turn {turn} has no trace")
            conversation = conversations.get(turn)
            if conversation is None:
                raise ValueError(f"{case_id} turn {turn} has no conversation transcript")
            response_hash = _text(trace.get("response_sha256"), f"{case_id} turn {turn}.response_sha256")
            review_id = _review_id(run_fingerprint, case_id, turn, response_hash)
            packets.append(
                {
                    "schema_version": SCHEMA_VERSION,
                    "review_id": review_id,
                    "run_fingerprint": run_fingerprint,
                    "case_id": case_id,
                    "turn": turn,
                    "response_sha256": response_hash,
                    "user_input": _text(
                        conversation.get("user_input"), f"{case_id} turn {turn}.user_input"
                    ),
                    "assistant_response": _text(
                        conversation.get("assistant_response"),
                        f"{case_id} turn {turn}.assistant_response",
                    ),
                    "conversation": {
                        "conversation_id": _mapping(
                            record.get("conversation"), f"{case_id}.conversation"
                        ).get("conversation_id", ""),
                        "turns": [
                            dict(conversations[number])
                            for number in sorted(conversations)
                            if number <= turn
                        ],
                    },
                    "status": "pending_review",
                    "evidence_refs": evidence_refs,
                    "trace_summary": _trace_summary(trace),
                    "rubric": {
                        "red_lines": [
                            {"id": item.id, "name": item.name, "description": item.description}
                            for item in rule.red_lines
                        ],
                        "dimensions": [
                            {
                                "module": item.name,
                                "weight": item.weight,
                                "positive": list(item.positive),
                                "negative": list(item.negative),
                            }
                            for item in rule.modules
                        ],
                    },
                }
            )
    return packets


def build_submission_templates(
    queue: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    templates: list[dict[str, Any]] = []
    for packet in queue:
        rubric = _mapping(packet.get("rubric"), "queue.rubric")
        red_lines = rubric.get("red_lines")
        dimensions = rubric.get("dimensions")
        if not isinstance(red_lines, list) or not isinstance(dimensions, list):
            raise ValueError("queue.rubric must include red_lines and dimensions arrays")
        templates.append(
            {
                "schema_version": SCHEMA_VERSION,
                "review_id": _text(packet.get("review_id"), "queue.review_id"),
                "run_fingerprint": _text(
                    packet.get("run_fingerprint"), "queue.run_fingerprint"
                ),
                "case_id": _text(packet.get("case_id"), "queue.case_id"),
                "turn": packet.get("turn"),
                "response_sha256": _text(
                    packet.get("response_sha256"), "queue.response_sha256"
                ),
                "reviewer_id": "<待填写：评审者标识，例如 reviewer-01>",
                "submitted_at": (
                    "<待填写：提交时间，例如 2026-08-23T14:30:00+08:00>"
                ),
                "red_lines": [
                    {
                        "id": _text(
                            _mapping(item, "queue.rubric.red_lines[]").get("id"),
                            "queue.rubric.red_lines[].id",
                        ),
                        "triggered": None,
                        "evidence_refs": [],
                    }
                    for item in red_lines
                ],
                "dimensions": [
                    {
                        "module": _text(
                            _mapping(item, "queue.rubric.dimensions[]").get("module"),
                            "queue.rubric.dimensions[].module",
                        ),
                        "score": None,
                        "supporting_evidence_refs": [],
                        "deduction_reason": "",
                    }
                    for item in dimensions
                ],
                "confidence": None,
                "notes": "",
            }
        )
    return templates


def render_submission_instructions(
    review_count: int,
    queue_filename: str = "7.1-human-review-queue.jsonl",
    submissions_filename: str = "7.2-human-review-submissions.jsonl",
) -> str:
    return f"""# 人工评审填写说明

本次共有 **{review_count}** 条待人工评审记录。请对照
`{queue_filename}`，填写 `{submissions_filename}` 中对应行。

## 不要修改的字段

以下字段由系统生成，用于确认评审对象和回答版本，请保持原值：

- `schema_version`
- `review_id`
- `run_fingerprint`
- `case_id`
- `turn`
- `response_sha256`
- `red_lines[].id`
- `dimensions[].module`

## 需要填写的字段

- `reviewer_id`：评审者标识，例如 `reviewer-01`。
- `submitted_at`：带时区的 ISO 8601 时间，例如 `2026-08-23T14:30:00+08:00`。
- `red_lines[].triggered`：只可填写 `true` 或 `false`，不可保留 `null`。
- `red_lines[].evidence_refs`：支持判断的证据引用；没有时保留 `[]`。
- `dimensions[].score`：依据 rating rule 锚点填写整数 0、1、2 或 3，不可填写小数或保留 `null`。
- `dimensions[].supporting_evidence_refs`：支持评分的证据引用；没有时保留 `[]`。
- `dimensions[].deduction_reason`：说明扣分原因；没有扣分时保留空字符串。
- `confidence`：只可填写 `low`、`medium` 或 `high`。
- `notes`：可选的整体备注；没有时保留空字符串。

## 提交前检查

1. 替换所有以 `<待填写：` 开头的占位文字。
2. 替换所有人工判断字段中的 `null`。
3. 每条 JSON 必须保持在单独一行，不要添加 JSON 注释或额外字段。
4. 使用 `import-human-review` 验证；不要直接编辑 validated 文件。
"""


def validate_submissions(
    queue: Sequence[Mapping[str, Any]],
    submissions: Sequence[Mapping[str, Any]],
    rule: RatingRule,
) -> list[dict[str, Any]]:
    queued = {_text(item.get("review_id"), "queue.review_id"): item for item in queue}
    if len(queued) != len(queue):
        raise ValueError("review queue contains duplicate review_id")
    validated: list[dict[str, Any]] = []
    seen: set[str] = set()
    for submission in submissions:
        review_id = _text(submission.get("review_id"), "submission.review_id")
        if review_id in seen:
            raise ValueError(f"duplicate submission for review_id {review_id}")
        seen.add(review_id)
        packet = queued.get(review_id)
        if packet is None:
            raise ValueError(f"submission review_id is not in queue: {review_id}")
        for field in ("run_fingerprint", "case_id", "turn", "response_sha256"):
            if submission.get(field) != packet.get(field):
                raise ValueError(f"submission {field} does not match review queue")
        try:
            normalized = _validate_submission(submission, rule)
        except ValueError as exc:
            case_id = submission.get("case_id", "unknown case")
            turn = submission.get("turn", "unknown turn")
            raise ValueError(
                f"{review_id} ({case_id} turn {turn}): {exc}"
            ) from exc
        normalized["validated_at"] = datetime.now(timezone.utc).isoformat()
        normalized["validation_status"] = "validated"
        normalized["queue_binding_sha256"] = _queue_binding_sha256(normalized, rule)
        normalized["validation_digest"] = _validation_digest(normalized)
        validated.append(normalized)
    missing = sorted(set(queued) - seen)
    if missing:
        raise ValueError(f"human review is missing submissions for: {', '.join(missing)}")
    return validated


def adjudicate_records(
    records: Sequence[Mapping[str, Any]],
    reviews: Sequence[Mapping[str, Any]],
    rule: RatingRule,
    run_fingerprint: str,
) -> tuple[list[dict[str, Any]], dict[str, Any], bool]:
    by_case_turn: dict[tuple[str, int], Mapping[str, Any]] = {}
    for review in reviews:
        if review.get("validation_status") != "validated":
            raise ValueError("human review must be produced by import-human-review")
        normalized = _validate_submission(review, rule, allow_validation_metadata=True)
        if "validated_at" not in normalized:
            raise ValueError("human review must include validated_at")
        if normalized.get("queue_binding_sha256") != _queue_binding_sha256(
            normalized, rule
        ):
            raise ValueError("human review queue binding does not match validated identity")
        if normalized.get("validation_digest") != _validation_digest(normalized):
            raise ValueError("human review validation digest does not match validated content")
        if normalized["run_fingerprint"] != run_fingerprint:
            raise ValueError("human review run_fingerprint does not match manifest")
        expected_review_id = _review_id(
            run_fingerprint,
            str(normalized["case_id"]),
            int(normalized["turn"]),
            str(normalized["response_sha256"]),
        )
        if normalized["review_id"] != expected_review_id:
            raise ValueError("human review review_id does not match its immutable identity")
        key = (str(normalized["case_id"]), int(normalized["turn"]))
        if key in by_case_turn:
            raise ValueError(f"multiple human reviews for {key[0]} turn {key[1]}")
        by_case_turn[key] = normalized

    output: list[dict[str, Any]] = []
    reviewed_turns = 0
    red_line_matches = 0
    dimension_deltas: dict[str, list[float]] = {item.name: [] for item in rule.modules}
    needs_adjudication = False

    for source in records:
        record = deepcopy(dict(source))
        case_id = _text(record.get("case_id"), "case_id")
        audit = _mapping(record.get("review"), f"{case_id}.review").get("judge_audit", [])
        if not isinstance(audit, list):
            audit = []
        case_reviews = []
        reviewed_by_turn: dict[int, Mapping[str, Any]] = {}
        case_red_line_disagreement = False
        for (review_case, turn), human in by_case_turn.items():
            if review_case != case_id:
                continue
            if turn < 1 or turn > len(audit):
                raise ValueError(f"human review turn does not exist: {case_id} turn {turn}")
            traces = _turn_traces(record, case_id)
            trace = traces.get(turn)
            if trace is None or human["response_sha256"] != trace.get("response_sha256"):
                raise ValueError(
                    f"human review response_sha256 does not match {case_id} turn {turn}"
                )
            ai = _primary_judgement(audit[turn - 1], case_id, turn)
            ai_red_lines = {str(item["id"]): bool(item["triggered"]) for item in ai["red_lines"]}
            human_red_lines = {str(item["id"]): bool(item["triggered"]) for item in human["red_lines"]}
            red_line_agrees = ai_red_lines == human_red_lines
            reviewed_turns += 1
            red_line_matches += int(red_line_agrees)
            case_red_line_disagreement |= not red_line_agrees
            ai_scores = {str(item["module"]): float(item["score"]) for item in ai["dimensions"]}
            human_scores = {str(item["module"]): float(item["score"]) for item in human["dimensions"]}
            for module in dimension_deltas:
                dimension_deltas[module].append(human_scores[module] - ai_scores[module])
            case_reviews.append(
                {
                    **human,
                    "ai_comparison": {
                        "red_line_agreement": red_line_agrees,
                        "dimension_score_deltas": {
                            module: human_scores[module] - ai_scores[module]
                            for module in human_scores
                        },
                    },
                }
            )
            reviewed_by_turn[turn] = human
        if case_reviews:
            combined_turn_scores: list[dict[str, float]] = []
            combined_red_lines: set[str] = set()
            for turn_index, audit_item in enumerate(audit, 1):
                human = reviewed_by_turn.get(turn_index)
                if human is not None:
                    combined_turn_scores.append({
                        str(item["module"]): float(item["score"])
                        for item in human["dimensions"]
                    })
                    combined_red_lines.update(
                        str(item["id"]) for item in human["red_lines"] if item["triggered"]
                    )
                else:
                    ai = _primary_judgement(audit_item, case_id, turn_index)
                    combined_turn_scores.append({
                        str(item["module"]): float(item["score"])
                        for item in ai["dimensions"]
                    })
                    combined_red_lines.update(
                        str(item["id"]) for item in ai["red_lines"] if item["triggered"]
                    )
            human_scores = {
                module.name: sum(turn[module.name] for turn in combined_turn_scores)
                / len(combined_turn_scores)
                for module in rule.modules
            }
            human_red_lines = sorted(combined_red_lines)
            quality = _mapping(record.get("quality"), f"{case_id}.quality")
            raw_weights = quality.get("final_weights")
            weights = (
                {item.name: float(raw_weights[item.name]) for item in rule.modules}
                if isinstance(raw_weights, Mapping)
                and all(item.name in raw_weights for item in rule.modules)
                else {item.name: item.weight for item in rule.modules}
            )
            human_total = 0.0 if human_red_lines else sum(
                human_scores[item.name] * weights[item.name] for item in rule.modules
            )
            record["human_review"] = {
                "status": "submitted",
                "reviews": case_reviews,
                "dimension_scores": human_scores,
                "weighted_total": human_total,
                "triggered_red_lines": human_red_lines,
            }
            status = "needs_adjudication" if case_red_line_disagreement else "adjudicated"
            record["adjudication"] = {
                "status": status,
                "reason": (
                    "AI and human red-line judgements disagree"
                    if case_red_line_disagreement
                    else "human review accepted alongside immutable AI evaluation"
                ),
                "adjudicated_weighted_total": None if case_red_line_disagreement else human_total,
            }
            needs_adjudication |= case_red_line_disagreement
        output.append(record)

    unmatched = sorted(
        f"{case_id} turn {turn}"
        for case_id, turn in by_case_turn
        if not any(str(record.get("case_id")) == case_id for record in records)
    )
    if unmatched:
        raise ValueError(f"human reviews reference unknown cases: {', '.join(unmatched)}")

    agreement = {
        "schema_version": SCHEMA_VERSION,
        "reviewed_turns": reviewed_turns,
        "red_line_agreement": red_line_matches / reviewed_turns if reviewed_turns else None,
        "dimension_mean_delta_human_minus_ai": {
            module: (sum(values) / len(values) if values else None)
            for module, values in dimension_deltas.items()
        },
        "needs_adjudication": needs_adjudication,
    }
    return output, agreement, needs_adjudication


def render_agreement_markdown(summary: Mapping[str, Any]) -> str:
    agreement = summary.get("red_line_agreement")
    lines = [
        "# Human Review Agreement",
        "",
        f"Reviewed turns: {summary.get('reviewed_turns', 0)}",
        f"Red-line agreement: {agreement:.3f}" if isinstance(agreement, (int, float)) else "Red-line agreement: n/a",
        f"Needs adjudication: {str(bool(summary.get('needs_adjudication'))).lower()}",
        "",
        "## Dimension mean delta (human - AI)",
        "",
        "| Dimension | Mean delta |",
        "| --- | ---: |",
    ]
    for module, value in dict(summary.get("dimension_mean_delta_human_minus_ai", {})).items():
        lines.append(f"| {module} | {value:.3f} |" if isinstance(value, (int, float)) else f"| {module} | n/a |")
    return "\n".join(lines) + "\n"


def _validate_submission(
    submission: Mapping[str, Any],
    rule: RatingRule,
    *,
    allow_validation_metadata: bool = False,
) -> dict[str, Any]:
    if submission.get("schema_version") != SCHEMA_VERSION:
        raise ValueError("unsupported human review schema_version")
    allowed = {
        "schema_version", "review_id", "run_fingerprint", "case_id", "turn",
        "response_sha256", "reviewer_id", "submitted_at", "red_lines",
        "dimensions", "confidence", "notes",
    }
    if allow_validation_metadata:
        allowed.update(
            {
                "validated_at",
                "validation_status",
                "queue_binding_sha256",
                "validation_digest",
            }
        )
    unknown = set(submission) - allowed
    if unknown:
        raise ValueError(f"human review contains unknown fields: {sorted(unknown)}")
    normalized: dict[str, Any] = {"schema_version": SCHEMA_VERSION}
    for field in ("review_id", "run_fingerprint", "case_id", "response_sha256", "reviewer_id", "submitted_at"):
        value = submission.get(field)
        if isinstance(value, str) and value.startswith(TEMPLATE_PLACEHOLDER_PREFIX):
            raise ValueError(f"submission.{field} still contains a template placeholder")
        normalized[field] = _text(submission.get(field), f"submission.{field}")
    _aware_datetime(normalized["submitted_at"], "submission.submitted_at")
    turn = submission.get("turn")
    if isinstance(turn, bool) or not isinstance(turn, int) or turn < 1:
        raise ValueError("submission.turn must be a positive integer")
    normalized["turn"] = turn
    confidence = submission.get("confidence")
    if confidence not in CONFIDENCE_LEVELS:
        raise ValueError("submission.confidence must be low, medium, or high")
    normalized["confidence"] = confidence
    red_lines = submission.get("red_lines")
    if not isinstance(red_lines, list):
        raise ValueError("submission.red_lines must be an array")
    expected_red_lines = {item.id for item in rule.red_lines}
    actual_red_lines = {str(item.get("id")) for item in red_lines if isinstance(item, Mapping)}
    if len(red_lines) != len(expected_red_lines) or actual_red_lines != expected_red_lines:
        raise ValueError("submission.red_lines must contain every rubric red line exactly once")
    normalized_red_lines = []
    for item in red_lines:
        mapping = _mapping(item, "submission.red_lines[]")
        unknown_red_line_fields = set(mapping) - {"id", "triggered", "evidence_refs"}
        if unknown_red_line_fields:
            raise ValueError("submission.red_lines[] contains unknown fields")
        triggered = mapping.get("triggered")
        if not isinstance(triggered, bool):
            raise ValueError("submission.red_lines[].triggered must be boolean")
        normalized_red_lines.append({
            "id": str(mapping["id"]),
            "triggered": triggered,
            "evidence_refs": _string_list(mapping.get("evidence_refs", []), "submission.red_lines[].evidence_refs"),
        })
    normalized["red_lines"] = normalized_red_lines
    dimensions = submission.get("dimensions")
    if not isinstance(dimensions, list):
        raise ValueError("submission.dimensions must be an array")
    expected_modules = {item.name for item in rule.modules}
    actual_modules = {str(item.get("module")) for item in dimensions if isinstance(item, Mapping)}
    if len(dimensions) != len(expected_modules) or actual_modules != expected_modules:
        raise ValueError("submission.dimensions must contain every rubric module exactly once")
    normalized_dimensions = []
    for item in dimensions:
        mapping = _mapping(item, "submission.dimensions[]")
        unknown_dimension_fields = set(mapping) - {
            "module", "score", "supporting_evidence_refs", "deduction_reason"
        }
        if unknown_dimension_fields:
            raise ValueError("submission.dimensions[] contains unknown fields")
        score = mapping.get("score")
        if isinstance(score, bool) or not isinstance(score, int) or score not in {0, 1, 2, 3}:
            raise ValueError(
                "submission.dimensions[].score must be an anchored integer from 0 to 3"
            )
        deduction_reason = mapping.get("deduction_reason")
        if not isinstance(deduction_reason, str):
            raise ValueError("submission.dimensions[].deduction_reason must be a string")
        normalized_dimensions.append({
            "module": str(mapping["module"]),
            "score": score,
            "supporting_evidence_refs": _string_list(mapping.get("supporting_evidence_refs", []), "submission.dimensions[].supporting_evidence_refs"),
            "deduction_reason": deduction_reason,
        })
    normalized["dimensions"] = normalized_dimensions
    notes = submission.get("notes")
    if not isinstance(notes, str):
        raise ValueError("submission.notes must be a string")
    normalized["notes"] = notes
    if "validated_at" in submission:
        normalized["validated_at"] = _text(submission["validated_at"], "submission.validated_at")
        _aware_datetime(normalized["validated_at"], "submission.validated_at")
    if "validation_status" in submission:
        normalized["validation_status"] = submission["validation_status"]
    for field in ("queue_binding_sha256", "validation_digest"):
        if field in submission:
            normalized[field] = _text(submission[field], f"submission.{field}")
    return normalized


def _queue_binding_sha256(submission: Mapping[str, Any], rule: RatingRule) -> str:
    payload = {
        "schema_version": submission.get("schema_version"),
        "review_id": submission.get("review_id"),
        "run_fingerprint": submission.get("run_fingerprint"),
        "case_id": submission.get("case_id"),
        "turn": submission.get("turn"),
        "response_sha256": submission.get("response_sha256"),
        "rating_rule_schema_version": rule.schema_version,
        "red_line_ids": sorted(item.id for item in rule.red_lines),
        "dimension_modules": sorted(item.name for item in rule.modules),
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _validation_digest(submission: Mapping[str, Any]) -> str:
    payload = {
        key: value
        for key, value in submission.items()
        if key != "validation_digest"
    }
    return hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()


def _canonical_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _aware_datetime(value: str, field: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"{field} must be an ISO 8601 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f"{field} must include a timezone offset")
    return parsed


def _turn_traces(record: Mapping[str, Any], case_id: str) -> dict[int, Mapping[str, Any]]:
    pipeline = _mapping(record.get("pipeline"), f"{case_id}.pipeline")
    traces = pipeline.get("turn_traces")
    if not isinstance(traces, list):
        raise ValueError(f"{case_id}.pipeline.turn_traces must be an array")
    result = {}
    for trace in traces:
        mapping = _mapping(trace, f"{case_id}.pipeline.turn_traces[]")
        turn = mapping.get("turn")
        if isinstance(turn, int) and not isinstance(turn, bool):
            result[turn] = mapping
    return result


def _conversation_turns(record: Mapping[str, Any], case_id: str) -> dict[int, Mapping[str, Any]]:
    conversation = _mapping(record.get("conversation"), f"{case_id}.conversation")
    turns = conversation.get("turns")
    if not isinstance(turns, list):
        raise ValueError(f"{case_id}.conversation.turns must be an array")
    result = {}
    for value in turns:
        turn = _mapping(value, f"{case_id}.conversation.turns[]")
        number = turn.get("turn")
        if isinstance(number, int) and not isinstance(number, bool):
            result[number] = turn
    return result


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    raw = trace.get("trace")
    nested = raw if isinstance(raw, Mapping) else {}
    route = nested.get("route") if isinstance(nested.get("route"), Mapping) else {}
    ground = nested.get("ground") if isinstance(nested.get("ground"), Mapping) else {}
    return {
        "route_id": route.get("id"),
        "resolved_ground": _string_list(
            ground.get("resolved_ground", []), "trace.ground.resolved_ground"
        ),
    }


def _primary_judgement(value: Any, case_id: str, turn: int) -> Mapping[str, Any]:
    audit = _mapping(value, f"{case_id} turn {turn}.judge_audit")
    return _mapping(audit.get("primary"), f"{case_id} turn {turn}.primary")


def _mean_human_scores(reviews: Sequence[Mapping[str, Any]], rule: RatingRule) -> dict[str, float]:
    totals = {item.name: 0.0 for item in rule.modules}
    for review in reviews:
        for dimension in review["dimensions"]:
            totals[str(dimension["module"])] += float(dimension["score"])
    return {module: total / len(reviews) for module, total in totals.items()}


def _review_id(run_fingerprint: str, case_id: str, turn: int, response_hash: str) -> str:
    identity = json.dumps([run_fingerprint, case_id, turn, response_hash], separators=(",", ":"))
    return "HR-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _mapping(value: Any, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{field} must be an object")
    return value


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"{field} must be an array of strings")
    return list(value)
