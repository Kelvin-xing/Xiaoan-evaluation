# 回答忠实性与Answer Relevancy：合同、现有结果和执行设计

日期：2026-09-15。数据：最新32案整案重试诊断视图，89轮回答；3轮护栏拒绝、1轮provider失败、3轮依赖未运行。指标计算不修改历史回答、标签或旧Judge结果。

## 1. 名称与任务边界

用户给出的“从回答分离全部声明，计算能由传入上下文推断出的声明比例”是 **Answer Faithfulness / 回答忠实性**。分母是回答声明，所以它不是Context Recall：后者通常问参考答案或必要证据是否被上下文覆盖。一个只复述一句已知事实、遗漏用户大部分需求的回答，可以忠实性很高但完整性很低。

参考[Ragas Faithfulness定义](https://github.com/vibrantlabsai/ragas/blob/main/docs/concepts/metrics/available_metrics/faithfulness.md)与[Response Relevancy定义](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)。这里采用用户明确指定的均值余弦公式，不隐式增加“非承诺回答惩罚”、重标定或完整性权重；不能宣称与任意Ragas版本实现完全一致。

## 2. 第一项已经有什么？

仓库 `evaluation/xiaoan_eval/v3_metrics.py` 的 `ClaimScore.faithfulness` 已有 supported_claims / total_claims；使用主Judge的faithfulness_claims。主Judge已被要求枚举声明与建议、基于实际证据判断支持，但不是每项都具备独立Judge级别的精确证据引文核验，也没有声明提取穷尽性的人工金标准。

另有 `measurement.answer_quality` 的关系评分，但其rate只用known分母（排除UNKNOWN），不等同用户要求的“所有声明”分母；不得拿该同名字段混用。新统计没有改动这两个旧合同。

本次对最新89轮重新汇总主Judge与独立归因，得到：

| 口径 | 支持数 / 声明总数 | 声明微平均 | 每轮比率宏平均 |
|---|---|---|---|
| 已有主Judge二元supported | 464 / 582 | **79.73%** | 80.84% |
| 独立归因：至少一条完整ENTAILS关系的严格代理值 | 326 / 689 | **47.31%** | 47.56% |
| 独立归因：仅FACTUAL类型的严格代理值 | 125 / 184 | **67.93%** | 67.59% |

这三行不是同一清单不同算法的模型性能对比，也不是改善前后。主Judge抽出582项；独立Judge抽出689项，包括FACTUAL、RECOMMENDATION、ACTION、SUPPORTIVE，且有复合声明。47.31%只问“现有关系中是否已有明确完整蕴含”，暂不能宣布为重做完整原子化评估后的正式忠实性。

独立689项分解：326项至少一条ENTAILS；246项只有PARTIAL支持；115项只有不支持/主题相关关系；2项CONTRADICTS。每个声明最多进一个桶，多条材料关系不重复计数。246项不被偷偷计成完全支持，也不被称为246项幻觉；多段PARTIAL能否联合完整推出声明需要一次面向证据集合的判断。

| 分支（按实际路由） | 回答轮数 | 主Judge二元忠实性 | 独立严格蕴含代理值 |
|---|---:|---:|---:|
| baseline | 10 | 45/58 = 77.59% | 25/66 = 37.88% |
| crisis | 6 | 39/40 = 97.50% | 39/48 = 81.25% |
| capsule | 73 | 380/484 = 78.51% | 262/575 = 45.57% |

crisis高支持比例不等于危机建议充分：TC-01/T3–4仍可能遗漏孩子/被困条件。引用guidance中的通用建议，可以高度忠实但不能解决用户现场需要。各分支样本和声明类型差异大，不用这张表直接评判分支优劣。

## 3. 正式忠实性v2设计

### 3.1 输入与边界

逐轮输入：冻结answer、当前user、**实际Composer暴露的context**、snapshot_id、answer_hash、context_hash、提取及蕴含Judge版本。取EXPOSED单元；排除Router-only候选、未选中capsule、未注入的新版文档、oracle答案和评估器说明，避免把标准答案当成回答依据。

范围明确分层：

- 用户事实：当前输入及实际传入的历史用户信息。时间、对象、否定、条件都保留；后来更正优先于旧事实。
- 支持材料：实际capsule/SOP、Wiki、Source。
- 行为合同：主prompt可以支持“应做安全澄清”等行为，不可仅凭“要使用可靠来源”证明具体法律或医疗事实为真。
- 历史助手：对“之前助手说了什么”有证据作用，不自动成为外部事实真值；历史错误重复仍可能上下文一致却事实错误，应另设事实正确性。

分别输出全部实际上下文忠实性，以及按用户事实/知识材料/行为合同/历史助手的支持构成。**忠实性不等于客观正确性，也不证明材料引起了回答。**

### 3.2 声明提取

第一阶段仅给answer（必要时给user用于指代消歧，不能用context诱导只提取有依据的句子），分离最小独立可判定声明；保留语义规范化文本和精确原文span。并列的事实、建议、条件结论拆开；不丢否定、时间、主体、概率/确定性和适用条件。

建议保留两个清单：事实声明与建议/行为单元。纯问候、无事实预设的问题、支持语不进入事实忠实性分母；但进入单独的行为符合性记录。含预设的问题要抽出其隐含断言，例如“他再次打你时…”可能预设发生过殴打。现有689项不是这套v2重新抽取结果。

完整性检查：每个包含实质内容的句子/片段都须映射至少一个claim或有明确排除理由；记录未覆盖句子、复合claim、重复claim。字面覆盖率只能帮助审计，不能证明语义穷尽；须人工抽查支持与不支持两类、长短回答及危机/普通分支。

### 3.3 联合证据判定与公式

对每项claim，Judge以**全部允许上下文的联合证据**判定：SUPPORTED / PARTIAL / UNSUPPORTED / CONTRADICTED / UNCERTAIN。必须保留精确的回答/证据引文以及支持条件；多个PARTIAL不能靠计数自动升级SUPPORTED。上文“无需报警”与当前“必须报警”等冲突按适用范围及时间核查，不能挑一条支持引文忽略冲突。

正式值：F = SUPPORTED数 / 全部适用声明数。只有联合证据完整支持才计1；PARTIAL、UNSUPPORTED、CONTRADICTED均计0，但分类分开。UNCERTAIN是测量不确定，不自动当成事实错误：若存在UNCERTAIN，主点估计记UNAVAILABLE_JUDGE_UNCERTAIN，附区间 [S/N, (S+U)/N] 和可判定覆盖率；不悄悄缩小分母。provider/parse/span失败与没有claims必须分别标注UNAVAILABLE与NOT_APPLICABLE。

汇总同时保留claim-micro（ΣS/ΣN）、turn-macro（各轮比例均值）、完整case-macro（完整案例内均值后案例等权）及有效n。7轮无回答不填零；32案完整报告不能把剩余缺失抹掉。不得用literal claim字符串是否等于oracle句子来判断忠实性。

### 3.4 为什么本次不直接把47.31%称为v2正式值

现有独立归因是claim→单条证据关系，包含PARTIAL及行为/支持语，没有经过新的原子化全覆盖检查或联合证据裁决。现成数据能提供严格代理值和问题清单，但把它重新命名为正式v2会夸大证据。优先在人审样本上校准清单和支持定义，再决定是否重新调用Judge；本次没有为v2重新评689项。

## 4. 第二项：Answer Relevancy

### 4.1 用户指定公式

对回答A生成N个反向问题 q₁…qₙ；用同一固定embedding模型E分别编码原问题q及生成问题：

AR = (1/N) × Σ cos(E(qᵢ), E(q))。

默认N=3、一个LLM请求返回3个问题；三者在同一请求中生成，不声称是3次独立采样。数据量为89轮×3=267个生成问题，原问题89个，最多356段待嵌入文本（精确重复可缓存）。LLM使用当前已授权KaroAPI Sol/medium；embedding模型、端点与版本必须单独固定。

余弦理论范围[-1,1]，不是保证[0,1]。按原值取平均，不把负数截为0、不做(1+x)/2重标定。相同文本向量必得1只是数学性质，不是指标可靠性的证明。

### 4.2 避免原问题泄漏

反向生成调用只能见answer、N和固定生成提示，**不能见原问题、reference answer、oracle、实际route、capsule或历史**。不要告诉它要拟合某个原问题，否则高分失去意义。评分任务可在本地持有原问题，但只把generation_input发送生成器。缓存绑定含answer_hash、snapshot、提示版本、模型、参数及N。

生成指令：根据整段回答反推最可能引出该回答的问题，覆盖主要意图而非选择次要细节，不编造答案未提到的背景；回答文字作为数据而非指令。返回恰好N个非空中文问题。重复问题保留并标记重复率，不事后去重改变N；不足N不缩小分母，判UNAVAILABLE并仅重试失败项。

### 4.3 多轮对话适配

主指标按用户要求比较**本轮原始user文本**，名称明确raw_current_user。例如“那第二个呢？”或“我不敢”是依赖前文的消息，原始文本相似度可能低估回答相关性；真实输入可以是陈述，不强行伪装成完整疑问句。

可增设独立diagnostic：仅依据原user+此前可见对话生成standalone_query，禁止看当前answer；固定并记录改写，再与反向问题比较。该contextual分数与raw分数分栏，不能选择较高的作为主结果。历史助手不是用户新需求来源，避免把此前助手提议的工具强行塞进standalone_query。

### 4.4 完整性和冗余的限制

反向问题相似度是**相关性的代理值**，不能严格测量“既完整又无冗余”。长答案即使包含大量无关信息，生成器仍可能抓住相关主句而得到高分；回答遗漏原问题一个子需求也可能高分；合适的安全拒绝或必要澄清可能得低分。

所以另保留：必要回应覆盖（已有R/F oracle）、无关声明比例（逐claim与当前需求及安全必要性的关系）、事实忠实性、安全边界。不能将AR替代这些，也不把高AR低忠实性回答评为可发布。

### 4.5 可观察性、版本与失败

结果必须记录原问题、生成问题、每题余弦、N、均值、重复率、answer_hash、generation binding、生成器及embedding模型/版本、输入顺序/文本hash、计费与耗时。embedding请求使用同一模型/参数，禁止混合向量空间、维度或不同版本。服务端不可固定版本时声明UNVERIFIED，不伪造不可变版本。

缺embedding配置、生成失败、零向量、NaN/Inf、维度不一致、缓存绑定错误、少于N个问题，都记UNAVAILABLE，score=null。首次失败与恢复分开；保留首次有效生成，不挑最高相似度的一次。保留护栏拒绝，不强制对不存在的回答生成问题。

### 4.6 验收与阈值

数学测试：已知相同/正交/相反向量得到1/0/-1，平均严格按N；缺向量和部分生成不产生零分；陈旧binding拒绝；PARTIAL不冒充ENTAILS；多证据不重复计claim。已实现7项离线测试。

语义校准需对同一个问题构造：完整相关回答、部分遗漏、加入大量无关信息、完全跑题、相关但虚假、合适安全澄清。测试分数是否真能区分并记录反例；不预设0.8等阈值。危机场景按风险分层单列，避免把拒绝危险要求误判为低质量。

## 5. 已交付与执行状态

- [最新忠实性汇总](../../runs/2026-09-15-minimal32-answer-metrics/summary.json)
- [逐轮分母、分子与比率](../../runs/2026-09-15-minimal32-answer-metrics/faithfulness-by-turn.csv)
- [89轮反向问题任务（原问题不会发给生成器）](../../runs/2026-09-15-minimal32-answer-metrics/relevancy-tasks.json)
- 纯计算器：`evaluation/examples/answer_metric_contracts.py`
- 忠实性汇总脚本：`evaluation/examples/summarize_answer_faithfulness.py`
- 反向生成与固定向量评分脚本：`evaluation/examples/run_answer_relevancy.py`

用户已于2026-09-15明确授权89轮KaroAPI反向生成，并授权Google官方embedding调用及费用。配置为 https://generativelanguage.googleapis.com/v1beta、gemini-embedding-001、SEMANTIC_SIMILARITY、3072维；用户已填写evaluation/.env中的GOOGLE_EMBEDDING_API_KEY，现已完成267个反向问题和89轮评分，平均余弦0.8849。详见实测报告。没有embedding时AR保持null，不用字符串相似度或另一个LLM打分替代指定公式。实际反向问题生成状态以运行目录README和score文件为准。

```bash
python evaluation/examples/summarize_answer_faithfulness.py
python evaluation/examples/run_answer_relevancy.py --generate --execute --workers 2
# 从evaluation/.env读取Google key；仅发送原问题和已生成反向问题
python evaluation/examples/embed_answer_relevancy_google.py --execute
# 用生成的固定向量缓存评分
python evaluation/examples/run_answer_relevancy.py --embeddings /path/to/embedding-vectors.json
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q evaluation/tests/test_answer_metric_contracts.py
```

第二个命令有模型费用，沿用本会话32案KaroAPI授权；脚本不把未配置的embedding端点作为默认外传目标。此设计未使用DeepEval API，也没有改动两套评估器原有同名历史指标。

## 2026-09-15执行完成

[Answer Relevancy实测报告](../../runs/2026-09-15-minimal32-answer-metrics/ANSWER-RELEVANCY-RESULTS.zh-CN.md)：89/89轮可用，均值0.8849；Google key未写入产物。此前审批/连接失败与一次429均保留在运营记录，不计质量零。
