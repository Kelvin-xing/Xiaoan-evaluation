# semantic_alignment 的实际读取与评分边界

截图中的 `reference_oracle.semantic_alignment` 会随整份 `expected` 传给主 Judge；用户关于“Judge 看得到这段内容”的理解正确。当前程序未把它编译成独立评分项，也未逐字段强制执行。因此，修改这段 YAML 不会自动建立一项可靠的语义一致性评分。

| 消费者 | 读取情况 | 实际作用 |
| --- | --- | --- |
| test-case loader | 保留整个 reference_oracle，包括 semantic_alignment | 校验版本、审核状态、引用范围和 Ground 基本结构；不校验截图各字段的语义 |
| 单模型主 Judge | pipeline 使用 asdict(expected)，provider 序列化完整 expected | 模型可见该段测试期待；具体是否据此评价取决于模型，暂无逐项强制结果 |
| 多模型主 Judge | dynamic_input.expected 同样保留该段 | 同上 |
| response oracle 评分器 | 只将 response_oracle.required_claims / forbidden_claims 转为 R1/F1 等评分项 | 绑定问题、上下文和答案，要求逐项 verdict 及答案精确引用；semantic_alignment 不参与该 binding |
| 独立 attribution Judge | 不接收 expected，也不接收 semantic_alignment | 根据本轮实际捕获的 effective_context_snapshot 构建证据目录，检查回答主张及适用性；它有自己的固定输出合同 |
| 被测小安回答模型 | 正常生产路径不读取测试 YAML | 接收选中的胶囊、命中 Ground 和对话上下文；测试期待属于评估侧 |

## 代码证据

- [主 pipeline 构建 expected](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/pipeline.py:183)。
- [主 Judge 完整请求序列化](/Users/mingjiexing/xiaoan/evaluation/company_eval_plugins.py:179)：还明确把请求内容视为证据数据，评分指令使用 rating rule、evidence catalog 和 oracle contract。
- [多模型 Judge 请求](/Users/mingjiexing/xiaoan/evaluation_multimodels/xiaoan_eval/multimodel.py:895)。
- [真正的 response oracle contract](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/oracle_judge.py:21)。
- [独立 attribution 请求](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/attribution_client.py:28)。
- [reference_oracle 解析器](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/reference_oracle.py:11)。

## 已验证的行为

`audit_judge_readers.py` 使用合成 fixture 和 mock transport，实际捕获主 pipeline 请求及 provider wire payload：截图字段完整保留。通过多模型序列化函数也得到相同字段。把 semantic_alignment 替换为哨兵值后，response oracle 的评分项及 binding 完全不变。独立 attribution 请求中不存在该字段。证据保存于 `judge-reader-audit.json`；此次审计没有调用外部模型。

这些检查证明“谁收到什么”及程序约束边界。在线模型是否实际采用该段期待，需要有完整请求与输出的运行记录。

## 建议如何使用

保留 `semantic_alignment` 作为可审查的测试合同说明。每轮必须完成的用户需求继续写入 `response_oracle`；回答是否受实际注入内容支持，由 attribution 证据链负责。若要将截图全部要求变成正式评分，下一步应建立明确适用字段、逐项结果和缺证据处理，将合同版本绑定到 attribution 请求与报告，并以缺 snapshot、错误片段、缺精确引文等反例验证。

目前不要只靠修改这段 YAML 就提高测试成熟度或批准汇总。`aggregate` 指跨案例汇总（如平均分、通过率），其适用范围和审核状态应与逐轮结果一同记录。
