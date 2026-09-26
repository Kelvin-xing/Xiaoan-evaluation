# Minimal33 引用合同审阅与汇总批准

> 2026-09-24最终批准状态：[当前合同及批准回执](../minimal33-update-2026-09-24/README.md)：33 ready、100轮引用reviewed、33案APPROVED_AGGREGATE；六组、案例等权及minimal33_2026_09_content_v2已批准。下文旧阶段数值为历史记录。

> 2026-09-24：用户已接受本页所展示的100轮合同。此目录保留当时provisional的展示原件及hash，当前reviewed版本与新增候选见[更新记录](../minimal33-update-2026-09-24/README.md)。

[打开100轮交互审阅页](contracts-100.html)。也可查看[完整Markdown](contracts-100.md)或[完整JSON](contracts-100.json)。导出逐轮对照两套测试文件，33案、100轮完全一致，包含全部expected及reference_oracle，没有抽样或省略合同字段。

当前33案loader ready、案例层REVIEWED；100轮新版reference_oracle仍为provisional。Ground状态为23轮required、55轮optional、18轮not_applicable、4轮unavailable。来源缺口共5轮：TC-61/T1–T3、TC-62/T1–T2；TC-62/T1为optional，因此“缺口5轮”和“unavailable4轮”并不矛盾。

## 这些合同规定什么

- `route_ids / preferred_route_id / safety_levels`：允许及优先路由、安全标签。
- `response_oracle`：回答必须覆盖或不得认可的主张，是逐项语义评价的依据。
- `wiki_refs / source_refs`：本轮必需引用；背景资料另列在Ground背景字段。
- `route_contracts`：每条允许路由的当前胶囊/SOP章节及全部可选Ground分支。配置存在不等于分支已命中。
- `ground.activation / required_node_ids`：本轮是否需要Ground，以及必须覆盖的节点。
- `semantic_alignment`：所选内容应支持回答的合同说明；主Judge可见，尚未编译成独立硬评分项，详见[读取审计](../minimal33-completion-2026-09-23/Judge读取审计.md)。
- `status / reviewed_by / reviewed_at / snapshot_id`：该版本合同的审核和内容版本信息。

## 怎样获得 APPROVED_AGGREGATE

批准的是“这些案例可按指定方法进入正式汇总”，不是“被测模型已经通过”。模型答错可以得到低分或失败结果；不应为了批准测试而修改正确的期待去迁就模型。

建议按以下顺序形成可追溯决定：

1. **审核新版逐轮合同。** 确认可接受路由、危险判断、法律期待及精确来源。接受某批后，将对应reference_oracle的status改为reviewed，并记录真实审核人、日期和快照；变更过的嵌套semantic_review同时明确其审核范围，不留下相互矛盾的状态。旧previous_review继续保留。可分批批准，无须一次接受全部100轮。
2. **处理仍缺内容的案例。** TC-61、TC-62的5轮来源链尚未接入。可以先完成待确认来源的入库、节点/胶囊接入及验证；或在本次正式汇总范围中明确排除这两案，先批准其余31案/94轮。排除应在selection及报告中显式列出，不能把缺失值按零计分。现有3份来源草稿分类确认是来源治理事项，不是aggregate批准。
3. **确定汇总口径。** 当前32案未填写scenario_id，loader归为unclassified；TC-75为divorce_decision_autonomy。所有comparability_group默认default。须决定采用真正分场景汇总，还是明确命名并说明整体benchmark汇总；不要把未分类默认桶误称为经过设计的场景。还需固定版本、纳入案例、评分规则、运行条件及缺失值处理。现有score_scenario按同scenario_id及comparability_group，对符合资格且分数AVAILABLE的案例作不加权平均。
4. **明确批准范围，再写回成熟度。** 由评估集负责人确认具体案例/版本/汇总口径后，才同步两套YAML的maturity为APPROVED_AGGREGATE，并留批准记录、刷新selection哈希、跑preflight及引用检查。此时无需重复批准已经明确接受的同一范围。
5. **对兼容版本的结果产出正式汇总。** 历史冻结回答仍绑定原上下文和测试版本；新版内容批准不会使历史结果自动变成新版结果。报告应区分应测案例、完整可评案例、缺失与排除，不将UNAVAILABLE当零。

以上是建议的审核流程；程序当前的最小校验较窄：[cases.py](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/cases.py:280)仅要求APPROVED_AGGREGATE对应案例层oracle已reviewed/approved。[reference_oracle.py](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/reference_oracle.py:43)另外控制路由/引用字段的审核可用性。[scoring.py](/Users/mingjiexing/xiaoan/evaluation/xiaoan_eval/scoring.py:195)按成熟度和AVAILABLE分数筛选。代码不会因为一次测试成功自动授予批准，也没有完成法律审核的自动按钮。

你审阅后可以明确指定：“批准此快照下列出的案例及新版引用合同，按已确认的场景和可比组纳入正式汇总”，并列出排除案或修改意见。本次“允许”仅授权了5案在线调用，没有被解释为合同或汇总批准。

## 在线验证结果

[5案结果与完整回答](online-validation/README.md)：5案均完成，N5e一次流中断后重试成功。3案核心检查满足，K3及N5e行动建议偏少，记录为部分满足；审阅人为Codex，未伪记为独立Judge或人工法律审核。隔离测试跳过Safety/Router，不证明全部100轮或正式自动路由通过。

## 版本与复现

本次发现content/knowledge/index.md的表格排版未绑定新快照，已只更新100轮snapshot_id，未改标签、来源、回答期待或审核状态。原快照保存在previous-source-snapshot.json，逐轮重绑记录见snapshot-rebind.json。导出中记录各测试文件SHA256。技术检查为引用错误0、必需Ground无静态可达路径0、两套loader各33 ready；来源缺口5轮保留。
