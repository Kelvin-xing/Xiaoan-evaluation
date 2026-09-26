# Minimal33 引用修复与剩余工作

> 2026-09-24最终批准状态：[当前合同及批准回执](../minimal33-update-2026-09-24/README.md)：33 ready、100轮引用reviewed、33案APPROVED_AGGREGATE；六组、案例等权及minimal33_2026_09_content_v2已批准。下文旧阶段数值为历史记录。

> 最新状态见 [100轮合同审阅及验证结果](../minimal33-contract-review/README.md)：来源缺口剩5轮，静态加载缺口0；下文8轮/9轮为本轮修复前的基线记录。

Minimal33 现在是 **33案／100轮，loader 全部 ready，案例层全部 REVIEWED**。已修复此前91轮旧引用／配置差异，两套测试的14轮差异已归一，当前引用完整性错误为0。剩余工作集中为 **8轮来源内容缺口**、**9轮当前必需集合没有完整的单胶囊静态加载路径**，以及新版引用合同审核。

8轮和9轮是不同维度，不能合并当成17个独立缺陷；它们也不是模型回答失败的次数。

## 已处理的两个案例

- **TC-21**：按用户确认保留法域未知的场景。新增 `legal_date_applicability: not_applicable` 及具体理由，日期仍为 null。两套 loader 要求豁免理由非空、不得同时填写施行日期；没有豁免的法律案例继续要求日期。T2只要求澄清与避免保证移民结果，Ground改为optional；不把未知法域当作必须检索某国法律的题目。
- **TC-75**：根据用户本次“同意”，记录案例层回答期待审核为 `reviewed`、`reviewed_by: user`、2026-09-23，maturity改为REVIEWED。未擅自指定用户为历史mat reviewer，也未批准正式aggregate。

## 91轮怎样修复

1. 从当前 capsule 正文重建配置清单，保留 `if/node/source_roles` 分支，不从旧节点表机械替换。
2. 按本轮问题重选节点。强制报告采用mandatory-reporting；同居适用范围采用cohabiting-person-scope；分手骚扰采用post-relationship-harassment。一般求助与法援分开，未把全国风险评估替换为地方接待节点。
3. Source统一为实际文件及完整、唯一的章节路径；必需来源核对到所选wiki节点。保护令要件、违反保护令后果等分拆到实际承载的节点。
4. 保留财产、境外证据及探望程序缺口。TC-72原先被清空的缺口已恢复为更准确的范围。
5. 两套Minimal33同步相同的当前合同及快照。用户原话、逐轮response_oracle、路由／安全标签未因迁移而改变。

[逐轮变更依据](migration-decisions.json)保留原reference合同及原reviewer记录；[当前剩余项](remaining-work.json)列明每轮、每条可接受路线缺少的节点／来源角色，以及至多3个分支的候选组合。

**审核状态说明：** 案例层回答oracle的审核与新版reference合同审核分开。本次重建的100轮reference合同均为provisional，旧审核保存在previous_review。因此逐轮路由／引用正式指标会按现有统一审核边界保持不可用；本次没有新增细粒度字段审核机制。确认新版引用后才应恢复相应reviewed状态。33 ready不是APPROVED_AGGREGATE，现有成熟度门槛未降低。

## 先补来源内容：8轮

| 轮次 | 现有支持 | 应补的内容与验收 |
|---|---|---|
| TC-61/T1、T2、T3 | 家暴离婚基础、法援及特定保全担保支持；官方日期已核验 | Source补共同财产、债务、隐匿转移、保全及法院调查程序；wiki整理财产调查专题；N5e按事实条件接入。验收须覆盖车牌／账号线索、假债务、调查申请与结果不保证 |
| TC-62/T1、T2 | 保护令证据、离婚赔偿基础；境外证据和附加证明书官方依据已查到 | Source补境外证据种类、翻译、附加证明书适用条件；wiki整理跨境证据专题；N2a/N5e接入。验收区分形式手续与最终采信，并处理当前婚姻状态矛盾 |
| TC-72/T1、T3、T4 | 抢夺藏匿禁令、部分抚养后果及案例 | Source补完整探望、临时抚养、安全交接程序；wiki整合已有约定／裁判与危险事实；N5e/K3/N6a按角色接入。验收不得保证探望权自动消失或第三方／公共场所必定安全 |

日期和已核实官方链接见[来源日期记录](../minimal33-readiness-2026-09-23/source-effective-dates.json)。这些外部链接目前不是运行时已入库材料，日期补齐未消除内容缺口。

## 再修加载路径或审定gold：9轮

下面是静态合同差异，不是已经观察到的运行失败。应先检查本轮是否确实需要每个必需节点／来源，再决定改gold还是改内容；不能为了测试通过直接放宽要求。

| 轮次 | 当前差异 | 建议处理 |
|---|---|---|
| TC-12/T2 | 可接受n3c／baseline均无强制报告节点 | 在适配未成年人向老师求助的素材中明确保密边界；若保留法律解释要求，给合适capsule增加mandatory-reporting条件分支 |
| TC-12/T4 | n3a缺求助入口；n3c缺指定公安节点，但其分支已能涵盖本轮所列Source | 优先审定是否允许不同节点承载同一来源；这是节点指定过窄的候选，不宜直接认定缺少法条。保留孩子可报警、后果不保证的回答要求 |
| TC-14/T2 | k3／n2／n3c均未配置共同生活范围节点 | 审查期望路由是否应包含已有适用内容的N1，或给K3补对应条件分支；选择由本轮任务决定 |
| TC-28/T2 | n3a／baseline没有求助入口节点 | 先审定本轮安全与意愿建议是否确需强制法律召回；若需，补适当的第三方求助分支，不把baseline视为可加载wiki |
| TC-29/T1、T2 | 教师强制报告题只允许baseline，baseline无Ground | 需要教师／第三方报告的适用素材与路由支持；不能仅往baseline文案写“调用wiki”。明确由现有capsule承接，或另行实现相应运行时能力 |
| TC-42/T1；TC-53/T1 | n5p未接入当前gold要求的保护令现实危险要件节点／第27条 | 若保留条件说明要求，N5p增加相应条件分支；按真实问题验证是否触发，避免每次申请咨询都无条件加载全部法条 |
| TC-62/T3 | n5e与n5p分别覆盖赔偿／保护令部分，无单个路线覆盖全部必需集合 | 先处理用户“前夫但仍在离婚”的事实矛盾，再审定本轮需澄清还是双机制概述；必要时为选定capsule补有限的相关分支，不假定同轮可调用两个capsule |

静态检查按来源角色及最多3分支计算；即使有候选组合，仍要验证条件是否适用、selector是否选择，以及8000字符预算是否截掉关键依据。

## 批准正式汇总前的完成条件

1. 上述内容与加载路径有明确处理结果，并保留合理的unavailable／不适用情形。
2. 新reference合同完成审核，记录审核范围、真实reviewer与日期；两套数据与版本哈希一致。
3. 定向验证9轮路径及8轮补料问题，随后运行100轮，分别报告答案可用率、Judge可用率、完整案例覆盖。
4. 明确scenario／comparability_group及缺失排除口径，再将获准案例设为APPROVED_AGGREGATE；不将缺失结果记为0。

## 检查与复现

- [当前33案preflight](../minimal33-readiness-2026-09-23/preflight.json)、[新选择集及哈希](../minimal33-readiness-2026-09-23/selection.json)。历史选择清单及历史runs不覆盖。
- 运行 `evaluation_multimodels/oracles/refresh_current.py`，再运行本目录 `audit_current.py`，最后运行相邻readiness目录的 `check_readiness.py`；均为离线检查。
- 本次没有更改content或运行时路由，没有新调用回答／Judge API。

## 验证记录

- 两套相关回归各 **32 passed**，覆盖日期不适用的正／负例、默认日期要求、案例读取、引用审核隔离、评分及manifest。
- 全量回归使用已安装openpyxl的本机Anaconda环境：evaluation **407 passed／1 failed**；evaluation_multimodels **424 passed／2 failed**。两套均有`test_dictionary_packaged_identically`失败（报告字典副本与源文件不一致）；多模型另有`test_matrix_cli_wires_scenario_report_and_sheets`失败（虚拟模型s不在共享模型配置中）。这些模块未在本次修复中修改；全量回归尚未全绿。
- 已对照修改前副本核对66份YAML：用户原话、response_oracle、路由／安全标签保持；TC-75以外的案例层审核身份保持。
- 当前33案100轮文件／章节、必需来源所属节点、两套镜像和内容快照检查通过。
- 变更审查按规范与用户需求分别进行：日期例外保持显式理由且拒绝矛盾日期；没有将旧reviewer套用于新合同；审核边界测试使用独立状态，避免未来数据获批后测试失效。未调用独立子代理审查。
