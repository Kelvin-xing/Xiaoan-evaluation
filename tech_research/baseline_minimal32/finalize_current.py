"""Finish local CSV/summary exports once the continuing evaluator writes its report."""
from pathlib import Path
import subprocess
import sys
import time

HERE = Path(__file__).resolve().parent
OUT = HERE / "runs/minimal32-current-qwen-kimi-20260921"
deadline = time.monotonic() + 24 * 60 * 60
while time.monotonic() < deadline:
    if (OUT / "results.xlsx").exists() and (OUT / "report.md").exists():
        subprocess.run([sys.executable, str(HERE / "summarize.py"), str(OUT)], check=True)
        print("Finished matrix summary and additional metric exports.", flush=True)
        break
    time.sleep(30)
else:
    raise SystemExit("Evaluation did not write final reports within 24 hours; checkpoint retained.")
