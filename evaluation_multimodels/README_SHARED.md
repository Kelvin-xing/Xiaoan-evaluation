# XiaoAn Evaluation｜共同設計指南

多模型 matrix 與單一 deployment evaluation 共用同一套 claim、requirements、missingness 和 gate 契約。完整共同設計請閱讀 [`evaluation/README_SHARED.md`](../evaluation/README_SHARED.md)；matrix 的操作命令和 provider 設定請閱讀 [`README/README.md`](README/README.md)。

matrix 的核心規則如下：

- 先按 subject lane 完成並凍結同一批多輪 answers，再讓不同 Judge 評估同一份 answer。
- 每個 answer 只抽取一次 immutable claim inventory；faithfulness、correctness、task、constraint、interaction 和 relevancy 分開判斷。
- `UNAVAILABLE`、`NOT_ATTEMPTED`、`UNKNOWN` 和 `NOT_APPLICABLE` 保留其語義，不能轉成品質零分或 PASS。
- self-judging cell 保留原始結果但排除主要 Judge 分母；不同 model alias 不自動代表獨立真值。
- `measure unified` 是明確選用的 `xiaoan-unified/v1` 第二階段入口，不會靜默重算 legacy matrix workbook。
- `measure capsule-ablation` 只測固定 `COMPOSER_FIXED_CONTEXT` 的 capsule 有／無，不等於 router 或完整 Chatflow 的因果驗證。

評估編排是 deterministic workflow 加上有限的語義 evaluator ensemble。模型數量或 Judge agreement 本身不是品質證據；正式結論仍需 approved oracle、gold inventory 或人工校準。
