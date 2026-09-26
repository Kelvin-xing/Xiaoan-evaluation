# 最小32案整改回归：运行与恢复

本次集合共96轮：TC-01、04、05、09、10、11、12、14、15、17、18、21、22、23、24、26、28、29、30、35、37、42、48、51、53、57、61、62、63、66、72、74。

本任务已明确授权这些案例及必要证据调用当前KaroAPI。脚本限制在该集合并核对provider主机；不输出API key。不要将此授权扩大到其他案例、provider或发布完整trace。

## 本次产物

- 首轮：`evaluation/runs/2026-09-14-minimal32-regression/`，77条回答；8个失败终止点及11个依赖未执行轮次保留。
- 5案回答补跑：`evaluation/runs/2026-09-14-minimal32-provider-retry/`，14条回答；TC-61/T2护栏拒绝，T3未运行。
- 原批次6轮主Judge补评：同级`.2026-09-14-minimal32-judge-retry.private/`，只对原本没有有效Judge的轮次发起新调用。
- 独立归因：各运行名加`-attribution.private`的点目录；每条记录绑定答案SHA、snapshot_id、完整请求hash。成功结果缓存，失败重试历史保留。
- 完整对话链的诊断选择：首轮目录`RETRIES.zh-CN.md`、`retry-summary.json`、`diagnostic-selected-turns.json`。原批次不覆盖。

## 命令约定

从仓库根运行，使用`/Users/mingjiexing/anaconda3/bin/python3`。调用前保留现有`.env`，不要复制凭据进脚本。`--execute`代表实际付费调用；没有该参数只准备/检查。

新一次同版完整案例运行示例（另取唯一run-id）：

```sh
/Users/mingjiexing/anaconda3/bin/python3 evaluation/examples/run_minimal32_remediation.py --execute --workers 2 --timeout-seconds 180 --run-id NEW-UNIQUE-RUN --cases TC-48 TC-61
```

复用回答，仅补失败Judge：

```sh
/Users/mingjiexing/anaconda3/bin/python3 evaluation/examples/rejudge_remediation_frozen.py --execute --source-run SOURCE-RUN --output-run NEW-JUDGE-RUN --cases TC-11 --only-missing --workers 2
```

补独立归因（成功缓存不重调）：

```sh
/Users/mingjiexing/anaconda3/bin/python3 evaluation/examples/run_remediation_attribution.py SOURCE-RUN --execute --workers 2
```

同一个回答批次运行期间不要修改其manifest绑定的runtime、content、oracle、评估核心代码。新版本必须新建run-id；不能覆盖旧manifest。跨版本不要复用旧Judge输出。补回答默认从案例第一轮开始，避免人工拼接对话；仅完整成功的案例尝试可替换诊断视图中的案例链。

报告命令不调用provider：

```sh
/Users/mingjiexing/anaconda3/bin/python3 evaluation/examples/summarize_minimal32_remediation.py SOURCE-RUN
/Users/mingjiexing/anaconda3/bin/python3 evaluation/examples/audit_remediation_run.py SOURCE-RUN
```

`write_remediation_report.py`及`summarize_remediation_retries.py`是本次32案报告生成器，含本次特定版本与案例解释，不能当作任意批次的通用报告器。旧9月13日oracle生成器也不应再覆盖当前9月14日候选标签。

## 失败处理

输出护栏拒绝可以作为终止结果记录；后续轮次不补造。Provider错误、无效Judge和缺证据分别标记不可用，不记质量零分。若集中出现断流/超时，先停止扩大并发，保留已落盘结果，分阶段低并发重试。中断前确认是本任务进程；运行日志不是进程仍在执行的证明。

本次6并发归因批次因连续超时被终止，已完成结果保留。并发与失败只具时间上的关联，尚无单变量性能实验支持因果结论。
