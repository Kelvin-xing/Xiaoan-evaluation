---
type: source-registry
title: "LLM Wiki 全量重建来源登记表"
updated: 2026-09-24
status: draft
rebuild_mode: empty-wiki-rebuild
---

# LLM Wiki 全量重建来源登记表

## 本轮边界

- 本表是 empty-wiki rebuild 的初始化记录，不继承旧 registry 的 `done`、`reviewed` 或 manifest 验收状态。
- 基线提交：`8b83489855e81e66bd796c99c55155386673ea40`；当前 source snapshot：`sha256:dca4c28eb6216e03d6465d8a594c61527747e8baf86351f65eabd88865259f6a`。
- 当前候选共有87份active canonical source；055和061已按律师复核结论退役并保留永久编号空缺，086为后续新增的江苏省现行条例。本轮已完成逐source覆盖并记录draft结果，尚未进行最终法律验收。
- 旧 `nodes/`、`syntheses/`、`edges.md`、`legal-mechanism-tree.md`、`index.md`、manifest 和 update report 已从工作树隔离归档；它们不得作为本轮事实、schema、覆盖记录或验收基线。
- 只有在后续逐 source／逐 section 处理、引用校验和人工内容审阅完成后，才能更新处理状态或接受新 manifest。

## 处理状态

- `pending`：尚未在本轮重建中处理；完成本轮整合后不得残留。
- `incorporated`：已处理，至少一项净新增进入节点、边或综合页。
- `in-progress`：正在按 section 处理，必须记录已完成范围。
- `covered-no-new-content`：已读完但没有独特增量，并已记录覆盖依据。
- `retained-reference-only`：source 留库，但不生成节点或边。
- `needs-repair`：文本、来源或现行性问题阻断相关范围。
- `blocked`：受持久化风险限制，解除前不得抽取受影响 passage。

## Source snapshot inventory

| canonical ID | 文件 | source_code | source_tier | SHA-256 | processing_status | open_risk_ids |
| --- | --- | --- | --- | --- | --- | --- |
| 001 | `001-宪法.md` | A | 1 | `3f15d8f53cdff943aa40458ad87d5ce9b408ae93044ac31e375746b3ecff00c6` | `retained-reference-only` | — |
| 002 | `002-中华人民共和国反家庭暴力法.md` | B | 1 | `519e04e43c781b51f8bc0891113fda4ec686949a84ae7b1b414728a820f9cbbe` | `incorporated` | — |
| 003 | `003-刑事诉讼法.md` | B | 1 | `465469bf44b10cf25cab69c62720db42cf11c28e3dfd3c127d96c2465d9f3f93` | `incorporated` | — |
| 004 | `004-刑法.md` | B | 1 | `cc579fb7c3375d94a065817ffd2ce38d3928ddc5406da7134fe278c764c51022` | `incorporated` | — |
| 005 | `005-妇女权益保障法.md` | B | 1 | `3301fb2bcf7cebd65cd45ed0aee1dd7a17bb040b4e5c22e87e28628cb38949ad` | `incorporated` | — |
| 006 | `006-家庭教育促进法.md` | B | 1 | `adc14a9149f268f3d87e9fe872f7ad15179c64e3b23906f1edc3af1d1d27de83` | `incorporated` | — |
| 007 | `007-未成年人保护法.md` | B | 1 | `e4e4d81d22075c482d497e3a1324124a226c0f288ce75dd66d6e182703014365` | `incorporated` | — |
| 008 | `008-残疾人保障法.md` | B | 1 | `0be9d731a3dd7f1dfc958823c05a7430d78e25eb084c53959844705f0bb041b3` | `incorporated` | — |
| 009 | `009-民法典婚姻家庭编.md` | B | 1 | `3c72e60fea5fba2c4c406679d79156d9afec9226af4002a1a383a68455ba6e2f` | `incorporated` | — |
| 010 | `010-治安管理处罚法.md` | B | 1 | `2f1147b2652c2780538f847ca62bda056e3a52caad6e3be00408898e238f0678` | `incorporated` | — |
| 011 | `011-法律援助法.md` | B | 1 | `f1e5aeac40fbf8e64b6dc7b85cb7a5746109a10ba7055ed36b26504b1bfa828d` | `incorporated` | — |
| 012 | `012-精神卫生法.md` | B | 1 | `ad52d8efbf93c7a467b38c8bb1474f256ab91d06959a73e7d19dffb3939a69d1` | `incorporated` | — |
| 013 | `013-老年人权益保障法.md` | B | 1 | `987796ed399ebaebdc4bbac9f7085e2bfc6bbd025ad30db65d2cc4df1220bcc7` | `incorporated` | — |
| 014 | `014-公职人员政务处分法.md` | B | 1 | `333b7d87192718f39a673c71b2853756fb6e6d721c9f3e6db41850057a70489b` | `incorporated` | — |
| 015 | `015-警察法（节选）.md` | B | 1 | `6c7285f8649cb37fd4a8be7c568034b185ecc9295bcf4889e125b3882d4f6928` | `incorporated` | — |
| 016 | `016-城市居民委员会组织法（节选）.md` | B | 1 | `d20bd41f27d57fb0bc605c37da9afa72f439819b4f1f7f427a773f4549bb7ef3` | `incorporated` | — |
| 017 | `017-村民委员会组织法（节选）.md` | B | 1 | `3a977440b2118da2957d0286cdee3cbb7539ccdb54c62adc49e5fb04cf541d8f` | `incorporated` | — |
| 018 | `018-人民调解法（节选）.md` | B | 1 | `18c64360974cb02d45ed8aad4877e5d0783efffae0771e64ddd3ea9ecbc499e0` | `incorporated` | — |
| 019 | `019-婚姻登记条例.md` | C | 1 | `dc416c204ea2b2b695f02dbab2548860f6d48b51f2345b6035252af3e5a4096d` | `incorporated` | — |
| 020 | `020-城市生活无着的流浪乞讨人员救助管理办法（节选）.md` | C | 1 | `55e7ce826250f23497538b1d2d8cfe7c08e91552892a42af6ad829a772ce1487` | `incorporated` | — |
| 021 | `021-云南省反家庭暴力条例.md` | D | 1 | `40c3e462692478cedf16ffbaa39c4af6f5f463c0c896cc23939c24322fb0289d` | `incorporated` | — |
| 022 | `022-吉林省反家庭暴力条例.md` | D | 1 | `508844a7970f50cb521642fee754d9fea8a272c0f1b2d45bced2a86c69ea82db` | `incorporated` | — |
| 023 | `023-山东省反家庭暴力条例.md` | D | 1 | `c6cb42a605949921717675ea7a60fba0c6645f7a9bf317f671bcb9f7e7f4e40c` | `incorporated` | — |
| 024 | `024-山西省家庭暴力预防和处置办法.md` | D | 1 | `844328ca03cbf9283e9543a4d516cba2432e5a7a05c0e9a81d6bd57d3a9204b2` | `incorporated` | — |
| 025 | `025-河北省反家庭暴力条例.md` | D | 1 | `2b9f842140c759cc1f03fe521921cb6e18a7f52a2659ca6e4fc33edf8d226b50` | `incorporated` | — |
| 026 | `026-河南省反家庭暴力条例.md` | D | 1 | `ba7175a3610d4ce44bd34f7559df60e81972ba7efb04e61c32381d341260bb33` | `incorporated` | — |
| 027 | `027-湖北省反家庭暴力条例.md` | D | 1 | `b63ee31d5a29096fe6d41359374f54626830b4d467325808cabddf6d41e66022` | `incorporated` | — |
| 028 | `028-甘肃省反家庭暴力条例.md` | D | 1 | `c5d09026824f355161220c07779d7856c104225084795e059e5aa9e58906ca35` | `incorporated` | — |
| 029 | `029-贵州省反家庭暴力条例.md` | D | 1 | `9d64c994c7da4fab10d2a1f9b6475a8f3dbaa3351c3e379856ae922b0ff2f805` | `incorporated` | — |
| 030 | `030-辽宁省反家庭暴力条例.md` | D | 1 | `29929a3a9dace2a3eac7e21c2b197240c785363e8931c392a0b2c3f1cbcedb53` | `incorporated` | — |
| 031 | `031-青海省反家庭暴力条例.md` | D | 1 | `1a5b8cb59994a7348477217fdff35e3468c5e42055fe047f3a57f484df077e4b` | `incorporated` | — |
| 032 | `032-黑龙江省反家庭暴力条例.md` | D | 1 | `ccbd9d0238ade54abf8b6c18df58a2530106831cff6a598b8dc5309e2d7b376e` | `incorporated` | — |
| 033 | `033-安徽省实施《中华人民共和国反家庭暴力法》办法.md` | D | 1 | `f3f2573aeaec1c9437a8067c378cbf0dbc44f49283bb3851f24315a5b0abbac4` | `incorporated` | — |
| 034 | `034-广东省实施《中华人民共和国反家庭暴力法》办法.md` | D | 1 | `4910460ea1311e7d695b241adc9deaf0617f83bab060864431625eb3e615403a` | `incorporated` | — |
| 035 | `035-湖南省实施《中华人民共和国反家庭暴力法》办法.md` | D | 1 | `6e09fd160e4b435645cb00993f95760c8b7c7a14142a90a52c2e0145289e1de4` | `incorporated` | — |
| 036 | `036-海南省实施《中华人民共和国反家庭暴力法》办法.md` | D | 1 | `d0cf58e4b0008b7ed038f0acf4f8d899156ac03a4c64a649d4a31add8fe4b3da` | `incorporated` | — |
| 037 | `037-陕西省实施《反家庭暴力法》办法.md` | D | 1 | `3cd9b2da8d0b5da4033e0cc1ede4b71eba5c3fe87cd23445de2980ac75b4a735` | `incorporated` | — |
| 038 | `038-重庆市实施《中华人民共和国反家庭暴力法》办法.md` | D | 1 | `d85a74b358a0db2ff3b69ca268f0a3d33c23e90a0f6383e7f85f836cb1c96ba3` | `incorporated` | — |
| 039 | `039-新疆维吾尔自治区实施《反家庭暴力法》办法.md` | D | 1 | `106080820def5d116192a16958f3df912efa871c120bc86a6049b5480aca4b30` | `incorporated` | — |
| 040 | `040-幼儿园工作规程.md` | E | 1 | `c4fc2f55aa561d62101378e3fb62aaa2eada43d9cf210c9377c2eb34cba7acce` | `incorporated` | — |
| 041 | `041-未成年人学校保护规定.md` | E | 1 | `42a06c3f1ae5607a5883b2a5b913ac45c61bff48e424abb2980652b08318db8e` | `incorporated` | — |
| 042 | `042-公安机关办理刑事案件程序规定（节选）.md` | E | 1 | `ea665b24e6994301d25e07eadd8178d78c663f178900daa4e21b4cab9173823e` | `incorporated` | — |
| 043 | `043-最高法关于民法典婚姻家庭编解释一.md` | F | 1 | `6399bd49f4e9851cedb67e14220f88d67b8ca4914f704143bf997ae59ecfb01c` | `incorporated` | — |
| 044 | `044-最高法关于民法典婚姻家庭编解释二.md` | F | 1 | `22a3bd0c823f48164eca819ea596a0524c35baf6097cd164cd34fcb64e51a0a1` | `incorporated` | — |
| 045 | `045-最高法关于人身安全保护令适用法律规定.md` | F | 1 | `a07e781d474338aa36d69a73e69687a437c6a067c483e61b25964eeb7316f751` | `incorporated` | — |
| 046 | `046-最高法关于刑诉法解释.md` | F | 1 | `f0cd22a405de3e4a3ff2dfe799d5615b10fb2391a0283b66d41eaf7b4ea8ea0a` | `incorporated` | — |
| 047 | `047-最高法关于办理财产保全案规定.md` | F | 1 | `4b1eb06b21afcb7383b82c85498ccc7934fe42a46088f123699f765c1e126141` | `incorporated` | — |
| 048 | `048-关于依法办理家庭暴力犯罪案件的意见.md` | G | 2 | `974300932ac7c9dd64cb6184f465a93f63600af264f4bfd26219526a16b3fc99` | `incorporated` | — |
| 049 | `049-关于做好家庭暴力受害人庇护救助工作的指导意见.md` | G | 2 | `784362198c3d477bb6e87d6becb72190ce0f0b7ffafb4248c0b900a339eb1258` | `incorporated` | — |
| 050 | `050-关于加强人身安全保护令制度贯彻实施的意见.md` | G | 2 | `d5b6d58f0f8de8e56e6a8518779cd9b261e3e3e4d97973d0513b3f79c5b6b526` | `incorporated` | — |
| 051 | `051-关于加强家庭暴力告诫制度贯彻实施的意见.md` | G | 2 | `8285e747be2bef4fcfd854022de65db2ad90eaabeb2e54f199bb0d2cd96fabb8` | `incorporated` | — |
| 052 | `052-关于建立侵害未成年人案件强制报告制度的意见试行.md` | G | 2 | `d1b2b578cc050da2bac0741f1d70eb71f8c2540f4c073cf8abad39aabde27494` | `incorporated` | — |
| 053 | `053-公安机关办理伤害案件规定.md` | G | 2 | `e27c013625c728e41406876baa30ccc8785bce03ef2d01a43f6bafb5836c0dcc` | `incorporated` | — |
| 054 | `054-托育机构管理规范试行.md` | G | 2 | `b8616c43dc024c14d4e0029fc83ac7cb385be12845337d2392af78a1aaa0ab2d` | `incorporated` | — |
| 056 | `056-关于依法处理监护人侵害未成年人权益行为若干问题的意见.md` | G | 2 | `ba99033fe4a331a3697ddf5edfadb8ee7d71269f0842347ca9af3ca17972d4b6` | `incorporated` | — |
| 057 | `057-城市生活无着的流浪乞讨人员救助管理办法实施细则（节选）.md` | G | 2 | `a6591c3e72eadf8611fd865dc3454698540d894d9d1c28d40cb77db2975bef69` | `incorporated` | — |
| 058 | `058-公安派出所执勤规范（节选）.md` | G | 2 | `99996677d0c8b44abcacaf26abda320b6b82d761a6acdf108dffa5cc2fec615e` | `incorporated` | — |
| 059 | `059-最高人民法院反家庭暴力典型案例.md` | H | 2 | `f004c0e9d433f368ca6a900c3a22e9c6576797e70936bfb051d58f584d81014a` | `incorporated` | — |
| 060 | `060-妇联组织受理家庭暴力投诉工作规程.md` | I | 2 | `6f047455f320eee7f2ed5a139af387f5df9e5d3d2677cd6515d3b148e1e29218` | `incorporated` | — |
| 062 | `062-预防和制止家庭暴力多部门合作工作手册.md` | I | 2 | `7b6c85a9e12ad5858bbdcd94c042a70119136722dcf35cd0a6e4a0bb172ec642` | `incorporated` | — |
| 063 | `063-未成年人法律援助服务指引（试行）（节选）.md` | I | 2 | `1021d554974ea0e068d5a4b06f629a5561b238ac091ee2844659b7f6c03b693f` | `incorporated` | — |
| 064 | `064-妇联-12338妇女维权热线工作指南.md` | I | 2 | `100e22f2c2fac44152e55781d7049d22ea9a18996209dbe2ce887116b3a3c932` | `incorporated` | — |
| 065 | `065-妇联-基层妇联维权工作手册.md` | I | 2 | `03c98dcdcc550d61956b62863da2aef24232520d8972f4bbf5b8427b69b7575b` | `incorporated` | — |
| 066 | `066-妇联-朝阳区基层妇联维权手册.md` | I | 2 | `cd4d99e42eafbb91dd310cb912d8dd91584603da5a4afd84d4777d5be1f2f117` | `incorporated` | SR-011 |
| 067 | `067-预防和制止家庭暴力警察工作手册.md` | I | 2 | `66d3ed197bf8344bbb59c2595238ca060caf3a20cf3a5a164685fd53ee23d8d8` | `incorporated` | — |
| 068 | `068-儿童权利公约(CRC).md` | J | 3 | `2008a1679a93fde54800c2a2d2867f01cea6afb547edb051ccfc71624a1ecdad` | `incorporated` | — |
| 069 | `069-残疾人权利国际公约(CRPD).md` | J | 3 | `27613459f0493e36d5e2302ca2c0b60581f6d35208744e9e2b383b0214679959` | `incorporated` | — |
| 070 | `070-经济社会文化权利国际公约(ICESCR)（节选）.md` | J | 3 | `1f8dd4608ed1e69c3a37ffd5b8f5834269a6275cfecccb3ee63d477cfa401dd8` | `incorporated` | — |
| 071 | `071-联合国-消除对妇女一切形式歧视公约.md` | J | 3 | `c5d088c57c20fd5e971af2137d932519ea898bbe7de1db35c3d919b8d3e0062c` | `incorporated` | — |
| 072 | `072-世界妇女大会行动纲领.md` | J | 3 | `d6a2c1af422d38a5a302cb6c0460c289d356954178fb9a7b1035b1ef4acb14a6` | `incorporated` | — |
| 073 | `073-联合国消除对妇女的暴力行为宣言.md` | J | 3 | `c1ef74fad5e7714cb897041f874bda8bd8f811e805899b7cecaa89f1147494ef` | `incorporated` | — |
| 074 | `074-中华人民共和国反家庭暴力法解读 全国人大常委会法制工作委员会社会法室编著.md` | K | 3 | `388195123103a8938badba75bacf7f203979be6b0209450782ce3bcb37295f8a` | `incorporated` | — |
| 075 | `075-公权力介入家务事有法可依——反家庭暴力法亮点解读.md` | K | 3 | `b2ea32abadb550ae7f4f592a9030744a10dc32c9590116095aaa2648a62d72f8` | `incorporated` | — |
| 076 | `076-《反家庭暴力法》出台：旗帜鲜明地反对家庭暴力——宋秀岩接受人民网专访.md` | K | 3 | `6b128c5b30614e5147ce842aac6896091eff529c930095c7159d8f8ee046264c` | `incorporated` | — |
| 077 | `077-反家暴法律与实务详解-妇联.md` | K | 3 | `ee5a9e6121d72cc585342fb31c54e915ec41001f26465a8e204f29f35fd59732` | `covered-no-new-content` | — |
| 078 | `078-中国反家暴立法与实践概述-《反对针对妇女的家庭暴力》.md` | K | 3 | `2acb1082769251079f8825b4c98d94a11950f8a6357793ef1c56bc4ee6b01429` | `incorporated` | — |
| 079 | `079-家庭暴力的基本问题-《反对针对妇女的家庭暴力》.md` | K | 3 | `147dcff8b016a4d1a808aa0995df23db5cbf54800285910364686258c5f38fce` | `incorporated` | SR-019 |
| 080 | `080-反家庭暴力典型案例选编.md` | K | 3 | `7f5e7f66a9d72cd56bd55840fcdc251802b2bf9de8665599e6baf6327a04b462` | `retained-reference-only` | — |
| 081 | `081-案例-典型案例评析-《反对针对妇女的家庭暴力》.md` | K | 3 | `969669ec16ab7da046ca70759629a2fd1f0ece4b2a45ef800f83815d4b0088c1` | `retained-reference-only` | — |
| 082 | `082-案例-家暴案例评析-《法治与家庭丛书 反家庭暴力案例评析》.md` | K | 3 | `8e45e870ddb76c28cf2b5b43190ff108f6fac63a8b5c76b1f0535b901f42c710` | `needs-repair` | SR-021 |
| 083 | `083-为平反家暴七周年案例分析.md` | K | 3 | `4a529c385581db52266d0041f7b4c72ab42c4db6d0a58fe89298a96c46ef86e6` | `incorporated` | — |
| 084 | `084-为平反家暴八周年案例分析.md` | K | 3 | `92080c6394d32c4c86192dffe6321d2c7cb3aa243897807e8e8d80ca66f30fd3` | `incorporated` | SR-022 |
| 085 | `085-源众-抢夺藏匿未成年子女案例研究报告.md` | K | 3 | `c7b2702be564b4d94103ae5a4e9c0f0c3bf591cff87fc60814af40362d076bbc` | `incorporated` | — |
| 086 | `086-江苏省反家庭暴力条例.md` | D | 1 | `5b31479a340957e00673f219d70980fcc273b383464deebceda2fddbb991f7dd` | `incorporated` | — |
| 087 | `087-中华人民共和国民事诉讼法.md` | B | 1 | `fa1e255d8281b30dd0ab075ace33edc0ceb3645b188a65b5d2d4573b31c59180` | `incorporated` | — |
| 088 | `088-最高人民法院关于民事诉讼证据的若干规定.md` | F | 1 | `17ebe6b2d26ba157aee09cb897f009e1acb8b95130cbcdae2f8036b1c95b9e34` | `incorporated` | — |
| 089 | `089-驻美使领馆停办领事认证业务通知.md` | G | 2 | `672e3eb0f2b76f1b99ce9246919ebad1bdfe469a041a5e12574d543358b9e0c5` | `incorporated` | — |

## 未解决的持久化风险

以下各行逐字复制自 `content/knowledge/source/source-文件处理规范.md` 的开放风险。
风险只约束列明的具体范围；普通的节选、历史时点、来源角色和跨来源去重不再登记为开放风险。

| risk_id | canonical source | 状态 | 问题／核验结果 | rebuild 限制／处理结论 |
| --- | --- | --- | --- | --- |
| SR-011 | 066 | `PROVENANCE_REVIEW` | 人工审核确认该文件是北京市朝阳区妇联2021年内部工作手册／培训材料节选，不属于挂文号发布的政策文件；与065重复内容已在节选时删除。现有材料经源众指导资料取得，源文件链并非朝阳区妇联官方发布，仍无父手册官方链接。 | 可标明地区、年份、内部材料和节选属性后使用现有地方流程；不得外推为全国规则、补写省略内容或声称已取得官方发布原件。 |
| SR-019 | 079 | `TEXT_BLOCKED` | 人工审核确认材料年代较早；“四、外国反家庭暴力立法简介／（一）美国”开头的流行率、伤亡和经济损失数字没有可用引证，也缺乏时效性。 | 只阻断该统计段落；其余学理和比较法内容可作为标明历史时点的 `doctrinal_foundation`。 |
| SR-021 | 082 | `TEXT_BLOCKED` | 人工审核确认“懦弱”“缺乏法律意识”“关系不清不楚”等受害者责备和基于旧《婚姻法》的建议属于材料原文，不改写或删除原文。 | 阻断这些评价与旧法建议段落；中性案件事实只可作为注明年代且待一手核验的二手 `case_application`。 |
| SR-022 | 084 | `TEXT_BLOCKED` | 人工审核确认“七、学校／点评”末句是原PDF自身的编校残缺；考虑资料重要性和核验成本，不向发布方追补缺文。 | 保留原PDF未完标记并阻断该未完句，不得推测补写；083、084其余内容可作监测评论，和059重复的案例按常规去重。 |

## 结论

- 当前 registry 仅保留4条开放风险；已解决或已重分类为常规使用边界的事项不再收录。
- 开放风险只阻断表中明确的坏段落或元数据判断，不自动限制整份 source。
- 当前registry已完成draft覆盖和结构整合；页面为`draft`或`needs-review`，均未标记`reviewed`，不表示法律结论已获人工验收。

## Per-source coverage

| ID | 覆盖范围 | processing_status | Wiki输出／理由 |
| --- | --- | --- | --- |
| 001 | 全文逐章／逐节。 | `retained-reference-only` | 宪法背景已读；没有需要独立建模的反家暴操作规则。 |
| 002 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/cohabiting-person-scope.md`、`content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/nodes/help-and-reporting-paths.md`、`content/knowledge/wiki/nodes/legal-aid-and-procedural-support.md`、`content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/nodes/mandatory-reporting.md`、`content/knowledge/wiki/nodes/police-response-and-investigation.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md`、`content/knowledge/wiki/nodes/protection-order-real-danger-element.md`、`content/knowledge/wiki/nodes/protection-order.md`、`content/knowledge/wiki/nodes/sexual-violence-in-family-context.md`、`content/knowledge/wiki/nodes/special-protection-groups.md`、`content/knowledge/wiki/nodes/temporary-shelter-and-placement.md`、`content/knowledge/wiki/nodes/warning-letter.md` |
| 003 | 当前收录条文逐条；补齐第五十条、第五十五条的现行证据规则。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/delayed-reporting-and-criminal-evidence.md`、`content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 004 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/sexual-violence-in-family-context.md` |
| 005 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md`、`content/knowledge/wiki/nodes/legal-aid-and-procedural-support.md`、`content/knowledge/wiki/nodes/post-relationship-harassment.md`、`content/knowledge/wiki/nodes/protection-order.md` |
| 006 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md` |
| 007 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/mandatory-reporting.md`、`content/knowledge/wiki/nodes/sexual-violence-in-family-context.md`、`content/knowledge/wiki/nodes/special-protection-groups.md`、`content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 008 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/special-protection-groups.md` |
| 009 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/family-law-relief.md` |
| 010 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/post-relationship-harassment.md`、`content/knowledge/wiki/nodes/warning-letter.md` |
| 011 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/legal-aid-and-procedural-support.md` |
| 012 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/special-protection-groups.md` |
| 013 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/special-protection-groups.md` |
| 014 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/liability-for-domestic-violence.md` |
| 015 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/police-response-and-investigation.md` |
| 016 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 017 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 018 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 019 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 020 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 021 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 022 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 023 | 全文逐条。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 024 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 025 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 026 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 027 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 028 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 029 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 030 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 031 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 032 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 033 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 034 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 035 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 036 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 037 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 038 | 全文逐条。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 039 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/local-regulations-comparison.md` |
| 040 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/mandatory-reporting.md` |
| 041 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/mandatory-reporting.md` |
| 042 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/help-and-reporting-paths.md`、`content/knowledge/wiki/nodes/police-response-and-investigation.md` |
| 043 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/nodes/family-law-relief.md` |
| 044 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/child-snatching-and-concealment.md` |
| 045 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/cohabiting-person-scope.md`、`content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/nodes/help-and-reporting-paths.md`、`content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md`、`content/knowledge/wiki/nodes/protection-order-real-danger-element.md`、`content/knowledge/wiki/nodes/protection-order.md`、`content/knowledge/wiki/nodes/warning-letter.md` |
| 046 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/help-and-reporting-paths.md` |
| 047 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/legal-aid-and-procedural-support.md` |
| 048 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/delayed-reporting-and-criminal-evidence.md`、`content/knowledge/wiki/nodes/legal-aid-and-procedural-support.md`、`content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/police-response-and-investigation.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md` |
| 049 | 全文逐节；OCR与断行已修复。 | `incorporated` | `content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 050 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/police-response-and-investigation.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md`、`content/knowledge/wiki/nodes/protection-order.md`、`content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 051 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/protection-order-evidence.md`、`content/knowledge/wiki/nodes/warning-letter.md` |
| 052 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/mandatory-reporting.md` |
| 053 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/police-response-and-investigation.md` |
| 054 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/mandatory-reporting.md` |
| 056 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 057 | 当前节选全部标题。 | `incorporated` | `content/knowledge/wiki/nodes/temporary-shelter-and-placement.md` |
| 058 | 当前节选全部条文；已核对2002年3月11日与公通字〔2002〕13号并修复第四十九条断行。 | `incorporated` | `content/knowledge/wiki/nodes/police-response-and-investigation.md`；仅作历史机关实施背景。 |
| 059 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/child-snatching-and-concealment.md`、`content/knowledge/wiki/nodes/cohabiting-person-scope.md`、`content/knowledge/wiki/nodes/delayed-reporting-and-criminal-evidence.md`、`content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/nodes/family-law-relief.md`、`content/knowledge/wiki/nodes/liability-for-domestic-violence.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md`、`content/knowledge/wiki/nodes/protection-order.md`、`content/knowledge/wiki/nodes/sexual-violence-in-family-context.md`、`content/knowledge/wiki/syntheses/implementation-observations.md` |
| 060 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md`、`content/knowledge/wiki/nodes/protection-order-evidence.md` |
| 062 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md` |
| 063 | 当前四个节选标题全部处理。 | `incorporated` | `content/knowledge/wiki/nodes/child-safety-and-guardianship.md`、`content/knowledge/wiki/nodes/protection-order.md` |
| 064 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md` |
| 065 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md` |
| 066 | 现有地方手册节选全部处理；按朝阳区2021年范围标注。 | `incorporated` | `content/knowledge/wiki/nodes/local-intake-risk-assessment-and-referral.md` |
| 067 | 全文逐章；仅作2013年历史培训/实施背景。 | `incorporated` | `content/knowledge/wiki/nodes/police-response-and-investigation.md` |
| 068 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 069 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 070 | 当前第九至十二条节选全部处理。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 071 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 072 | D节全部处理；不登记全文覆盖。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 073 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/international-framework.md` |
| 074 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/nodes/sexual-violence-in-family-context.md`、`content/knowledge/wiki/syntheses/doctrinal-and-legislative-context.md` |
| 075 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/doctrinal-and-legislative-context.md` |
| 076 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/doctrinal-and-legislative-context.md` |
| 077 | 全文逐章／逐节。 | `covered-no-new-content` | 全文已读；法条问答由002、045和074以更强来源覆盖，没有独特、可复用净新增。 |
| 078 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/doctrinal-and-legislative-context.md` |
| 079 | 全文逐章；排除SR-019无引证美国统计段。 | `incorporated` | `content/knowledge/wiki/nodes/domestic-violence-scope.md`、`content/knowledge/wiki/syntheses/doctrinal-and-legislative-context.md` |
| 080 | 全文逐章／逐节。 | `retained-reference-only` | 16个二手匿名案例已读；缺少足以稳定识别并优于059等官方案例的独特材料，保留参考。 |
| 081 | 全文逐章／逐节。 | `retained-reference-only` | 4个二手案例已读；未确认与一手裁判的稳定对应关系，保留参考而不创建案例节点。 |
| 082 | 全文逐案；排除SR-021受害者责备与旧法建议。 | `needs-repair` | 全文已读；SR-021受害者责备与旧法建议较密集，中性事实尚缺一手核验，待修复／核验。 |
| 083 | 全文逐章／逐节。 | `incorporated` | `content/knowledge/wiki/syntheses/implementation-observations.md` |
| 084 | 全文逐节；排除SR-022原PDF未完句。 | `incorporated` | `content/knowledge/wiki/syntheses/implementation-observations.md` |
| 085 | 全文逐节；人工审核确认维度2图表错误，保留27起有罪、11起无罪及71%／29%。 | `incorporated` | `content/knowledge/wiki/nodes/child-snatching-and-concealment.md` |
| 086 | 国家法律法规数据库2025年1月14日修正版全文逐章／逐条。 | `incorporated` | `content/knowledge/wiki/edges.md`、`content/knowledge/wiki/nodes/jiangsu-domestic-violence-scope.md`、`content/knowledge/wiki/syntheses/local-regulations-comparison.md`；仅适用于江苏法域和有效期间。 |

## 2026-09-23 增量补充

模式：incremental ingest；保留现有4项开放风险及其限制，manifest未接受。009补1062、1064、1066、1084、1086、1087、1092；043补65—68；044补13。完整条文经最高法官方页面核对。新增上述2个独立法律概念节点（needs-review），不为凑图谱增加关系边；现有边的引用与端点保持有效。新增087—089的草稿在oracles的pending-sources，尚未进入active inventory。

## 2026-09-24 程序与境外证据增量（候选）

- 087：处理第64、67、70、103—106、108条；调查和保全独立概念进入civil-investigation-and-preservation。第70条暂作上下文保留，不为覆盖而添加无关节点。
- 088：处理第11、14—17、20条；第20条支持调查申请，其余支持foreign-civil-evidence。
- 089：四项通知全文已核对；第二、四项以institutional_implementation挂靠境外证据节点，第16条司法解释承担法律依据，不让通知单独承重。
- 两个新增节点均为needs-review；不增加缺乏必要性的关系边。原有4项开放风险范围与限制不变，manifest未接受。候选分类待确认，正式目录尚未改变。
