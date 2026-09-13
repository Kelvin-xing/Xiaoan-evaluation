"""One report entry point for all measurement methods, without implicit network calls."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from .measurement import VERSION, digest, retrieval_batch, cluster_interval, verified_outcome, run_perturbations, online_summary, answer_quality
from .comparative import pairwise, calibration
from .oracle_judge import validate, summarize

METHODS=('answer','retrieval','oracle','pairwise','cluster','outcome','perturbation','calibration','online')

def register(commands):
    p=commands.add_parser('measure',help='evaluate explicit measurement evidence; no implicit live API calls')
    p.add_argument('method',choices=METHODS);p.add_argument('input');p.add_argument('--output',required=True)
    p.add_argument('--provider',help='explicit MODULE:CALLABLE for pairwise or perturbation harness')
    p.add_argument('--egress-validator',help='MODULE:CALLABLE; required before invoking provider')

def plugin(name):
    module,sep,attribute=name.partition(':')
    if not sep:raise ValueError('plugin must be MODULE:CALLABLE')
    value=getattr(importlib.import_module(module),attribute)
    if not callable(value):raise ValueError('plugin is not callable')
    return value

def run(args):
    source=Path(args.input);spec=json.loads(source.read_text(encoding='utf-8'))
    if not isinstance(spec,dict) or spec.get('schema_version')!=VERSION:raise ValueError(f'schema_version must be {VERSION}')
    input_hash=digest(spec)  # Reject non-finite JSON before any provider invocation.
    out=Path(args.output)
    # Never overwrite input or an existing reviewer report.
    out.mkdir(parents=True,exist_ok=True)
    targets=[out/'measurement.json',out/'measurement.md']
    if any(p.exists() for p in targets):raise ValueError('measurement output already exists; use a new directory')
    provider=None
    if args.method in ('pairwise','perturbation'):
        if not args.provider or not args.egress_validator:raise ValueError('explicit provider and egress validator required')
        call=plugin(args.provider);check=plugin(args.egress_validator)
        def provider(request):
            if check(request) is not True:raise ValueError('measurement egress rejected')
            return call(request)
    if args.method=='answer':result={'answers':[answer_quality(r) for r in spec['rows']]}
    elif args.method=='retrieval':result=retrieval_batch(spec['rows'])
    elif args.method=='cluster':result=cluster_interval(spec['rows'],paired=spec.get('paired',False),seed=spec.get('seed',0))
    elif args.method=='oracle':
        assessments=[validate(r.get('assessment'),r['request']) for r in spec['rows']]
        result={'assessments':assessments,'summary':summarize(assessments)}
    elif args.method=='pairwise':result=pairwise(spec,provider)
    elif args.method=='outcome':result={'tasks':[{'task_id':r['spec']['task_id'],**verified_outcome(r['spec'],r.get('observation'))} for r in spec['rows']]}
    elif args.method=='perturbation':result=run_perturbations(spec['probes'],provider)
    elif args.method=='calibration':result=calibration(spec)
    else:result=online_summary(spec['rows'])
    envelope={'schema_version':VERSION,'method':args.method,'input_hash':input_hash,'result':result,
              'provenance':{'provider':args.provider,'egress_validator':args.egress_validator},
              'validity':'MEASUREMENT_ONLY_NOT_REAL_WORLD_SAFETY_CERTIFICATION'}
    content=json.dumps(envelope,ensure_ascii=False,indent=2,allow_nan=False)+'\n'
    targets[0].write_text(content,encoding='utf-8')
    targets[1].write_text(f'# {args.method} measurement\n\nInput hash: `{envelope["input_hash"]}`\n\nMissing observations stay unavailable. Counts and denominators are reported in the structured results.\n\n```json\n{json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)}\n```\n',encoding='utf-8')
    return 0
