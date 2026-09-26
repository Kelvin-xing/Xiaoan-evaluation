# Report Agent：正式報告流程

`run`、`report`、`matrix`（多模型版）及更新工作簿的 experiment/stability/human-review 流程，預設由 LLM Report Agent 生成 `report.md`。舊 `render_decision_report` / `render_matrix_report` 保留為歷史相容工具，正式 CLI 不呼叫，也不在 Agent 失敗時回退。

測評的評分、metrics 和 Excel 證據計算保留；停用的是用 Python 模板編寫最終分析報告的路徑。scenario/knowledge 的分析事實仍寫入 Excel，不再把舊 Markdown 分析附錄拼到新報告。

## 模型與連線

Report Agent 預設重用所在 evaluation 的 `company_eval_plugins` 連線設定與金鑰讀取。單模型版使用既有 OpenAI-compatible Judge 連線；多模型版使用其既有 GlobalAI/compatible Judge 連線。不會自動改用 Qwen/Kimi 專用 Subject transport。

在對應的本地 `.env` 設定（不要提交金鑰）：

```dotenv
XIAOAN_REPORT_MODEL=你的報告模型ID
XIAOAN_REPORT_REASONING_EFFORT=medium
XIAOAN_REPORT_WIRE_API=responses
```

`XIAOAN_REPORT_MODEL` 未設時沿用 `XIAOAN_JUDGE_MODEL`，再回退現有默认 `gpt-5.5`。wire 未設則沿用 `XIAOAN_OPENAI_WIRE_API`，再使用 `responses`；只支援 Chat Completions 的服務請設為 `chat_completions`。模型必須能輸出 JSON object；provider 的模型支援及連線須另行實測。

CLI 會在執行測評前檢查預設定義表及 provider 設定；這不是付費的連線探測。正式生成會產生额外 LLM 调用费用。只发送工作簿工具实际读取的内容与定义表，不向 Agent 提供 repo 文件、环境变量或 shell 工具。

自訂 provider：`--report-agent-plugin module:callable`，或 `XIAOAN_REPORT_AGENT_PLUGIN`。callable 接收 `{messages, step, prompt_version}`，返回 JSON 字串。可接入其他 provider 或本地模型；不可返回預寫模板冒充模型分析。

## 工作方式

1. 評估完成後先產生 `results.xlsx`。
2. 強制載入打包的 `xiaoan_eval/report_metric_dictionary.md`。
3. Agent 取得 sheet/欄位/資料列數目錄，以受限 `read`、`search` 動作讀取原始資料。
4. Agent 生成 findings、引用及完整 Markdown；程式檢查必需 sheet 已讀、引用確曾讀取、至少一個引文與儲存格原文相符。
5. 只有通過檢查才替換正式報告；程式只添加來源雜湊等 provenance front matter，不撰寫分析正文。

定義表的編輯來源是 repository 的 `docs/plans/evaluation-report-metric-dictionary.zh-HK.md`；兩個套件各打包同一份內容，以支援獨立安裝。更新來源時必須同步兩份 packaged resources；測試會核對其一致性。也可以明確傳入 `--metric-definitions /path/to/definition.md`，實際內容的雜湊會記錄於報告及 audit。

預設最多 48 次模型動作、累積上下文 240000 字元。可使用 `--report-agent-max-steps`、`--report-agent-context-chars` 調整。工具分頁不截斷單個儲存格；超出整體預算會明確失敗，不以未讀完的內容冒充完整分析。

## 只重跑報告

在對應 evaluation 資料夾執行：

```bash
python -m xiaoan_eval report-workbook runs/RUN_ID/results.xlsx \
  --output runs/RUN_ID/report.md
```

輸入也可以是失敗後保存的 audit `input.xlsx`。此命令不重跑 Subject 或 Judge，不修改原 Excel。原有 `report CASE_RESULTS.jsonl --output DIR` 仍接受案例 JSONL，先形成 Excel，再調用 Agent。

## 失敗與追溯

一般 workflow 將 audit 存於輸出目錄旁的 `.RUN_ID.report-agent-audit/`。每次嘗試獨立保存：input.xlsx、dictionary.md、messages.json、逐步模型原文、manifest.json；成功另有 findings.json、report.md。

manifest 包含 prompt 版本、模型標識、workbook/dictionary 雜湊、完成狀態及已讀資料列。這些 audit 含測試對話及證據，維持本地私有，不應提交或公開。

Agent 缺少設定、服務失敗、JSON 無效、引用不合法或預算耗盡時，不生成模板替代品。生成中的 Excel 已在 audit 保存；已有正式 workbook/report 在 Agent 失敗時保持原樣。測評 provider 失敗仍按原有 UNAVAILABLE 邏輯處理，與 Report Agent 失敗分開。

## 驗證邊界

機械檢查證明引用存在、精確引文存在及來源可追溯；不能證明 LLM 的所有算術、因果解釋或建議均正確。Agent 被要求按定義表標明分母、缺失、暫定 oracle、Judge 分歧及根因假設；產品決策仍需人工覆核或受控實驗。首版沒有增加新的 Python 報告統計層，也沒有自動修改 prompt/router/capsule/ground。
