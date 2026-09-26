# Minimal33 来源补齐与分组实施（2026-09-24）

本次指定的5轮来源缺口已补齐并正式接入，两套Minimal33均为33 ready，33案／100轮镜像一致。六组scenario_id、可比版本minimal33_2026_09_content_v2已写入两套测试，案例等权口径已获用户确认。

- [当前100轮合同：交互页](contracts-100.html)、[JSON](contracts-100.json)、[Markdown](contracts-100.md)。
- [入库与分组确认回执](activation-receipt.json)、[分组配置及汇总口径](grouping-approved.json)、[分组说明](分组与汇总建议.md)。
- [本次验证结果](verification.json)、[就绪性](preflight.json)、[引用检查](remaining-work.json)、[预算](budget-audit.json)、[实际注入检查](isolation-audit.json)、[本次五轮的8条路由组合](source-integration-audit.json)。

来源087民诉法B/1（2024-01-01）、088最高法民事证据规定F/1（2020-05-01）、089驻美使馆通知G/2（实施日期2023-11-07）已入库，来源日期写入相关测试。当前共87份来源、25个节点；新增两个节点和N5e/N2a条件分支。来源分类获用户确认，新增wiki节点仍为needs-review。

| 测试轮 | 补充 | 可审查材料 |
| --- | --- | --- |
| TC-61/T1 | 共同财产转移后果；诉中/诉前保全条件、担保与范围 | 009第1092条，087第103—105条；财产节点及调查保全节点；N5e/N2a |
| TC-61/T2 | 法院/代理律师调查，线索、书面申请与举证期限 | 087第64、67条；088第20条；N5e |
| TC-61/T3 | 共同债务与伪造债务区分、调查申请 | 009第1064、1092条；088第20条；N5e/N2a |
| TC-62/T1 | 原始材料、电子数据保存 | 088第11、14、15条；保持optional，不强制首次披露即展开全部认证手续 |
| TC-62/T2 | 境外文书分类、中文译本、中美附加证明书及采信边界 | 088第16、17条；089第二、四项；N5e/N2a |

美国通知分支只用于上下文明确材料在美国形成的情况；其他国家加载通用证据规则。官方依据：[民事诉讼法](https://www.szgm.gov.cn/gmsfj/gkmlpt/content/11/11422/post_11422196.html)、[最高法证据规定](https://www.court.gov.cn/zixun/xiangqing/212721.html)、[驻美使馆通知](https://us.china-embassy.gov.cn/chn/lsfw/zj/fjzm/202310/t20231025_11167574.htm)。

当前100轮引用合同均为reviewed，33案均为APPROVED_AGGREGATE。用户已明确接受TC-61/T1–T3、TC-62/T1–T2新增来源合同，并批准全部33案按六组、案例等权及minimal33_2026_09_content_v2纳入正式汇总。批准版本、原话及两套文件哈希见[正式汇总批准回执](aggregate-approval-receipt.json)。

原100轮接受记录保存在[历史接受回执](accepted-contracts-receipt.json)，本次批准前的95 reviewed／5 provisional合同、就绪性和验证结果保存在[批准前快照](before-aggregate-approval/)。现有[五轮变更对照](five-turn-contract-applied.json)保留来源接入时的历史版本；当前审核身份以contracts-100.json为准。

正式汇总资格已生效。实际汇总需使用匹配此批准版本的结果；UNAVAILABLE保留缺失并显示参与案例数。当前未重跑受测模型或Judge，也未把旧结果自动视为新版评测结果。

本次离线验证覆盖精确章节、来源角色、最多3分支／8000字符预算及实际composer注入，未调用外部模型。此前5案在线结果保留，不作为新增财产／境外证据问答的在线验证。范围外案例仍有引用和内容问题，参见[全量清单](reference-integrity-2026-09-24.json)；Minimal33的0来源缺口指本轮登记缺口关闭。

candidate目录、candidate-manifest.json、grouping-proposal.json保留为入库前历史材料；当前有效批准状态以aggregate-approval-receipt.json、本次标签增量partial-abstention-receipt.json及当前contracts-100.json为准；activation-receipt.json和grouping-approved.json保留来源入库及分组阶段记录。原9月23日100轮展示页保留原样，以便核验接受回执的哈希。

## 局部 abstention 标注

已为11轮已有要求添加局部拒绝／暂缓结论标签及继续帮助边界，详见[标注清单与Judge读取方式](partial-abstention.md)。用户确认与当前文件哈希见[标签增量回执](partial-abstention-receipt.json)。100轮reviewed及33案APPROVED_AGGREGATE保留；当前版本未新增独立局部拒答准确率指标。
