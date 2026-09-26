"""Shared subject generation, persistent case lanes and frozen checkpoint rows."""
from __future__ import annotations
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from uuid import uuid4

from xiaoan_eval_core.contracts import digest
from .frozen_ingress import ROOT, freeze_answer, validate_frozen_spec


class LocalChatflowSubject:
    """In-process real Chatflow, including its captured Composer context."""
    def __init__(self):
        location = str(ROOT / 'tech_multimodels/chatflow/poc')
        if location not in sys.path:
            sys.path.insert(0, location)
        from chat_service import load_capsules
        self.capsules = load_capsules()

    def start(self, subject, case_id):
        from state import ConversationState
        return ConversationState()

    def turn(self, subject, row, state, history):
        from chat_service import run_turn
        from context_snapshot import capture_turn
        from xiaoan_eval_core import model_config
        debug = []
        answer, state = capture_turn(run_turn)(row['question'], self.capsules, state=state,
            safety_model=model_config.model('XIAOAN_SAFETY_MODEL'),
            router_model=subject['model'], response_model=subject['model'], debug_callback=debug.append)
        trace = debug[0] if debug else {}
        from .frozen_provider import usage
        composer=trace.get('effective_context_snapshot',{}).get('invocations',{}).get('composer',{})
        tokens=usage({'usage':composer.get('usage') or {}})
        if trace.get('route',{}).get('capsule_id')=='safety_clarification' and composer.get('status')=='NOT_APPLICABLE':
            tokens={'input_tokens':0,'output_tokens':0,'total_tokens':0,'no_model_call':True}
        fallback = trace.get('safety', {}).get('fallback_reason')
        return {'text':answer, 'trace':trace, 'usage':tokens,
                **({'status':'UNAVAILABLE', 'reason':'SAFETY_CLASSIFIER_FALLBACK'} if fallback else {})}, state

    def snapshot_state(self,state):
        from dataclasses import asdict
        value=asdict(state);value['grounded_capsule_ids']=sorted(value['grounded_capsule_ids'])
        return value

    def restore_state(self,value):
        from state import ConversationState
        value=deepcopy(value);value['grounded_capsule_ids']=set(value['grounded_capsule_ids'])
        return ConversationState(**value)


class HttpChatflowSubject:
    def __init__(self, base_url):
        self.base_url = base_url
    def start(self, subject, case_id):
        from .transport import FastAPITransport
        from xiaoan_eval_core import model_config
        transport = FastAPITransport(self.base_url, models={
            'safety':model_config.model('XIAOAN_SAFETY_MODEL'), 'router':subject['model'], 'response':subject['model']})
        return transport, transport.create_conversation()
    def turn(self, subject, row, state, history):
        transport, conversation = state
        return transport.send_turn(conversation, row['question']), state


class DirectSubject:
    """Explicit direct model mode; no invented Chatflow context/trace."""
    def __init__(self, provider): self.provider = provider
    def start(self, subject, case_id): return None
    def turn(self, subject, row, state, history):
        return self.provider.subject(subject, row['question'], history, []), state
    def snapshot_state(self,state): return None
    def restore_state(self,value): return None


def generate(spec, subject_provider, *, checkpoint_dir, max_workers=2, previous_rows=None, retry_lanes=None):
    directory = Path(checkpoint_dir)
    directory.mkdir(parents=True, exist_ok=True)
    result = deepcopy(spec)
    subjects = {s['id']:s for s in spec['plan']['subjects']}
    lanes = {}
    for row in spec['rows']:
        lanes.setdefault((row['subject_id'],row['case_id']),[]).append(row)
    previous = {}
    if previous_rows is not None:
        validate_frozen_spec({**spec, 'rows':previous_rows})
        for row in previous_rows:
            previous.setdefault((row['subject_id'],row['case_id']),[]).append(row)
        if set(previous) != set(lanes):
            raise ValueError('Previous subject lanes differ from frozen plan')
        if not retry_lanes or not set(retry_lanes) <= set(lanes):
            raise ValueError('Select existing subject lanes to retry')
        if any(all(r['status']=='AVAILABLE' and not r.get('trace',{}).get('safety',{}).get('fallback_reason')
                   for r in previous[key]) for key in retry_lanes):
            raise ValueError('Subject retry requires an unavailable lane')

    def lane(item):
        key, planned = item
        if previous and key not in retry_lanes:
            return previous[key]
        planned.sort(key=lambda r:r['turn'])
        path = directory / (digest([spec['manifest']['manifest_digest'],key]) + '.json')
        progress_path=path.with_suffix('.progress.json')
        if path.exists():
            saved = json.loads(path.read_text())
            check = {**spec,'rows':saved,'planned_subjects':[key[0]],'planned_turns':{key[1]:spec['planned_turns'][key[1]]}}
            validate_frozen_spec(check)
            # Freeze complete lane success; failed lane requires explicit new generation.
            return saved
        subject, history, rows, state = subjects[key[0]], [], [], None
        generation_id = str(uuid4())
        failed = False
        if progress_path.exists():
            progress=json.loads(progress_path.read_text())
            if progress.get('in_flight'):
                raise ValueError('Interrupted subject call outcome unknown; choose an explicit new generation')
            if not hasattr(subject_provider,'restore_state'):
                raise ValueError('Subject transport cannot safely resume; choose an explicit new generation')
            rows=progress['rows'];history=progress['history'];generation_id=progress['generation_id']
            state=subject_provider.restore_state(progress['state']);failed=progress['failed']
        try:
            if not rows: state = subject_provider.start(subject,key[1])
        except Exception as exc:
            failed = type(exc).__name__
        def save_progress(in_flight=False):
            current={'rows':rows,'history':history,'generation_id':generation_id,'failed':failed,
                     'state':subject_provider.snapshot_state(state) if state is not None and hasattr(subject_provider,'snapshot_state') else None,
                     'in_flight':in_flight}
            temporary=progress_path.with_suffix('.'+uuid4().hex+'.tmp')
            temporary.write_text(json.dumps(current,ensure_ascii=False));temporary.chmod(0o600);temporary.replace(progress_path)
        for row in planned[len(rows):]:
            started = datetime.now(timezone.utc).isoformat()
            begin = time.monotonic()
            if failed:
                response = {'status':'UNAVAILABLE','error_type':str(failed)}
            else:
                try:
                    save_progress(in_flight=True)
                    response, state = subject_provider.turn(subject,row,state,history)
                except Exception as exc:
                    response = {'status':'UNAVAILABLE','error_type':type(exc).__name__}
                    failed = type(exc).__name__
            response = {**response,'started_at':started,'completed_at':datetime.now(timezone.utc).isoformat(),
                        'elapsed_ms':(time.monotonic()-begin)*1000}
            raw_path = directory / (digest([generation_id,row['planned_unit_id']])+'.raw.json')
            raw_path.write_text(json.dumps({'question':row['question'],'history':history,'response':response},ensure_ascii=False,indent=2))
            raw_path.chmod(0o600)
            frozen = freeze_answer(row,response,history,generation_id=generation_id)
            frozen['raw_artifact'] = {'path':str(raw_path.resolve()),'sha256':__import__('hashlib').sha256(raw_path.read_bytes()).hexdigest()}
            frozen['row_digest'] = digest({k:v for k,v in frozen.items() if k!='row_digest'})
            rows.append(frozen)
            if frozen['status']=='AVAILABLE':
                history.extend([{'role':'user','content':row['question']},{'role':'assistant','content':frozen['answer']}])
            else:
                failed = failed or 'PREVIOUS_TURN_UNAVAILABLE'
            save_progress()
        temporary = path.with_suffix('.'+uuid4().hex+'.tmp')
        temporary.write_text(json.dumps(rows,ensure_ascii=False,indent=2)); temporary.chmod(0o600)
        temporary.replace(path)
        return rows

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        result['rows'] = [r for group in executor.map(lane,lanes.items()) for r in group]
    return validate_frozen_spec(result)
