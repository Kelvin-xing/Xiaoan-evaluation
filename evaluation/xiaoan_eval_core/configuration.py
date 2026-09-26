"""Versioned evaluator assets: the files are the executable configuration."""
from pathlib import Path
import hashlib

DEFAULT_ROOT = Path(__file__).resolve().parents[1] / 'evaluator-config'
if not DEFAULT_ROOT.is_dir():
    from importlib.resources import files
    DEFAULT_ROOT = Path(str(files('xiaoan_evaluator_config')))
ROOT = DEFAULT_ROOT

def configure(root=None):
    """Select assets before starting evaluator threads; return the selected directory."""
    global ROOT
    selected = Path(root).resolve() if root is not None else DEFAULT_ROOT
    required = ['rating-rule.yml', 'workflow.yml',
                *('prompts/' + name + '.md' for name in ('rubric', 'claim-extraction', 'claim-assessment', 'relevancy')),
                *('schemas/' + name + '.json' for name in ('rubric', 'claim-extraction', 'claim-assessment', 'relevancy'))]
    if any(not (selected / name).is_file() for name in required):
        raise ValueError('evaluator configuration is incomplete')
    ROOT = selected
    return ROOT

def prompt(name):
    return (ROOT / 'prompts' / name).read_text(encoding='utf-8').strip()

def snapshot():
    return {str(path.relative_to(ROOT)): {'content': path.read_text(encoding='utf-8'),
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
            for path in sorted(ROOT.rglob('*')) if path.is_file()
            and path.suffix in {'.md', '.json', '.yml', '.yaml', '.txt'}
            and not any(part.startswith('.') or part == '__pycache__' for part in path.relative_to(ROOT).parts)}

def workflow():
    import yaml
    return yaml.safe_load((ROOT / 'workflow.yml').read_text(encoding='utf-8'))

def schema(name):
    import json
    return json.loads((ROOT / 'schemas' / (name + '.json')).read_text(encoding='utf-8'))
