"""Preserve non-duplicate successful checkpoints before pruning a run."""
from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
import shutil


def preserve(source: Path, existing: Path, destination: Path) -> dict:
    kept = []
    skipped = 0
    folder = source / 'checkpoint'
    if not folder.is_dir() or not (existing / 'checkpoint').is_dir():
        raise ValueError('Both runs require a checkpoint directory')
    for path in sorted(folder.glob('*.json')):
        key = path.name.removesuffix('.partial.json') if path.name.endswith('.partial.json') else path.stem
        if len(key) != 64 or any(c not in '0123456789abcdef' for c in key):
            raise ValueError(f'Unexpected checkpoint name: {path.name}')
        payload = json.loads(path.read_text())
        if payload.get('request_hash') != key or 'response' not in payload:
            raise ValueError(f'Invalid checkpoint payload: {path}')
        if (existing / 'checkpoint' / path.name).is_file():
            skipped += 1
            continue
        if path.name.endswith('.partial.json'):
            raise ValueError(f'Unique partial checkpoint needs individual review: {path}')
        target = destination / 'checkpoint' / path.name
        if target.exists():
            if target.read_bytes() != path.read_bytes():
                raise ValueError(f'Conflicting preserved checkpoint: {target}')
            skipped += 1
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
        raw = target.read_bytes()
        if raw != path.read_bytes():
            raise ValueError(f'Checkpoint copy mismatch: {target}')
        kept.append({'name': path.name, 'sha256': sha256(raw).hexdigest()})
    result = json.loads((source / 'results.json').read_text())
    return {'source': str(source.resolve()), 'existing': str(existing.resolve()),
            'source_generation': result['result_generation'],
            'source_manifest': result['manifest']['manifest_digest'],
            'preserved': kept, 'skipped': skipped}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--existing', type=Path, required=True)
    parser.add_argument('--destination', type=Path, required=True)
    parser.add_argument('--record', type=Path, required=True)
    args = parser.parse_args()
    summary = preserve(args.source, args.existing, args.destination)
    if args.record.exists():
        raise ValueError('Existing preservation record')
    args.record.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + '\n')
    print(f"Preserved {len(summary['preserved'])} unique checkpoints; "
          f"skipped {summary['skipped']} present checkpoints")
