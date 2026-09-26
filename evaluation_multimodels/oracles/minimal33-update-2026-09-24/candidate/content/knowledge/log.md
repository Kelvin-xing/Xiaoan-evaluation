# Knowledge Log

Append-only chronological record of ingests, durable query pages, lint passes, and major wiki maintenance.

## [2026-06-06] ingest | 中华人民共和国反家庭暴力法

- Added initial LLM-wiki schema in `AGENTS.md`.
- Created `knowledge/index.md` as the content catalog.
- Created source summary, legal atoms, legal mechanisms, and one draft scenario capsule derived from `knowledge/source/中华人民共和国反家庭暴力法.md`.
- Open gaps: police implementation details, local rules, social work practice sources, and expert review.

## [2026-06-06] scope-correction | 法律机制树中间层

- Corrected current scope to the legal middle layer only.
- Removed LLM-created source-summary and scenario-capsule pages.
- Added `legal-mechanism-tree` as the root node for Obsidian visualization.
- Clarified that `knowledge/source/` is user-maintained and read-only for the LLM.
- Clarified that scenario capsules are future product-layer work and should not be created or edited in this phase.

## [2026-06-07] schema | legal atoms as nodes, mechanisms as edges

- Rebased `copilot/llm-persistent-knowledge-wiki` onto latest `main`.
- Reworked `knowledge/AGENTS.md` so legal atoms are represented as graph nodes and legal mechanisms are represented as sourced edges.
- Moved initial legal atom pages into `knowledge/wiki/nodes/`.
- Added `edges` as the mechanism edge catalog.
- Removed separate legal mechanism pages that implied a misleading Legal Atom -> Legal Mechanism layer split.

## [2026-06-07] schema-v0.1 | node/edge/source-type taxonomy

- Added Schema v0.1 to `knowledge/AGENTS.md`: node kinds, edge relations, `source_type` trust tiers, ingest granularity, and out-of-scope rules.
- Aligned `knowledge/wiki/edges.md` edge vocabulary with the schema.
- Added `source-registry` cataloging all `knowledge/source/` files with `source_type`, tier, and ingest status, plus a pilot ingest batch.
- Status conventions: new legal claims default to `draft`; cross-source/interpretive claims default to `needs-review`; legal-reviewer-confirmed claims become `reviewed`.

## [2026-06-07] pilot-ingest | 4 sources, schema v0.1 frozen

- Froze schema v0.1 and ran pilot ingest on 4 sources.
- ingest | 人身安全保护令实务 (practice_guide): added `protection-order-evidence` node; enriched `personal-safety-protection-order` with judicial-interpretation refinements (needs-review); enriched `support-and-legal-aid` (legal aid not limited by hardship, needs-review).
- ingest | 公安机关办理伤害案件规定 (agency_rule): added `injury-appraisal-procedure` node (appraisal commission/timelines, mediation limits).
- ingest | 预防和制止家庭暴力警察工作手册 (official_manual): added `police-dv-handling-workflow` node (5-stage workflow, risk assessment); flagged conflicts_with current law (predates 2016, no 告诫书) -> needs-review.
- ingest | 广东省实施反家暴法办法 (local_regulation): added `guangdong-implementation` local-rule node with 3 `localizes` edges.
- Schema gaps found: (1) no relation for judicial-interpretation refining national law (used provides_evidence_for + needs-review; consider adding `interprets`/`refines`); (2) existing protection-order node bundles remedy+procedure+condition+consequence, may need splitting; (3) secondary sources citing primary judicial interpretations should consistently be needs-review with "原文待补".
- Next: legal reviewer to check needs-review nodes/edges; then ingest remaining sources per `source-registry`.

## [2026-06-07] graph-cleanup | make Obsidian graph match node/edge structure

- Root cause: Obsidian renders one node per file and one edge per `wikilink`; `edges.md` and `source-registry.md` were becoming star hubs because they linked to every node/source.
- Converted all `wikilinks` in `edges.md` (34) and `source-registry.md` (37) to plain inline code.
- Changed node pages' "详见 `edges`" (8) to plain `edges.md`.
- Verified all 17 edges are mirrored as node-to-node `wikilinks` in node pages, so no graph edges were lost.
- Added an Obsidian graph convention to `knowledge/AGENTS.md`: node-to-node wikilinks are the graph edge source of truth; catalogs use plain text; use Graph filter `path:nodes` for a pure node view.

## [2026-06-07] schema-v0.2 | consolidate edge types 10 -> 6

- Audited declared vs used edge relations. Used: provides_evidence_for(6), enables, localizes, defines_scope_for, parallel_support_channel_for, conflicts_with. Unused: triggers, requires, creates_consequence_for, plus stray `limits`.
- Deleted `triggers` (folded into `defines_scope_for`), `requires` (inverse direction), `creates_consequence_for` + `limits` (unused; consequence stays inside node until a consequence node is split out).
- Merged `assists_execution_of` -> `enables` (relabeled 1 edge + 2 node pages).
- Final vocabulary = 6 relations; all 17 edges remap cleanly (provides_evidence_for 6, enables 3, localizes 3, defines_scope_for 2, parallel_support_channel_for 2, conflicts_with 1).
- Updated `knowledge/AGENTS.md` (Edge relations table + label list) and `knowledge/wiki/edges.md` vocabulary.
- Recommendation recorded: if only one edge type can be visualized, use `provides_evidence_for` (connects 6/8 nodes, converges on protection-order; evidence is the highest-leverage DV problem).

## [2026-06-07] schema-v0.3 + synthesis | element layer (请求权基础分析)

- Studied the real 六段式要件清单 from CSlawyer1985/china-lawyer-analyst (请求权基础分析法: 总体情况概述/立案审查/原告诉请/被告抗辩/要件事实/知识图谱).
- Added `element` node_kind and two requirement-layer relations `is_element_of` (element->claim) and `proves` (evidence->element) to knowledge/AGENTS.md (schema v0.3). Documented the lawyer chain: 来源 --provides_evidence_for--> 证据 --proves--> 要件 --is_element_of--> 请求权.
- Created node `protection-order-element-danger` (要件3: 遭受家暴或面临现实危险, needs-review).
- Created synthesis `syntheses/protection-order-six-part-checklist.md`: mimics the six-part framework applied to the protection order, fully source-grounded, with needs-review flags and a reviewer checklist.
- Rewired the protection-order subgraph to route evidence through the element (no longer evidence->remedy directly): evidence proves element; element is_element_of remedy; definition defines_scope_for element. Removed the subsumed duty->remedy evidence shortcut. Edge count stays 17; nodes 8->9.
- Caught a possible citation error to surface for review: practice guide cites "《反家暴法》第八条" for the "对方有过错不影响核发" defense, but 第八条 is about township prevention work — likely a misattributed 审理指南 clause. Flagged in the checklist's review list.

## [2026-06-08] full-ingest | all 32 sources (waves 1-3)

- Rebased onto latest origin/main (source renames: 中国…司法解释, 河北简体). Updated source-registry accordingly.
- Wave 1 (judicial, tier 1): ingested 中国反家庭暴力法律法规与司法解释 (contains 法释〔2022〕17号 + 公通字〔2024〕34号 primary text) and 涉及家庭暴力婚姻案件审理指南.
  - Resolved prior needs-review flags: "较大可能性" standard (法释17号第六条), 11类证据 (第六条), 远离/电话骚扰令 (第十条), 代为申请 (第二条).
  - Resolved the "第八条" citation question: practice guide's "第八条" = 法释〔2022〕17号第八条 (认可家暴但辩称对方有过错不影响作出), not a misattribution; 审理指南第八条 separately states DV is not victim's fault.
  - Added node `warning-letter` (告诫书) from 公通字〔2024〕34号.
- Wave 2 (agency/manual/medical): added node `dv-risk-assessment` (妇联危险预测量表 + police manual, cross-source); enriched `support-and-legal-aid` (妇联 intake procedure) and `injury-appraisal-procedure` (medical evidence collection). Channel directories + NGO case reports registered done without legal nodes (schema: not used to invent duties).
- Wave 3 (18 provincial regulations): created synthesis `local-regulations-comparison` (delta matrix: 网络/经济/冻饿/目睹未成年人/告诫强制/远离令/强制报告/代为申请/热线/信息共享) instead of 18 near-duplicate nodes; kept guangdong-implementation as worked example. All marked done.
- Graph now: 12 nodes, evidence routed through the element layer (请求权基础分析). 2 syntheses filed back.
- Remaining needs-review: police-dv-handling-workflow (pre-2016), local-regulations-comparison (per-province 条号 verification), 法律援助法第32条 primary text not in source.

## [2026-06-08] lint | resolve 法律援助法第32条 (was false "missing")

- Traced the needs-review flag to its origin: `人身安全保护令实务.md` line 405 cites 《法律援助法》第32条 as a secondary claim.
- Found the primary text was ALREADY in the corpus: `中国反家庭暴力法律法规与司法解释.md` §13 (法律援助法) line 325, 第三十二条 — the large compilation's section 13, missed in wave-1 first pass.
- Resolved: added primary source_ref to `support-and-legal-aid` node; corrected scope ("主张相关权益" is broader than the secondary doc's "申请保护令"); checked off the synthesis review item; updated index gaps.
- Lint lesson recorded: large multi-law compilations need per-section verification; first-pass ingest can miss later sections. Flagged in index Open Gaps.

## [2026-06-08] expand | broaden coverage 11 -> 17 nodes

- User chose breadth over depth. Extracted 6 new nodes from existing sources (no new ingest needed):
  - `mandatory-reporting` (duty, 第14/35条 + 山西/重庆): institutional reporting + non-report sanctions.
  - `guardianship-revocation` (remedy, 第21条): revoke guardianship; support duties survive.
  - `temporary-shelter` (support, 第15/18条 + 告诫意见): setup, police-assisted placement, warning-letter voucher.
  - `child-witness-victim` (definition, local regs, needs-review): minors witnessing DV as victims — local extension, not in national law.
  - `special-protection-groups` (definition, 第5条): hub node for minors/elderly/disabled/pregnant/ill.
  - `divorce-and-dv` (procedure, 法释17号第11条 + 审理指南, needs-review): DV as divorce ground, "new circumstances" re-filing, separation violence.
- Added 15 edges; back-links added to existing node pages so Obsidian graph renders them.
- Graph: 17 nodes, 36 edges. defines_scope_for 9, enables 9, provides_evidence_for 6, localizes 6, parallel 3, is_element_of/proves/conflicts_with 1 each.
- Deferred: admonishment-vs-punishment (治安/刑事 vs 告诫) kept inline rather than split, to avoid over-fragmentation.

## [2026-06-08] refactor | merge Guangdong into comparison; add liability-ladder; schema v0.4

- Q from user exposed an inconsistency: guangdong-implementation was a standalone node while 17 other provinces lived in the comparison synthesis — guangdong was special only because it was done first (historical accident, not design).
- Also found a 0-byte stray `nodes/local-regulations-comparison.md` (auto-created by Obsidian when following the [[link]]); deleted.
- Chose option A: merged Guangdong's specifics into `syntheses/local-regulations-comparison.md` (added as 4th 标志性条款 province), deleted `nodes/guangdong-implementation.md`, rerouted its 3 localizes edges to originate from local-regulations-comparison (now connects definition/public-security/protection-order). 18 provinces now treated uniformly.
- Split out `liability-ladder` (consequence node): 批评教育 → 告诫书(行政指导) → 治安处罚 → 刑事责任, plus protection-order-violation penalties (第34条). Clarifies 告诫 vs 治安/刑事 distinction the user asked about.
- Schema v0.4: re-introduced `creates_consequence_for` now that a real consequence node exists (protection-order --creates_consequence_for--> liability-ladder). Documented in AGENTS.md + edges.md vocab (now 9 relations).
- Graph: 17 nodes (−1 guangdong +1 liability-ladder), 39 edges, all valid, no broken links.

## [2026-07-07] lint | repair temporary-shelter source_ref anchor

- Ran `tech/chatflow/poc/wiki_update.py`; no source files were added, modified, or deleted, but one stale `source_ref` was detected.
- Repaired `temporary-shelter` node reference from the non-existent anchor `#告诫制度意见` to the concrete 公通字〔2024〕34号第十四项 anchor in `knowledge/source/中国反家庭暴力法律法规与司法解释.md`.
- Updated the corresponding `warning-letter -> temporary-shelter` edge source label and `knowledge/index.md` summary to cite 公通字〔2024〕34号第十四项.

## [2026-09-07] lint | stage heading-path migration without changing sources

- Updated the source guide and agent instructions to use exact heading paths, preserve numbered filenames and `目录.md`, and retire the old four-tier registry columns. Unconfirmed source classifications remain explicitly pending.
- Added opt-in strict heading extraction and recursive source discovery. Default runtime extraction remains compatible; historical document-only refs now emit migration warnings instead of silently disappearing.
- Verified all 32 source files are unchanged. The audit exposes 30 document-only page/ref pairs missing anchors; strict mode additionally rejects 59 anchored pairs whose raw source headings have not yet migrated. Neither result is strict acceptance; the source manifest was not updated.
- All 93 focused and related runtime tests passed. The 17 existing nodes (76 node/excerpt items) and 21 capsules retain identical legacy output. Raw source and wiki-reference migration remain follow-up work.

## [2026-09-07] refactor | relocate content and audit runtime references

- Moved authored content under `content/`, tests under `test/`, and interaction design under `ux/`; runtime filesystem constants and Docker inputs now use those physical paths.
- Kept `knowledge/source/...` and `knowledge/wiki/...` as stable logical identifiers in manifests, API/debug payloads, and `source_refs`; migrated references with unambiguous numbered-file replacements.
- Regenerated the runtime capsule artifacts from `content/capsule/`: 20 capsules, 2 N1 schema errors, and no warnings. Instruction and template files are excluded from discovery.
- Refreshed the wiki drift audit without accepting a new manifest. The current corpus has 88 source documents versus the legacy 32-source baseline; 30 document-level refs still need anchors, and strict mode reports 89 unresolved refs.
- Repaired seven malformed YAML test cases and aligned the offline router's N3a2 specificity with its existing police-dismissal regression contract.
- Focused refactor tests pass. The full suite passes 120 of 123 tests; the remaining three errors all originate from the missing `如何寻求医院及法医鉴定的帮助` source.
- Decision: keep J/K sources under `practice/` with their J/K and tier 3 metadata
  until further discussion.
- Deferred: leave the missing `如何寻求医院及法医鉴定的帮助` reference as-is for now;
  do not accept a new manifest or finish anchor migration incrementally. The next
  wiki change will be a full rebuild.

## [2026-09-13] full-rebuild-start | 85 canonical sources

- Explicitly started an empty-wiki rebuild after source preparation and proportional risk re-audit.
- Moved legacy nodes, syntheses, edge catalog, tree, manifest, and update report out of the repository worktree; retained the old log only as historical activity.
- The new rebuild uses only current source files, persistent methodology, and the fresh draft source registry. Old graph content, counts, labels, and conclusions are not rebuild input.
- Initial state: 85 sources pending; 9 narrowly scoped open risks; no node, edge, synthesis, or manifest accepted.

## [2026-09-13] full-rebuild-draft | 85 canonical sources

- 从空Wiki开始，以当前85份canonical source、持久方法论和fresh registry为唯一输入；旧节点、边、综合页、manifest和报告已移出工作树归档。
- 逐份、长文件逐节读取全部source，并按claim/case粒度去重：78份产生净新增，1份`covered-no-new-content`，3份`retained-reference-only`，3份`needs-repair`。
- 生成15个节点、16条有来源关系和4个综合页；核心节点均由A–F现行法源承重，G/I只作机关实施，H/K只作案例、评论或实证观察。
- 地方规则以19法域比较综合承载，不复制19套近似节点；059作为重合案例的官方主来源；083/084只保留非重复监测观察。
- 23条历史风险记录保留审计轨迹，其中9条仍开放且仅阻断具体坏段或元数据判断。
- 自动化检查覆盖source快照、85份处理结果、strict heading引用、source role权威边界、边端点与反向链接、索引链接和开放风险段落排除。
- 当前为draft：strict引用0破损，但尚未接受source manifest，也未标记任何内容`reviewed`。

## [2026-09-13] refactor | source-only 节点边界重构 15 → 29 节点

- 依据 `wiki-node-boundary-audit-source-only.md`（基线`787bcc7`，仅以 canonical source 和知识层治理规则为判断依据）重构知识层，未读取或修改 capsule、prompt、Router、grounding、runtime。
- 拆分6个混合了不同请求权、义务主体、程序或后果的宽节点：`police-response-and-investigation`、`temporary-shelter-and-placement`、`legal-aid-and-procedural-support`、`child-safety-and-guardianship`、`family-law-relief`、`liability-for-domestic-violence`。
- 保留并收窄9个节点，新建20个节点，最终29个节点、32条关系、4个综合页；节点数由请求权/义务/要件/程序/后果的边界产生，不由 source 数量决定。
- 关键边界：`post-relationship-harassment-protection` 只表达005第二十九条的独立主体与触发情形，保护令生命周期引用 `protection-order`；`child-custody-and-domestic-violence` 保持一个节点但分节表述解释二14（离婚首次确定）与解释一56（既有关系变更）；`institutional-accountability` 只处理强制报告失败、履职失责和地方检察公益诉讼，公职人员本人施暴的政务处分单列在 `public-security-liability-for-domestic-violence`；`litigation-fee-and-preservation-security-relief` 明确不存在家暴专属财产保全程序；`risk-assessment-and-referral` 保持登记—评估—分级—转介—结案—回访的连续机制。
- 来源边界：049 的“一、工作对象”结构完整可用，其余章节因 SR-005 断行按抽取粒度整节不引用；085 的判决比例冲突不选择、不合并、不复述；080、081 仍只作参考不建案例节点。
- edges.md 重建为含节点类型与关系词汇的目录，32条边全部有精确来源，并在起点节点“机制关系”中有同方向 wikilink；无来源支持的节点保持无边并写明理由。
- 同步 `legal-mechanism-tree.md`、`content/knowledge/index.md`、`source-registry.md` 逐 source 输出映射与覆盖统计、`wiki-update-report.md`；综合页内容未受节点变化影响，保持原状。
- 校验：`test_wiki_rebuild.py` 7项通过（节点数29、边数32、SR-005 阻断段落改为按具体章节排除）；`wiki_update.py --strict-headings` 0条破损引用、85份 source 无变更、manifest 未接受。
- 仍为 draft/needs-review；未标记任何页面 `reviewed`，未写 manifest，未提交或推送。

## [2026-09-13] maintenance | 仅保留开放风险

- 根据 review 意见，持久风险清单和当前 `source-registry.md` 不再保留已解决或已重分类为普通使用边界的事项，只保留9条仍会影响抽取、归因或法律判断的开放风险。
- 同步更新 source-format 回归断言；`test_source_format.py` 13项通过。

## [2026-09-13] correction | 恢复 15 节点知识结构

- 用户逐节点审阅29节点版本后，确认首版15节点的内容聚合与分类更合理；知识层节点、边、树、索引、逐来源输出映射和更新报告恢复到`787bcc7`的15节点版本。
- 保留后续“仅保留开放风险”的治理改动：持久清单和当前registry仍只有9条开放风险，不恢复已解决风险记录。
- 29节点重构记录保留为历史，不作为当前Wiki结构。
- 校验：15个节点及相关结构文件逐文件哈希匹配`787bcc7`；`test_source_format.py`与`test_wiki_rebuild.py`共20项通过，严格标题检查为0条破损引用。

## [2026-09-13] correction | 复核 legal-basis 承重与节点边界

- 逐一复核15个节点后，确认14个节点的聚合边界可保留；原`risk-assessment-and-referral`没有`legal_basis`，并把妇联、热线、多部门和警察的不同流程合并为一个实践节点，不符合当前建模原则。
- 将其重建为`local-intake-risk-assessment-and-referral`，以云南、吉林、河南、湖北地方性法规承载首接、风险评估与转介规则，并明确法域限制；全国妇联和地方妇联材料只作机关实施说明。
- 2013年警察手册中的现场危险评估与证据固定内容归入公安处置节点；妇联归档材料的证据作用归入保护令证据节点。
- 删除跨节点重复承载：家庭法救济节点不再重复子女抚养和财产保全支持，未成年人节点不再重复紧急安置。
- 调整后仍为15个节点，关系由16条收敛为14条；所有节点均须有A–F现行法源作为`legal_basis`。

## [2026-09-14] source-retirement | 退休 canonical 055、061

- 根据律师复核结论，从 active source 库删除 canonical 055《关于预防和制止家庭暴力的若干意见》和061《涉及家庭暴力婚姻案件审理指南》；永久保留两个 canonical ID 空缺，不重编号后续资料。
- 两份材料此前只作为`institutional_implementation`搭载在既有节点，未作为`legal_basis`或决定节点边界；删除后节点仍为15个、关系仍为14条。
- 同步移除055在求助入口和公安处置节点中的2008年历史实施说明，以及061在家庭法救济节点中的联系方式保密、背靠背调解说明。

## [2026-09-20] source-repair | 吸收 PR #109 并关闭四项风险

- 采纳 PR #109 对023、038、049、051、052和058的有效修复，并补齐049“出入登记”、051／052目录发布机关和058历史使用边界。
- 关闭`SR-002`、`SR-004`、`SR-005`、`SR-007`和`SR-023`；持久风险清单与registry仅保留`SR-011`、`SR-019`、`SR-021`和`SR-022`。
- 049作为2015年历史庇护实施材料接入临时庇护节点；058作为2002年历史机关实施材料接入公安处置节点。两者均不作为现行`legal_basis`。
- 恢复084原PDF未完标记，不以推测补全缺文；根据人工审核结论，085保留与38件样本计数一致的27起／11起和71%／29%，删除错误图表值及残留30.6%。
- 将PR conversation中的人工审核结论写入066元数据和剩余风险处理边界；当前83份active source中78份`incorporated`、1份`covered-no-new-content`、3份`retained-reference-only`、1份`needs-repair`。51项相关测试通过；严格标题审计0条破损引用、5份有意未引用来源；manifest未写入。

## [2026-09-20] issue-112 | 细化 Wiki 范围与条件 Ground

- 将宽泛的`domestic-violence-scope`收窄为行为认定节点，并新增共同生活人员、特殊保护群体、关系终止后骚扰、家庭情境性侵害、延迟控告与刑事证据五个全国性窄节点。
- 将059号最高法2025年案例2、案例3分别作为性侵害同意判断和延迟控告证据审查的`case_application`；两项结论均由现行A–F法源承重，典型案例不单独建立全国规则。
- 从国家法律法规数据库收录2025年1月14日修正的086《江苏省反家庭暴力条例》，新增仅限江苏法域的窄节点，并把地方规则综合页从19个法域更新为20个法域。
- Ground运行时实现严格`if + node + source_roles`解析、当前问题分支选择、按role展开、跨分支去重和8000字符完整条目预算；格式错误由loader报错，条件分支本身不发送给回答模型。
- 收窄N2a“延迟报案”和N1性暴力／经济控制表述，明确不从单一典型案例推出一般证据效力，也不把江苏规定外推为全国规则。

## 2026-09-23 Minimal33定向增量补充

补充009、043、044相关完整财产及探望条文，新增财产实体认定、探望交接两个needs-review节点。修改N3c教师及保密例外、N3a报案入口、K3同居适用与探望、N5p现实危险、N5e交接及并行救济。TEXT_ONLY内容与已实现条件Ground配置，无新增工具或跨轮状态。来源分类确认及程序/跨境材料入库待完成；新增结论未授予法律审核或aggregate批准。

## 2026-09-24 程序与境外证据补充候选

新增087—089完整相关条文及通知，新增两个needs-review节点，N5e/N2a条件接入。美国实施通知分支须用户上下文明确材料在美国形成；未知国家只加载通用证据规则。TEXT_ONLY素材与现有Ground配置，无新增工具能力。五轮合同增量另行记录；分类及候选激活状态见本次审核记录。
