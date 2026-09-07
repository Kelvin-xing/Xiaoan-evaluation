# 多模型交叉評審方法論：既有對話與 XiaoAn 實作對照

日期：2026-09-07
範圍：Claude、Gemini、GPT、DeepSeek、Qwen 的 subject × judge 評估；不使用 DeepEval API。

## 來源與判讀

本筆記把引用對話（task `01a05eba-7df8-7741-8777-f1294b1b603e`）的技術建議，對照目前
`evaluation_multimodels` 的 runner、workbook、calibration 與 stability 實作。對話中最可借鑑的
原則是：固定案例與控制條件、先完成 subject 回答再評審、盲化回答、絕對評分與成對比較並行、
自評獨立報告、故障狀態不轉成品質零分，以及用不同一致性統計回答不同問題。

## 已經具備、應保留

- `multimodel.py` 將 subject answer 與 judge 結果以 `answer_id` 關聯，答案只保存一次；
  `UNAVAILABLE` 不進品質分母，且保留 latency、token、retry、cache telemetry（見
  [multimodel.py](/Users/mingjiexing/xiaoan/evaluation_multimodels/xiaoan_eval/multimodel.py:1)）。
- matrix prompt、judge evidence、model/rule 設定與 checkpoint 有版本／digest 綁定；這支持
  對話要求的固定 prompt、schema、模型版本與可重跑性。
- `build_blinded_review_packet()` 已移除 judge、experiment arm、candidate identity，符合盲評
  邊界（見 [calibration.py](/Users/mingjiexing/xiaoan/evaluation_multimodels/xiaoan_eval/calibration.py:177)）。
- stability 已明確標記為 repeatability、不是 correctness；這個語義必須延伸到多 judge
  一致性報告，避免「一致」被誤寫成「正確」（見
  [stability.py](/Users/mingjiexing/xiaoan/evaluation_multimodels/xiaoan_eval/stability.py:1)）。

## 需要修正或補強

### 1. 先釐清矩陣定義

目前預設是 10×5：五家 provider 各兩個 subject tier，加五個 judge；`PROVIDERS` 目前還包含
`kimi`。若本項目正式問題是五個模型的 5×5，應在 manifest 明確保存：

```json
{
  "matrix_version": "5x5/v1",
  "subjects": [{"subject_id": "claude", "provider": "claude", "model": "..."}],
  "judges": [{"judge_id": "gpt", "provider": "gpt", "model": "..."}],
  "self_judging_policy": "report_separately",
  "case_manifest_digest": "...",
  "control_digest": "..."
}
```

10×5 可作模型 tier 實驗，但不能與 5×5 的結果共用排名或 denominator。每一 row 還要保存
`subject_provider`、`subject_model_version`、`judge_provider`、`judge_model_version`，不要只依賴
可變的環境變數名稱。

### 2. 絕對分數與成對比較分開建模

現有 `All_Judgements` 主要是 dimension score／weighted score。建議新增獨立的
`Pairwise_Judgements`（或等價 JSONL），每筆固定：

```text
case_id, turn, pair_id, left_answer_id, right_answer_id,
display_order, winner in {LEFT, RIGHT, TIE, INVALID},
judge_id, rubric_version, prompt_hash, status, rationale
```

同一 pair 要以相反 display order 重跑，檢查 position bias；`TIE` 不可默默轉成半分，必須在
協議中固定。輸出 absolute score、pairwise win/tie rate、以及兩者不一致的案例清單；不能把
pairwise 勝率直接當成絕對分數的校正值。

### 3. 五種一致性統計要各自命名分母

對每個 dimension、case strata 和 overall（只用 `status=PASS` 且有完整 judge labels）報告：

- **Krippendorff alpha（ordinal）**：多 judge 對 0–3/1–5 ordinal label 的一致性；缺失值排除並
  另報 `unavailable_count`。安全 red-line 的 TRUE/FALSE 另用 nominal alpha。
- **Kendall W**：五個 judge 對 subject ranking 的協調程度；明確記錄 ties 修正與 ranking
  population（case-level、dimension-level 或 run-level）。
- **Spearman rho**：只作 judge pair 的排序趨勢；附 `n_pairs`，不宣稱絕對尺度一致。
- **Pairwise agreement**：同一 `pair_id`、同一 case/turn 的方向一致率；另報 tie-aware policy、
  position-flip rate，並以 Cohen/Fleiss 或 Krippendorff nominal 指標作機率一致校正。
- **Human calibration**：沿用目前 `build_agreement_report()` 的 human-vs-judge；不能用 judge-vs-judge
  高一致取代人工 correctness。校準結果保留 raw labels、adjudicated labels 與 disagreement queue。

每個統計都要輸出 `eligible_n`、`missing_n`、`stratum`、bootstrap CI（以 case 為重抽樣單位），
避免同一回答的多個 dimension 造成虛假的獨立樣本量。

### 4. 由「平均分」改成受約束的排名報告

建議報告順序：

1. hard gate／執行成功率／高風險錯誤率（不可被平均分抵銷）；
2. 非自評 absolute score（平均、中位數、judge spread）；
3. pairwise 勝率與 tie rate；
4. case-strata 分數與 bootstrap CI；
5. human-adjudicated calibration 與 judge agreement。

自評 cell 只作 bias diagnostics。若需要比較 judge 尺度，保留原始分數後另產 judge-within
centered 或 ordinal model；不要只發布 z-score，也不要把 judge standardization 當成客觀校正。

### 5. 把固定控制條件變成可驗證 contract

`control_digest` 應涵蓋 system/user/history、角色與截止日期、temperature/top_p/max tokens、
工具與 knowledge snapshot、case order、random seed、judge prompt/rubric/schema、display order
randomization policy。任何 digest 不同，baseline comparison 應為 `NOT_COMPARABLE`，而不是重新平均。

對話所說的「先生成、後評審」應在 runner 層落實：先完成所有 subject artifacts，再讀取 immutable
answer artifacts 給 judges；judge 失敗可重試而不重跑 subject。這也使 provider outage 不會改變
被評回答。

## 建議的最小落地順序

1. 增加 5×5 manifest 與 `matrix_version`，把 10×5、provider tier、Kimi 等配置隔離。
2. 加入 pairwise artifact/schema、反向 display order 與 position-flip 指標。
3. 新增多 judge agreement report（ordinal/nominal alpha、Kendall W、pairwise Spearman、
   pairwise agreement），所有結果以 `DESCRIPTIVE_ONLY` 起步。
4. 對 10–20% 分層案例建立 frozen human benchmark；judge/rubric/prompt 改動先跑 calibration，
   高風險 disagreement 進人工 adjudication。
5. release gate 只接受：控制 digest 相同、hard gate 無回歸、provider/Judge unavailable 與
   quality denominator 分開、CI／strata 覆蓋足夠，並且未把一致性誤述為 correctness。

## 不應直接借鑑的做法

- 不把單一 composite score 當唯一排行榜；安全、拒答、關鍵錯誤與操作失敗必須分列。
- 不把 `401/429/5xx/timeout/空回應/解析失敗` 記成 0 分。
- 不讓模型 judge 自己產生或修改 oracle；oracle 必須由人工審核並有 provenance。
- 不把 DeepEval SDK/API 引入 runtime；本筆記只採納可由現有 XiaoAn artifacts、schemas 與本地統計
  實作的測量原則。
