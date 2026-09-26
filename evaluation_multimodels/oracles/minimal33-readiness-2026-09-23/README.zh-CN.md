# Minimal33 当前就绪性（2026-09-23）

> 2026-09-24最终批准状态：[当前合同及批准回执](../minimal33-update-2026-09-24/README.md)：33 ready、100轮引用reviewed、33案APPROVED_AGGREGATE；六组、案例等权及minimal33_2026_09_content_v2已批准。下文旧阶段数值为历史记录。

> 最新状态见 [100轮合同审阅及验证结果](../minimal33-contract-review/README.md)：来源缺口剩5轮，静态加载缺口0；下文8轮/9轮为本轮修复前的基线记录。

用户确认TC-21的法域澄清测试目的及TC-75回答期待后，两套Minimal33均为 **33 ready／0 needs_remediation／0 invalid**，33案／100轮，案例层33 REVIEWED。此前31 ready／2待修的结果已被本次复核取代。

TC-21使用有理由的日期不适用状态；TC-75案例层审核已记录。91轮旧引用／配置差异已修复。剩余8轮内容来源缺口、9轮静态加载覆盖差异，以及新reference合同审核，见[引用修复及后续处理](../minimal33-reference-repair-2026-09-23/README.zh-CN.md)。

aggregate指汇总；当前score_scenario只对同一场景与comparability_group下、成熟度为APPROVED_AGGREGATE且分数可用的案例取不加权平均。当前0案APPROVED_AGGREGATE。ready检查、案例层回答审核、新引用合同审核及正式汇总批准是不同环节。

新版100轮reference合同为provisional，原审核保存在previous_review；这不会撤回案例层已确认的回答期待。当前preflight没有检查所有引用、条件分支和法律充分性，需与修复报告一起阅读。

## 日期已补到哪里

每案 `oracle_provenance` 新增 `source_effective_dates`，含法律名称、施行日期、官方链接、日期依据和适用条文主题。`legal_dates_checked_by: codex` 记录本次日期核验；原 `reviewed_by: mat` 及原审核日期没有扩展成新内容的批准记录。

旧单值字段 `legal_effective_date` 为兼容 loader，填写**本次列出的相关法律版本中最新的施行日期**。逐来源日期才是实际依据；该单值不代表审核日期、检索日期或该案所有主张均已覆盖。新加的细分元数据目前由 YAML 和本核验包保存，loader 的 OracleProvenance 数据模型仍只读取旧单值字段。

| 案例 | 单值字段更新为 | 主要日期依据 |
|---|---|---|
| TC-01、TC-11、TC-14、TC-63 | 2016-03-01 | 反家庭暴力法；TC-01 仅为中国内地求助处置的法律背景，危机行动仍按安全合同评估 |
| TC-15 | 2023-01-01 | 妇女权益保障法修订版；另列反家暴法、保护令规定 |
| TC-29 | 2024-04-26 | 未成年人保护法现行修正版本；第11条强制报告机制早于此次修正已存在 |
| TC-37、TC-42、TC-57、TC-66 | 2022-08-01 | 保护令司法解释；同时列相关反家暴法依据 |
| TC-61 | 2024-01-01 | 民事诉讼法2023年修正版本；另列民法典2021-01-01 |
| TC-62 | 2023-11-07 | 附加证明书公约在中美间生效；另列证据规定2020-05-01、民法典2021-01-01、保护令规定2022-08-01等 |
| TC-72 | 2025-02-01 | 婚姻家庭编解释（二）；另列民法典。替换原2026-08-19 |
| TC-74 | 2016-03-01 | 反家暴法求助及公安处置背景；不据此承诺警方陪同取物。替换原2026-08-19 |

官方核验入口：[反家暴法](https://www.beijing.gov.cn/zhengce/zhengcefagui/qtwj/201606/t20160628_776539.html)、[保护令规定](https://www.court.gov.cn/fabu/xiangqing/366021.html)、[妇女权益保障法修订说明](https://www.npc.gov.cn/c2/c30834/202211/t20221101_320169.html)、[未成年人保护法现行版本](https://flk.npc.gov.cn/detail?fileId=&id=ff8081818f197cf001905e567af635a0&title=中华人民共和国未成年人保护法&type=)、[民法典](https://www.court.gov.cn/zixun/xiangqing/233181.html)、[民诉法修改决定](https://www.npc.gov.cn/npc/c2/c30834/202309/t20230901_431419.html)、[证据规定](https://www.court.gov.cn/zixun/xiangqing/212721.html)、[驻美使馆附加证明书通知](https://us.china-embassy.gov.cn/chn/lsfw/zj/fjzm/202310/t20231025_11167574.htm)、[婚姻家庭编解释（二）](https://www.court.gov.cn/zixun/xiangqing/452771.html)。

完整来源与修改前后文件哈希见 [source-effective-dates.json](source-effective-dates.json)。外部已核实法律的链接没有自动变成运行时 Source：TC-61 的财产调查程序、TC-62 的境外证据手续、TC-72 的完整探望规则等仍需完成来源入库与引用合同修复。

## 当前产物

- [preflight.json](preflight.json)：两套33案100轮当前loader及审核状态。
- [selection.json](selection.json)：当前选择集哈希；原2026-09-22清单保留作为来源。
- `check_readiness.py`：从仓库根目录使用项目Python执行即可重建以上两项。
