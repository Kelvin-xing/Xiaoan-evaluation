from dataclasses import asdict
from pathlib import Path

import pytest
import yaml

from xiaoan_eval.cases import CaseValidationError, load_case
from xiaoan_eval.rules import load_rating_rule


def load_modified(tmp_path, **fields):
    raw = yaml.safe_load(Path('test-cases/TC-21.yaml').read_text())
    provenance = raw['oracle_provenance']
    provenance.pop('legal_date_applicability', None)
    provenance.pop('legal_date_not_applicable_reason', None)
    provenance['legal_effective_date'] = None
    provenance.update(fields)
    path = tmp_path / 'TC-21.yaml'
    path.write_text(yaml.safe_dump(raw, allow_unicode=True))
    return load_case(path, load_rating_rule('ratings rule.yml'))


def test_missing_date_still_requires_remediation(tmp_path):
    result = load_modified(tmp_path)
    assert 'missing_legal_effective_date' in {i.issue_type for i in result.preflight.issues}


def test_explicit_non_applicability_is_ready_and_preserved(tmp_path):
    result = load_modified(tmp_path, legal_date_applicability='not_applicable',
                           legal_date_not_applicable_reason='仅检验法域澄清，不要求特定法域的法律结论。')
    assert result.preflight.status == 'ready'
    assert asdict(result.case.oracle_provenance)['legal_date_applicability'] == 'not_applicable'


@pytest.mark.parametrize('fields', [
    {'legal_date_applicability': 'not_applicable'},
    {'legal_date_applicability': 'not_applicable', 'legal_date_not_applicable_reason': '  '},
    {'legal_date_applicability': 'not_applicable', 'legal_date_not_applicable_reason': '澄清', 'legal_effective_date': '2024-01-01'},
    {'legal_date_applicability': 'unknown'},
])
def test_invalid_exemptions_are_rejected(tmp_path, fields):
    with pytest.raises(CaseValidationError):
        load_modified(tmp_path, **fields)
