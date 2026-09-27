"""One JSON-grounded Report Agent with independent resumable provider calls."""
from datetime import datetime, timezone
from pathlib import Path
import json
import os
import sys
from .evidence import EvidenceStore, digest, dumps, file_hash

INSTRUCTIONS = (Path(__file__).parent / "prompts" / "report.md").read_text(encoding="utf-8")


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))
    os.chmod(tmp, 0o600)
    tmp.replace(path)


def resolve_pointer(value, pointer):
    if not pointer.startswith("/"):
        raise ValueError("invalid JSON pointer")
    for key in pointer[1:].split("/"):
        key = key.replace("~1", "/").replace("~0", "~")
        value = value[int(key)] if isinstance(value, list) else value[key]
    return value


def validate_report(report, store, *unused):
    errors = []
    if not isinstance(report, dict):
        return ['report must be an object']
    if not isinstance(report.get('findings', []), list) or not isinstance(report.get('facts', []), list):
        return ['findings and facts must be arrays']
    if not isinstance(report.get('diagnoses', []), list):
        return ['diagnoses must be an array']
    if report.get("action") != "finish" or report.get("generation") != store.generation:
        errors.append("finish action and matching generation required")
    if not report.get("title") or not report.get("findings"):
        errors.append("title and evidence-grounded findings required")
    for item in store.diagnostics:
        for ref in item['required_refs']:
            if ref not in store.exposed:
                errors.append(f"required diagnostic evidence not read: {ref}")
    for finding in report.get("findings", []):
        if not isinstance(finding, dict) or not isinstance(finding.get('quotes', []), list):
            errors.append('finding must be an object with quotes array')
            continue
        if finding.get("kind") not in {"fact", "judge", "hypothesis", "proposal"} or not finding.get("conclusion") or not finding.get("scope"):
            errors.append("finding type/conclusion/scope required")
        if finding.get("kind") == "proposal" and not finding.get("verification"):
            errors.append("proposal requires verification")
        if finding.get("kind") == "hypothesis" and not finding.get("verification"):
            errors.append("causal hypothesis requires a verification plan")
        if finding.get('root_cause_status') == 'CONFIRMED' and store.runtime_verification['status'] != 'VERIFIED':
            errors.append('confirmed runtime bug requires verified historical code/config and reproduction')
        if not finding.get("quotes"):
            errors.append("finding requires quotes")
        for q in finding.get("quotes", []):
            if not isinstance(q,dict) or not isinstance(q.get('text'),str) or not q['text'] or not isinstance(q.get('ref'),str) or not store.was_exposed(q.get("ref"), q["text"]):
                errors.append("quote not verbatim in exposed page")
    leads = {item['ref']: item for item in store.diagnostics}
    for item in report.get('diagnoses', []):
        if not isinstance(item, dict):
            errors.append('diagnosis must be an object')
            continue
        lead = leads.get(item.get('signal_ref'))
        if lead is None or item.get('field') not in lead['candidate_fields']:
            errors.append('diagnosis must target a candidate field of a selected diagnostic')
        if any(not item.get(key) for key in ('observation', 'hypothesis', 'experiment')):
            errors.append('diagnosis requires observation, hypothesis and single-variable experiment')
        if 'recommendation' in item and (not isinstance(item['recommendation'], str) or not item['recommendation'].strip()):
            errors.append('recommendation must be nonempty text')
        quote = item.get('quote')
        if (not isinstance(quote, dict) or not lead or
            quote.get('ref') not in {lead['answer_ref'], lead['envelope_ref']} or
            not isinstance(quote.get('text'), str) or not quote['text'] or
            not store.was_exposed(quote.get('ref'), quote.get('text', ''))):
            errors.append('diagnosis requires a verbatim answer or Judge quote that was read')
        if item.get('root_cause_status') == 'CONFIRMED' and store.runtime_verification['status'] != 'VERIFIED':
            errors.append('confirmed diagnosis requires verified historical code/config and reproduction')
    for fact in report.get("facts", []):
        try:
            if not fact["pointer"].startswith("/aggregates/") or resolve_pointer(store.result, fact["pointer"]) != fact["value"]:
                errors.append("numeric fact mismatch")
            if "/aggregates" not in store.exposed:
                errors.append("aggregate facts not read")
        except (KeyError, ValueError, TypeError, IndexError, AttributeError):
            errors.append("invalid fact pointer")
    return errors
class KaroProvider:
    """Report role using the same configured wire transport as evaluation."""
    def __init__(self, model=None):
        from xiaoan_eval.frozen_provider import ConfiguredProvider, identity
        from xiaoan_eval_core import model_config
        self.transport = ConfiguredProvider()
        self.transport.values['XIAOAN_PROVIDER_TIMEOUT'] = str(max(
            300, float(self.transport.values.get('XIAOAN_PROVIDER_TIMEOUT', '120'))))
        self.identity = identity("XIAOAN_REPORT_MODEL", model=model)
        self.model = self.identity["model"]
        self.endpoint = model_config.client_config(self.model, self.transport.values)["base_url"]

    def __call__(self, instructions, payload):
        from xiaoan_eval.frozen_provider import response_text, usage
        raw = self.transport._request({"model": self.model, "store": False,
              "messages": [{"role": "system", "content": instructions}, {"role": "user", "content": dumps(payload)}],
              "response_format": {"type": "json_object"}})
        return response_text(raw), usage(raw)


class ReportAgent:
    def __init__(self, store, provider, output, *, max_rounds=18):
        from .presentation import PRESENTATION_VERSION
        self.store, self.provider, self.output = store, provider, Path(output)
        self.max_rounds = max_rounds
        self.binding = digest({"generation": store.generation, "model": provider.model,
                               "endpoint": provider.endpoint, "instructions": INSTRUCTIONS,
                               "presentation_version": PRESENTATION_VERSION})
        self.output.mkdir(parents=True, exist_ok=True)
        manifest = self.output / "manifest.json"
        if manifest.exists() and json.loads(manifest.read_text())["binding"] != self.binding:
            raise ValueError("report configuration/source changed; use a new report generation directory")
        self.manifest = {"binding": self.binding, "result_generation": store.generation, "model": provider.model,
                         "endpoint": provider.endpoint, "status": "PREPARED", "presentation_version":PRESENTATION_VERSION,
                         "created_at": datetime.now(timezone.utc).isoformat()}
        self.receipts = []
        write_json(manifest, self.manifest)

    def call(self, stage, payload):
        key = digest({"binding": self.binding, "stage": stage, "payload": payload})
        cache = self.output / "calls" / (key + ".json")
        reused = cache.exists()
        if reused:
            record = json.loads(cache.read_text())
        else:
            write_json(self.output / "requests" / (key + ".json"), {"instructions": INSTRUCTIONS, "payload": payload})
            try:
                raw, usage = self.provider(INSTRUCTIONS, payload)
                record = {"request_digest": key, "raw": raw, "usage": usage}
                write_json(cache, record)
            except Exception as exc:
                write_json(self.output / "validation.json", {"status": "FAILED", "error_type": type(exc).__name__, "stage": stage})
                raise
        self.receipts.append({"request_digest": key, "reused": reused, "new_usage": {"total_tokens": 0} if reused else record["usage"]})
        write_json(self.output / "request-receipts.json", self.receipts)
        try:
            from xiaoan_eval.frozen_provider import parse_response_json
            value = parse_response_json(record["raw"])
            return value if isinstance(value, dict) else {"action": "invalid"}
        except ValueError:
            return {"action": "invalid"}

    def run(self):
        prior = self.output / "request-receipts.json"
        previous_payloads = []
        if prior.exists():
            for receipt in json.loads(prior.read_text()):
                request = self.output / "requests" / (receipt['request_digest'] + '.json')
                cached = self.output / "calls" / (receipt['request_digest'] + '.json')
                if not request.exists() or not cached.exists():
                    break
                saved = json.loads(request.read_text())
                if saved['instructions'] != INSTRUCTIONS:
                    raise ValueError('Saved report request uses different instructions')
                previous_payloads.append(saved['payload'])
        history = []
        for number in range(self.max_rounds):
            payload = (previous_payloads[number] if number < len(previous_payloads) else
                       {"catalog": self.store.catalog(compact=True), "history": history,
                        "remaining_rounds": self.max_rounds - number})
            value = self.call(str(number), payload)
            write_json(self.output / "draft.json", value)
            history.append({"agent": value})
            if value.get("action") == "inspect":
                requests = value.get("requests", [])
                if not isinstance(requests, list) or not 1 <= len(requests) <= 3:
                    history.append({"error": "requires 1..3 read-only requests"})
                    continue
                for request in requests:
                    try:
                        output = self.store.query(request["tool"], request.get("args", {}))
                    except (ValueError, KeyError, TypeError) as exc:
                        output = {"error": str(exc)}
                    history.append({"request": request, "result": output})
                write_json(self.output / "query-log.json", self.store.journal)
                continue
            errors = validate_report(value, self.store)
            if errors:
                invalid = [{"finding": i, "quote": j, "ref": quote.get('ref')}
                           for i, finding in enumerate(value.get('findings', [])) if isinstance(finding, dict)
                           for j, quote in enumerate(finding.get('quotes', [])) if isinstance(quote, dict)
                           and not self.store.was_exposed(quote.get('ref'), quote.get('text', ''))]
                history.append({"validation_errors": errors, "invalid_quotes": invalid})
                continue
            if not self.store.unchanged():
                raise ValueError("source changed during reporting")
            write_json(self.output / "findings.json", value)
            text = render(value, self.store, self.manifest)
            (self.output / "report.md").write_text(text)
            write_json(self.output / "validation.json", {"status": "PASSED", "generation": self.store.generation,
                       "read_coverage": self.store.exposed, "report_sha256": file_hash(self.output / "report.md"),
                       "diagnostics_reviewed": [item['ref'] for item in self.store.diagnostics],
                       "runtime_verification": self.store.runtime_verification,
                       "note": "Quoted evidence and structured facts verified; interpretation remains subject to human review."})
            self.manifest["status"] = "COMPLETE"
            write_json(self.output / "manifest.json", self.manifest)
            return self.output / "report.md"
        write_json(self.output / "validation.json", {"status": "INCOMPLETE", "reason": "bounded repair budget exhausted", "read_coverage": self.store.exposed})
        raise RuntimeError("report validation exhausted; draft saved, evaluation unchanged")


def render(report, store, manifest):
    from .presentation import render_readable
    return render_readable(report,store)
