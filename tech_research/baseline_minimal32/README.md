# 無 Chatflow 的 32 案基準測試

這是一個薄入口，直接重用 `../../evaluation_multimodels` 的最新 rating rule、模型 registry、案例解析、Judge、計分及 Excel 輸出，不另寫一套評分公式。需與該資料夾保持目前相對位置。

## 執行

需要 Python 3.11+。在本資料夾執行：

```bash
python3 -m pip install -r requirements.txt
python3 run.py                      # 僅預覽模型、案例、呼叫量；不呼叫 API
python3 run.py --run                # 正式評測，會呼叫及計費
python3 run.py --run --resume       # 中斷後續跑；重試失敗或未完成的對話
```

五家最高設定檔位的 **5×5，包含自評**：

```bash
python3 run.py --run --latest-only --include-self-judging --output runs/latest5-self
```

這個模式共 480 次回答、最多 2400 次 Judge 評分（重試另計）。自評保留標記並納入主要矩陣；Judge 一致性仍沿用原框架的 non-self 分析口徑。

查看執行進度（僅本機讀取，不顯示對話內容、不呼叫 API）：

```bash
python3 status.py runs/latest5-self
```

執行結束後，另匯出簡短矩陣摘要、每格有效案例数、逐條 semantic oracle 判定及用量 CSV：

```bash
python3 summarize.py runs/latest5-self
```

API key 和模型覆寫直接讀取 `../../evaluation_multimodels/.env`，不用複製。模型沿用該目錄實際設定，不自動猜測或更換模型 ID。預設 10 subjects × 5 Judges。32 案共 **96 輪**：最多 960 次回答、4800 次評分，重試另計。API 是否支援這些模型需實際驗證。

先做小測試：

```bash
python3 run.py --run --cases TC-01 --output runs/smoke
```

也可用 `--subjects subjects.json --judges judges.json` 縮小模型數；JSON 格式例如：

```json
[{"provider":"gpt","model":"gpt-5.6-sol","tier":"latest","reasoning_effort":"medium"}]
```

Judge 檔相同格式但 `tier` 必須為 `judge`。只選一個 Judge 時，建議與 subject 不同模型，否則自評隔離會使主要分數不可用。

## 測試邊界

- 「無 prompt」指**不加應用層 system/developer 提示**。受測模型仍收到測試問題和同案先前 user/assistant 訊息；不同案例互相隔離。無分流、Chatflow、知識注入、工具或答案提示。
- 最新規則、quality focus 和預期答案只提供給 Judge。原生多輪 messages 由本腳本補上；原 evaluator 的 direct transport 本身僅傳當輪 user 訊息。
- 32 案取自 `../../docs/plans/evaluation-case-minimal-set.zh-CN.md` 的完整清單，保留全部輪次；沒有把 TC-01 至 TC-32 誤當最小集。
- 7 維度整數 0–3，focus 權重 ×1.5 後歸一化；沿用原 evaluator 的紅線優先、完整 case 平均及 case-macro 聚合。模型或 Judge 失敗保留 `UNAVAILABLE`，不當零分。預設同模型自評排除主要分母；使用 `--include-self-judging` 時納入。
- 先生成並凍結回答，再交不同 Judge。某輪回答失敗後不繼續污染該案對話；續跑會重建該失敗／部分完成的對話並重新評分。
- 無 Chatflow 的路由、檢索、grounding 遙測不適用。法律及資源真確性沒有另接 lawwiki 核驗；RL-02 是 Judge 判斷，需要人工複核，不能稱已核實的法律準確率。

未計算 Faithfulness 或 Answer Relevancy；semantic oracle 的要求滿足率是獨立指標。

## 輸出

預設在 `runs/baseline/`：

- `results.xlsx`：回答、Judge 評分、維度、Subject × Judge 矩陣。
- `report.md`：聚合結果及基準限制。
- `checkpoint.jsonl`：逐步保存回答與評分，供續跑。
- `manifest.json`、`inputs/`：本次模型、案例／規則快照及程式雜湊。來源或模型變更會拒絕混用 checkpoint；改用新 output。

不複製 `.env`。`runs/` 已忽略 Git。退出碼 1 表示有不可用觀察，仍會輸出可用結果。輸出目錄非空時需明確 `--resume` 或另選新目錄。續跑期間請保持 endpoint、輸出 token 預算等環境設定不變；manifest 不保存密鑰或完整環境。

## 離線驗證

```bash
python3 -m unittest -v test_run.py
```

測試使用假回應，檢查兩種 API 格式的多輪歷史、不注入提示、案例隔離、失敗停案，以及 32 案計分／Excel／checkpoint。離線通過不代表任何 live API 已可用。
