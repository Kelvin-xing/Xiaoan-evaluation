# XiaoAn Chatflow：法律問題重寫、要件抽取與 Wiki 檢索方案的文件研究

日期：2026-09-23  
範圍：只檢查專案內的設計文件、知識庫規則、GraphRAG 實作計畫與目前可見的 runtime contract；不把本研究視為已完成的 production 驗證。

## 結論

專案文件確實討論過「語義路由／向量召回／法律要件圖譜／結構化 query planner」等相鄰方案，但沒有找到一個已被採用的完整中間層：

```text
使用者口語
  -> 法律語言重寫 + 要件/事實抽取
  -> 以抽取結果做通用 Wiki 語義檢索
  -> 回到回答生成
```

目前採用的是較受限的分層設計：安全先行，先按使用者目的選 capsule；只有命中的 capsule 明確要求法律依據時，才由 `ground` 的條件分支選 node 和 source role，再由 resolver 展開來源。這是明確的 MVP design choice，不是因為團隊否定法律要件分析；相反，Wiki 方法論已採用「請求權基礎分析」來建模要件和證據，但把 Wiki 抽取與 runtime retrieval 分開。

文件給出的主要理由是：使用者按處境和目的提問，不按法律章節提問；MVP 需要低複雜度、可審計、可控制的證據邊界；在 capsule 數量很小時，把候選直接放進 prompt 比先建向量庫更簡單。未來方向則是 hybrid routing、bounded planner、element-aware graph traversal 和在 locator evidence 不足時有限度使用 embedding，而不是無限制地讓模型自由檢索。

## 1. 文件明確採用的現行方案

### 1.1 Capsule 是按使用者目的，不按法律章節

`tech/chatflow/design-doc.md` 明確寫道，N5p 是「使用者想申請保護令／建立安全邊界」，不是《反家暴法》第 23–34 條；理由是使用者按處境和目的提問，法律章節屬於 Ground 而不是路由主軸。[`design-doc.md:390-394`](../../tech/chatflow/design-doc.md#L390-L394)

因此，現行 runtime 的主要語義變換不是「法律語言重寫」，而是把自然語言輸入與 capsule card（`triggers`、`use_when`、`do_not_use_when`）交給 router；MVP 每輪把全部 capsule cards 和 baseline 放入同一次路由 prompt，輸出 capsule、信心、理由和 active-capsule 延續決定。[`design-doc.md:291-317`](../../tech/chatflow/design-doc.md#L291-L317)

### 1.2 Ground 是條件式、capsule 內的證據入口

MVP 的 Ground contract 是嚴格的 `if + node + source_roles`。統一 Ground intent 命中後，編排層根據當前訊息和既有使用者上下文選最多三個直接相關分支；resolver 再讀取命中 node 及其指定 source roles 的 refs。[`design-doc.md:396-411`](../../tech/chatflow/design-doc.md#L396-L411)

模型只看到 resolver 提供的 Ground，不在回答階段自由「想起」法條；理由是法律回答要可審計，避免看似權威但不可追溯的引用。[`design-doc.md:557-561`](../../tech/chatflow/design-doc.md#L557-L561)

這解釋了為什麼目前 Wiki 有 element node，不代表每次輸入都會自動搜尋所有 element：runtime 的召回入口仍是 capsule locator／Ground branch，而不是通用法律要件檢索器。

## 2. 文件曾討論的相鄰方案，以及採用狀態

### 2.1 向量相似度做意圖到 SOP 映射：明確不作核心方案

`content/knowledge/knowledge_strategy.md` 的方案 A 提出把高頻問題向量化，命中後直接取預設 SOP，模型只做語氣潤色；文件記錄的棄用原因是交互會變成機械觸發式，缺乏上下文共情和多輪推演。結論是只可作系統崩潰兜底或極高危攔截網，不能作核心體驗。[`knowledge_strategy.md:23-31`](../../content/knowledge/knowledge_strategy.md#L23-L31)

這不是「所有 embedding 都不用」的決定，而是拒絕把單純向量命中 + 固定 SOP 作為完整產品架構。

### 2.2 暴力循環時間軸／狀態機：降級為狀態標籤

方案 B 曾考慮按潛伏、爆發、取證、訴訟、恢復等生命週期隔離知識；棄用原因是使用者狀態非線性，頻繁跳轉和回溯會增加中間件維護成本。文件結論是更適合作為狀態標籤。[`knowledge_strategy.md:33-39`](../../content/knowledge/knowledge_strategy.md#L33-L39)

### 2.3 R-A-G Scenario Capsule：明確採用

方案 C 把具體痛點作為知識單元，拆成 Recognize、Act、Ground；命中後按狀態和追問意圖選擇性展開。文件把它列為同時保留共情與行動、多輪能力及法律／實務轉譯的核心方案；代價是人工整理、專家審核，以及未命中時要有 fallback。[`knowledge_strategy.md:41-64`](../../content/knowledge/knowledge_strategy.md#L41-L64)

這也是「為什麼沒有先做通用法律重寫層」的最直接產品背景：團隊先把高價值使用者痛點整理成可審核的回答資產，而不是把所有抽象法律推理責任交給 runtime 模型。

### 2.4 MVP 不上向量庫：明確延後而非永久否定

Chatflow design doc 的明確選擇是 12 個 capsule 時直接把 candidates 放進 prompt；理由是簡單、可解釋、零基礎設施，能更快暴露 schema 和邊界問題。只有在 capsule 超過約 50–100 個、路由成本升高或混淆矩陣顯示召回不足時，才引入 embedding recall。[`design-doc.md:343-347`](../../tech/chatflow/design-doc.md#L343-L347)

同一文件已把 production 方向寫成 hybrid：規則處理 red flag／強意圖、embedding 取 top-K、LLM rerank，並用混淆矩陣驗證低信心行為。[`design-doc.md:319-327`](../../tech/chatflow/design-doc.md#L319-L327)

因此，文件支持「未來增加語義召回」；但沒有證據顯示「法律語言重寫 + 要件抽取」曾被定義為該召回的必要前置層。

### 2.5 `triggers` 與 `use_when` 分離：以自然語言樣例承擔召回，以條件承擔精度

文件保留兩種欄位：`triggers` 描述使用者怎麼說，`use_when` 描述何時適用；理由是前者是 recall anchor，後者是 semantic precision filter，合併會讓作者無法區分口語樣例和適用條件。文件也指出未來 embedding 可吃 `triggers`，LLM reranker 可吃 `use_when`／`do_not_use_when`。[`design-doc.md:349-353`](../../tech/chatflow/design-doc.md#L349-L353)

這是目前最接近「輸入重寫」的設計替代物，但它不是每輪產生一份法律語言或要件 JSON，而是由作者預先把口語召回錨點和適用條件寫入 capsule。

## 3. Wiki 是否採用了法律要件分析？是，但 ownership 與 runtime 入口被刻意分開

### 3.1 Wiki 方法論明確要求要件、抗辯和證據

`content/knowledge/WIKI_MAINTENANCE.md` 要求從來源識別權利／救濟或法律後果、適用條件與構成要件、例外／抗辯，以及支持每個要件的證據；並給出「record-producing actor/procedure -> evidence -> element -> right/remedy」鏈條。[`WIKI_MAINTENANCE.md:134-153`](../../content/knowledge/WIKI_MAINTENANCE.md#L134-L153)

重建流程也要求抽取 candidate claims、legal elements 和 case-identity signals，再跨來源比較、合併。[`WIKI_MAINTENANCE.md:360-366`](../../content/knowledge/WIKI_MAINTENANCE.md#L360-L366)

`content/knowledge/log.md` 更記錄了 schema v0.3 的實際採用：新增 `element` node kind、`is_element_of` 和 `proves`，建立 protection-order 的 danger element，並把 evidence 改接到 element 再接到 remedy。[`log.md:62-69`](../../content/knowledge/log.md#L62-L69)

所以「最新版 Wiki 缺乏要件」不準確；要件在 authoring／graph layer 已被明確建模。

### 3.2 為什麼這些要件沒有自動變成 runtime 的通用檢索輸入？

Wiki maintenance 明確規定 Wiki extraction independent of downstream consumers；不要為了 capsules、prompts 或 runtime routing 改變 graph shape，downstream adaptation 是獨立任務。[`WIKI_MAINTENANCE.md:21-26`](../../content/knowledge/WIKI_MAINTENANCE.md#L21-L26)

同一文件把 source retention、Wiki incorporation、runtime retrieval 分成三個獨立決定，並要求 runtime 只取當前問題所需的最小精確段落，而不是因為來源或節點存在就使整份文件 runtime-eligible。[`WIKI_MAINTENANCE.md:103-123`](../../content/knowledge/WIKI_MAINTENANCE.md#L103-L123)

這提供了「為什麼沒有直接採用通用要件檢索」的架構理由：要件圖譜的正確性和來源治理先獨立成立；怎樣把一輪使用者輸入映射到圖譜，另需 runtime retrieval 設計與驗證，不能由 Wiki rebuild 自動推導。

## 4. 後續文件提出了更接近該方案的設計，但仍屬計畫／bounded 版本

### 4.1 AWS GraphRAG 計畫：element-aware retrieval

GraphRAG implementation plan 要求 Local retrieval 從 capsule locator 開始，沿 `proves`、`is_element_of`、`enables`、`provides_evidence_for` 等關係最多一跳展開，套用 authority／review／jurisdiction 過濾，再返回 typed EvidenceBundle。[`2026-07-18-aws-graphrag-chatflow.md:564-590`](../../docs/superpowers/plans/2026-07-18-aws-graphrag-chatflow.md#L564-L590)

當 locator-seeded evidence 不足時，計畫只允許注入的 EmbeddingClient 對 reviewed node embeddings 做一次排序，合併超過已測 relevance threshold 的候選並重新做 source validation；空成功 bundle 不被接受。[同上](../../docs/superpowers/plans/2026-07-18-aws-graphrag-chatflow.md#L588-L590)

這是「Wiki 語義檢索」的明確後續方向，但它以 capsule locator 和審核後 sidecar 為錨點，不是對原始訊息先做法律語言重寫再任意搜尋全圖。

### 4.2 Bounded intent/query planner：有結構化規劃，但不是法律要件抽取器

同一計畫提出 `PlannerClient.plan`，輸入是 redacted message、compact redacted history、capsule cards 和 active state，輸出 `PlannerDecision`；它涵蓋 baseline、single Local、compound Multi-local、Global、延續、換題和低信心。[`2026-07-18-aws-graphrag-chatflow.md:604-626`](../../docs/superpowers/plans/2026-07-18-aws-graphrag-chatflow.md#L604-L626)

這代表未來會有「結構化意圖／查詢規劃」層，但文件沒有把輸出定義成法律元素、已知／未知事實、證據候選或法律語言改寫；因此不能把它等同於本次問題所說的 legal-frame rewrite。

### 4.3 Compound intent 曾被納入評估，而不是直接改成無界多路由

評估平台計畫要求用至少 30 個專家審核的 compound-intent cases，比較 bounded Multi-local 與 single capsule + signpost，並在相同模型、prompt、index、capsule version 和 budget 下做 A/B。[`2026-07-18-evaluation-platform-deployment.md:604-622`](../../docs/superpowers/plans/2026-07-18-evaluation-platform-deployment.md#L604-L622)

這說明混合需求被視為需要測量的風險，但文件選擇先以有界的兩種架構比較，而不是直接引入任意數量的法律子問題拆解。

## 5. 「為什麼沒有最終採用」的證據分級

### Explicit decision

- 核心產品採用 R-A-G scenario capsules；向量命中固定 SOP 不作核心體驗。[`knowledge_strategy.md:23-64`](../../content/knowledge/knowledge_strategy.md#L23-L64)
- MVP 以 capsule purpose routing 為主；法律章節／法律依據放在 Ground。[`design-doc.md:390-394`](../../tech/chatflow/design-doc.md#L390-L394)
- 12 個 capsule 時不上向量庫；embedding recall 是規模、成本或召回不足時的 production extension。[`design-doc.md:343-347`](../../tech/chatflow/design-doc.md#L343-L347)
- Ground 由 resolver 提供可追溯證據，模型不得自行自由檢索法條。[`design-doc.md:396-419`](../../tech/chatflow/design-doc.md#L396-L419)
- Wiki extraction 不為下游 routing 服務；downstream adaptation 另行處理。[`WIKI_MAINTENANCE.md:21-26`](../../content/knowledge/WIKI_MAINTENANCE.md#L21-L26)

### Proposal / deferred direction

- Production hybrid routing：rules + embedding recall + LLM rerank。[`design-doc.md:319-327`](../../tech/chatflow/design-doc.md#L319-L327)
- GraphRAG 的 locator-seeded element-aware traversal，必要時一次 embedding fallback。[`aws-graphrag-chatflow.md:564-590`](../../docs/superpowers/plans/2026-07-18-aws-graphrag-chatflow.md#L564-L590)
- Bounded structured planner 和 compound-intent Multi-local。[`aws-graphrag-chatflow.md:604-630`](../../docs/superpowers/plans/2026-07-18-aws-graphrag-chatflow.md#L604-L630)
- Compound-intent 的 A/B 評估先於架構採用。[`evaluation-platform-deployment.md:604-622`](../../docs/superpowers/plans/2026-07-18-evaluation-platform-deployment.md#L604-L622)

### Inference

- 沒有採用完整 legal-frame rewrite，最合理的解釋是架構把高風險的法律證據選擇放到受控 capsule／Ground contract，把共情與行動資產先人工整理，避免 runtime 直接把含混口語轉成未經確認的法律事實。
- Wiki 的要件缺口若存在，屬於「runtime locator／query mapping 未充分接通」的問題，而不是「Wiki 沒有要件模型」本身。此推論由 Wiki 的 element chain 與 runtime 的 capsule-seeded resolver 共同支持，但文件沒有一段明文說「因此拒絕 legal rewrite」。

### Unknown

- 文件沒有找到 legal-frame rewrite 的正式 schema、欄位（例如 known/unknown/inferred）、prompt version、離線評測結果或正式拒絕 ADR。
- 文件沒有提供「加入要件抽取後召回率下降／上升」的實測比較，也沒有證明現行 capsule Ground 對混合型法律提問的 element recall 已足夠。
- GraphRAG plan 標為 implementation plan；本研究沒有把計畫中的未勾選任務當成已在目前 POC runtime 上線。

## 對當前疑慮的回答

你的擔心有一半已被文件處理：Wiki 端已保存 legal elements、evidence-to-element 和 element-to-remedy 關係；但另一半仍是實際工程缺口：目前主路由和 Ground 召回是 capsule-seeded，而不是從每輪混合口語中產生可審計的 legal frame 再做 element-aware retrieval。

因此，文件支持的下一個低風險研究步驟不是立刻把重寫結果當作法律事實，而是做一個可回放的比較實驗：在固定 capsule、Wiki snapshot、model 和 budget 下，對比現行 Ground selector 與「只作檢索輔助、保留 known/unknown/inferred、不可覆蓋原文」的 legal-frame candidate，分開量 route recall、element recall、source adequacy、clarification quality、safety 和 latency/cost。現有計畫已要求 route／retrieval／legal grounding 指標，但沒有看到這個 exact A/B 已完成。
