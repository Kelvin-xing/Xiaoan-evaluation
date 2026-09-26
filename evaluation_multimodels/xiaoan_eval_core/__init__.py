"""Source-checkout bridge; wheels package the canonical core directly.

Keep the two evaluation directories together when running from source.
No copied scoring implementation lives in the multimodel runner.
"""
from pathlib import Path

_canonical = Path(__file__).resolve().parents[2] / "evaluation" / "xiaoan_eval_core"
if not _canonical.is_dir():
    raise ImportError("Place evaluation/ beside evaluation_multimodels/ or install the evaluator wheel")
__path__ = [str(_canonical)]
from .version import VERSION
