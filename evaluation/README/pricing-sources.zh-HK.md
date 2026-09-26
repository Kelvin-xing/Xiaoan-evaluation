# 成本分析定價來源（離線目錄）

本功能只接受明確的 `provider`、`model`、`billing_route`、`currency` 和每百萬 token 費率。`gpt` 是模型家族/供應商標籤，不是 billing route；`GlobalAI`、官方 API、雲市場和 reseller 的價格不可互相代用。目錄沒有精確匹配時，成本為 `UNAVAILABLE`。

## 已核對的官方來源

- [Anthropic Claude Platform pricing](https://platform.claude.com/docs/en/about-claude/pricing)：頁面列出模型的 base input、cache write、cache hit 和 output 每 MTok 費率；本例保留 Claude Haiku 4.5 的 USD 1/5 及其 cache 乘數。這是 Anthropic 直連價格，不能推導 GlobalAI 或 Bedrock 的實際帳單。
- [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching)：`input_tokens` 是 cache breakpoint 之後的未快取 token；完整 input 應加上 cache read 和 cache creation/write token。因此分析器不把 `input_tokens` 當成已包含 cache 的總數。
- [Alibaba Cloud Model Studio model pricing](https://www.alibabacloud.com/help/en/model-studio/model-pricing)：官方頁面列出 Qwen model ID 和 Model Studio deployment scope 的 input/output 費率。本例保留 `qwen-max` 的 illustrative schema entry，並指定 `model-studio-international` route；不能套用到 XiaoAn 目前未核實的 `qwen3.8-max` 或 GlobalAI endpoint。

## 目錄和研究限制

`pricing.example.json` 是 schema/example catalog，不是本次 XiaoAn matrix 的 live billing confirmation。當前 defaults 含有可能是未來或尚未核實的 model ID；本研究沒有為它們臆造價格，也沒有讀取 `.env` 或發出外部評測呼叫。若要納入實際 matrix，先以 invoice/provider response 確認完整 route、model ID、currency、cache policy 和 token usage，再新增 exact entry。
