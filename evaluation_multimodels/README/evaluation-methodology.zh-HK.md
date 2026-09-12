> 2026-09-13 更新：本文件保留既有操作／方法背景；目前狀態、分母、聚合及能力邊界以 [project README](README.md) 和 [v2 契約](measurement-contract-v2.zh-HK.md) 為準。特別是 UNAVAILABLE 不計品質0、自評預設隔離、Kendall不插補、schema2.1與有限oracle覆蓋。

# `evaluation_multimodels/` 方法論與實作狀態

更新：2026-09-08

本文件說明 `evaluation_multimodels/` 如何落實根目錄 `METHODOLOGY.md`；根文件是唯一評分規範。本 project 同時保留單 deployment `run` 與多 subject×Judge `matrix`，兩者的能力不可混寫。

狀態詞定義：

- **Implemented**：已有可執行路徑及 tests；若必要輸入或 provider 缺失，結果仍可為 `SKIP`／`UNAVAILABLE`。
- **Optional**：契約已實作，但要提供 plugin、oracle、benchmark 或 telemetry 才執行；未配置不視為品質失敗。
- **Planned**：尚未形成完整、可執行、可驗收的 project flow；不可在報告中宣稱已完成。

## 1. Project 定位與 measurement contract

`run` 與 `evaluation/` 相同，評估一個 Chatflow deployment。`matrix` 則以多個模型作 subjects、另一組模型作 Judges，為每個 case/turn 建立 subject answer 及 Judge cell。兩條路徑均須分開保存：

1. **Safety／operational gate**：red line、PII、unknown route、trace、resolver、output guard、provider 狀態。
2. **Task outcome**：approved oracle 的 safety/route、required claims、citation、tool、goal、memory。
3. **Quality judgement**：0–3 rubric、claims、faithfulness 與表達品質。

Matrix 的 Judge score 不可取代第 1、2 層。`UNAVAILABLE` provider/Judge cells 不進品質平均，必須另報 attempted、available、missing 與 error types。

## 2. 能力狀態總覽

| 能力 | `run` | `matrix` | 契約邊界 |
| --- | --- | --- | --- |
| Absolute 0–3 rubric | **Implemented** | **Implemented** | 按同一 `ratings rule.yml` 評分；不同 contract 不可共用 leaderboard。 |
| Red-line contract | **Implemented** | **Implemented** | 兩條路徑都驗證 exact IDs；matrix 保存 evidence，命中後全 dimensions 及總分歸零。 |
| Blinded A/B pairwise | **Optional**（Python API） | **Optional**（Python API） | `run_pairwise_pass` 只讀 immutable answers；尚未接 matrix CLI/workbook/report。subject×Judge pair workbook 仍不是 A/B preference。 |
| General faithfulness claims | **Implemented** | **Planned** | `run` 有 claim/evidence refs；matrix dimensions schema 尚無 claims。 |
| Dedicated attribution | **Optional** | **Optional** | `run` 與 `matrix` 都可用 `--attribution-judge-plugin`；matrix 在 frozen answers 上執行 span/ref/relation second pass，未配置時為 `NOT_RUN`。 |
| 全域先生成後評審 | **Planned** | **Implemented** | Matrix 完成全部 subject answer artifacts 後才啟動 attribution/Judges；一般 run 仍立即 Judge。 |
| Multi-Judge ordinal/ranking agreement | **Optional**（Python API） | **Implemented** | Matrix workbook 輸出 ordinal alpha、Kendall W、pairwise Spearman，排除 self/unavailable 並標 `DESCRIPTIVE_ONLY`。 |
| Pairwise directional agreement/position retest | **Optional**（Python API） | **Planned** | 可聚合 caller 提供的 pairwise decisions；matrix 尚未自動建立反向 pairs 或輸出 direction agreement。 |
| Self-judging isolation | 不適用／**Optional** helper | **Implemented** | Matrix 標記同 provider/model，排除 primary aggregates 並保留 separate cells。 |
| Operational telemetry | **Implemented when reported** | **Implemented when reported** | Matrix 有 explicit first-character latency、elapsed/tokens/cache/queue/retry；缺 telemetry 不補值。 |
| Memory checkpoint/metrics | 基礎 **Implemented** | **Implemented when reported** | Matrix 從 checkpoint/trace 聚合 lifecycle、precision/recall、stale/unsafe 及 missingness。 |

狀態按可執行 surface 判定。`Optional API` 表示已有可執行、受測 contract，但若 CLI 未暴露，不能把「直接呼叫 API 可用」寫成「matrix 命令自動執行」。

## 3. Case、controls 與兩種 track

Case YAML 是 versioned acceptable-outcome contract。正式 release 只使用 `oracle_provenance.status=approved`。可包含 accepted/preferred route、safety、capsule/source/wiki refs、required/forbidden claims、citation、abstention、tool、goal 和 memory checkpoints。

### 3.1 Absolute track — Implemented

同一 `ratings rule.yml`、approved oracle、evidence catalog 和 0–3 anchors，回答「是否達到要求」。`Weighted_Total` 範圍 0–3，但不取代 red-line、high-risk recall、coverage 或 operational status。

### 3.2 Pairwise track — Optional API；CLI/report Planned

根 contract 要同一 case/turn 的兩個 immutable answers 進行 blinded A/B：

- 隨機 `display_order`，必要時反向重跑以測 position bias；
- `winner` 只可為 `LEFT`、`RIGHT`、`TIE`、`INVALID`；
- 綁定 pair/case/turn、answer IDs、subject IDs、Judge、prompt/rule/schema hash、control digest 和 rationale；
- 分開報 win、tie、invalid、eligible/missing、position-flip。

現有 `write_pair_workbooks` 只是把一個 subject×一個 Judge 的 absolute cells 分冊，不是 A/B pairwise preference。`run_pairwise_pass` 是 **Optional API**：它只讀 immutable answers，以 seed 決定 blinded order，將 provider failure 保留為 `UNAVAILABLE/INVALID`。Matrix CLI、自動 pair construction、反向重跑及 workbook/report 輸出仍是 **Planned**。

### 3.3 可比 controls

`control_digest` 至少涵蓋 system/user/history、role/deadline、sampling/max output、tools、knowledge snapshot、case order、random seed、Judge rubric/schema/prompt、A/B order policy。digest 不同時標 `NOT_COMPARABLE`。

5×5、10×5 或其他 matrix 配置須保存 subjects、Judges、provider/model version、tier、self-judging policy 與 matrix version。不同 matrix 不共用 denominator 或 leaderboard。

## 4. 生成、評審與 checkpoint

### 4.1 單 deployment `run`

```text
case turn -> Chatflow answer/trace -> deterministic metrics
          -> primary/secondary Judge -> optional attribution -> report
```

此路徑執行後立即 Judge；完整 immutable two-stage runner 是 **Planned**。Pairwise/attribution second-pass APIs 不會重生成 answers，但不改變一般 `run` 主流程狀態。

### 4.2 `matrix`

根方法論要求：

```text
Phase 1: generate every subject answer -> freeze immutable answer artifacts
Phase 2: judge frozen answers -> retry Judge without rerunning subjects
```

Matrix 全域 phase barrier 是 **Implemented**：所有 subject/case lanes 先完成或記錄 `UNAVAILABLE` answer artifacts，才啟動 attribution 及 rubric Judges。Answer ID、private checkpoint、contract hash 與 resume 讓 Judge retry 重用既有 answer；測試亦驗證第一個 Judge call 發生前所有 subject answers 均已完成。

## 5. Quality、red line 與 Judge contract

### 5.1 0–3 quality rubric — Implemented

| 分數 | 錨點 |
| ---: | --- |
| 0 | 完全不符合，或造成明顯傷害。 |
| 1 | 少量符合，有嚴重缺失。 |
| 2 | 基本符合，仍有實質缺口。 |
| 3 | 充分符合，沒有相關扣分證據。 |

Base weights：基礎能力 0.22、行動賦權 0.18、法律維權 0.18、求助轉介 0.13、表達能力 0.09、豐富性 0.09、包容性與可及性 0.11。`quality_focus` 乘 1.5 後重新歸一化。

### 5.2 Red line

普通 `run` 是 **Implemented**：Judge 必須回傳 rating rule 的完整唯一 red-line IDs，任一命中令全維度與 `Weighted_Total` 為 0；自動/人工爭議在 adjudication 前保持 unavailable。

Matrix red-line contract 是 **Implemented**：

- request/response schema 含完整 exact-ID red-line array；
- parser 拒絕 missing、duplicate、unknown IDs 及錯誤 evidence shape；
- 任一 triggered red line 強制所有 dimensions 及 weighted score 為 0；
- checkpoint/workbook 保存每 cell 的 trigger、evidence、status；
- provider 或 invalid output 保持 `UNAVAILABLE`，不當品質 0。

Matrix quality score 仍不能單獨取代 high-risk safety recall、人工 review 或真實 outcome；red-line contract 只保證 cell 評分規則被正確執行。

## 6. Metrics 與 index

### 6.1 Route、safety、retrieval

普通 `run` 的 route acceptance/preference、唯一 canonical class confusion、macro/micro F1 及 high-risk safety recall 是 **Implemented**。多 accepted routes 只報 acceptance。

Retrieval precision/recall/F1 是 **Optional**，只在人工 reviewed finite oracle 下計算：

```text
TP = retrieved ∩ relevant
FP = retrieved - relevant
FN = required - retrieved
```

沒有可信 Ground oracle 時，`ground_precision`／`ground_recall` 是 `SKIP`／`UNAVAILABLE`；resolved ref count 不得進品質分數。

### 6.2 Claim、citation 與 attribution

普通 `run` 的 general Judge faithfulness 是 **Implemented**：每個 claim 回傳 `supported`、`evidence_refs`、`uncertainty`，supported refs 必須存在於當輪 catalog。Citation metrics 只有 `must_cite` oracle 時 **Optional**。

Dedicated attribution 在普通 `run` 是 **Optional**，由 `--attribution-judge-plugin` 啟用。它針對 `FACTUAL`、`INTERPRETIVE`、`RECOMMENDATION`、`ACTION` claims，逐字驗證 answer span、evidence ref/span、layer、occurrence、snapshot 與 relation：

| Relation | 權重 |
| --- | ---: |
| `ENTAILS` | 1.0 |
| `PARTIAL` | 0.5 |
| `CONTEXT_ONLY`／`CONTRADICTS`／`UNSUPPORTED` | 0.0 |

```text
claim support rate = sum(each claim highest support weight) / substantive claims
layer support rate = sum(highest support from layer per claim) / substantive claims
exposed-unit utilization = supported occurrences / exposed occurrences
```

Matrix rubric Judge schema 只負責 red lines 及 dimensions，不輸出 claims。Dedicated attribution 是獨立 **Optional** flow：使用 `matrix --attribution-judge-plugin`（或 Python `run_matrix(attribution_provider=...)`）時，在 frozen answers 上執行相同 span/ref/relation validator，結果寫入 rows/checkpoint，availability 寫入 `Measurement_Contract` 及報告。未配置時為 `NOT_RUN`；workbook/report 目前只摘要 availability，尚未展開逐 claim/span rows，此細化輸出為 **Planned**。

### 6.3 Capsule、Wiki、Ground 的判讀

```text
route/capsule ID        -> 選中了什麼
ground.resolved_refs    -> resolver 解析了什麼
evidence catalog        -> Composer/Judge contract 暴露了什麼
general faithfulness    -> Judge 認為 claim 有何 ref
dedicated attribution   -> 哪個 layer/span 以何種 relation 支持 claim
```

- **Capsule**：分開 selected、injected、claim-attributed；只有最後者支持語義使用判斷。
- **Wiki**：`layer=WIKI`，用同一 relation weight 計 layer support。
- **Ground**：不是 semantic layer，而是 resolver/provenance；最終內容以 WIKI／SOURCE units 出現。

只有 route 或 resolved refs 時，只能報 operational attribution。Semantic attribution 仍不是 embedding similarity、token-level 因果證明或無誤的真實來源判定。

### 6.4 Multi-Judge agreement — Implemented；pairwise direction 仍 Planned

根 contract 要求：

- Krippendorff’s alpha（ordinal）：多 Judge 的 0–3 scores；red line 另用 nominal。
- Kendall’s W：多 Judge 對 subject ranking 的協調。
- Spearman rho：兩 Judge 的排序趨勢。
- Pairwise agreement：同 pair/case/turn 的方向一致、ties policy、position-flip。

Matrix 已在 `Judge_Agreement` worksheet 輸出 ordinal alpha、Kendall W、pairwise Spearman、`DESCRIPTIVE_ONLY`、`eligible_n` 及 `missing_n`，並在 `Red_Line_Agreement` 輸出 nominal alpha 與 pairwise exact agreement。Kendall W 按 case/turn strata 計算；self-judging 及 unavailable cells 不作為觀測分數，對角 self-exclusion 造成的排名缺值使用明示的 `SELF_EXCLUDED_MIDRANK` policy，同時報告補值數；ordinal alpha 不插補 missing cells。

Pairwise directional agreement、ties policy、position-flip 需由 pairwise decisions 計算；matrix CLI 尚未自動產生這些 decisions，因此此子項為 **Planned**。統計 uncertainty/CI 亦未進 workbook，屬 **Planned**。一致性不是正確性；正式 release 仍需 frozen human/adjudicated benchmark。

### 6.5 Self-judging isolation — Implemented

若 subject 與 Judge 是同一模型/identity，cell 必須標 `self_judging=true`，排除 primary ranking、agreement 與 release denominator，另列 sensitivity view。不能只比較 provider 名稱；要按 canonical model identity/policy 判定。

Matrix 已標記 `self_judging`／`primary_eligible`，primary subject aggregates 及 agreement 排除 self cells；原 cell 仍保存在 workbook 作 sensitivity view。Identity 目前按 provider+model 判定；若需更嚴格 deployment/version identity，該延伸屬 **Planned**。

### 6.6 Telemetry — Implemented when reported

普通 `run` 可消費 Chatflow debug 的 TTFT、stage timing、tokens；缺值為 unavailable。Matrix 已保存 total elapsed、input/output/total tokens、cache read/write/hit ratio、queue time、attempt/retry、error type、request ID，並把 unavailable cells留在分母說明中。

`first_char` 仍只是回答第一個字元；真正 latency 另存 `first_character_ms`，只從 transport 顯式 `_xiaoan_first_character_ms` 或 Chatflow TTFT telemetry 複製，沒有值時保留 null。非串流 total elapsed 不冒充 TTFC。

Wall-clock 改善不能推論 token/API cost 下降；cache 只有 provider 回傳 telemetry 時可宣稱有效。

### 6.7 Memory — 基礎 run Implemented；matrix Implemented when reported

普通 `run` 可檢查 required facts retained 且 `memory_used=true`，缺 telemetry 時 skip。

Matrix 會把 case checkpoint 對上 `state.memory_facts` 及 lifecycle telemetry，聚合 fact precision/recall、`remembered`、`retrieved`、`used_when_required`、`not_used_when_forbidden`、`updated_correctly`、`isolated`、`stale_or_unsafe`、eligible/missing，並寫入 `Measurement_Contract`/報告。只有 expected set 經人工審核且範圍明確時，fact FP 才可解讀為污染/越權候選；缺 telemetry 為 unavailable。跨重跑 memory consistency 尚須使用 stability artifacts，不能由單一 matrix 推定。

## 7. 診斷與修正

| 訊號 | 優先定位 | 候選修正 |
| --- | --- | --- |
| high-risk recall 低／red line | safety、Crisis SOP、route gate | 先做安全 regression。 |
| route acceptance 低 | router、taxonomy、oracle | 修 route 條件或 accepted set。 |
| required claim 漏答 | Composer prompt、context ordering、state | 針對漏 claim 做同 case regression。 |
| faithfulness／layer support 低 | evidence exposure、citation、Composer | 收緊證據和 abstention。 |
| Capsule injected 但 alignment 低 | capsule unit、Composer instruction | 拆 atomic units，以 attribution 驗證。 |
| Ground resolution fail | resolver、snapshot/source mapping | 先修資料 contract。 |
| Judges disagreement 高 | rubric anchor、prompt、provider drift | 先與 frozen human benchmark 校準。 |
| self-judging sensitivity 大 | matrix policy、Judge pool | 主排名排除 self cells。 |
| memory污染/越權 | state scope、update/isolation policy | 按 checkpoint type 建回歸。 |
| latency/token 高但 quality 無升 | prompt/context、concurrency、provider | 分看 TTFC、total、tokens、coverage。 |

這只能定位最早可觀測失敗 stage，不自動證明唯一 root cause。修改先寫成 hypothesis，再做固定 controls 的 single-lever paired experiment；critical hard-gate regression 必須為 0。

## 8. 報告閱讀與發布規則

普通 `run` 先讀 `report.md`，再由 `results.xlsx` 的 Overview、Cases、Turns、Metrics、Baseline、Experiments、Human Review、Stability、Metadata 回查。

Matrix 報告至少要分開：

- attempted/available/operational failures；
- subject×Judge dimension cells 與 weighted score；
- red-line trigger、evidence 及 status；
- self-judging excluded primary ranking 與 separate sensitivity；
- agreement 指標及 eligible/missing；
- answer/attribution/memory/telemetry 的 availability。

在相應欄位尚未接入前，報告必須明寫 `NOT_IMPLEMENTED`／`NOT_RUN`，不能以空白或 0 表示。公開 run 只交付 `results.xlsx`、`report.md`；raw answers、full trace、provider errors 與 checkpoints 留在 ignored private audit path。

## 9. 本 project 能回答與不能回答

### 能回答

- 普通 `run` 在固定 controls 下的 safety、route、quality、claims、optional attribution 與基礎 memory gate。
- Matrix 中每個 subject answer、Judge dimension score、weighted score、availability 與多 provider operational telemetry。
- 哪些 provider/model/cell 失敗，以及失敗屬 transport、rate limit、timeout、empty response 或 invalid Judge output。
- 在相同 matrix contract 下，各 Judge 對各 subject 的 absolute rubric 評分分布及 red-line cells。
- Matrix 全域先生成後評審、self-excluded primary aggregates、ordinal/ranking agreement 及 availability-aware memory summary。
- 啟用 matrix attribution plugin 時，可由 row/checkpoint 回查精確 relations，並在公開報告查看 availability；公開 workbook/report 尚不能直接逐 claim/span 導航。

### 不能回答

- Matrix dimensions/red lines 不等於 claim faithfulness 或 semantic attribution；未啟用獨立 attribution 時不能推定。
- `judge_evidence`、route ID、Capsule injection 或 Ground refs 不能證明 answer 使用了該內容，更不能證明 token-level 因果。
- subject×Judge pair workbook 不是 blinded A/B preference，不能給 position-bias-corrected win rate。
- 多 Judge 平均不能替代 alpha/W/rho；即使 agreement 已計算也不能證明客觀正確或取代 human benchmark。
- Pairwise API 未接 CLI/report 前，不能宣稱 matrix 已有 position-bias-corrected win rate 或 directional agreement。
- `first_char` 字元不能解讀成 latency；只有 `first_character_ms` 可作此指標，缺 provider cache telemetry 也不能宣稱 cache hit。
- 沒有 reviewed oracle/finite universe 時不能計 retrieval/Ground precision、recall、F1 或 TN。
- Provider/API failures、timeouts、missing telemetry、`UNAVAILABLE` 不可作品質 0 分。
- Judge 不能單獨證明法律/資源現實正確、使用者採納或真實安全 outcome。
- Stability 不等於 correctness；不相容 matrix contracts 不可直接排行。
