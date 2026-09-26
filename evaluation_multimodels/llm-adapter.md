# 多模型请求配置

`evaluation_multimodels` 与 `tech_multimodels/chatflow/poc` 共用 `evaluation_multimodels/.env`。修改后下一次请求读取新值；请求参数不会从同名进程环境变量取值。核心实现在 `evaluation/xiaoan_eval_core/llm_adapter.py`，两个项目从同一实现导入。

```dotenv
XIAOAN_OPENAI_WIRE_API=responses
XIAOAN_CLAUDE_WIRE_API=messages
XIAOAN_GEMINI_WIRE_API=gemini_native
XIAOAN_OPENAI_REQUEST_BODY='{"max_output_tokens":4096,"reasoning":{"effort":"medium"},"temperature":null}'
XIAOAN_CLAUDE_REQUEST_BODY='{"max_tokens":4096}'
XIAOAN_GEMINI_REQUEST_BODY='{}'
XIAOAN_MODEL_REQUEST_BODIES='{"gpt-5.6-luna":{"reasoning":{"effort":"high"}},"claude-sonnet-5":{"max_tokens":8192}}'
```

将示例中的模型 ID 换成当前 `.env` 配置的精确 ID。厂商字段支持 `OPENAI`、`CLAUDE`、`GEMINI`，保留的 Qwen/Kimi 路径也可使用 `QWEN`、`KIMI`。省略协议时，OpenAI 默认 Responses，Claude 默认 Messages，其余默认 Chat Completions。旧 `XIAOAN_CLAUDE_API_MODE=openai` 仍可显式选择兼容协议，但新的 `XIAOAN_CLAUDE_WIRE_API` 优先。

请求体优先级：调用方默认参数 → 厂商 `REQUEST_BODY` → 精确模型 `MODEL_REQUEST_BODIES`。对象递归合并，`null` 删除字段；数组整体替换。使用目标协议的原生参数名，例如 Responses 使用 `max_output_tokens` 和 `reasoning`，Messages 使用 `max_tokens` 和可选 `thinking`。参数是否被具体模型或中转服务接受，需要由该服务支持。

模型、消息、system/instructions、结构化输出和串流控制字段由程序生成，配置覆盖这些字段会直接报错。非法 JSON 同样会在请求发出前报错。SDK 未声明的供应商扩展参数会经 `extra_body` 发送。OpenAI 的 `text.verbosity` 可配置，`text.format` 仍由评估器管理。

调整协议或请求参数后，请使用新的评估输出目录；现有 checkpoint 的身份校验尚未包含这些 env 覆写，直接 resume 会复用旧答案。

适配覆盖矩阵的回答与 Judge，以及评估辅助客户端、Chatflow 安全分类、Router、Ground selector、同步和异步回答生成。Responses 转换 `input`、token 上限、reasoning 和 JSON schema；Messages 分离顶层 `system`，保留对话历史，并以工具提交结构化结果。端点可填写 API 根路径或完整方法路径，适配器会规范化方法后缀。

Claude 的现有 Chatflow 异步路径仍在后台线程等待完整 Messages 回包后输出，不提供逐 token 的原生 Messages SSE。Responses 保留原有流式路径。验证使用合成内容和 mock HTTP，未执行真实供应商评测。

协议依据：[OpenAI Responses API](https://developers.openai.com/api/reference/python/resources/responses/methods/create)、[Anthropic Messages API](https://platform.claude.com/docs/en/api/messages/create)。

## 本次离线验证

新增契约测试覆盖 env 优先级、递归合并与删除、非法配置、三种协议的真实 SDK HTTP 序列化、矩阵 Responses JSON/SSE 回包、Messages 历史与结构化输出，以及 Chatflow 同步／异步 Responses。

全量评估测试记录为 445 通过、2 失败；Chatflow 全量记录为 219 通过、15 失败（另有 1373 个通过的子测试）。失败涉及报表字典副本、测试模型与共享配置约束、内容语料快照和对话历史预期。这些全量结果不是上线验收通过；本次未修改对应业务规则或内容快照。

## 当前模型矩阵

- GPT：回答与 Judge 均为 `gpt-5.6-luna`，使用 OpenAI Responses。
- Claude：回答与 Judge 均为 `claude-sonnet-5`，使用 Anthropic Messages。
- Gemini：回答使用 `gemini-3.8-flash`，备用／比较模型为 `gemini-3.1-pro-preview`，经 GlobalAI Gemini 原生 `generateContent` 端点调用，不经过 KaroAPI。
- DeepSeek：回答与 Judge 均为 `deepseek-chat`，走 DeepSeek 官方 Chat Completions 端点。

GlobalAI、KaroAPI 及其他共享中转端点已从运行时配置移除。各厂商必须单独填写对应的 `XIAOAN_*_API_KEY`；空 key 会在请求前失败。

## 统一调用约束（当前实现）

所有生产模型请求现在由 `llm_adapter` 的 `astream`、`acomplete` 或 `arequest` 发起；上层的 `OpenAI`/`AsyncOpenAI` 对象只作为 adapter 的协议客户端。评估矩阵使用 `arequest`，Chatflow 使用 `astream`，同步兼容入口内部也转入 async adapter。

每次请求都会重新读取共享 `.env`。模型、端点、API key、协议、请求体覆写和 cache 模式都不从旧的进程环境或硬编码默认值取得；缺少对应 key 会在请求前失败。

`XIAOAN_PROMPT_CACHE_MODE=explicit` 时，Responses 使用 cache key/TTL，Messages 使用 `cache_control`，Chat Completions 使用 provider 支持的 cache key 字段；返回的 cache telemetry 继续由评估器记录。未返回 telemetry 时只记录未知，不推断命中。

## 并发与请求参数

并发限制也由共享 `.env` 控制：

```dotenv
XIAOAN_CLAUDE_MAX_CONCURRENCY=2
XIAOAN_OPENAI_MAX_CONCURRENCY=2
XIAOAN_GEMINI_MAX_CONCURRENCY=2
XIAOAN_DEEPSEEK_MAX_CONCURRENCY=2
XIAOAN_SUBJECT_CONCURRENCY=2
XIAOAN_JUDGE_CONCURRENCY=3
XIAOAN_MAX_IN_FLIGHT=3
```

其中 `XIAOAN_<PROVIDER>_MAX_CONCURRENCY` 是单供应商硬限制；`XIAOAN_MAX_IN_FLIGHT` 是全局硬限制。CLI 显式参数仍可覆盖矩阵并发值。超时、重试次数、输出 token 上限、stream 和 cache 参数也从同一 `.env` 读取。
