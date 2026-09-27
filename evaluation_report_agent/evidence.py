"""Read-only, paged access to one complete frozen result generation."""
from pathlib import Path
import hashlib
import json
from collections import defaultdict


DOMAIN_FIELDS = {
    '法律維權': ('capsule.ground', 'wiki.source_refs', 'capsule.act', 'capsule.render_policy'),
    '行動支持': ('capsule.act', 'capsule.scripts', 'capsule.render_policy'),
    '心理支持': ('capsule.recognize', 'capsule.act', 'capsule.render_policy'),
}


def diagnostic_domain(module):
    if '法律' in module:
        return '法律維權'
    if '行動' in module or '转介' in module or '轉介' in module:
        return '行動支持'
    if '基础能力' in module or '基礎能力' in module or '心理' in module or '同理' in module:
        return '心理支持'
    return None


def dumps(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(value):
    return hashlib.sha256(dumps(value).encode()).hexdigest()


def file_hash(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class EvidenceStore:
    def __init__(self, results):
        from xiaoan_eval_core.results import validate_complete_results
        self.path = Path(results).resolve()
        self.file_sha256 = file_hash(self.path)
        self.result = validate_complete_results(json.loads(self.path.read_text()))
        self.generation = self.result["result_generation"]
        self.sources = {}
        self.exposed = {}
        self.journal = []
        for section in ("manifest", "plan", "aggregates", "answers", "inventories", "envelopes", "stages", "provenance"):
            data = self.result[section]
            items = list(enumerate(data)) if isinstance(data, list) else [(None, data)]
            for key, value in items:
                pointer = "/" + section + ("/" + str(key) if key is not None else "")
                self.sources[pointer] = {"ref": pointer, "digest": digest(value), "data": value}
        self.dimension_signals, self.domain_examples = self._dimension_signals()
        self.diagnostics = self._diagnostics()
        self.runtime_verification = {
            "status": "PENDING_HISTORICAL_SNAPSHOT",
            "steps": ["核對此結果 generation 與當時 Chatflow 程式、Router/Safety、capsule 各欄位及 Wiki node/source_refs 的封存版本",
                      "用同一案例輸入重現執行路徑，對照原始日誌與 trace",
                      "由人工確認成因；在此前只能提出待驗證假說"],
        }

    def _dimension_signals(self):
        """Count low rubric scores without treating them as confirmed defects."""
        answers = {a['answer_id']: a for a in self.result['answers']}
        groups = defaultdict(lambda: {'evaluated': 0, 'low': 0, 'cases': set()})
        examples = defaultdict(list)
        for envelope in self.result['envelopes']:
            answer = answers.get(envelope['answer_id'])
            if not answer or answer.get('status') != 'AVAILABLE':
                continue
            route = (answer.get('trace') or {}).get('route', {}).get('capsule_id')
            if not route or route in {'crisis_sop', 'safety_clarification', 'baseline'}:
                continue
            for cell in envelope['rubric']:
                if cell.get('status') != 'AVAILABLE':
                    continue
                judge = cell['judge_id']
                by_domain = {}
                for detail in cell.get('rubric', {}).get('dimension_details', []):
                    domain = diagnostic_domain(detail.get('module', ''))
                    score = detail.get('score')
                    if not domain or not isinstance(score, (int, float)) or isinstance(score, bool):
                        continue
                    previous = by_domain.get(domain)
                    if previous is None or score < previous['score']:
                        by_domain[domain] = detail
                for domain, detail in by_domain.items():
                    score = detail['score']
                    key = (domain, answer['subject_id'], judge)
                    groups[key]['evaluated'] += 1
                    if score <= 1:
                        groups[key]['low'] += 1
                        groups[key]['cases'].add(answer['case_id'])
                        examples[domain].append((score, answer['subject_id'], answer['case_id'],
                                                 answer['turn'], judge, answer, detail['module']))
        summary = [{'domain': domain, 'subject_id': subject, 'judge_id': judge,
                    'low': data['low'], 'evaluated': data['evaluated'],
                    'affected_cases': len(data['cases'])}
                   for (domain, subject, judge), data in sorted(groups.items())]
        return summary, examples

    def _diagnostics(self):
        """Bounded, deterministic leads from approved runtime checks and case scores."""
        answers = self.result['answers']
        answer_index = {a['answer_id']: i for i, a in enumerate(answers)}
        envelope_index = {e['answer_id']: i for i, e in enumerate(self.result['envelopes'])}
        grouped = {'safety': [], 'routing': [], 'quality': [], 'ground': [],
                   **{domain: [] for domain in DOMAIN_FIELDS}}

        def add(kind, answer, priority, signal, *, judge_id=None):
            aid = answer['answer_id']
            if aid not in envelope_index:
                return
            a_ref = f"/answers/{answer_index[aid]}"
            e_ref = f"/envelopes/{envelope_index[aid]}"
            grouped[kind].append((priority, answer['subject_id'], answer['case_id'], answer['turn'],
                                  judge_id or '', {
                                      'kind': kind, 'subject_id': answer['subject_id'],
                                      'case_id': answer['case_id'], 'turn': answer['turn'],
                                      'answer_id': aid, 'judge_id': judge_id,
                                      'signal': signal, 'answer_ref': a_ref, 'envelope_ref': e_ref,
                                      'oracle_status': answer.get('oracle_status'),
                                      'oracle_version': answer.get('oracle_provenance'),
                                      'candidate_fields': (
                                          ('capsule.triggers', 'capsule.use_when', 'capsule.do_not_use_when')
                                          if kind == 'routing' else
                                          ('capsule.ground', 'wiki.source_refs') if kind == 'ground' else
                                          DOMAIN_FIELDS.get(kind, ())),
                                      'field_status': 'HISTORICAL_CONFIG_NOT_VERIFIED',
                                      'trace': {key: (answer.get('trace') or {}).get(key)
                                                for key in ('route', 'safety', 'ground')},
                                  }))

        for detail in self.result['aggregates'].get('routing', {}).get('details', []):
            if detail.get('accepted_hit') is not False or detail['answer_id'] not in answer_index:
                continue
            priority = (0 if detail.get('expected_mode') == 'CRISIS' else
                        1 if detail.get('actual_mode') == 'CRISIS' else 2)
            add('routing', answers[answer_index[detail['answer_id']]], priority,
                {key: detail.get(key) for key in ('expected_route', 'actual_route', 'accepted_routes',
                                                   'oracle_version', 'oracle_snapshot')})
        for answer in answers:
            oracle = answer.get('oracle_source', {}).get('reference_oracle',
                                                          answer.get('reference_oracle', {}))
            if oracle.get('status') not in {'approved', 'reviewed'} or 'safety_levels' not in oracle.get('scope', []):
                continue
            for req in answer.get('requirements', []):
                field = req.get('provenance', {}).get('field')
                if field not in {'safety_levels', 'ground_required_nodes'}:
                    continue
                check = answer.get('observations', {}).get(req['id'], {})
                if check.get('status') == 'AVAILABLE' and check.get('value') is False:
                    kind = 'safety' if field == 'safety_levels' else 'ground'
                    add(kind, answer, 0, {'expected': req.get('expected'),
                                          'actual': check.get('actual'), 'check_id': req['id']})
        by_case = {}
        for answer in answers:
            by_case.setdefault((answer['subject_id'], answer['case_id']), answer)
        for metric in self.result['aggregates'].get('case_metrics', []):
            if metric.get('metric') not in {'rubric_gate', 'requirements_gate'} or metric.get('gate') != 'FAIL':
                continue
            answer = by_case.get((metric['subject_id'], metric['case_id']))
            if answer:
                add('quality', answer, 0 if metric['metric'] == 'requirements_gate' else 1,
                    {'metric': metric['metric'], 'gate': metric['gate']}, judge_id=metric['judge_id'])
        for domain, examples in self.domain_examples.items():
            for score, _, _, _, judge, answer, module in examples:
                add(domain, answer, score, {'module': module, 'score': score,
                    'interpretation': 'Judge 低分線索；是否適用及成因需核對案例與歷史配置'}, judge_id=judge)

        selected = []
        for kind, candidates in grouped.items():
            seen = set()
            for *_, item in sorted(candidates):
                key = (item['subject_id'], item['case_id'])
                if key in seen:
                    continue
                seen.add(key)
                ref = f"/diagnostics/{len(selected)}"
                item['ref'] = ref
                item['required_refs'] = [ref, item['answer_ref']]
                if kind == 'quality' or kind in DOMAIN_FIELDS:
                    item['required_refs'].append(item['envelope_ref'])
                self.sources[ref] = {'ref': ref, 'digest': digest(item), 'data': item}
                selected.append(item)
                if len(seen) == (1 if kind in DOMAIN_FIELDS or kind == 'ground' else 2):
                    break
        return selected

    def catalog(self, *, compact=False):
        from .presentation import source_label
        index = self.sources.items()
        if compact:
            index = ((ref, source) for ref, source in index if ref in {'/manifest', '/plan', '/aggregates'})
        return {"generation": self.generation, "core_digest": self.result["core_digest"],
                "source_index": [{"ref": k, "label":source_label(self.result,k), "digest": v["digest"]} for k, v in index],
                **({"source_count": len(self.sources),
                    "case_ids": sorted({a['case_id'] for a in self.result['answers']}),
                    "subjects": sorted({a['subject_id'] for a in self.result['answers']}),
                    "judges": [j['id'] for j in self.result['plan'].get('judges', [])],
                    "metric_index": [{"ref": f"/aggregates/metrics/{i}",
                                      "subject_id": item['subject_id'], "judge_id": item['judge_id'],
                                      "metric": item['metric'], "value": item['value'],
                                      "effective_cases": item['effective_cases']}
                                     for i, item in enumerate(self.result['aggregates'].get('metrics', []))
                                     if item.get('scope') == 'own_complete_cases'],
                    "diagnostics": [{key: item[key] for key in ('ref', 'kind', 'subject_id', 'case_id',
                                                                  'turn', 'judge_id', 'required_refs')}
                                    for item in self.diagnostics],
                    "dimension_signals": self.dimension_signals,
                    "runtime_verification": self.runtime_verification}
                   if compact else {}),
                "tools": "read_evidence(ref,offset=0,limit=12000); get_case(case_id); read_artifact(path,offset=0,limit=12000)",
                "notice": "Index is not read evidence. Read pages before citing. Numbers use /aggregates facts only. get_case finds case refs."}

    def query(self, name, args):
        if name == "get_case":
            ids = {a["answer_id"] for a in self.result["answers"] if a["case_id"] == args["case_id"]}
            value = {"refs": [r for r, s in self.sources.items() if isinstance(s["data"], dict) and s["data"].get("answer_id") in ids]}
        elif name in {"read_evidence", "read_artifact"}:
            if name == "read_artifact":
                rel = args["path"]
                artifact = next((a for a in self.result["artifacts"] if a.get("path") == rel), None)
                if artifact is None:
                    raise ValueError("artifact not in frozen index")
                path = (self.path.parent / rel).resolve()
                if not path.is_relative_to(self.path.parent):
                    raise ValueError("artifact escapes result directory")
                if file_hash(path) != artifact["sha256"]:
                    raise ValueError("artifact digest mismatch")
                ref = "/artifacts/" + rel
                source = {"ref": ref, "digest": artifact["sha256"], "data": path.read_text()}
                self.sources[ref] = source
            else:
                ref = args["ref"]
                if ref not in self.sources and ref.startswith('/aggregates/metrics/'):
                    parts = ref.split('/')
                    if len(parts) != 4 or not parts[3].isdigit():
                        raise ValueError('unsupported aggregate pointer')
                    try:
                        data = self.result['aggregates']['metrics'][int(parts[3])]
                    except IndexError as exc:
                        raise ValueError('aggregate pointer out of bounds') from exc
                    self.sources[ref] = {"ref": ref, "digest": digest(data), "data": data}
                source = self.sources[ref]
            text = dumps(source["data"])
            offset = int(args.get("offset", 0))
            limit = min(12000, int(args.get("limit", 12000)))
            if offset < 0 or limit < 1:
                raise ValueError("invalid page bounds")
            chunk = text[offset:offset + limit]
            self.exposed.setdefault(ref, []).append((offset, offset + len(chunk)))
            value = {"ref": ref, "digest": source["digest"], "generation": self.generation, "text": chunk,
                     "offset": offset, "next_offset": offset + limit if offset + limit < len(text) else None, "total_characters": len(text)}
        else:
            raise ValueError("unsupported read-only tool")
        self.journal.append({"tool": name, "args": args, "result": value})
        return value

    def was_exposed(self, ref, text):
        if ref not in self.sources:
            return False
        raw = dumps(self.sources[ref]["data"])
        # Text must be in a delivered page, not just in an indexed source.
        encoded = json.dumps(text, ensure_ascii=False)[1:-1]
        return any(text in raw[start:end] or encoded in raw[start:end]
                   for start, end in self.exposed.get(ref, []))

    def unchanged(self):
        return file_hash(self.path) == self.file_sha256
