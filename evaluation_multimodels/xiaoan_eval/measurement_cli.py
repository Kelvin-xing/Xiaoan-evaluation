"""One report entry point for all measurement methods, without implicit network calls."""
from __future__ import annotations
import importlib
import json
from pathlib import Path
from .measurement import VERSION, digest, retrieval_batch, cluster_interval, verified_outcome, run_perturbations, online_summary, answer_quality
from .comparative import pairwise, calibration
from .oracle_judge import validate, summarize

METHODS=('answer','retrieval','oracle','pairwise','cluster','outcome','perturbation','calibration','online','unified','staged','capsule-ablation')

def register(commands):
    p=commands.add_parser('measure',help='evaluate explicit measurement evidence; no implicit live API calls')
    p.add_argument('method',choices=METHODS);p.add_argument('input');p.add_argument('--output',required=True)
    p.add_argument('--provider',help='explicit MODULE:CALLABLE for pairwise or perturbation harness')
    p.add_argument('--checkpoint-dir', help='reusable validated unified evaluation responses')
    p.add_argument('--subject-provider', help='explicit MODULE:CALLABLE for fixed-context capsule ablation')
    p.add_argument('--egress-validator',help='MODULE:CALLABLE; required before invoking provider')
    p.add_argument('--rubric-provider', help='explicit MODULE:CALLABLE for staged rubric judging')
    p.add_argument('--relevancy-generator', help='explicit MODULE:CALLABLE for staged reverse-question generation')
    p.add_argument('--embedding-provider', help='explicit MODULE:CALLABLE for staged answer relevancy embeddings')
    p.add_argument('--rating-rule', default='ratings rule.yml', help='rating rule for staged rubric judging')
    p.add_argument('--legacy-output', action='store_true', help='emit deprecated measurement.* files for compatibility')

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
    canonical = args.method in ('unified', 'staged')
    targets=[out/'results.json', out/'results.md', out/'results.xlsx'] if canonical else [out/'measurement.json',out/'measurement.md']
    if args.method in ('unified', 'capsule-ablation') and (args.method == 'capsule-ablation' or getattr(args, 'legacy_output', False)):
        targets.append(out / 'measurement.xlsx')
    if canonical and getattr(args, 'legacy_output', False):
        targets.extend([out/'measurement.json', out/'measurement.md'])
    if any(p.exists() for p in targets):raise ValueError('measurement output already exists; use a new directory')
    provider=None
    if args.method in ('pairwise','perturbation') or (args.method in ('unified','staged','capsule-ablation') and args.provider):
        if not args.provider or not args.egress_validator:raise ValueError('explicit provider and egress validator required')
        call=plugin(args.provider);check=plugin(args.egress_validator)
        def provider(request):
            if check(request) is not True:raise ValueError('measurement egress rejected')
            return call(request)
    if args.method in ('unified','capsule-ablation'):
        from .unified import load_records, run as run_unified
        spec = load_records(spec, source)
        subject_provider = None
        if getattr(args, 'subject_provider', None):
            if not args.egress_validator:
                raise ValueError('explicit egress validator required for subject generation')
            subject_call = plugin(args.subject_provider)
            subject_check = plugin(args.egress_validator)
            def subject_provider(request):
                if subject_check(request) is not True:
                    raise ValueError('subject egress rejected')
                return subject_call(request)
        result = run_unified(spec, provider, checkpoint_dir=getattr(args, 'checkpoint_dir', None),
                             ablation=args.method == 'capsule-ablation', subject_provider=subject_provider)
    elif args.method=='staged':
        from xiaoan_eval_core.orchestration import run_orchestration
        from .rules import load_rating_rule
        def staged_plugin(name, kind):
            if not name: return None
            if not args.egress_validator: raise ValueError(f'--egress-validator is required for {kind}')
            call=plugin(name); check=plugin(args.egress_validator)
            def guarded(request):
                if check(request) is not True: raise ValueError(f'{kind} egress rejected')
                return call(request)
            return guarded
        def embed_plugin(name):
            if not name: return None
            if not args.egress_validator: raise ValueError('--egress-validator is required for embedding')
            call=plugin(name); check=plugin(args.egress_validator)
            def guarded(texts, task):
                if check({'task':'answer_relevancy_embedding','texts':texts,'binding':task.get('binding')}) is not True:
                    raise ValueError('embedding egress rejected')
                return call(texts, task)
            return guarded
        rule=load_rating_rule(args.rating_rule) if args.rubric_provider else None
        result=run_orchestration(spec, faithfulness_provider=provider,
            rubric_provider=staged_plugin(args.rubric_provider,'rubric'),
            generation_provider=staged_plugin(args.relevancy_generator,'relevancy generation'),
            embedding_provider=embed_plugin(args.embedding_provider), rating_rule=rule,
            checkpoint_dir=getattr(args,'checkpoint_dir',None))
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
    if not canonical or getattr(args, 'legacy_output', False):
        (out/'measurement.json').write_text(content,encoding='utf-8')
        (out/'measurement.md').write_text(f'# {args.method} measurement\n\nInput hash: `{envelope["input_hash"]}`\n\nMissing observations stay unavailable. Counts and denominators are reported in the structured results.\n\n```json\n{json.dumps(result,ensure_ascii=False,indent=2,allow_nan=False)}\n```\n',encoding='utf-8')
    if args.method == 'unified':
        from xiaoan_eval_core.results import build_results, write_results_workbook
        compact = build_results(spec.get('rows', []), faithfulness_stage=result.get('cells', []))
        write_results_workbook(compact, out / 'results.xlsx')
        (out / 'results.json').write_text(json.dumps(compact, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        (out / 'results.md').write_text(f'# Unified evaluation results\n\nInput hash: `{input_hash}`\n\nCanonical workbook sheets: Overview, Answers, Scores, Claims, Rating_Details.\n', encoding='utf-8')
        if getattr(args, 'legacy_output', False):
            from xiaoan_eval_core.reporting import markdown, workbook
            (out/'measurement.md').write_text(markdown(result), encoding='utf-8')
            workbook(result, out/'measurement.xlsx')
    if args.method == 'capsule-ablation':
        from xiaoan_eval_core.reporting import markdown, workbook
        (out/'measurement.md').write_text(markdown(result), encoding='utf-8')
        workbook(result, out/'measurement.xlsx')
    if args.method == 'staged':
        from xiaoan_eval_core.results import write_results_workbook
        write_results_workbook(result['results'], out / 'results.xlsx')
        (out / 'results.json').write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + '\n', encoding='utf-8')
        (out / 'results.md').write_text(f'# Staged evaluation results\n\nInput hash: `{input_hash}`\n\nCanonical workbook sheets: Overview, Answers, Scores, Claims, Rating_Details.\n', encoding='utf-8')
    return 0
