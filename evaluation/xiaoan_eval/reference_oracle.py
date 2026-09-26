"""Versioned reference-label contracts; authoring never implies human approval."""
from __future__ import annotations

from collections.abc import Mapping
import re

VERSION = 'case-reference-oracle/v1'
FIELDS = frozenset({'route_ids', 'preferred_route_id', 'safety_levels', 'capsule_ids', 'wiki_refs', 'source_refs'})


def parse_reference_oracle(value):
    if value is None:
        return None
    if not isinstance(value, Mapping) or value.get('version') != VERSION:
        raise ValueError('reference_oracle must use case-reference-oracle/v1')
    if value.get('status') not in {'provisional', 'reviewed', 'approved'}:
        raise ValueError('reference_oracle has invalid review status')
    if value['status'] != 'provisional' and not all(value.get(k) for k in ('reviewed_by', 'reviewed_at')):
        raise ValueError('reviewed reference_oracle requires reviewed_by and reviewed_at')
    if not isinstance(value.get('snapshot_id'), str) or not re.fullmatch(r'sha256:[0-9a-f]{64}', value['snapshot_id']):
        raise ValueError('reference_oracle requires a SHA256 snapshot_id')
    scope = value.get('scope')
    if not isinstance(scope, list) or any(not isinstance(k, str) for k in scope) or set(scope) != FIELDS:
        raise ValueError('reference_oracle scope must cover all reference and route fields')
    if not isinstance(value.get('route_contracts'), Mapping) or not value['route_contracts']:
        raise ValueError('reference_oracle requires route_contracts')
    ground = value.get('ground')
    if not isinstance(ground, Mapping) or ground.get('activation') not in {'required', 'optional', 'not_applicable', 'unavailable'}:
        raise ValueError('reference_oracle has invalid ground activation')
    for key in ('required_node_ids', 'background_node_ids', 'background_source_refs'):
        if not isinstance(ground.get(key), list) or any(not isinstance(v, str) or not v for v in ground[key]):
            raise ValueError(f'reference_oracle ground.{key} must be a string list')
    if ground['activation'] == 'required' and not ground['required_node_ids']:
        raise ValueError('required ground must declare required_node_ids')
    if ground['activation'] != 'required' and ground['required_node_ids']:
        raise ValueError('non-required ground must not declare required_node_ids')
    return dict(value)


def field_is_reviewed(expected, field: str) -> bool:
    """Apply the additive review boundary without revoking old response approvals."""
    reference = expected.get('reference_oracle') if isinstance(expected, Mapping) else expected.reference_oracle
    return not reference or field not in reference.get('scope', ()) or reference.get('status') in {'reviewed', 'approved'}


def reviewed_expected(expected: Mapping) -> dict:
    """Retain response gold while excluding newly authored labels from aggregates."""
    return {key: value for key, value in expected.items() if field_is_reviewed(expected, key)}
