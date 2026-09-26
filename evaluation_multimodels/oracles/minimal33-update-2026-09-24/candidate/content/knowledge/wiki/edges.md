---
type: legal-edge-catalog
title: "法律机制关系目录"
updated: 2026-09-20
status: draft
---

# 法律机制关系目录

## 本轮关系词汇

| Relation | 含义 |
| --- | --- |
| `defines_scope_for` | 定义或范围规则界定另一机制的适用范围。 |
| `initiates` | 依法报告、报案或申请后启动另一法定程序。 |
| `provides_evidence_for` | 某程序形成的记录进入证据集合。 |
| `proves` | 证据用于证明法律要件。 |
| `is_element_of` | 某要件属于某项请求权或救济的构成条件。 |
| `enables` | 某机关行为使另一保护措施得以实施。 |
| `creates_consequence_for` | 违反命令或规则触发责任后果。 |
| `may_be_restrained_by` | 某行为可以由特定禁令或救济制止。 |
| `locally_supplements` | 地方性法规在特定法域内为全国性法律机制增加更具体的义务或流程。 |
| `requires_special_protection_in` | 特定主体处境要求既有受理或救济机制加强保护。 |
| `governs_evidence_for` | 证据规则约束另一机制中事实认定的方式和标准。 |

## 当前关系

| ID | From | Relation | To | Claim | Source refs | Status |
| --- | --- | --- | --- | --- | --- | --- |
| E001 | `domestic-violence-scope` | `defines_scope_for` | `protection-order-real-danger-element` | 家暴法定含义界定保护令“遭受家庭暴力”的要件范围。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第一章 总则/第二条`<br>`knowledge/source/002-中华人民共和国反家庭暴力法.md#第四章 人身安全保护令/第二十七条` | draft |
| E002 | `domestic-violence-scope` | `defines_scope_for` | `family-law-relief` | 家暴认定影响准予离婚和损害赔偿规则的适用。 | `knowledge/source/009-民法典婚姻家庭编.md#第一千零七十九条`<br>`knowledge/source/009-民法典婚姻家庭编.md#第一千零九十一条` | draft |
| E003 | `domestic-violence-scope` | `defines_scope_for` | `liability-for-domestic-violence` | 家暴行为仅在满足具体违法或犯罪构成时进入对应责任层级。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第五章 法律责任/第三十三条` | draft |
| E004 | `help-and-reporting-paths` | `initiates` | `police-response-and-investigation` | 向公安报案或有关机关依法移送，可启动公安受理和处置。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第三章 家庭暴力的处置/第十三条`<br>`knowledge/source/003-刑事诉讼法.md#第一百一十条` | draft |
| E005 | `help-and-reporting-paths` | `provides_evidence_for` | `protection-order-evidence` | 有关单位形成的投诉、反映和求助记录可以作为保护令证据。 | `knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第六条` | draft |
| E006 | `mandatory-reporting` | `initiates` | `police-response-and-investigation` | 强制报告启动公安受理、调查与保护处置。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第三章 家庭暴力的处置/第十四条`<br>`knowledge/source/002-中华人民共和国反家庭暴力法.md#第三章 家庭暴力的处置/第十五条` | draft |
| E007 | `police-response-and-investigation` | `provides_evidence_for` | `protection-order-evidence` | 出警、接警、询问和鉴定等记录可以进入保护令证据集合。 | `knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第六条` | draft |
| E008 | `police-response-and-investigation` | `enables` | `temporary-shelter-and-placement` | 对法定危险状态人员，公安通知并协助民政安置。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第三章 家庭暴力的处置/第十五条` | draft |
| E009 | `warning-letter` | `provides_evidence_for` | `protection-order-evidence` | 告诫书是司法解释列举的保护令证据。 | `knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第六条` | draft |
| E010 | `protection-order-evidence` | `proves` | `protection-order-real-danger-element` | 达到较大可能性的证据组合用于证明家暴或现实危险。 | `knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第六条` | draft |
| E011 | `protection-order-real-danger-element` | `is_element_of` | `protection-order` | 遭受家暴或面临现实危险是作出保护令的法定条件之一。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第四章 人身安全保护令/第二十七条` | draft |
| E012 | `protection-order` | `creates_consequence_for` | `liability-for-domestic-violence` | 违反保护令可能触发训诫、罚款、拘留或刑事责任。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第五章 法律责任/第三十四条`<br>`knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第十二条` | draft |
| E013 | `child-snatching-and-concealment` | `may_be_restrained_by` | `protection-order` | 抢夺、藏匿未成年子女可由保护令或人格权侵害禁令制止。 | `knowledge/source/044-最高法关于民法典婚姻家庭编解释二.md#最高人民法院关于适用《中华人民共和国民法典》婚姻家庭编的解释(二)/第十二条` | draft |
| E014 | `local-intake-risk-assessment-and-referral` | `locally_supplements` | `help-and-reporting-paths` | 在适用法域内，地方性法规为国家法的投诉、反映和求助入口增加首接、跟进、转介、反馈或风险评估要求。 | `knowledge/source/021-云南省反家庭暴力条例.md#第一章 总  则/第六条`<br>`knowledge/source/021-云南省反家庭暴力条例.md#第三章 家庭暴力的处置/第二十三条`<br>`knowledge/source/026-河南省反家庭暴力条例.md#第三章 家庭暴力的处置/第二十条` | draft |
| E015 | `cohabiting-person-scope` | `defines_scope_for` | `domestic-violence-scope` | 共同生活关系范围与暴力行为范围需要分别满足，才能适用相应反家暴机制。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第六章 附则/第三十七条`<br>`knowledge/source/045-最高法关于人身安全保护令适用法律规定.md#最高人民法院关于办理人身安全保护令案件适用法律若干问题的规定/第四条` | draft |
| E016 | `special-protection-groups` | `requires_special_protection_in` | `help-and-reporting-paths` | 受理投诉、求助或报案时，应结合未成年人、老年人、残疾人、孕哺期妇女和重病患者的处境加强保护。 | `knowledge/source/002-中华人民共和国反家庭暴力法.md#第一章 总则/第五条` | draft |
| E017 | `post-relationship-harassment` | `defines_scope_for` | `protection-order` | 妇女在恋爱、交友、关系终止或离婚后遭受特定纠缠骚扰时，存在独立的保护令入口。 | `knowledge/source/005-妇女权益保障法.md#第二十九条` | draft |
| E018 | `sexual-violence-in-family-context` | `creates_consequence_for` | `liability-for-domestic-violence` | 家庭或亲密关系中的性侵害满足具体犯罪构成时，依法进入刑事责任层。 | `knowledge/source/004-刑法.md#第二百三十六条` | draft |
| E019 | `delayed-reporting-and-criminal-evidence` | `governs_evidence_for` | `liability-for-domestic-violence` | 刑事证据规则和家暴案件调查要求约束具体犯罪事实的认定，延迟控告本身不是自动采信或排除规则。 | `knowledge/source/003-刑事诉讼法.md#第五十条`<br>`knowledge/source/003-刑事诉讼法.md#第五十五条` | draft |
| E020 | `jiangsu-domestic-violence-scope` | `locally_supplements` | `domestic-violence-scope` | 江苏省现行条例在本法域内明确列举性暴力、经济控制并规定共同生活人员参照适用。 | `knowledge/source/086-江苏省反家庭暴力条例.md#第一章 总则/第二条`<br>`knowledge/source/086-江苏省反家庭暴力条例.md#第一章 总则/第三条`<br>`knowledge/source/086-江苏省反家庭暴力条例.md#第六章 附则/第五十四条` | draft |
