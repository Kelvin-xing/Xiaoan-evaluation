"""Complete-result evidence exposure and independent report recovery."""
import json
import sys
from pathlib import Path
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation"))
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "evaluation" / "tests"))
from test_frozen_outputs import fixture_result
from evaluation_report_agent.evidence import EvidenceStore
from evaluation_report_agent.agent import ReportAgent, validate_report


def report(store):
    return {"action": "finish", "generation": store.generation, "title": "評估結果", "findings": [{"kind": "judge", "conclusion": "評委的分數不同。", "scope": "本案", "quotes": [{"ref": "/answers/0", "text": "完整回答"}]}], "facts": [], "limitations": ["小型測試"]}


def test_read_exposure_and_wrong_generation(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    value = report(store)
    assert validate_report(value, store)
    store.query("read_evidence", {"ref": "/answers/0", "limit": 2})
    assert validate_report(value, store)
    store.query("read_evidence", {"ref": "/answers/0"})
    assert validate_report(value, store) == []
    value["generation"] = "wrong"
    assert validate_report(value, store)


def test_bounded_report_and_cached_resume(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    class Provider:
        model = "fixture"
        endpoint = "offline"
        def __init__(self): self.calls = 0
        def __call__(self, instructions, payload):
            self.calls += 1
            value = ({"action": "inspect", "requests": [{"tool": "read_evidence", "args": {"ref": "/answers/0"}}]} if not payload["history"] else report(store))
            return json.dumps(value, ensure_ascii=False), {"total_tokens": 2}
    store = EvidenceStore(source)
    provider = Provider()
    output = tmp_path / "report"
    path = ReportAgent(store, provider, output, max_rounds=3).run()
    assert path.exists() and provider.calls == 2
    second_store = EvidenceStore(source)
    ReportAgent(second_store, provider, output, max_rounds=3).run()
    assert provider.calls == 2
    receipts = json.loads((output / "request-receipts.json").read_text())
    assert all(r["new_usage"]["total_tokens"] == 0 for r in receipts)


def test_numerical_fact_is_source_bound(tmp_path):
    source = tmp_path / "results.json"
    source.write_text(json.dumps(fixture_result(), ensure_ascii=False))
    store = EvidenceStore(source)
    store.query("read_evidence", {"ref": "/answers/0"})
    store.query("read_evidence", {"ref": "/aggregates"})
    value = report(store)
    value["facts"] = [{"pointer": "/aggregates/metrics/0/value", "value": 100}]
    assert "numeric fact mismatch" in validate_report(value, store)


def test_malformed_provider_payload_can_be_repaired(tmp_path):
    source=tmp_path/'results.json'
    source.write_text(json.dumps(fixture_result(),ensure_ascii=False))
    store=EvidenceStore(source)
    for value in [None,{'findings':None},{'findings':['bad']},{'findings':[{'quotes':[None]}]},{'facts':[{'pointer':None}]}]:
        assert validate_report(value,store)
