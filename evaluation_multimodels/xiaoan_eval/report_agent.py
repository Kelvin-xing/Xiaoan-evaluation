"""Single canonical JSON report facade; no matrix-specific report engine."""
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[2]
for path in (ROOT, ROOT / "evaluation"):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
from evaluation_report_agent.agent import KaroProvider, ReportAgent
from evaluation_report_agent.evidence import EvidenceStore


def generate_report(results_json, *, output, provider=None, max_rounds=18):
    return ReportAgent(EvidenceStore(results_json), provider or KaroProvider(), output, max_rounds=max_rounds).run()
