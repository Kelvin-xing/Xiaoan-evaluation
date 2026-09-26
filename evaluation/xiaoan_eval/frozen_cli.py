"""One public entry point for generation, frozen evaluation, reports and review."""
from __future__ import annotations
import argparse
import importlib
import json
import os
from pathlib import Path
import sys
from uuid import uuid4

from .frozen_ingress import ROOT, SUITE, build_plan, validate_frozen_spec


def write_json(path, payload):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    content = json.dumps(payload, ensure_ascii=False, indent=2, allow_nan=False)+'\n'
    if path.exists() and path.read_text()!=content:
        raise ValueError(f'Immutable artifact exists: {path}; choose a new output directory')
    if not path.exists():
        temporary=path.with_name('.'+path.name+'.'+uuid4().hex+'.tmp')
        try:
            with temporary.open('x') as stream:
                temporary.chmod(0o600);stream.write(content);stream.flush();os.fsync(stream.fileno())
            try:
                os.link(temporary,path)
            except FileExistsError:
                if path.read_text()!=content: raise ValueError('Concurrent immutable artifact conflict')
        finally:
            temporary.unlink(missing_ok=True)


def load_plugin(value):
    module, separator, name = value.partition(':')
    if not separator: raise ValueError('Plugin must be MODULE:CALLABLE')
    return getattr(importlib.import_module(module), name)


def execute_frozen(spec, output, *, execute=False, provider=None, report=False, max_workers=None, checkpoint_dir=None, evaluator_config=None):
    from xiaoan_eval_core.orchestration import run_orchestration
    from .frozen_export import export_results_workbook
    from .frozen_provider import ConfiguredProvider
    out = Path(output);out.mkdir(parents=True,exist_ok=True)
    spec = validate_frozen_spec(spec)
    if evaluator_config:
        from xiaoan_eval_core.configuration import configure, snapshot
        configure(evaluator_config)
        spec['evaluation_config']=snapshot()
    write_json(out/'frozen-input.json',spec)
    from xiaoan_eval_core.results import validate_complete_results
    if (out/'results.json').exists():
        existing=json.loads((out/'results.json').read_text())
        validate_complete_results(existing)
        export_results_workbook(existing,out/'results.xlsx')
        if report:
            generate_report(out/'results.json',out/'report',execute=execute)
        return existing
    call = provider or (ConfiguredProvider(out/'provider-artifacts') if execute else None)
    if isinstance(call,ConfiguredProvider):
        from .frozen_provider import transport_options
        if spec.get('provider_options',{}) != transport_options(call.values):
            raise ValueError('Provider options differ from frozen evaluation input')
    try:
        result = run_orchestration(spec, faithfulness_provider=call,rubric_provider=call,
                  generation_provider=call, embedding_provider=getattr(call,'embeddings',None),
                  checkpoint_dir=checkpoint_dir or out/'checkpoint',max_workers=max_workers)
    finally:
        if provider is None and isinstance(call,ConfiguredProvider):
            call.close()
    from .frozen_ingress import file_hash
    from xiaoan_eval_core.results import seal_complete_results, validate_complete_results
    artifacts = []
    for folder in ('provider-artifacts','subject-checkpoint','checkpoint'):
        for artifact in sorted((out/folder).glob('*')):
            if artifact.is_file() and artifact.suffix in ('.json','.jsonl'):
                artifacts.append({'id':file_hash(artifact),'path':str(artifact.relative_to(out)),
                                  'sha256':file_hash(artifact),'type':folder})
    result['artifacts'] = [*result.get('artifacts',[]),*artifacts]
    seal_complete_results(result);validate_complete_results(result)
    write_json(out/'results.json',result)
    export_results_workbook(result,out/'results.xlsx')
    if report:
        generate_report(out/'results.json',out/'report',execute=execute)
    return result


def generate_report(results, output, *, execute=False, provider=None):
    if str(ROOT) not in sys.path: sys.path.insert(0,str(ROOT))
    from evaluation_report_agent.evidence import EvidenceStore
    from evaluation_report_agent.agent import ReportAgent, KaroProvider
    store=EvidenceStore(Path(results))
    if not execute and provider is None:
        write_json(Path(output)/'catalog.json',store.catalog())
        return None
    return ReportAgent(store,provider or KaroProvider(),Path(output)).run()


def register_generation(commands):
    retry=commands.add_parser('retry-evaluation',help='以封存回答選擇性重跑不可用的評估格位')
    retry.add_argument('--from-results',required=True)
    retry.add_argument('--output',required=True)
    retry.add_argument('--stages',nargs='+',choices=('extraction','rubric','assessment','relevancy'))
    retry.add_argument('--answer-ids',nargs='+')
    retry.add_argument('--judges',nargs='+')
    retry.add_argument('--add-judges',nargs='+',help='向原凍結回答計畫追加已配置 Judge，不改寫回答 manifest')
    retry.add_argument('--reuse-checkpoints',nargs='+',type=Path,
                       help='從尚未封存的評估目錄只匯入成功的檢查點；不修改來源')
    retry.add_argument('--execute',action='store_true')
    retry.add_argument('--new-evaluator-cohort',action='store_true',
                       help='配置變更時保留凍結回答，重新評估所有格位')
    retry.add_argument('--adopt-current-runtime',action='store_true',
                       help='只允許根 schema 收緊時局部重跑，並記錄混合評測設定來源')
    retry.add_argument('--max-workers',type=int,default=2)
    retry.add_argument('--provider-max-inflight',type=int,
                       help='每個供應商的執行期並行上限，不修改凍結評測設定或檢查點鍵')
    lanes=commands.add_parser('retry-subject-lanes',help='只重生選中的失敗 subject/case lane')
    lanes.add_argument('--from-results',required=True)
    lanes.add_argument('--lanes',nargs='+',required=True,metavar='SUBJECT:CASE')
    lanes.add_argument('--output',required=True)
    lanes.add_argument('--execute',action='store_true')
    lanes.add_argument('--adopt-current-runtime',action='store_true')
    lanes.add_argument('--subjects-only',action='store_true',
                       help='只重跑 subject；新答案的 Judge 格位保持不可用，稍後單獨補評測')
    lanes.add_argument('--max-workers',type=int,default=2)
    routing=commands.add_parser('route-analysis',help='從 frozen trace 離線建立路由模式混淆矩陣')
    routing.add_argument('results');routing.add_argument('--output',required=True)
    cost=commands.add_parser('cost',help='根據凍結回答 tokens 與官方價格離線估算成本')
    cost.add_argument('results');cost.add_argument('--output',required=True);cost.add_argument('--pricing-catalog')
    for name in ('run','matrix'):
        parser=commands.add_parser(name,help='產生 canonical frozen answers，接共用評估引擎')
        parser.add_argument('--cases',nargs='+',help='Minimal33 case IDs; default all 33')
        parser.add_argument('--subjects',nargs='+',help='Configured model IDs')
        parser.add_argument('--judges',nargs='+',help='Configured Judge model IDs')
        parser.add_argument('--selection-dir',default=str(SUITE))
        parser.add_argument('--subject-mode',choices=('chatflow','http','direct'),default='chatflow')
        parser.add_argument('--base-url')
        parser.add_argument('--output',required=True)
        parser.add_argument('--execute',action='store_true',help='Explicitly call configured providers')
        parser.add_argument('--report',action='store_true')
        parser.add_argument('--max-workers',type=int,default=2)
    report=commands.add_parser('report',help='从完整 results.json 生成报告')
    report.add_argument('results');report.add_argument('--output',required=True);report.add_argument('--execute',action='store_true')
    review=commands.add_parser('import-human-review',help='導入 results.xlsx 的 Human Review，產生新 generation')
    review.add_argument('results');review.add_argument('workbook');review.add_argument('--output',required=True)
    review.add_argument('--confirmed-by')
    export=commands.add_parser('export-human-review',help='從完整 JSON 重新生成含 Human Review 的 workbook；不重算聚合')
    export.add_argument('results');export.add_argument('--output',required=True)
    refresh=commands.add_parser('refresh-derived-results',help='離線重算凍結結果的衍生聚合並寫入新的封存目錄')
    refresh.add_argument('results');refresh.add_argument('--output',required=True)
    refresh.add_argument('--case-taxonomy',help='離線追加已標記的案例分類，不重跑答案或 Judge')
    merge=commands.add_parser('merge-subject-results',help='合併同案例同 Judges 的獨立 subject 封存結果')
    merge.add_argument('--base',required=True)
    merge.add_argument('--add',required=True)
    merge.add_argument('--output',required=True)
    from .frozen_calibration_cli import register_calibration_commands
    register_calibration_commands(commands)


def dispatch(args):
    if args.command=='merge-subject-results':
        from .frozen_merge import merge_subject_results
        merge_subject_results(json.loads(Path(args.base).read_text()), json.loads(Path(args.add).read_text()),
                              args.output, base_path=args.base, addition_path=args.add)
        return 0
    if args.command in ('retry-evaluation','retry-subject-lanes'):
        from .frozen_retry import retry_evaluation
        from xiaoan_eval_core.results import validate_complete_results
        source=Path(args.from_results)
        parent=validate_complete_results(json.loads(source.read_text()))
        out=Path(args.output)
        if out.resolve()==source.parent.resolve():
            raise ValueError('Retry must use a new output directory')
        if args.command=='retry-evaluation':
            if args.provider_max_inflight is not None and args.provider_max_inflight < 1:
                raise ValueError('--provider-max-inflight must be positive')
            spec=json.loads((source.parent/'frozen-input.json').read_text())
            validate_frozen_spec(spec)
            if args.add_judges:
                from .frozen_retry import extend_judges
                from .frozen_provider import identity
                spec=extend_judges(spec,[identity('XIAOAN_CLAIM_ASSESSOR_MODEL',model=name)
                                         for name in args.add_judges])
            if args.reuse_checkpoints and not args.execute:
                for folder in args.reuse_checkpoints:
                    if not (folder/'checkpoint').is_dir():
                        raise ValueError(f'Checkpoint directory missing: {folder}')
            outcome=retry_evaluation(spec,parent,out,stages=args.stages,answer_ids=args.answer_ids,
                             judge_ids=args.judges,execute=True,max_workers=args.max_workers,
                             provider_max_inflight=args.provider_max_inflight,
                             new_evaluator_cohort=args.new_evaluator_cohort,
                             adopt_current_runtime=args.adopt_current_runtime,dry_run=not args.execute,
                             checkpoint_sources=args.reuse_checkpoints if args.execute else None)
            if not args.execute: print(json.dumps(outcome,ensure_ascii=False,indent=2))
            elif (source.parent/'plan.json').is_file():
                write_json(out/'plan.json',json.loads((source.parent/'plan.json').read_text()))
            return 0
        plan=json.loads((source.parent/'plan.json').read_text())
        validate_frozen_spec(plan)
        requested=set()
        for value in args.lanes:
            subject,separator,case=value.partition(':')
            if not separator or not subject or not case:
                raise ValueError('Lane must be SUBJECT:CASE')
            requested.add((subject,case))
        if parent['manifest']!=plan['manifest']:
            raise ValueError('Parent and subject plan have different manifests')
        if (out/'results.json').exists():
            raise ValueError('Retry output already sealed; choose a new directory')
        from xiaoan_eval_core.configuration import snapshot
        from .frozen_retry import compatible_schema_update
        if parent['evaluation_config']!=snapshot() and not (args.adopt_current_runtime and
                compatible_schema_update(parent['evaluation_config'],snapshot())):
            raise ValueError('Evaluator configuration changed; start a new evaluation cohort before subject retry')
        current={(row['subject_id'],row['case_id']):[] for row in parent['answers']}
        for row in parent['answers']:
            current[(row['subject_id'],row['case_id'])].append(row)
        if not requested <= current.keys() or any(
                all(row['status']=='AVAILABLE' and not row.get('trace',{}).get('safety',{}).get('fallback_reason')
                    for row in current[lane]) for lane in requested):
            raise ValueError('Select existing subject lanes with unavailable answers')
        mode=plan['plan']['subject_mode']
        if mode not in {'chatflow','direct'}:
            raise ValueError('Partial subject retry currently supports chatflow/direct modes')
        from .frozen_provider import ConfiguredProvider,transport_options
        if not args.adopt_current_runtime and transport_options(ConfiguredProvider().values)!=plan.get('provider_options',{}):
            raise ValueError('Provider options differ from frozen subject plan')
        if not args.execute:
            print(json.dumps({'parent_generation':parent['result_generation'],
                              'selected_subject_lanes':sorted([list(lane) for lane in requested])},
                             ensure_ascii=False,indent=2))
            return 0
        from .frozen_generation import generate,LocalChatflowSubject,DirectSubject
        call=ConfiguredProvider(out/'provider-artifacts')
        try:
            if mode=='chatflow': subject=LocalChatflowSubject()
            else: subject=DirectSubject(call)
            frozen=generate(plan,subject,checkpoint_dir=out/'subject-checkpoint',max_workers=args.max_workers,
                            previous_rows=parent['answers'],retry_lanes=requested)
            write_json(out/'plan.json',plan)
            prior_ids={old['answer_id'] for old in parent['answers']}
            changed=[row['answer_id'] for row in frozen['rows'] if row['answer_id'] not in prior_ids]
            provider = (lambda _request: (_ for _ in ()).throw(LookupError('SUBJECTS_ONLY'))) if args.subjects_only else call
            retry_evaluation(frozen,parent,out,answer_ids=changed,provider=provider,max_workers=args.max_workers,
                             adopt_current_runtime=args.adopt_current_runtime)
        finally:
            call.close()
        return 0
    if args.command=='route-analysis':
        from xiaoan_eval_core.results import validate_complete_results,seal_complete_results
        from xiaoan_eval_core.routing import route_analysis
        from .frozen_export import export_results_workbook
        value=validate_complete_results(json.loads(Path(args.results).read_text()))
        parent=value['result_generation']
        value['aggregates']['routing']=route_analysis(value['answers'],value.get('plan',{}))
        value.setdefault('provenance',[]).append({'operation':'route_mode_analysis','parent_generation':parent})
        seal_complete_results(value)
        write_json(Path(args.output)/'results.json',value)
        export_results_workbook(value,Path(args.output)/'results.xlsx')
        return 0
    if args.command=='cost':
        from xiaoan_eval_core.results import validate_complete_results,seal_complete_results
        from xiaoan_eval_core.costs import build_answer_costs,load_catalog
        from .frozen_export import export_results_workbook
        value=validate_complete_results(json.loads(Path(args.results).read_text()))
        parent=value['result_generation']
        value['aggregates']['answer_costs']=build_answer_costs(value['answers'],load_catalog(args.pricing_catalog))
        value.setdefault('provenance',[]).append({'operation':'official_price_estimate','parent_generation':parent})
        seal_complete_results(value)
        write_json(Path(args.output)/'results.json',value)
        export_results_workbook(value,Path(args.output)/'results.xlsx')
        return 0
    if args.command in ('run','matrix'):
        from .frozen_provider import identity, ConfiguredProvider, transport_options
        from .frozen_generation import generate, LocalChatflowSubject, HttpChatflowSubject, DirectSubject
        from xiaoan_eval_core import model_config
        subjects=[identity('XIAOAN_RESPONSE_MODEL',model=m) for m in (args.subjects or [model_config.model('XIAOAN_RESPONSE_MODEL')])]
        judges=[identity('XIAOAN_CLAIM_ASSESSOR_MODEL',model=m) for m in (args.judges or [model_config.model('XIAOAN_CLAIM_ASSESSOR_MODEL')])]
        if args.command=='run' and len(subjects)!=1: raise ValueError('run accepts one subject; use matrix')
        rule=ROOT/'evaluation/evaluator-config/rating-rule.yml'
        values=model_config.read_env()
        options=transport_options(values)
        spec=build_plan(subjects,judges,identity('XIAOAN_CLAIM_EXTRACTOR_MODEL'),case_ids=args.cases,
                        selection_dir=args.selection_dir,rating_rule=rule,relevancy_generator=identity('XIAOAN_RELEVANCY_MODEL'),
                        subject_mode=args.subject_mode,provider_options=options)
        spec['embedding_identity']={'provider':'configured','model':values.get('XIAOAN_EMBEDDING_MODEL') or values.get('GOOGLE_EMBEDDING_MODEL'),
            'revision':values.get('XIAOAN_EMBEDDING_REVISION','provider-unspecified'),
            'dimensions':values.get('GOOGLE_EMBEDDING_DIMENSIONS'), 'task_type':values.get('GOOGLE_EMBEDDING_TASK_TYPE')}
        out=Path(args.output)
        write_json(out/'plan.json',spec)
        if not args.execute:
            print(f'Plan saved: {out / "plan.json"}; no API calls')
            return 0
        call=ConfiguredProvider(out/'provider-artifacts')
        try:
            if args.subject_mode=='chatflow': subject=LocalChatflowSubject()
            elif args.subject_mode=='http':
                if not args.base_url: raise ValueError('--base-url required for HTTP mode')
                subject=HttpChatflowSubject(args.base_url)
            else: subject=DirectSubject(call)
            frozen=generate(spec,subject,checkpoint_dir=out/'subject-checkpoint',max_workers=args.max_workers)
            execute_frozen(frozen,out,execute=True,provider=call,report=args.report,max_workers=args.max_workers)
        finally:
            call.close()
    elif args.command=='report':
        generate_report(args.results,args.output,execute=args.execute)
    elif args.command=='import-human-review':
        from .frozen_review import import_review_rows,read_review_workbook
        from .frozen_export import export_results_workbook
        value=import_review_rows(json.loads(Path(args.results).read_text()),read_review_workbook(args.workbook),confirmed_by=args.confirmed_by)
        write_json(Path(args.output)/'results.json',value)
        export_results_workbook(value,Path(args.output)/'results.xlsx')
    elif args.command=='export-human-review':
        from .frozen_export import export_results_workbook
        export_results_workbook(json.loads(Path(args.results).read_text()),Path(args.output))
    elif args.command=='refresh-derived-results':
        import hashlib
        import yaml
        from os.path import relpath
        from xiaoan_eval_core.results import aggregate_complete_results, seal_complete_results, validate_complete_results
        from xiaoan_eval_core.taxonomy import case_taxonomy
        from xiaoan_eval_core.costs import build_answer_costs
        from .frozen_export import export_results_workbook
        source=Path(args.results).resolve()
        out=Path(args.output).resolve()
        if out==source.parent or (out/'results.json').exists():
            raise ValueError('Refresh requires a new output directory')
        parent=validate_complete_results(json.loads(source.read_text()))
        parent_generation=parent['result_generation']
        result=parent
        if args.case_taxonomy:
            taxonomy_path=Path(args.case_taxonomy).resolve()
            mapping=json.loads(taxonomy_path.read_text())['cases']
            case_ids={answer['case_id'] for answer in result['answers']}
            if not case_ids.issubset(mapping):
                raise ValueError('case taxonomy missing frozen case IDs')
            taxonomy={}
            source_hashes={}
            for case_id in sorted(case_ids):
                case_path=taxonomy_path.parent/(case_id+'.yaml')
                contents=case_path.read_bytes()
                row=yaml.safe_load(contents)
                labels=case_taxonomy(row)
                if [labels['test_type'],labels['scenario_category'],labels['scenario_tags']] != mapping[case_id]:
                    raise ValueError(f'case taxonomy mismatch: {case_id}')
                taxonomy[case_id]=labels
                source_hashes[case_id]=hashlib.sha256(contents).hexdigest()
            for answer in result['answers']:
                answer.update(taxonomy[answer['case_id']])
            result['provenance']=[*result.get('provenance',[]), {'operation':'classify_cases',
                'taxonomy_path':str(taxonomy_path),'taxonomy_sha256':hashlib.sha256(taxonomy_path.read_bytes()).hexdigest(),
                'case_sha256':source_hashes,'approval_scope':'diagnostic_metadata_only'}]
        result['aggregates']=aggregate_complete_results(result)
        result['aggregates']['answer_costs']=build_answer_costs(result['answers'])
        result['provenance']=[*result.get('provenance',[]), {'operation':'refresh_derived_results',
            'parent_generation':parent_generation,'source_path':str(source)}]
        for artifact in result['artifacts']:
            path=Path(artifact['path'])
            if not path.is_absolute():
                artifact['path']=relpath(source.parent/path,out)
        seal_complete_results(result);validate_complete_results(result)
        write_json(out/'results.json',result)
        export_results_workbook(result,out/'results.xlsx')
    elif args.command=='frozen-calibration':
        from .frozen_calibration_cli import run_calibration_command as calibrate
        return calibrate(args)
    else:
        raise ValueError('Unknown canonical command')
    return 0
