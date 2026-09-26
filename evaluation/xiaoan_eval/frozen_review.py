"""Bound, full-population human review of frozen evaluation results.

Only review decisions and explicit revisions are editable. Imports create a new
result generation; automatic observations remain byte-for-byte equivalent.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from xiaoan_eval_core.contracts import digest

EDITABLE = frozenset({'decision', 'notes', 'reviewer', 'reviewed_at', 'revisions_json'})
DECISIONS = frozenset({'APPROVE', 'REJECT', 'NEEDS_INFO'})


def excel_display(value, json_pointer='/'):
    """Deterministic Excel display; source digests continue to bind full strings."""
    if isinstance(value, str) and len(value) > 32767:
        return value[:32500] + '\n[TRUNCATED; full content: results.json ' + json_pointer + ']'
    return value


def _json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def _judge_id(value):
    return value.get('judge_id') or value.get('id')


def _evaluation(envelope, judge_id):
    return {key: next((v for v in envelope.get(key, []) if _judge_id(v) == judge_id), None)
            for key in ('rubric', 'assessments')}


def _priorities(envelope, answer):
    flags = []
    critical_ids = {r.get('id') for r in answer.get('requirements', []) if r.get('critical')}
    dimensions = {}
    verdicts = {}
    for entry in envelope.get('rubric', []):
        rubric = entry.get('rubric', entry)
        for red in rubric.get('red_lines', []):
            if red.get('triggered'):
                flags.append('RED_LINE:' + str(red.get('id')))
        for key, score in rubric.get('scores', {}).items():
            if isinstance(score, (int, float)) and not isinstance(score, bool):
                # Different rule snapshots must not be compared as one rubric.
                dimensions.setdefault((entry.get('rating_rule_digest'), key), []).append(score)
    for (_, key), scores in dimensions.items():
        if len(scores) > 1 and max(scores) - min(scores) >= 2:
            flags.append('RUBRIC_DISAGREEMENT:' + key)
    for cell in envelope.get('assessments', []):
        assessment = cell.get('assessment', {})
        for requirement in assessment.get('requirements', []):
            if (requirement.get('critical') or requirement.get('id') in critical_ids) and requirement.get('verdict') == 'VIOLATED':
                flags.append('CRITICAL_REQUIREMENT:' + str(requirement.get('id')))
        for claim in assessment.get('claims', []):
            for dimension in ('faithfulness', 'correctness'):
                key = (cell.get('inventory_id', envelope.get('inventory_id')),
                       cell.get('evidence_digest'), claim.get('id'), dimension)
                verdicts.setdefault(key, set()).add(claim.get(dimension, {}).get('verdict'))
        gate_values = list(cell.get('gates', {}).values()) + [cell.get('requirements', {}).get(name) for name in ('release_gate', 'safety_gate', 'task_gate')]
        for gate in gate_values:
            status = gate.get('status') if isinstance(gate, dict) else gate
            if status == 'UNDETERMINED':
                flags.append('RECOVER_MISSING_DATA' if cell.get('status') != 'AVAILABLE' or any(r.get('missing_reason') or r.get('evidence_status') == 'UNAVAILABLE' for r in assessment.get('requirements', []))
                             else 'CONTENT_UNCERTAIN')
    for (_, _, claim, dimension), values in verdicts.items():
        if {'ENTAILED', 'CONTRADICTED'} <= values:
            flags.append(f'CLAIM_CONFLICT:{claim}:{dimension}')
    return sorted(set(flags))


def build_review_rows(results: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return one bound row for every planned answer × Judge, including failures."""
    if results.get('schema_version') != 'xiaoan-results/v2':
        raise ValueError('human review requires xiaoan-results/v2')
    from xiaoan_eval_core.results import complete_digest
    if results.get('core_digest') != complete_digest({k: v for k, v in results.items() if k not in {'core_digest', 'result_generation'}}):
        raise ValueError('source result digest mismatch')
    envelopes = {e['answer_id']: e for e in results.get('envelopes', [])}
    judges = results.get('plan', {}).get('judges', results.get('manifest', {}).get('judges', []))
    planned = [j if isinstance(j, str) else _judge_id(j) for j in judges]
    output = []
    for answer in results.get('answers', []):
        envelope = envelopes.get(answer['answer_id'], {})
        identifiers = list(dict.fromkeys(planned + [_judge_id(e) for key in ('rubric', 'assessments')
                                                    for e in envelope.get(key, [])]))
        for judge_id in identifiers:
            if not judge_id:
                raise ValueError('missing planned Judge identity')
            evaluation = _evaluation(envelope, judge_id)
            generation = results['result_generation']
            row = {
                'review_id': digest([generation, answer['answer_id'], judge_id]),
                'result_generation': generation, 'core_digest': results['core_digest'],
                'answer_id': answer['answer_id'],
                'answer_sha256': answer.get('answer_sha256') or (hashlib.sha256(answer['answer'].encode()).hexdigest()
                                  if isinstance(answer.get('answer'), str) else None),
                'assessment_digest': digest(evaluation), 'case_id': answer.get('case_id'),
                'turn': answer.get('turn'), 'subject_id': answer.get('subject_id'),
                'judge_id': judge_id, 'question': answer.get('question'), 'answer': answer.get('answer'),
                'evaluation_summary': _json({key: ({'status': value.get('status'), 'scores': value.get('rubric', {}).get('scores', {}), 'reason': value.get('reason')} if value else None) for key, value in evaluation.items()}), 'priority_flags': _json(_priorities(envelope, answer)),
                'decision': '', 'notes': '', 'reviewer': '', 'reviewed_at': '', 'revisions_json': '',
            }
            output.append(row)
    return output


def _resolve(value, pointer):
    if not isinstance(pointer, str) or not pointer.startswith('/'):
        raise ValueError('revision pointer must be absolute within evaluation')
    for token in pointer[1:].split('/'):
        token = token.replace('~1', '/').replace('~0', '~')
        value = value[int(token)] if isinstance(value, list) else value[token]
    return value


def import_review_rows(results, rows, *, confirmed_by=None):
    """Validate an edited sheet and return a new generation without mutating input.

    Explicit revisions: [{pointer, value, reason, evidence, scope}]. Pointers
    address the bound evaluation_summary object; they cannot alter identities.
    confirmed_by must be supplied by the actual human confirmation workflow.
    """
    expected = {r['review_id']: r for r in build_review_rows(results)}
    seen, submissions = set(), []
    for row in rows:
        identifier = row.get('review_id')
        if identifier in seen or identifier not in expected:
            raise ValueError('duplicate or foreign review_id')
        seen.add(identifier)
        original = expected[identifier]
        for key, value in original.items():
            if key not in EDITABLE and row.get(key) not in (value, excel_display(value)):
                # Excel normalizes empty cells to None.
                if not (row.get(key) in ('', None) and value in ('', None)):
                    raise ValueError(f'immutable review field changed: {key}')
        decision = row.get('decision') or ''
        if not decision:
            if any(row.get(k) for k in ('notes', 'reviewer', 'reviewed_at', 'revisions_json')):
                raise ValueError('review fields require decision')
            continue
        if decision not in DECISIONS:
            raise ValueError('invalid review decision')
        if not row.get('reviewer') or not row.get('reviewed_at'):
            raise ValueError('reviewer and reviewed_at required')
        try:
            datetime.fromisoformat(str(row['reviewed_at']).replace('Z', '+00:00'))
        except ValueError as exc:
            raise ValueError('invalid reviewed_at timestamp') from exc
        if decision != 'APPROVE' and not str(row.get('notes') or '').strip():
            raise ValueError('REJECT/NEEDS_INFO requires affected item and reason in notes')
        revisions = json.loads(row.get('revisions_json') or '[]')
        if not isinstance(revisions, list):
            raise ValueError('revisions must be an array')
        if revisions and decision != 'REJECT':
            raise ValueError('explicit revisions require REJECT')
        envelope = next(e for e in results['envelopes'] if e['answer_id'] == original['answer_id'])
        evaluation = _evaluation(envelope, original['judge_id'])
        pointers = set()
        for revision in revisions:
            pointer = revision.get('pointer')
            if pointer in pointers:
                raise ValueError('duplicate revision pointer')
            pointers.add(pointer)
            if not isinstance(pointer, str):
                raise ValueError('revision pointer required')
            if not any(pointer.startswith(p) for p in ('/rubric/rubric/', '/assessments/assessment/')):
                raise ValueError('revision must target an evaluation value')
            if pointer.rsplit('/', 1)[-1] not in {'score', 'reason', 'verdict', 'triggered', 'evidence'}:
                raise ValueError('revision must target score/reason/verdict/triggered/evidence')
            _resolve(evaluation, pointer)
            field = pointer.rsplit('/', 1)[-1]
            value = revision.get('value')
            if field == 'score' and (type(value) is not int or not 0 <= value <= 3):
                raise ValueError('rubric revision score must be within 0..3')
            if field == 'triggered' and not isinstance(value, bool):
                raise ValueError('red-line revision must be boolean')
            if field == 'verdict':
                allowed = {'SATISFIED', 'VIOLATED', 'UNCERTAIN', 'NOT_APPLICABLE'} if '/requirements/' in pointer else {'ENTAILED', 'PARTIAL', 'CONTRADICTED', 'UNSUPPORTED', 'UNKNOWN', 'NOT_APPLICABLE'}
                if value not in allowed:
                    raise ValueError('invalid human revision verdict')
            if field == 'evidence' and not isinstance(value, list):
                raise ValueError('revised evidence must be a list')
            if field == 'reason' and (not isinstance(value, str) or not value.strip()):
                raise ValueError('revision reason must be nonempty')
            if 'value' not in revision or not all(revision.get(k) for k in ('reason', 'evidence', 'scope')):
                raise ValueError('revision requires value, reason, evidence and scope')
        submissions.append({**{k: deepcopy(row.get(k)) for k in original if k != 'revisions_json'},
                            'revisions': revisions, 'confirmed_by': confirmed_by,
                            'gold_eligible': bool(confirmed_by and (decision == 'APPROVE' or revisions))})
    if seen != set(expected):
        raise ValueError('full-population review sheet required; retain blank pending rows')
    if not submissions:
        raise ValueError('no completed review decisions')
    out = deepcopy(results)
    receipt = {'parent_generation': results['result_generation'], 'parent_core_digest': results['core_digest'],
               'submissions': submissions, 'policy': 'single-user-final-confirmation/v1',
               'coverage': {'planned': len(expected), 'filled': len(submissions),
                            'approved': sum(r['decision'] == 'APPROVE' for r in submissions)}}
    submission_digest = digest(submissions)
    provenance = out.setdefault('provenance', [])
    if not isinstance(provenance, list):
        raise ValueError('provenance must be an array')
    if any(r.get('submission_digest') == submission_digest for r in provenance):
        raise ValueError('duplicate review submission')
    provenance.append({'type': 'human_review_import', **receipt, 'submission_digest': submission_digest})
    for envelope in out.get('envelopes', []):
        envelope.setdefault('human_review', []).extend(r for r in submissions if r['answer_id'] == envelope['answer_id'])
    from xiaoan_eval_core.results import seal_complete_results
    return seal_complete_results(out)



def read_review_workbook(path):
    """Read the canonical Human Review sheet without loading formulas as values."""
    from openpyxl import load_workbook
    book = load_workbook(Path(path), read_only=True, data_only=False)
    try:
        sheet = book['Human Review']
        rows = sheet.iter_rows(values_only=True)
        headers = next(rows)
        if len(set(headers)) != len(headers):
            raise ValueError('duplicate review columns')
        return [dict(zip(headers, values)) for values in rows if any(v is not None for v in values)]
    finally:
        book.close()
