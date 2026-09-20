# XiaoAn 89轮评估公开产物

本目录发布32案96轮诊断选择中的89轮有效回答及7轮不可用状态。统计、逐轮诊断、Faithfulness、Answer Relevancy与整合报告均来自冻结结果；没有在发布时重新调用模型或向量服务。

## 目录

- `2026-09-15-minimal32-answer-metrics/`：Faithfulness与Answer Relevancy汇总、逐轮CSV、反向问题和审阅HTML。
- `2026-09-21-minimal32-scenario-analysis/`：按任务、主题、限制、对话特征和风险的情境标签与chatflow诊断。
- `2026-09-21-minimal32-integrated-report/`：通过正常evaluation report入口生成的Markdown与Excel。

整体Answer Relevancy均值为0.884936；主Judge支持率为464/582；独立严格蕴含代理值为326/689。各指标口径、分母与限制见对应报告。

## 发布边界

本公共目录不包含完整原始运行trace、`.private` attribution文件、embedding向量缓存、API请求缓存、`.env`或API key。逐轮报告保留复核这些结果所需的回答、声明、证据层、绑定摘要和统计；缺失运行资料不会被当作质量零分。
