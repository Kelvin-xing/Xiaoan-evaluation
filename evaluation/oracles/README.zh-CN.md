# Test case oracle 全量更新（2026-09-13）

> 当前使用2026-09-14整改版：[整改与校准单](minimal32-remediation/REVIEW.zh-CN.md)、[逐轮引用清单](reference-review-2026-09-14.csv)、[完整性检查](reference-integrity-2026-09-14.json)。9月13日快照和复审结果为历史版本。用户已确认危机产品边界，单条oracle仍是待审核草案。


已更新 evaluation 与 evaluation_multimodels 两套一致的正式 74 案、217 轮。另同步 proposed 下的 TC-17/52 镜像和 TC-75–81（合计 20 轮）；proposed 未升入默认测试集。不是只修改原最小 32 案。

## 已落地

- 每轮均有 safety_levels、route_ids、preferred_route_id、capsule_ids；已下线的 k1 不再出现在当前期望中，原标签只留在 prior_labels 供复核。
- 每轮 reference_oracle 记录当前 capsule/SOP 文件、真实存在的段落、ground 配置节点与按需加载策略、所需或背景 Wiki/Source 引用、版本 SHA256、适用性和缺口。
- source_refs 使用当前平铺三位编号 Source 文件及精确章节；wiki_refs 使用 content/knowledge/wiki/nodes 实际文件。旧 required_ground_refs/relevant_ground_refs 已移除，避免继续填写 evaluator 不读取的旧字段。
- Ground 必需集由问题主题选择，不是复制 capsule 全部配置作为每轮必须召回。configured_ground_node_ids 是现状描述；required_node_ids 是待审核测试期望，两者分开。
- 原逐轮用户输入、回答 required_claims/forbidden_claims 和记忆检查点保留。没有给所有场景强加 reference_answer、长度限制、公开引文、工具或现实目标完成值。
- 新增 parser、指标聚合与 coverage 的字段级审核边界：新增引用/分流/安全标签为 provisional，不能继承旧回答 oracle 的 mat 审核。原回答 oracle 仍按原审核状态计算。以后审核引用合同需填写 reviewed_by 和 reviewed_at。

## Ground 适用性（正式 217 轮）

| 状态 | 轮数 | 含义 |
|---|---:|---|
| required | 60 | 已填当前节点及精确 Source 章节，作为待审核期望 |
| optional | 66 | 可按需加载，本轮不要求外部依据 |
| not_applicable | 68 | 危机/SOP、一般对话或无 ground 场景，不要求检索 |
| unavailable | 23 | 有问题相关背景，但不足以组成完整来源 gold |

not_applicable 不等于模型通过，unavailable 不等于质量零分。Ground recall/precision 在原框架仍为未实现，新增引用本身不会让该指标自动出现有效分数。排名检索需要完整 qrels 及排名 telemetry；当前 resolver 没有这类合同。工具和现实任务完成指标不适用于当前无工具 chatflow。memory 检查仍需 fact 级遥测；TC-77 的具体工作事实种子和 TC-79 的跨会话 harness 缺口未因填引用而消失。

## 仍缺完整来源的 25 轮

这表示当前仓库语料不能支撑完整 gold，不是宣称相关法律不存在。已有的可用背景条文保留在 background_source_refs；不得用旧指南或相关条文代替完整现行适用依据。尚未进行仓库外法律更新核验。

- **TC-20/T1, TC-20/T2**：缺少生育自主与强迫避孕/生育的专项完整权威依据。
- **TC-21/T2**：当前语料不支持签证、居留、遣返的结论，需要当地适用法及专业转介依据。
- **TC-22/T1, TC-22/T2**：反家暴法第二条不能独立证明婚内性暴力的全部刑事责任及认定规则。
- **TC-43/T2, TC-61/T1, TC-61/T2, TC-61/T3, TC-71/T1, TC-71/T2, TC-71/T4**：当前民法典节选缺少共同财产、转移财产、虚假债务及调查令的完整条文和程序依据。
- **TC-45/T2, TC-71/T3**：当前语料未提供窃听、间谍软件、非法取证与隐私的完整适用规则。
- **TC-58/T1, TC-68/T1**：冻结/挨饿可由保护令规定第三条部分支持，其他经济控制形式的适用边界需专项依据。
- **TC-62/T1, TC-62/T2**：当前语料未提供境外证据认证、翻译、跨境适用的完整权威依据。
- **TC-67/T1, TC-67/T3, TC-67/T4**：1091条只支持赔偿请求基础；金额、举证、财产分割关系及协议离婚后请求的具体规则仍需补全。
- **TC-69/T2**：当前民法典节选缺少离婚冷静期条文，不能用离婚诉讼条文替代完整证明。
- **TC-72/T1, TC-72/T3, TC-72/T4**：当前民法典节选缺少抚养权、探望权、抢夺藏匿子女的完整适用条文；需要专项来源核验。

## 测试揭示的内容/技术缺口

- 当前 Wiki frontmatter 仍有 **64 条旧 Source 路径引用**。测试引用已按当前文件更新，Wiki 自身的迁移没有在本任务中完成；不应把新 testcase 路径存在误当成运行链路已经修复。
- **24 轮**的待审核必需节点未全部包含在某个可接受 capsule 的当前 ground 配置中。详见 reference-integrity-2026-09-13.json 的 runtime_ground_gap_turns。这是需要复核的「测试期望 vs 配置」差异，不是已观察到的运行失败；也不能靠放宽 route 或改 expected 隐藏。
- capsule 按照内容回答，需要原回答与实际注入内容的精确引文和同轮快照。已在 semantic_alignment 合同中声明；仅有路由命中、段落路径、注入数量或引用命中不能证明语义使用，更不能证明因果依赖。后者仍需独立 attribution judge / 对照实验。

## 检查与复现

```sh
python evaluation/examples/audit_reference_oracles.py --output /tmp/reference-integrity.json
```

审计验证两套 case 一致、注册路由、当前文件、唯一章节、快照哈希、回应 oracle 非空。当前 reference integrity PASS；这不是法律审核或模型质量结论。语料修改后须重新审核引用并生成新版本快照，不可单独更新哈希掩盖语义漂移。

审核入口：reference-review-2026-09-13.csv（217 行）；完整逐轮依据在 testcase.expected.reference_oracle。原最小 32 案的已运行结果和私有 checkpoint 保持历史版本，本任务未重新调用回答或 Judge API。

最初引用更新测试：evaluation 294 passed；evaluation_multimodels 326 passed。2026-09-14完整复审后回归：305／334 passed。引用最终校验 PASS。


## 2026-09-14 后续：原32案96轮完整复审

逐轮必要/禁止行为、允许替代、争议及独立风险依据见 [完整复审包](minimal32-completion/README.zh-CN.md)。新增标签仍待人工审阅。上方引用统计已按复审后的标签刷新；25轮的相关专题有来源缺口，其中部分本轮只需支持/澄清，不再强制检索。原先关于没有统一长度约束的描述需以实际捕获prompt修正：普通回答有300字硬上限，明确展开有500字上限，危机另按其合同。
