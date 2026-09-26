"""Public facade for the single complete-JSON Report Agent.

No workbook ingestion, alternate prompt, provider or analysis loop lives here.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from evaluation_report_agent.agent import KaroProvider, ReportAgent
from evaluation_report_agent.evidence import EvidenceStore


def generate_report(results_json, *, output, provider=None, max_rounds=18):
    store = EvidenceStore(results_json)
    return ReportAgent(store, provider or KaroProvider(), output, max_rounds=max_rounds).run()


__all__ = ["EvidenceStore", "ReportAgent", "KaroProvider", "generate_report"]
