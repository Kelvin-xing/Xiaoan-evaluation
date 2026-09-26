# 诊断记录与指标边界

## 已修复：历史快照转换导致归因不可用

可重复的原始回放：92 轮有回答，其中 58 轮报 `snapshot.router.units[2] PRIOR_USER source_turn must be earlier than snapshot.turn`；34 轮通过。

最小回归命令（在 evaluation 目录）：

```sh
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -m pytest -q tests/test_evidence.py -k runtime_history
```

修复前输出：`1 failed, 1 passed`，失败位置为 `_unit` 检查历史 source_turn。测试使用第5轮中长度为2的历史窗口，要求来源轮次为3、3、4、4；同时检查 Router 历史不能进入 Composer 证据目录。

检查了三种假设：转换器统一赋当前轮、窗口序号误作绝对轮次、当前内容混入历史。实际代码表明：Chatflow `state.context_for_router` 提供完成对话的末尾窗口，`router.py` 用窗口内零基序号生成 history/N/role；evaluator 之前无条件写 `source_turn=turn`。因此在转换入口按明确的窗口合同还原，并拒绝未知格式、身份不一致、不连续或超长历史窗口。正文和内容哈希不修改。

修复后完整92轮均通过；测试还验证错误历史仍被拒绝。未改 subject 的分流或回答行为，历史运行结果不重写。

## 已观察：Router 有历史，Composer 无显式历史

这次 KaroAPI 冻结 trace 中，后续61个有回答轮次的 Composer 都没有 PRIOR_USER 历史单元，也未使用 provider continuation。58个有 Router 调用的后续轮次，其历史窗口正确；3轮危机绕过 Router。

实际 `compose.prepare_compose_request` 在自定义 API base 下不发送 previous_response_id，当前请求只构造本轮 user_message、capsule、ground、safety_message。故 Router 的正确记忆窗口不能证明 Composer 获得前文。它可解释 TC-05 忽略视障/无可信人、TC-29 丢失教师身份等现象，但修复历史传递是否改善这些回答仍需要单变量重跑，不能当成已证实的因果结论。

本次新增 `conversation_context_observation` 和双session本地装置：

```sh
python evaluation/examples/probe_memory_session_isolation.py
```

正常不同状态对象 PASS；故意共享状态的负对照 FAIL。仅证明当前进程 ConversationStore 的隔离检查能抓到串会话，不证明模型语义不泄漏或服务器API鉴权正确。

## 新增归因回放的验证边界

独立归因 Judge 仅收到冻结回答与经过快照校验、实际向 Composer 暴露的证据目录。Router 独占资料、当前新版但当时未注入的 Source、原始完整私有 trace 均不作为其回答依据。

每条主张的回答引文及证据引文须精确匹配原文。错位时仅允许原文中唯一的完整相同引文重新定位，原始输出保留；缺失、重复且错位、未知证据引用均拒绝。UNSUPPORTED 不能和支持关系混用；不修改语义关系去强行通过。

Provider 最初拒绝未显式声明 type 的 enum/const schema；修正的是请求格式，没有放宽响应验证。结构校验失败用 JUDGE_INVALID，网络/服务错误用 PROVIDER_ERROR，两者均不当成质量零分。

实际快照缺少结构化 policy_ids；因此“逐项policy合规”仍为 TRACE_MISSING，不以空列表算全部合规。主张级 attribution 可独立报告哪些内容受 capsule、prompt、用户信息支持，以及哪些只有主题相关或无依据；它不证明因果依赖，也尚非人工校准的发布门槛。

## 已完成的 oracle 复审范围

96行 authored decision 按用户上下文重新作出，不复制实际路由/扫描器为gold；复审并非盲审，仍需人审校准。每轮包括可接受集合、preferred、风险依据、crisis接管、必要和禁止行为、允许替代及争议。新增标签均为 provisional；人审角色仍由用户/领域审阅者承担。

回答 oracle 全部逐轮复核；两处提出修订：TC-11/T2 的两小时照护误读，TC-62/T2 避免必须复述公约名称。其余保留语义要求并明确替代边界。修订稿保存在 response_candidate，未悄悄改写已审核历史 gold；原92条 Judge 结果按原输入绑定重新验证。

TC-72/74 的 after_turn=3 与 usage 明确要求第4轮不一致，已在 memory-probe-contracts.yaml 提出第4轮检查合同。TC-77 补具体工作事实种子；TC-79 补双session seed、查询、负对照及证据要求。新的模型级记忆测试未运行，不冒充已通过。
