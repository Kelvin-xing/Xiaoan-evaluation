import pytest

from xiaoan_eval.experiment_ledger import ExperimentLedger


def test_ledger_is_append_only_and_resumable(tmp_path):
    ledger = ExperimentLedger(tmp_path / "ledger.jsonl", "e1", "digest")
    ledger.append("PREPARED")
    ledger.append("RUNNING_CONTROL")
    ledger.append("PARTIAL", {"completed": "control"})

    resumed = ExperimentLedger(tmp_path / "ledger.jsonl", "e1", "digest")
    assert [event.state for event in resumed.read()] == ["PREPARED", "RUNNING_CONTROL", "PARTIAL"]
    resumed.append("RUNNING_CANDIDATE")
    resumed.append("PARTIAL")
    resumed.append("COMPLETE")


def test_ledger_rejects_conflicting_experiment_digest(tmp_path):
    path = tmp_path / "ledger.jsonl"
    ExperimentLedger(path, "e1", "one").append("PREPARED")
    with pytest.raises(ValueError, match="identity or digest conflict"):
        ExperimentLedger(path, "e1", "two").read()
