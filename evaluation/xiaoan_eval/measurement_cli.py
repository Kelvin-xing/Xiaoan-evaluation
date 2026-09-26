"""One report entry point for all measurement methods, without implicit network calls."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from .measurement import VERSION, digest, retrieval_batch, cluster_interval, verified_outcome, run_perturbations, online_summary, answer_quality
from .comparative import pairwise, calibration
from .oracle_judge import validate, summarize

METHODS=('answer','retrieval','oracle','pairwise','cluster','outcome','perturbation','calibration','online','frozen-answer-evaluation','capsule-ablation')

def register(commands):
    p=commands.add_parser('measure',help='evaluate explicit measurement evidence; no implicit live API calls')
    p.add_argument('method',choices=METHODS);p.add_argument('input');p.add_argument('--output',required=True)
    p.add_argument('--provider',help='explicit MODULE:CALLABLE for evaluation or measurement')
    p.add_argument('--checkpoint-dir', help='reusable validated evaluation responses')
    p.add_argument('--subject-provider', help='explicit MODULE:CALLABLE for fixed-context capsule ablation')
    p.add_argument('--egress-validator',help='MODULE:CALLABLE; required before invoking provider')
    p.add_argument('--execute', action='store_true', help='call configured APIs')
    p.add_argument('--report', action='store_true', help='generate independent report after evaluation')
    p.add_argument('--evaluator-config', help='candidate evaluator-config directory; frozen answers stay unchanged')

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
    if args.method == 'frozen-answer-evaluation':
        from .frozen_cli import execute_frozen
        provider = plugin(args.provider) if args.provider else None
        if provider and args.egress_validator:
            call, check=provider,plugin(args.egress_validator)
            def provider(request):
                if check(request) is not True: raise ValueError('evaluation egress rejected')
                return call(request)
            if hasattr(call,'embeddings'):
                def embeddings(texts,task):
                    if check({'task':'embedding','texts':texts,'binding':task.get('binding')}) is not True:
                        raise ValueError('embedding egress rejected')
                    return call.embeddings(texts,task)
                provider.embeddings=embeddings
        execute_frozen(spec, out, execute=getattr(args, 'execute', False), provider=provider,
                       report=getattr(args, 'report', False),checkpoint_dir=args.checkpoint_dir,
                       evaluator_config=getattr(args,'evaluator_config',None))
        return 0
    if any((out/name).exists() for name in ('measurement.json','measurement.md')):
        raise ValueError('measurement output already exists; use a new directory')
    provider = plugin(args.provider) if args.provider else None
    if provider:
        if not args.egress_validator: raise ValueError('explicit egress validator required')
        call, check = provider, plugin(args.egress_validator)
        def provider(request):
            if check(request) is not True: raise ValueError('measurement egress rejected')
            return call(request)
    if args.method=='capsule-ablation':
        from .unified import run as run_ablation
        result=run_ablation(spec,provider,checkpoint_dir=args.checkpoint_dir,ablation=True,
                            subject_provider=plugin(args.subject_provider) if args.subject_provider else None)
    elif args.method=='answer':result={'answers':[answer_quality(r) for r in spec['rows']]}
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
    if True:
        (out/'measurement.json').write_text(content,encoding='utf-8')
        (out/'measurement.md').write_text(f'# {args.method} measurement\n\nInput hash: `{envelope["input_hash"]}`\n\nMissing observations stay unavailable. Counts and denominators are reported in the structured results.\n\n```json\n{json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)}\n```\n',encoding='utf-8')
    if args.method == 'capsule-ablation':
        from xiaoan_eval_core.reporting import markdown, workbook
        (out/'measurement.md').write_text(markdown(result), encoding='utf-8')
        workbook(result, out/'measurement.xlsx')
    return 0
