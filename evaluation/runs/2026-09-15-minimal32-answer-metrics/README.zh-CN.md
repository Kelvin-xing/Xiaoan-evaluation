# 32案：回答忠实性与Answer Relevancy

2026-09-15，使用最新整案重试诊断选择的89轮回答。7轮无回答保留各自执行状态，不计质量零分。

## 忠实性现有结果

- 主Judge二元supported：**464/582 = 79.73%**；每轮比例均值80.84%。这是已有主Judge清单的重新汇总。
- 独立逐引文归因的严格蕴含代理值：**326/689 = 47.31%**；每轮比例均值47.56%。
- 独立清单：326项完整支持、246项只有部分支持、115项不支持/仅主题相关、2项矛盾。只统计FACTUAL的代理值为125/184 = 67.93%。

不同清单不能混成同一个准确率，也不能把所有非完整支持都叫幻觉。现有清单含复合声明及行为/支持语，未重做v2原子化全覆盖和联合证据裁决；因此严格代理值不是新的正式忠实性金标准。

## Answer Relevancy状态

**已完成89/89轮评分**，共267个反向问题、356段原问题/生成问题文本向量。整体平均余弦 **0.8849**，中位数 **0.8895**；完整28案case-macro **0.8839**。baseline 0.9038（10轮）、crisis 0.8950（6轮）、capsule 0.8815（73轮）。这不是正确率，尚无经人工校准的通过阈值。

使用KaroAPI Sol/medium仅从回答反推问题；Google官方gemini-embedding-001，SEMANTIC_SIMILARITY、3072维。用户已明确授权两类调用。一次早期连接错误、一次Google 429限流均保留；限流后25秒间隔续跑，成功缓存复用。

- [实测统计与解释](ANSWER-RELEVANCY-RESULTS.zh-CN.md)
- [逐轮原文、生成问题与相似度](answer-relevancy-review.html)
- [逐轮CSV](answer-relevancy-by-turn.csv)
- [独立重算与凭据扫描验证](validation.json)

## 文件

- [2026-09-21情境分類與chatflow診斷：重用本批凍結回答](../2026-09-21-minimal32-scenario-analysis/REPORT.zh-CN.md)
- [逐輪情境、原文、claim引文及整改候選](../2026-09-21-minimal32-scenario-analysis/review.html)
- [正常evaluation流程產出的整合報告](../2026-09-21-minimal32-integrated-report/report.md)
- [完整指标设计、公式、多轮边界与验收](../../oracles/minimal32-remediation/ANSWER-FAITHFULNESS-RELEVANCY.zh-CN.md)
- [汇总与分支统计](summary.json)
- [逐轮忠实性CSV](faithfulness-by-turn.csv)
- [逐轮指标与执行状态](turn-metrics.json)
- [反向生成待评任务](relevancy-tasks.json)
- [Answer Relevancy状态表](answer-relevancy-scores.json)
- [embedding输入状态](embedding-inputs.json)

验证：7项离线合同测试通过，覆盖PARTIAL不计完整支持、多证据不重复计数、矛盾不能被支持掩盖、余弦1/0/-1、N不足或陈旧binding不可用、无效向量和重复问题处理。没有将程序测试当成语义正确性证明。

## Google key填写位置

embedding凭据不随公共结果发布；运行配置请参考本地项目的忽略文件，不要提交密钥。官方base为 `https://generativelanguage.googleapis.com/v1beta`，模型 `gemini-embedding-001`，两边文本都用 `SEMANTIC_SIMILARITY`、3072维。

配置完成后执行 `python evaluation/examples/embed_answer_relevancy_google.py --execute`，再用 `run_answer_relevancy.py --embeddings evaluation/runs/.2026-09-15-minimal32-answer-relevancy.private/google-embedding-vectors.json` 计算指定的平均余弦。成功生成和向量缓存可复用，失败保留；不自动更换模型。

接口依据：[Google官方Embeddings API](https://ai.google.dev/api/embeddings)。
