"""Generate one report from complete results.json, independently of evaluation."""
import argparse
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "evaluation"))
from .agent import KaroProvider, ReportAgent, write_json
from .evidence import EvidenceStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--model")
    parser.add_argument("--max-rounds", type=int, default=18)
    args = parser.parse_args()
    if not 1 <= args.max_rounds <= 30:
        parser.error("max-rounds must be 1..30")
    store = EvidenceStore(args.results)
    if args.execute:
        print(ReportAgent(store, KaroProvider(args.model), args.output, max_rounds=args.max_rounds).run())
    else:
        write_json(args.output / "catalog.json", store.catalog())
        print("Prepared complete-result catalog; no API calls.")


if __name__ == "__main__":
    main()
