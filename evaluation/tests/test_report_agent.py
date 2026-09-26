"""The package exposes the sole canonical JSON report engine."""
import json
from pathlib import Path
import sys
import pytest
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from xiaoan_eval import report_agent as facade
from evaluation_report_agent.agent import ReportAgent
from evaluation_report_agent.evidence import EvidenceStore
from test_frozen_outputs import fixture_result


def test_package_is_single_engine_facade():
    assert facade.ReportAgent is ReportAgent
    assert facade.EvidenceStore is EvidenceStore
    assert not hasattr(facade, 'WorkbookReader')
    assert not hasattr(facade, 'render_existing')


def test_workbook_not_accepted(tmp_path):
    source = tmp_path / 'old.xlsx'
    source.write_bytes(b'not-json')
    with pytest.raises((ValueError, UnicodeError)):
        facade.generate_report(source, output=tmp_path / 'report', provider=object())


def test_facade_uses_json_source(tmp_path):
    source = tmp_path / 'results.json'
    result = fixture_result()
    source.write_text(json.dumps(result, ensure_ascii=False))
    class Provider:
        model = 'offline'
        endpoint = 'fixture'
        def __call__(self, instructions, payload):
            if not payload['history']:
                value = {'action':'inspect','requests':[{'tool':'read_evidence','args':{'ref':'/answers/0'}}]}
            else:
                value = {'action':'finish','generation':result['result_generation'],'title':'報告','findings':[{'kind':'judge','conclusion':'評判結果','scope':'本案','quotes':[{'ref':'/answers/0','text':'完整回答'}]}],'facts':[],'limitations':[]}
            return json.dumps(value), {}
    assert facade.generate_report(source, output=tmp_path / 'report', provider=Provider(), max_rounds=3).exists()
