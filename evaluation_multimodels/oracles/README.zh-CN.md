# Oracle 当前内容清单（2026-09-23）

> 2026-09-24最终批准状态：[当前合同及批准回执](minimal33-update-2026-09-24/README.md)：33 ready、100轮引用reviewed、33案APPROVED_AGGREGATE；六组、案例等权及minimal33_2026_09_content_v2已批准。下文旧阶段数值为历史记录。

已按当前 `content/source` 的实际位置 `content/knowledge/source/`、`content/knowledge/wiki/` 和 `content/capsule/` 重建版本清单、逐轮引用对照与完整性报告。正式测试现为 **75 案／221 轮**，另有 proposed **20 轮**。本目录的当前入口是以下 9 月 23 日文件。

| 文件 | 用途 |
|---|---|
| [当前内容索引](content-index-2026-09-23.json) | capsule 的真实条件分支、节点、来源角色；wiki 节点的 Source 引用 |
| [当前版本快照](source-snapshot-2026-09-23.json) | 当前 content Markdown 文件及 SHA256 |
| [逐轮对照](reference-refresh-2026-09-23.json) | 原 expected 与当前 route_contracts 并列，保留差异、来源缺口、两套测试差异 |
| [逐轮审核表](reference-review-2026-09-23.csv) | 241 轮正式／proposed 分列，便于筛选问题 |
| [完整性结果](reference-integrity-2026-09-23.json) | 当前审计统计及输入 testcase 文件哈希 |
| [内容缺口更新](content-gaps-2026-09-23.md) | 修正旧缺口表，区分已有内容与尚缺内容 |
| [清理记录](cleanup-2026-09-23.json) | 已删除的 7 个旧副本、保留位置与一致性哈希 |


Minimal33 的日期修复、33 ready／0 needs_remediation 结果及 aggregate／provisional 说明见 [Minimal33 就绪性报告](minimal33-readiness-2026-09-23/README.zh-CN.md)。

## 最新Minimal33审阅入口

[100轮合同：交互页面、完整导出和批准流程](minimal33-contract-review/README.md)。在线5案已完成（N5e重试成功）；3案核心检查满足、2案行动建议待改善。当前Minimal33为33 ready、引用错误0、静态加载缺口0、来源缺口0；100轮引用合同均已审核，33案已批准正式汇总。当前导出见上方9月24日入口。

## 当前结果

- 当前 capsule 配置指向的 wiki 节点、wiki frontmatter 声明的 Source 文件和完整章节路径：**0 项引用错误**。旧文档所称「64 条旧 Source 路径」已不适用于当前内容。
- 正式测试合同中 **82 轮**有引用或 capsule 配置差异；**121 轮**仍绑定旧快照；与 `evaluation/test-cases/` 相比，**21 轮**内容不一致。
- 当前多模型 testcase 仍记录 **19 轮**专题来源缺口；这些是旧合同的记录值，最新内容判断见缺口更新文档。
- 完整性状态为 **NEEDS_REMEDIATION**。节点／文件存在验证不涵盖法律充分性、条件分支实际命中、来源角色筛选和模型回答质量。

Minimal33 的33案／100轮已同步两套YAML并修复旧引用；其余案例尚未迁移，详见[修复报告](minimal33-reference-repair-2026-09-23/README.zh-CN.md)。本目录保留当前内容索引与oracle对照产物。`current_route_contracts` 来自当前 capsule 正文；`recorded_expected` 保留多模型 testcase 原合同。未把当前配置自动改为每轮必需召回集，也未用新快照覆盖旧合同的 reviewer 身份。两套 testcase 的语义差异仍需逐轮修正，不能仅靠同步哈希解决。

## 保留的历史材料

- `source-snapshot-2026-09-14.json`：历史版本，现有 `evaluation/examples/audit_reference_oracles.py` 仍硬编码读取，暂保留供兼容；不代表当前内容。
- `minimal32-completion/`：2026-09-14 的 32 案／96 轮审核与历史诊断材料。
- `report-labels-2026-09-22/`：特定历史运行的标签补齐包。

上述材料中的通过数、比例和缺口属于其原日期与范围。旧 9 月 13／14 日完整性、逐轮清单、CSV 和 9 月 13 日快照的本目录重复副本已删除；逐字一致的原件留在 `../../evaluation/oracles/`，清理记录可追溯。历史回答、运行结果及 checkpoint 未改变。

## 重新生成

在仓库根目录执行：

```sh
.venv/bin/python evaluation_multimodels/oracles/refresh_current.py
```

脚本仅离线读取 content 与两套 testcase，更新本目录的 9 月 23 日清单，不调用模型、不改 testcase、不授予法律或人工审核状态。日期固定为本次审计版本；以后生成新审计时应先更新脚本中的 `DATE`。缺口说明是人工整理文件，不由脚本自动裁定。
