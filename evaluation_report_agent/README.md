# 統一評測報告 Agent

唯一輸入是通過完整性驗證的 `xiaoan-results/v2` JSON 與其綁定附件。Excel 由評測 exporter 獨立生成，Report Agent 不讀 workbook。

```bash
PYTHONPATH=evaluation python -m evaluation_report_agent --results runs/example/results.json --output runs/example/report
PYTHONPATH=evaluation python -m evaluation_report_agent --results runs/example/results.json --output runs/example/report --execute
```

省略 `--execute` 只準備本地來源目錄。執行時分頁查詢凍結證據，逐次保存已讀範圍、請求與用量；來源和 prompt/model 共同綁定報告版本。原結果不改寫，報告失敗留下草稿，可獨立重試相同請求。更改配置或來源需新報告目錄。

輸出為 `report.md`、`findings.json`、`manifest.json`、`validation.json`、`query-log.json`、`request-receipts.json`、`calls/` 和 `requests/`。引用須出現在已傳送頁面；結構化數字由 JSON pointer 核對。報告解釋仍需人工審閱。
