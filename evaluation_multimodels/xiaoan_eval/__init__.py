"""Shared evaluator package, with local subject transport helpers."""
from pathlib import Path
_local = Path(__file__).resolve().parent
_canonical = _local.parents[1] / 'evaluation' / 'xiaoan_eval'
__path__ = [str(_canonical), str(_local)]
