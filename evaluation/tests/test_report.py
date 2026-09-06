import json

import pytest

from xiaoan_eval.report import UnsafeReportData, verify_for_report, write_jsonl
from xiaoan_eval.runner import CaseRunResult, TurnRunResult


def test_jsonl_report_is_stable_and_excludes_raw_user_input(tmp_path) -> None:
    result = CaseRunResult(
        case_id="TC-01",
        status="pass",
        conversation_id="conversation-1",
        turns=[
            TurnRunResult(
                turn=1,
                response="redacted answer",
                trace={"route": {"id": "baseline"}},
            )
        ],
    )

    destination = tmp_path / "turns.jsonl"
    verified = verify_for_report(result, contains_pii=lambda _: False)
    write_jsonl(destination, [verified])

    row = json.loads(destination.read_text(encoding="utf-8"))
    assert row["case_id"] == "TC-01"
    assert "user" not in row["turns"][0]


def test_report_refuses_records_that_have_not_passed_redaction_validation(tmp_path) -> None:
    result = {"case_id": "TC-01", "message": "private"}

    with pytest.raises(UnsafeReportData):
        write_jsonl(tmp_path / "turns.jsonl", [result])


def test_report_detects_pii_regardless_of_field_name() -> None:
    result = CaseRunResult(
        case_id="TC-01",
        status="pass",
        conversation_id="conversation-1",
        turns=[TurnRunResult(turn=1, response="call 13800138000", trace={})],
    )

    with pytest.raises(UnsafeReportData, match="failed PII validation"):
        verify_for_report(result, contains_pii=lambda text: "13800138000" in text)
