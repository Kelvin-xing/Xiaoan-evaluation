# 統一評測報告 Agent

唯一輸入是通過完整性驗證的 `xiaoan-results/v2` JSON 與其綁定附件。Excel 由評測 exporter 獨立生成，Report Agent 不讀 workbook。

```bash
PYTHONPATH=evaluation python -m evaluation_report_agent --results runs/example/results.json --output runs/example/report
PYTHONPATH=evaluation python -m evaluation_report_agent --results runs/example/results.json --output runs/example/report --execute
```

省略 `--execute` 只準備本地來源目錄。執行時分頁查詢凍結證據，逐次保存已讀範圍、請求與用量；來源和 prompt/model 共同綁定報告版本。原結果不改寫，報告失敗留下草稿，可獨立重試相同請求。更改配置或來源需新報告目錄。

模型收到精簡目錄及從核准路由差異、安全檢查失敗和案例 gate 失敗選出的有限優先線索；完成報告前須讀取對應的診斷摘要與原始回答或評分。該流程定位異常，不驗證程式根因。此版結果沒有歷史 Chatflow 程式與配置快照時，報告將核對狀態列為待完成，成因只可列為附重現方法的假說。

輸出為 `report.md`、`findings.json`、`manifest.json`、`validation.json`、`query-log.json`、`request-receipts.json`、`calls/` 和 `requests/`。引用須出現在已傳送頁面；結構化數字由 JSON pointer 核對。報告解釋仍需人工審閱。

## 報告模板與覆蓋邊界

`prompts/report.md` 規定閱讀、逐鍵位建議及證據條件；`presentation.py` 固定按實際案例／Subject／Judge 命名，依「覆蓋口徑、評分矩陣、分流與品質、Chatflow 定位、Capsule/Wiki 逐鍵位建議、案例與評委分歧、Subject 成本、驗證及證據索引」編排。每個 Subject 的危機硬分類 AUROC 從凍結路由矩陣計算，未知／缺失實際路由排除；成本只顯示 Subject 總計。逐鍵位表的四欄固定為 `capsule/wiki`、`鍵位`、`修改建議`、`證據`；沒有讀到具體配置和案例的項目不得編造鍵位修補。

共用 Agent 目前仍按預算分頁讀取優先案例，因此其閱讀覆蓋節明示已讀範圍，不能自稱逐句核讀所有回答。需要全案語意結論時，另外產出全量逐案底稿及審計，再由有覆蓋檢查的整合腳本合成一篇報告；只更新本模板不會自動補齊尚未閱讀的案例。模板版本寫入報告綁定，變更模板後需使用新的報告目錄，凍結評分及既有報告不覆寫。

## 全量研究工作流

`research.py` 是上述抽樣式報告之外的逐單位研究入口，不更改評分封套。它按凍結的 100 輪、8 Subject、4 Judge 抽取 3,200 個可追溯單位；每輪一次模型編碼、每個失敗模式一次欄位審核，兩層分別檢查點續接。`PARTIAL` assessment 的有效判語照樣讀取，不能把缺值當零分。評委低分只是一條線索，危機回覆中的法律／豐富性低分另列適用性覆核。

```bash
PYTHONPATH=.:evaluation python -m evaluation_report_agent.research \
  --results runs/example/results.json --frozen-input runs/example/frozen-input.json \
  --capsules tech_multimodels/chatflow/poc/capsules.json \
  --wiki-nodes content/knowledge/wiki/nodes --output runs/example/research

PYTHONPATH=.:evaluation python -m evaluation_report_agent.research \
  --results runs/example/results.json --frozen-input runs/example/frozen-input.json \
  --capsules tech_multimodels/chatflow/poc/capsules.json \
  --wiki-nodes content/knowledge/wiki/nodes \
  --scored-report runs/example/scored/report-full-33-cases.md \
  --output runs/example/research --execute --workers 4
```

第一條只抽取並驗證矩陣，沒有 API 呼叫。第二條重用成功的逐輪與逐模式檢查點；`--max-turns 1 --workers 1` 可先做一次收費試跑。報告需至少 90% 評委單位可分析，並逐一標記 32 格 Subject×Judge 覆蓋；未分析或不適用的理由不補零、不當作低分。所有輪次會先嘗試，才進入欄位審核；未過門檻或欄位審核未完成時 `validation.json` 為 `INCOMPLETE`，不交付完整報告。

`judge_observations.jsonl` 保存逐評委判語、trace 與原始封套 pointer；`turns/` 保存模型編碼，`coded_observations.jsonl` 保存全部 3,200 個單位的處理狀態。`patterns.json` 同時按評委單位、唯一回答和案例計數；`field_requests/`、`field_reviews/` 保存由跨案例理由到具體現行鍵位的審核。`field_decisions.json` 包含每個盤點鍵位，包括無修改證據者。最終 `report.md` 把同份凍結結果的評分矩陣、路由統計與研究發現依序整合，逐鍵位四欄表只展示有案例證據的候選。任何建議均待固定其他環節後單鍵位重播、核對來源與人工審核，不能把現行檔案當作歷史執行版本的證明。
