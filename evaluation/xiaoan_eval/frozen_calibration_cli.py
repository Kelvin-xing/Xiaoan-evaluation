"""Offline calibration commands for the canonical frozen-answer workflow."""
from __future__ import annotations

import json
from pathlib import Path

from xiaoan_eval_core.contracts import digest
from .frozen_calibration import (
    freeze_split, snapshot_calibration, build_benchmark, compare_calibration,
    record_adoption, judge_inputs, mark_validation_used_for_development,
)


def register_calibration_commands(subparsers):
    """Register under any argparse subparsers; dispatch via run_calibration_command."""
    root = subparsers.add_parser('frozen-calibration', help='凍結人工基準、配置及校準比較（離線）')
    commands = root.add_subparsers(dest='calibration_command', required=True)
    split = commands.add_parser('split', help='凍結 Minimal33 的 22/11 case 切分')
    split.add_argument('--cases', required=True, help='JSON array of 33 case IDs, or object with case_ids and metadata')
    split.add_argument('--seed', type=int, default=33)
    split.add_argument('--output', required=True)
    bench = commands.add_parser('benchmark', help='匯出已人工確認的校準標籤')
    bench.add_argument('--results', required=True)
    bench.add_argument('--split', required=True)
    bench.add_argument('--partition', choices=['calibration', 'validation'], default='calibration')
    bench.add_argument('--purpose', choices=['development', 'final-validation'], default='development')
    bench.add_argument('--output', required=True)
    snapshot = commands.add_parser('snapshot', help='凍結原版及候選配置，不改 active config')
    snapshot.add_argument('--baseline-config', required=True)
    snapshot.add_argument('--candidate-config', required=True)
    snapshot.add_argument('--split', required=True)
    snapshot.add_argument('--changes', required=True, help='修改理由 Markdown 檔案')
    snapshot.add_argument('--output', required=True, help='新的 calibration directory')
    compare = commands.add_parser('compare', help='以凍結人工標籤比較新舊 Judge 結果')
    compare.add_argument('--benchmark', required=True)
    compare.add_argument('--baseline', required=True)
    compare.add_argument('--candidate', required=True)
    compare.add_argument('--output', required=True)
    adopt = commands.add_parser('adopt', help='保存使用者採用紀錄，不自動覆寫 active config')
    adopt.add_argument('--directory', required=True)
    adopt.add_argument('--confirmed-by', required=True)
    adopt.add_argument('--scope', required=True, nargs='+', help='Judge/evaluator IDs')
    adopt.add_argument('--reason', required=True)
    adopt.add_argument('--comparison', required=True)
    inputs = commands.add_parser('inputs', help='匯出不含人工 gold 的凍結 Judge 輸入')
    inputs.add_argument('--results', required=True)
    inputs.add_argument('--split', required=True)
    inputs.add_argument('--partition', choices=['calibration', 'validation'], default='calibration')
    inputs.add_argument('--purpose', choices=['development', 'final-validation'], default='development')
    inputs.add_argument('--output', required=True)
    reuse = commands.add_parser('mark-holdout-used', help='記錄驗證集已用於開發，撤銷獨立性')
    reuse.add_argument('--split', required=True)
    reuse.add_argument('--reason', required=True)
    reuse.add_argument('--output', required=True)
    root.set_defaults(frozen_calibration_handler=run_calibration_command)
    return root


def _read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def _save(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2, allow_nan=False)


def run_calibration_command(args):
    command = args.calibration_command
    if command == 'split':
        data = _read(args.cases)
        value = freeze_split(data if isinstance(data, list) else data['case_ids'],
                             metadata={} if isinstance(data, list) else data.get('metadata', {}), seed=args.seed)
    elif command == 'benchmark':
        value = build_benchmark(_read(args.results), _read(args.split), partition=args.partition, purpose=args.purpose)
    elif command == 'snapshot':
        return snapshot_calibration(args.output, args.baseline_config, args.candidate_config,
                                    _read(args.split), changes=Path(args.changes).read_text(encoding='utf-8'))
    elif command == 'compare':
        value = compare_calibration(_read(args.benchmark), _read(args.baseline), _read(args.candidate))
    elif command == 'adopt':
        comparison = _read(args.comparison)
        return record_adoption(args.directory, confirmed_by=args.confirmed_by, scope=args.scope,
                               reason=args.reason, comparison_digest=digest(comparison))
    elif command == 'inputs':
        from .frozen_calibration import validate_split
        split = _read(args.split)
        validate_split(split)
        if args.partition == 'validation' and args.purpose != 'final-validation':
            raise ValueError('validation answers may not be exported for prompt development')
        value = judge_inputs(_read(args.results), split[args.partition + '_case_ids'])
    elif command == 'mark-holdout-used':
        value = mark_validation_used_for_development(_read(args.split), reason=args.reason)
    else:
        raise ValueError('unknown calibration command')
    _save(args.output, value)
    if command == 'compare':
        report = Path(args.output).with_suffix('.md')
        lines = ['# Judge 校準比較', '', '是否採用由使用者確認；此命令不修改生效配置。', '',
                 '| Judge | 改善 | 退步 | 候選缺失 |', '| --- | ---: | ---: | ---: |']
        for judge, values in value['by_judge'].items():
            lines.append(f"| {judge} | {values['improved']} | {values['regressed']} | {values['candidate_missing']} |")
        with report.open('x', encoding='utf-8') as stream:
            stream.write('\n'.join(lines) + '\n')
    return value
