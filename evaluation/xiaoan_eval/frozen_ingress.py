"""Canonical plans and immutable answers; no legacy workbook ingestion."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import re
from pathlib import Path
from uuid import uuid4

import yaml

from xiaoan_eval_core.contracts import digest
from .cases import load_case
from .rules import load_rating_rule
from .evidence import validate_effective_context_snapshot, build_evidence_catalog

ROOT = Path(__file__).resolve().parents[2]
SUITE = ROOT / 'evaluation_multimodels/oracles/minimal33-update-2026-09-24'


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


_TAXONOMY_BLOCK = re.compile(rb'(?m)^test_type: [^\r\n]+\nscenario_category: [^\r\n]+\nscenario_tags: \[[^\r\n]+\]\n')


def _approved_case_bytes(content):
    """Only three additive taxonomy lines may differ from the approved YAML bytes."""
    stripped, count = _TAXONOMY_BLOCK.subn(b'', content)
    if count != 1:
        raise ValueError('expected exactly one case taxonomy block')
    return stripped


def verify_minimal33(directory=SUITE):
    directory = Path(directory)
    approval_path = directory / 'aggregate-approval-receipt.json'
    approval = json.loads(approval_path.read_text())
    expected = {f['path']: f['approved_sha256'] for f in approval['files']}
    artifacts = {str(approval_path.relative_to(ROOT)): file_hash(approval_path)}
    supplement_path = directory / 'partial-abstention-receipt.json'
    if supplement_path.exists():
        supplement = json.loads(supplement_path.read_text())
        if supplement['parent_approval_sha256'] != file_hash(approval_path):
            raise ValueError('Minimal33 approval parent mismatch')
        for change in supplement['changes']:
            if expected.get(change['path']) != change['before_sha256']:
                raise ValueError('Minimal33 approval chain mismatch')
            expected[change['path']] = change['after_sha256']
        artifacts[str(supplement_path.relative_to(ROOT))] = file_hash(supplement_path)
    from xiaoan_eval_core.taxonomy import case_taxonomy
    taxonomy_path = ROOT / 'evaluation/test-cases/scenario-taxonomy.json'
    mapping = json.loads(taxonomy_path.read_text())['cases']
    taxonomy_hashes = {}
    for path, checksum in expected.items():
        content = (ROOT / path).read_bytes()
        if hashlib.sha256(_approved_case_bytes(content)).hexdigest() != checksum:
            raise ValueError(f'Minimal33 approved file changed: {path}')
        case_id = Path(path).stem
        labels = case_taxonomy(yaml.safe_load(content))
        if [labels['test_type'], labels['scenario_category'], labels['scenario_tags']] != mapping[case_id]:
            raise ValueError(f'Minimal33 case taxonomy mismatch: {path}')
        taxonomy_hashes['taxonomy:' + path] = hashlib.sha256(content).hexdigest()
    selection_path = directory / 'selection.json'
    selection = json.loads(selection_path.read_text())
    if selection['case_ids'] != approval['case_ids']:
        raise ValueError('Minimal33 membership/order mismatch')
    for case in selection['cases']:
        if expected.get(case['source']) != case['sha256']:
            raise ValueError('Minimal33 selection digest mismatch')
    grouping_path = directory / approval['grouping_file']
    if file_hash(grouping_path) != approval['grouping_sha256']:
        raise ValueError('Minimal33 grouping mismatch')
    artifacts.update({str(p.relative_to(ROOT)): file_hash(p) for p in (selection_path, grouping_path, taxonomy_path)})
    artifacts.update(taxonomy_hashes)
    return selection, approval, artifacts


def resolve_reference_facts(expected, *, root=ROOT):
    """Resolve only independently approved, hash-bound source text as factual gold.

    Approval of route/source selection or aggregate eligibility is not factual
    approval. Existing source_refs without fact_approval remain explicit unknown.
    """
    reference = expected.get('reference_oracle', {})
    approval = reference.get('fact_approval', {})
    explicit = expected.get('reference_facts', [])
    refs = list(expected.get('source_refs', [])) + list(reference.get('ground', {}).get('background_source_refs', []))
    if not explicit and not refs:
        return [], 'missing', None, ['NO_REFERENCE_FACTS']
    if (approval.get('status') != 'approved' or 'reference_facts' not in approval.get('scope', [])
            or not approval.get('approved_by') or not approval.get('truth_version')):
        return [], 'missing', None, ['TRUTH_SCOPE_NOT_APPROVED']
    hashes = approval.get('source_hashes', {})
    root = Path(root).resolve()
    facts = []
    sources = explicit or [{'ref': ref, 'source_path': ref, 'layer': 'SOURCE'} for ref in dict.fromkeys(refs)]
    for fact in sources:
        path_ref = fact.get('source_path', fact.get('ref', ''))
        if not isinstance(path_ref, str) or not path_ref or '#' in path_ref:
            raise ValueError('reference facts require an approved whole source path; section extraction must be explicit')
        path = (root / path_ref).resolve()
        if not path.is_relative_to(root):
            raise ValueError('reference source path outside approved repository')
        checksum = hashes.get(path_ref)
        if not checksum:
            raise ValueError('reference source lacks approved snapshot hash')
        content = path.read_text(encoding='utf-8')
        if file_hash(path) != checksum.removeprefix('sha256:'):
            raise ValueError('reference source snapshot hash mismatch')
        selected = fact.get('content', content)
        if not isinstance(selected, str) or not selected.strip() or selected not in content:
            raise ValueError('reference fact content must quote approved source snapshot')
        if fact.get('layer', 'SOURCE') not in {'SOURCE', 'REFERENCE'}:
            raise ValueError('reference fact layer must be SOURCE or REFERENCE')
        facts.append({**deepcopy(fact), 'ref': fact.get('ref', path_ref), 'content': selected,
                      'layer': fact.get('layer', 'SOURCE'), 'source_path': path_ref,
                      'source_digest': checksum, 'scope': deepcopy(approval['scope']),
                      'truth_version': approval['truth_version'], 'approval': deepcopy(approval)})
    if len({fact['ref'] for fact in facts}) != len(facts):
        raise ValueError('duplicate approved fact reference')
    return facts, 'approved', approval['truth_version'], []


def oracle_row(case, turn):
    """Explicit mapping preserves authoring scope; never invent factual gold."""
    expected = turn.get('expected', {})
    response = expected.get('response_oracle', {})
    reference = expected.get('reference_oracle', {})
    provenance = case.get('oracle_provenance', {})
    requirements, seen = [], set()
    remediation = []
    applicability = reference.get('metric_applicability', {})
    approved = provenance.get('status') in ('reviewed', 'approved')

    def add(field, values, kind='task', critical=False, prefix=''):
        for n, value in enumerate(values or []):
            body = value.get('text') if isinstance(value, dict) else str(value)
            key = (kind, prefix + body)
            if key in seen:
                continue
            seen.add(key)
            requirements.append({'id': f"{case['id']}:T{turn['turn']}:{field}:{n}",
                'kind': kind, 'text': prefix + body,
                'critical': bool(value.get('critical', critical)) if isinstance(value, dict) else critical,
                'provenance': {'case_id': case['id'], 'turn': turn['turn'], 'field': field,
                               'oracle_status': 'approved' if approved else 'provisional'}})
    add('must_include', expected.get('must_include'))
    add('required_claims', response.get('required_claims'))
    add('forbidden_behaviors', expected.get('forbidden_behaviors'), 'constraint', prefix='不得：')
    add('forbidden_claims', response.get('forbidden_claims'), 'constraint', prefix='不得：')
    for kind, field in [('route','route_ids'), ('safety','safety_levels')]:
        if expected.get(field):
            add(field, ['實際值必須屬於：' + json.dumps(expected[field], ensure_ascii=False)], kind)
    if not str(applicability.get('answer_must_cite', '')).startswith('not_applicable'):
        add('must_cite', response.get('must_cite'), 'evidence', prefix='須引用（對外回答範圍）：')
    if response.get('max_chars') is not None:
        add('max_chars', [f"回答 Unicode 字元數不得超過 {response['max_chars']}"], 'constraint')
    for field in ('expected_tools', 'goal_completed', 'max_steps'):
        metric = 'tool_execution' if field in ('expected_tools', 'max_steps') else 'real_world_goal'
        if field in response and not str(applicability.get(metric, '')).startswith('not_applicable'):
            add(field, [field + '：' + json.dumps(response[field], ensure_ascii=False)], 'evidence')
    # Partial-abstention is an author-authored scope, not a binary whole-answer score.
    partial = response.get('partial_abstention', {})
    if partial:
        for req in requirements:
            field = req['provenance']['field']
            index = int(req['id'].rsplit(':', 1)[1]) + 1
            marker = ('R' if field == 'required_claims' else 'F') + str(index)
            ids = partial.get('required_claim_ids' if field == 'required_claims' else 'forbidden_claim_ids', [])
            if field in ('required_claims','forbidden_claims') and marker in ids:
                req['abstention_scope'] = deepcopy(partial)
    if 'should_abstain' in response and not any(response.get(k) for k in ('partial_abstention','abstention')):
        remediation.append('SHOULD_ABSTAIN_SCOPE_REQUIRED')
    for req in requirements:
        field = req['provenance']['field']
        req['runtime_check'] = field in {'route_ids', 'safety_levels', 'max_chars', 'expected_tools', 'goal_completed', 'max_steps'}
        if req['runtime_check']:
            req['expected'] = deepcopy(expected.get(field, response.get(field)))
    # Keep declared runtime scope, even when there is no applicable check.
    ground = reference.get('ground', {})
    if ground.get('required_node_ids'):
        add('ground_required_nodes', ['必須提供已批准 ground 節點：' + json.dumps(ground['required_node_ids'], ensure_ascii=False)], 'evidence')
        requirements[-1].update(runtime_check=True, expected=deepcopy(ground['required_node_ids']))
    if partial:
        bound = {('R' if r['provenance']['field'] == 'required_claims' else 'F') + str(int(r['id'].rsplit(':', 1)[1]) + 1)
                 for r in requirements if 'abstention_scope' in r}
        if set(partial.get('required_claim_ids', []) + partial.get('forbidden_claim_ids', [])) - bound:
            raise ValueError('partial abstention references missing claim requirements')
    if response.get('abstention') and not partial:
        remediation.append('ABSTENTION_EXPLICIT_REQUIREMENT_MAPPING_REQUIRED')
    if case.get('memory_checkpoints'):
        remediation.append('MEMORY_CHECKPOINT_RUNTIME_MAPPING_REQUIRED')
    facts, truth_status, truth_version, fact_reasons = resolve_reference_facts(expected)
    remediation.extend(fact_reasons)
    return {'requirements': requirements, 'oracle_status': 'approved' if approved else 'provisional',
            'reference_facts': facts, 'truth_status': truth_status, 'truth_version': truth_version,
            'oracle_source': deepcopy(expected), 'oracle_provenance': deepcopy(provenance),
            'reference_oracle': deepcopy(reference), 'remediation': remediation,
            'runtime_expectations': {'preferred_route_id': expected.get('preferred_route_id'), 'capsule_ids': deepcopy(expected.get('capsule_ids', [])), 'ground': deepcopy(ground), 'metric_applicability': deepcopy(applicability)},
            'observations': {}, 'quality_focus': case.get('quality_focus', []),
            'test_type': case.get('test_type'), 'scenario_category': case.get('scenario_category'),
            'scenario_tags': deepcopy(case.get('scenario_tags', [])),
            'scenario': case.get('scenario_id'), 'maturity': case.get('maturity'),
            'comparability_group': case.get('comparability_group'),
            'memory_checkpoints': deepcopy(case.get('memory_checkpoints', []))}


def build_plan(subjects, judges, extractor, *, case_ids=None, selection_dir=SUITE, rating_rule=None,
               relevancy_generator=None, subject_mode='fixture', provider_options=None):
    selection, approval, artifacts = verify_minimal33(selection_dir)
    requested = set(case_ids or selection['case_ids'])
    if requested - set(selection['case_ids']):
        raise ValueError('Unapproved case selection')
    chosen = [x for x in selection['cases'] if x['case_id'] in requested]
    known_routes={'baseline','crisis_sop','safety_clarification'}
    for item in selection['cases']:
        approved_case=yaml.safe_load((ROOT/item['source']).read_text())
        for turn in approved_case['turns']:
            known_routes.update(turn.get('expected',{}).get('reference_oracle',{}).get('route_contracts',{}))
    rule_path = Path(rating_rule or ROOT / 'evaluation/ratings rule.yml')
    rule = load_rating_rule(rule_path)
    cases = []
    for item in chosen:
        loaded = load_case(ROOT / item['source'], rule)
        if loaded.preflight.status != 'ready':
            raise ValueError(f"Case not ready: {item['case_id']}")
        cases.append(yaml.safe_load((ROOT / item['source']).read_text()))
    plan = {'suite_id': 'Minimal33', 'case_ids': [x['id'] for x in cases],
            'known_route_ids':sorted(known_routes),
            'full_suite_case_count': 33, 'subjects': deepcopy(subjects), 'judges': deepcopy(judges),
            'extractor':deepcopy(extractor), 'relevancy_generator':deepcopy(relevancy_generator),
            'subject_mode':subject_mode,
            'branches': {k: True for k in ('rubric','claims','requirements','relevancy','checks')},
            'aggregation_policy': approval['aggregation_policy'], 'case_equal_weight': True}
    from xiaoan_eval_core.configuration import snapshot
    manifest = {'schema_version': 'frozen-plan/v1', 'suite_id': 'Minimal33',
                'comparability_group': approval['comparability_group'],
                'source_artifacts': artifacts, 'cases': chosen, 'plan': plan,
                'rating_rule_sha256': file_hash(rule_path), 'snapshot_id': approval['snapshot_id'],
                'evaluator_config':snapshot(), 'provider_options':deepcopy(provider_options or {})}
    manifest['manifest_digest'] = digest(manifest)
    rows, turns = [], {}
    for case in cases:
        turns[case['id']] = [t['turn'] for t in case['turns']]
        for subject in subjects:
            for turn in case['turns']:
                unit = digest([manifest['manifest_digest'], subject['id'], case['id'], turn['turn']])
                rows.append({'planned_unit_id': unit, 'answer_id': 'pending:'+unit,
                    'case_id': case['id'], 'turn': turn['turn'], 'subject_id': subject['id'],
                    'subject_provider': subject['provider'], 'subject_model': subject['model'],
                    'question': turn['user'], 'history': [], 'answer': None,
                    'status': 'UNAVAILABLE', 'execution_status': 'PENDING', 'availability': 'UNAVAILABLE',
                    'reason': 'NOT_ATTEMPTED', 'answer_sha256': None,
                    'manifest_digest': manifest['manifest_digest'], 'context': [],
                    'context_capture': 'UNAVAILABLE', 'context_version': None, **oracle_row(case, turn)})
    return {'schema_version': 'evaluation-methods/v3', 'contract': 'frozen-answer-evaluation/v1',
            'plan': plan, 'manifest': manifest, 'planned_subjects': [s['id'] for s in subjects],
            'planned_turns': turns, 'extractor': deepcopy(extractor), 'judges': deepcopy(judges),
            'rows': rows, 'artifacts': {}, 'provenance': {'source': 'approved-minimal33'},
            'relevancy_generator':deepcopy(relevancy_generator), 'provider_options':deepcopy(provider_options or {}),
            'audit_sample_fraction': 0}


def freeze_answer(planned, response, history, *, generation_id=None):
    row = deepcopy(planned)
    row['history'] = deepcopy(history)
    row['history_kind'] = 'conversation_transcript'
    row['effective_generation_input'] = deepcopy(response.get('effective_generation_input'))
    row['effective_generation_input_status'] = 'AVAILABLE' if response.get('effective_generation_input') is not None else 'UNAVAILABLE'
    row['answer_id'] = digest([row['planned_unit_id'], generation_id or str(uuid4())])
    answer = response.get('text', response.get('response'))
    success = isinstance(answer, str) and bool(answer.strip()) and response.get('status', 'PASS') in ('PASS','AVAILABLE','SUCCEEDED')
    partial = isinstance(answer,str) and bool(answer) and response.get('status') == 'PARTIAL'
    row.update(answer=answer if isinstance(answer, str) else None, status='AVAILABLE' if success else 'PARTIAL' if partial else 'UNAVAILABLE',
               availability='AVAILABLE' if success else 'PARTIAL' if partial else 'UNAVAILABLE', execution_status='SUCCEEDED' if success else 'FAILED',
               reason=None if success else response.get('reason', response.get('error_type','SUBJECT_UNAVAILABLE')))
    row['answer_sha256'] = hashlib.sha256(answer.encode()).hexdigest() if isinstance(answer,str) else None
    row['usage'] = deepcopy(response.get('usage', {}))
    row['telemetry'] = {k:response.get(k) for k in ('elapsed_ms','queue_ms','ttft_ms','request_id','started_at','completed_at')}
    trace = response.get('trace', response.get('chatflow_debug', {})) or {}
    row['trace'] = deepcopy(trace)
    snapshot = trace.get('effective_context_snapshot')
    row['effective_context_snapshot'] = deepcopy(snapshot)
    if not row['usage'] and snapshot:
        composer=snapshot.get('invocations',{}).get('composer',snapshot.get('composer',{}))
        if composer.get('usage'):
            from .frozen_provider import usage
            row['usage']=usage({'usage':composer['usage']})
    if snapshot is not None:
        validated = validate_effective_context_snapshot(snapshot)
        if validated.turn != row['turn']:
            raise ValueError('Snapshot turn mismatch')
        if validated.composer.status == 'INVOKED':
            row.update(context=build_evidence_catalog(validated), context_capture='EXPOSED', context_version=validated.snapshot_id)
    for req in row['requirements']:
        field = req['provenance']['field']
        if field == 'route_ids':
            value = trace.get('route', {}).get('id', trace.get('route', {}).get('capsule_id'))
            allowed = row['oracle_source'].get(field, [])
        elif field == 'safety_levels':
            value = trace.get('safety', {}).get('level'); allowed = row['oracle_source'].get(field, [])
        elif field == 'max_chars':
            value = len(answer) if success else None
            allowed = None
        elif field in {'expected_tools', 'goal_completed', 'max_steps', 'ground_required_nodes'}:
            if field == 'expected_tools':
                value = trace.get('tool_calls')
                passed = set(req['expected']) <= {call.get('name') for call in value} if isinstance(value, list) else None
            elif field == 'goal_completed':
                value = trace.get('goal_completed')
                passed = value == req['expected'] if isinstance(value, bool) else None
            elif field == 'max_steps':
                value = trace.get('step_count')
                passed = value <= req['expected'] if isinstance(value, int) else None
            else:
                value = trace.get('ground', {}).get('resolved_node_ids')
                passed = set(req['expected']) <= set(value) if isinstance(value, list) else None
            row['observations'][req['id']] = {'status': 'AVAILABLE' if passed is not None else 'UNAVAILABLE', 'value': passed, 'actual': deepcopy(value)}
            continue
        else:
            continue
        passed = (value in allowed) if allowed is not None else (value <= row['oracle_source']['response_oracle']['max_chars'] if value is not None else None)
        row['observations'][req['id']] = {'status': 'AVAILABLE' if value is not None else 'UNAVAILABLE', 'value': passed if value is not None else None}
    row['row_digest'] = digest({k:v for k,v in row.items() if k != 'row_digest'})
    return row


def validate_frozen_spec(spec):
    from xiaoan_eval_core.runtime import prepare_rows
    result = deepcopy(spec)
    prepare_rows(result)
    manifest = result.get('manifest', {})
    checksum = manifest.get('manifest_digest')
    if not checksum or checksum != digest({k: v for k, v in manifest.items() if k != 'manifest_digest'}):
        raise ValueError('Frozen manifest digest mismatch')
    plan = result.get('plan', {})
    original_plan = manifest.get('plan', {})
    extension = result.get('judge_extension')
    if extension is not None:
        original = original_plan.get('judges', [])
        appended = extension.get('added_judges') if isinstance(extension, dict) else None
        if (not isinstance(appended, list) or not appended or
                extension.get('source_manifest_digest') != checksum or
                plan.get('judges') != original + appended or
                result.get('judges') != plan.get('judges') or
                {k:v for k,v in plan.items() if k != 'judges'} !=
                {k:v for k,v in original_plan.items() if k != 'judges'} or
                len({j.get('id') for j in plan['judges']}) != len(plan['judges'])):
            raise ValueError('Frozen Judge extension mismatch')
    elif plan != original_plan:
        raise ValueError('Frozen manifest plan mismatch')
    if result.get('provider_options', {}) != manifest.get('provider_options', {}):
        raise ValueError('Frozen manifest provider_options mismatch')
    for field in ('extractor', 'judges', 'relevancy_generator'):
        if result.get(field) != plan.get(field):
            raise ValueError('Frozen model identity mismatch: ' + field)
    for row in result['rows']:
        actual = hashlib.sha256(row['answer'].encode()).hexdigest() if isinstance(row.get('answer'), str) else None
        if actual != row.get('answer_sha256'):
            raise ValueError('Frozen answer hash mismatch')
        if row.get('manifest_digest') != manifest['manifest_digest']:
            raise ValueError('Frozen row manifest binding mismatch')
        snapshot_value = row.get('effective_context_snapshot')
        if snapshot_value is not None:
            captured = validate_effective_context_snapshot(snapshot_value)
            if captured.turn != row['turn']:
                raise ValueError('Frozen snapshot turn mismatch')
            if captured.composer.status == 'INVOKED':
                if row.get('context') != build_evidence_catalog(captured) or row.get('context_version') != captured.snapshot_id:
                    raise ValueError('Frozen raw/normalized context conflict')
        checksum = row.get('row_digest')
        if row.get('execution_status') != 'PENDING' and not checksum:
            raise ValueError('Frozen row digest required')
        if checksum and checksum != digest({k:v for k,v in row.items() if k != 'row_digest'}):
            raise ValueError('Frozen row digest mismatch')
    return result
