# RAG 與 Agent 評估：八個指定來源核對、方法定義與使用限制

核對日期：2026-09-13。本文是來源研究，並非 repository 執行結果。未呼叫付費模型 API、未讀取 `.env` 或私人 runs。公式與案例中的建議是研究者整理；不表示原文章逐項提出。為避免把二手文章錯誤帶進 evaluator，方法定義優先採官方文件與原論文。

## 1. 指定來源的實際可讀範圍

| ID | 指定來源 | 本次狀態 | 可使用的內容／缺口 |
|---|---|---|---|
| S1 | [Fordige：RAG 系統知識庫效能評估完整指南](https://fordige.com/blog/rag-system-evaluation-methods-complete-guide) | 正文可讀 | 2026-06-08；框架、四個主要指標、golden set、回歸建議；部分技術敘述需勘誤 |
| S2 | [AWS：使用指標來了解 RAG 系統效能](https://docs.aws.amazon.com/zh_tw/bedrock/latest/userguide/knowledge-base-evaluation-metrics.html) | 正文可讀 | 兩種 job、12 個 builtin metrics；原頁只列概念，具體尺度另查官方 evaluator prompts |
| S3 | [IBM：結果評估](https://www.ibm.com/cn-zh/think/architectures/rag-cookbook/result-evaluation) | 正文可讀 | 2024-11-15；檢索、生成、成本、診斷；圖表圖片未逐格轉錄 |
| S4 | [Tencent 文章 2658116](https://cloud.tencent.com/developer/article/2658116) | 未取得正文 | web open 回傳 Internal Error；文章 ID 與完整 URL 定向搜尋未找到可核對正文 |
| S5 | [HackMD：RAG Triad of metrics](https://hackmd.io/@YungHuiHsu/H16Y5cdi6) | 文字與程式碼可讀 | 課程筆記；圖片未逐一視覺解讀；TruLens 舊版 API 不代表目前接口 |
| S6 | [知乎文章 717985736](https://zhuanlan.zhihu.com/p/717985736) | 未取得正文 | web open 回傳 Internal Error；精確搜尋未找到可核對文章；不能以其他知乎文替代 |
| S7 | [DataAgent：RAGAS 八大指標](https://www.idataagent.com/2024/05/27/mastering-rag-assessment-skills-from-beginner-to-expert/) | 正文可讀 | 2024-05-27；正文重點為四項指標，八項名稱亦見 tags；不能假稱正文提供八項完整公式 |
| S8 | [ClorisSignal X 貼文](https://x.com/ClorisSignal/status/2098241919843484128) | 未取得正文 | web open 回傳 Internal Error，精確 status ID/URL 搜尋無可核對正文 |

另嘗試使用本機 urllib 直接讀取 S3/S4/S6/S7/S8，本機網路 DNS 失敗；主代理另以瀏覽器入口嘗試 S4，工具初始化逾時，未取得額外正文。沒有使用登入繞過、付費鏡像或不明轉載。上述三項缺口表示「本次取不到」，不證明文章已刪除或不存在。因此不能宣稱已完整總結八篇。可讀五篇的主要方法及必要補充列於下文。

## 2. 逐篇摘要與主張核對

### S1 Fordige

作者以檢索、生成、任務匹配三層組織評估，介紹 Ragas、TruLens、ARES，主張建立含單文件、多文件、邊界問題的測試集，再做版本回歸與人工抽查。Faithfulness 以主張支持比例計算；context recall 應看 reference facts。文中的 20／30–50 題、0.8 分與 10% 退化門檻是實務建議，並無本領域驗證，不能直接作 XiaoAn 上線標準。[原文](https://fordige.com/blog/rag-system-evaluation-methods-complete-guide)

我們的核對：Answer Relevancy 段落把 reverse-question generation 稱為「追問」，容易理解錯誤；真正做法是從回答反推它回答了甚麼問題，再與原 query 比較，並非提出後續問題。ARES 被歸為 Google Research 亦與原論文署名不合：作者隸屬 Stanford、Databricks、UC Berkeley。原法先生成合成資料、微調三個裁判，再以人工標註做 PPI 校正與信賴區間，並非無人工的簡單三步分類。[Ragas 定義](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)、[ARES 原論文](https://arxiv.org/html/2311.09476v2)

### S2 AWS

原頁將 retrieval-only 的 context relevance／coverage 與 retrieve-and-generate 的十個回答／安全指標分開。coverage 明確需要 ground truth；faithfulness、correctness、completeness、citation precision／coverage 各自回答不同問題。可用自訂指標，不能只把 AWS 名稱套在本地 heuristic 上便宣稱同一量測。[官方總表](https://docs.aws.amazon.com/zh_tw/bedrock/latest/userguide/knowledge-base-evaluation-metrics.html)

### S3 IBM

IBM 強調可重現實驗、黃金答案與 contexts IDs，涵蓋 MRR、NDCG、MAP、faithfulness、輸入擾動、BLEU／ROUGE，以及計算、API、基建與營運成本。低檢索分可檢查資料、chunk、metadata、reranker、query rewrite；低生成分可檢查 prompt、生成設定及模型。這些是調查方向，不能從兩個分數直接推出因果。[原文](https://www.ibm.com/cn-zh/think/architectures/rag-cookbook/result-evaluation)

我們的原文內部檢查：在「用 AI 評估 AI」的 NER few-shot 範例，正確出現的 IBM 被標 0，而不吻合原文的電話被標 1；與上方「1 為最高」的 rubric 不一致。定位方式是搜尋該頁 `1-800-555-1234`、`+1 888 426 4409`、`分数：0`。這表示範例不宜直接複製，並非證明 IBM 評估產品執行有錯。CPU/GPU 分工亦是示意；dense retrieval／reranking 可以使用 GPU，不能把成本帳硬分成 CPU=檢索、GPU=生成。

### S5 HackMD

筆記以 query、retrieved context、answer 三角關係介紹 context relevance、groundedness、answer relevance，並比較專家、人類回饋、傳統 NLP、小型分類模型及 LLM judges 的成本與可擴展性，延伸至 helpful／honest／harmless；實作以 feedback functions 接到應用 trace。[原筆記](https://hackmd.io/@YungHuiHsu/H16Y5cdi6)、[TruLens 原始定義](https://www.trulens.org/getting_started/core_concepts/rag_triad/)

我們的解讀限制：groundedness 譯作「真實性」容易混同外部事實正確；三角高分不能保證零幻覺。筆記後半把 context relevance 說成對話理解，與前半 query–retrieved-context 定義不同，應在 schema 分開。約 80–85% 人機一致只適用其研究基準，不能移植為中文家暴支援的校準證據。[Judge 原研究](https://arxiv.org/abs/2306.05685)

### S7 DataAgent

正文介紹 claim support、逆向問題、檢索覆蓋與排序，另談資料清洗、後處理、檢索範圍和動態資料。關鍵勘誤：在「上下文召回率與精度的計算方法」及表格，使用的是「生成答案」作 recall 的分母對象；對 Ragas Context Recall 應是 reference answer 的主張。按文章寫法會把 recall 變成近似 faithfulness，無法發現答案和檢索同時漏掉的事實。[原文定位](https://www.idataagent.com/2024/05/27/mastering-rag-assessment-skills-from-beginner-to-expert/)、[Ragas Context Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)

### 不可讀三篇

S4、S6、S8 沒有可驗證正文，不列作者觀點、不猜測標題或推薦方法。以下 Agent 部分是額外的一手資料與本次工程推導，不歸因於這三篇。

## 3. 最先分清：量測對象、輸入與缺失狀態

採用以下符號：`q` 為當前問題；`h` 為對話歷史；`a` 為實際回答；`C=[c1,...,cK]` 為實際傳入生成器的有序 context；`g` 為人工審定 reference answer；`G` 為完整 relevant context IDs；`T` 為工具與狀態事件軌跡。

| 要回答的問題 | 必需證據 | 適合指標 | 不能推論 |
|---|---|---|---|
| 是否找齊必要資料 | q、C、g 或 G | Recall、coverage | 生成器有用到它 |
| 找到的資料是否相關且排前 | q、ordered C、relevance labels | Precision、AP、NDCG、context relevance | 答案正確 |
| 回答能否由資料支持 | a、實際 C | Faithfulness／groundedness | 資料本身真實或最新 |
| 回答事實對不對 | a、g、有效性／時間／地區標註 | Correctness | 有引用或有用過檢索 |
| 回答是否解決所有要求 | q、h、a、requirements | Completeness、goal success | 已在真實環境完成操作 |
| 引文是否支持其聲稱 | a 的 claim–citation links、引用全文 | Citation precision／coverage | 有 URL 就有語義支持 |
| 工具選擇、參數、狀態正確否 | T、tool results、expected state | Tool metrics、state assertions | 最終文字自稱成功就成功 |

本次建議把每個值連同 `metric_id/version`、`status`、`evidence_ids`、`denominator`、`reason` 儲存。至少區分 `SCORED`、`NOT_APPLICABLE`、`MISSING_EVIDENCE`、`UNAVAILABLE`、`INVALID_OUTPUT`。無 reference 無法算有 reference recall；provider error 不是零分；空答案的 faithfulness 不自動作滿分；不需要檢索的同理回應可為 N/A。這是工程設計建議，並非某一框架共同的預設實作。

## 4. 檢索指標：公式和每個分母的含義

### 4.1 以 context ID 作基準

令 `v_i=1` 表示第 i 個 chunk 在 gold relevant set 內，否則 0；先將重複 chunk／同源重複片段按事先定義去重。

| 指標 | 定義 | 捕捉／盲點 |
|---|---|---|
| Hit@K | `1[Σ(i≤K)v_i > 0]`；dataset hit rate 為 query 平均 | 只需一個命中；多跳缺另一來源仍可得 1 |
| Precision@K | `Σ(i≤K)v_i / K` | 檢索噪聲；不足 K 的分母需固定契約 |
| Recall@K | `|retrieved_topK ∩ G| / |G|` | gold 內漏檢；gold 不完整時不是整個語料真實 recall |
| RR@K、MRR@K | 首個 relevant rank 為 r 則 `1/r`；未命中 0；MRR 為 query 平均 | 不檢查第二個以後必要證據 |
| AP@K、MAP@K | 此處採 `AP@K=Σ P@i·v_i / |G|`；MAP 為 query 平均 | 兼顧排序與未找回 gold；須聲明另一常見截斷分母 `min(|G|,K)` 是否採用 |
| NDCG@K | `DCG=Σ (2^rel_i−1)/log2(i+1)`；`NDCG=DCG/IDCG` | 支援 graded relevance；必須固定 gain、discount、gold pool；IDCG=0 需明示處理 |

基礎排名定義依 [Stanford IR 教科書](https://nlp.stanford.edu/IR-book/html/htmledition/evaluation-of-ranked-retrieval-results-1.html) 整理；截斷、去重、空 gold 是本次明列的實作決策。跨 chunk 策略比較必須重建 ID 對映，或改用穩定 source span／fact IDs；否則只是切塊 ID 改名就會造成假的退化。

### 4.2 Ragas Context Precision 的變體不能混為一談

Ragas 排序型公式：`Σ(i=1..K) P@i·v_i / Σv_i`，分母是**本次 top-K 裏被判 relevant 的項目數**，不是 gold 所有必要項目；因此可能 precision=1 但 recall 很低。定義、變體及輸入見 [官方 Context Precision](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_precision/)。

| 變體 | v_i 的判定依據 | 需要輸入 | 解讀限制 |
|---|---|---|---|
| LLM with reference／ContextPrecision | context 對 reference 的支援／用途 | q、C、g | 受 reference 完整性及 Judge 影響 |
| LLM without reference／ContextUtilization | context 相對實際 response 的用途 | q、C、a | 回答漏答會連帶改變 relevance 標準；不可用作完整任務 recall |
| Non-LLM with reference contexts | context 與 gold contexts 的字串距離或相似度、閾值 | C、reference_contexts | 相似不代表 entailment；切塊長度影響比對 |
| ID-based precision | retrieved IDs 與 reference IDs 集合交集 | 兩組 ID | 是集合 precision；不應把名字相似當成上述 ranking formula |

例（本次構造）：五個必要 facts，只檢索一個正確 chunk，排名型 context precision 可為 1，fact recall 為 0.2；兩者並不矛盾。另有 `C=[relevant, irrelevant]` 時排序型得 1，而普通 Precision@2 得 0.5，報告必須展示 metric variant。

### 4.3 Ragas Context Recall 和 Entities Recall

`ContextRecall = supported claims(g,C) / claims(g)`。先將 reference 拆成原子主張，再判斷每項能否由實際 contexts 推得。ID-based recall 用兩組 IDs；non-LLM 變體用 reference context 比對，估计對象不同。[官方](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_recall/)

`ContextEntityRecall = |entities(g) ∩ entities(C)| / |entities(g)|`。它檢查人、地、組織、日期等是否出現，不檢查關係、否定、數字條件或時間有效性。[官方 Entities Recall](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/context_entities_recall/)

本次分析：entity recall 適合作診斷，不能替代 fact recall。「A 機構不再提供 B」和「A 機構提供 B」可有相同 entities。抽取和正規化需處理中文別名、繁簡、日期、同名機構；零個 gold entity 不能靠除數加 epsilon 靜默生成品質分。

官方範例也需審閱：上述 Context Recall 頁面 `Example` 把「巴黎是法國首都」作 context、把「艾菲爾鐵塔位於巴黎」作 reference，卻展示 1.0。我們的邏輯檢查認為 context 單獨不足以推出 reference；應以正式主張支持定義為準。這是文件範例問題，未實跑 Ragas，不能據此宣稱程式必定如此評分。

## 5. 生成、真實性、完整性與引文

### 5.1 Faithfulness／Groundedness

`F = |{s∈claims(a): C supports s}| / |claims(a)|`。需要實際提供給生成器的完整 context，而非命中的節點名稱或事後從全部知識庫搜到的支持。Ragas 使用先拆 claims、再判 entailment 的流程，可用 Judge 或 HHEM 類模型執行後一階段。[官方 Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

本次操作建議：每個 claim 儲存文本跨度、supported／contradicted／insufficient evidence、來源 span 和理由；將長句拆成數字、否定、條件、時間、地區可各自核對的原子命題。同理、問句、創作或建議不是一律當成外部事實。嚴重安全錯誤需另設 gate，不能被大量低風險正確敘述稀釋。

**三件事不可合併：**答案與資料一致是 semantic support；runtime trace 中資料有進 prompt 是 exposure／provenance；移除／替換資料後答案改變才提供 causal-use 證據。Faithfulness 不單獨證明後兩者，也不證明資料本身正確。

### 5.2 Correctness、Completeness、Semantic Similarity

Ragas factual correctness 以 a 與 g 的主張比較，產生 TP／FP／FN，再按 precision、recall 或 Fβ 計算；原子化粒度與 coverage 設定會改變分母。[Factual Correctness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/factual_correctness/)

`P=TP/(TP+FP)`、`R=TP/(TP+FN)`、`Fβ=(1+β²)PR/(β²P+R)`。這些 TP／FP／FN 是**主張匹配**，不是 retrieved chunk 匹配。版本較舊的 AnswerCorrectness 預設把 factuality 與 embedding similarity 按 0.75／0.25 混合；不能將這個加權分直接解釋為「75% 事實正確率」。[v0.1.21 API](https://docs.ragas.io/en/v0.1.21/references/metrics.html)

語義相似通常以回答與 reference embeddings 的 cosine 等方式量化，適合找措辭接近的回應；「可以」與「不可以」可能相似度很高，故不能作安全 correctness gate。[Semantic Similarity](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/semantic_similarity/)

本次建議將 correctness 與 completeness 獨立：前者核對已說 facts，後者核對必須涵蓋的要求／facts。golden answer 應容許多種正確措辭及合理策略，並標示「必須」「可選」「禁止」，而非全文單一答案相似比對。

### 5.3 Answer／Response Relevancy

Ragas 的逆向問題法：從 a 產生 N 個可能問題 q′，取 `mean cosine(E(q),E(q′))`，常見 N=3。此法不衡量事實正確；cosine 數學範圍為 −1 至 1，官方亦說明不保證總在 0–1。[官方](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/answer_relevance/)

本次建議：區分這種 embedding proxy 與 rubric-based「是否回應全部問題」；澄清問題、適當拒絕、情緒陪伴等可能合理卻不易逆向還原。多輪先明定當前 query 是否含 history 中尚未解決的要求，勿只餵最後一句「好」。

### 5.4 Citation precision／coverage

引用有兩個不同分母：precision 檢查已附引文的 support；coverage 檢查需要引文的內容有多少得到支持。URL 有效、來源在 allowlist、文字附 `[1]`、資料曾被 retrieved，均不等於支持對應 claim。AWS 的具體 prompt 見下一節；本次建議更細的 claim–citation edge 判定，以定位「來源存在但被錯引」與「有事實卻沒引文」。

### 5.5 傳統 NLP 與舊版 Ragas 名稱

BLEU 以 clipped n-gram precision 的幾何平均乘 brevity penalty：`BLEU=BP·exp(Σw_n log p_n)`；生成長度 c 大於參考有效長度 r 時 BP=1，否則 `exp(1−r/c)`。原方法主要作 corpus-level 翻譯評估，單句值尤其易受用詞與零 n-gram 重疊影響。中文需固定斷詞、繁簡、標點、smoothing 與多參考策略。[BLEU 原論文](https://aclanthology.org/P02-1040.pdf)

ROUGE-N 以 reference n-grams 中被匹配的比例衡量 recall；ROUGE-L 以最長共同子序列構造 precision、recall、F-score。必須報告具體 variant 及 P／R／F，不只寫「ROUGE」。措辭重疊不驗證否定、事實、行動或安全；本次建議只作輔助回歸訊號。[ROUGE 原論文](https://aclanthology.org/W04-1013.pdf)

舊式 Context Relevancy 可按 query 所需的 context sentences 佔全部 context sentences 的比例估計；這是 Ragas 早期論文的 context relevance 思路，與現行排序型 Context Precision、AWS passage relevance 不同。舊文章列出的八項名稱不應當成永久固定的一套 API。[Ragas 原論文](https://arxiv.org/html/2309.15217v2)

## 6. AWS builtin 的輸入與尺度：以實際 evaluator prompt 為準

以下是 **Amazon Nova Pro 的 RAG evaluator** 公開 prompt 映射，不是所有 Bedrock Judge 的通用契約。`H/q/a/C/g` 分別代表歷史、問題、回答、context、reference；尺度是原始 labels 映射，不能與報告中的 normalized scores 混用。[Nova Pro RAG evaluator prompts](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-type-kb-prompt-kb-nova.html)

| Builtin | 輸入 | 原始尺度／方向 |
|---|---|---|
| ContextRelevance | q、單一 passage | 0／1／2：無／不確定／有關 |
| ContextCoverage | q、C、g | 0–4：無、少、約半、多、全部 |
| Correctness | 有 g：q、a、g；無 g：H、q、C、a | 0／1／2：錯、混合、對 |
| Completeness | q、a、可選 g | 0–4：無至完整 |
| Helpfulness | H、q、C、a | 0–6：無用至超出預期 |
| LogicalCoherence | 可選 H、q、a | 0／1／2：不連貫、混合、連貫 |
| Faithfulness | C、a | 0–4：無支持至全支持 |
| CitationPrecision | a、被引 passage | 0／1：沒有／有資訊重疊 |
| CitationCoverage | a、被引 passages | 0–4：無至全部支持 |
| Harmfulness | q、a | 0／1：未檢出／檢出 |
| Stereotyping | q、a | 0／1：未檢出／檢出 |
| Refusal | q、a | 0／1：未拒絕／拒絕 |

不同模型的 prompt 可能含不同 history 欄位、JSON／XML 格式與尺度，實作要 pin model ID、prompt 版本與 label mapping。不得由指標名稱推定輸入完全相同。[Haiku 4.5 RAG prompts](https://docs.aws.amazon.com/bedrock/latest/userguide/model-evaluation-type-kb-prompt-claude-haiku-4-5.html)

本次解讀與移植注意：

1. Nova Pro 頁面 Helpfulness 說明段寫 1–7，但實際 mapping 為 0–6；應保存 raw label，按明列 mapping 解析，再核對 service output。這是可定位的文件敘述差異，不是對線上計分的測試結果。
2. Correctness 有 g 時採 reference 對齊，reference 錯仍可能得高分；gold 審核與時效必須獨立。
3. Faithfulness 允許容易推出的常識推論；若 XiaoAn 要求 strict supplied evidence，需明確收窄規則。
4. CitationPrecision 的「至少一些資訊有用」比每個 claim–citation pair 都支持寬鬆；不能稱為逐主張 entailment precision。
5. Harmfulness 與 Stereotyping 是檢出率，越高通常越有問題；Refusal 是現象，不是越高或越低越好。
6. 家暴支援可能合理重述暴力經驗，或拒絕不安全請求；要另分「適當拒絕」「過度拒絕」「有害配合」「支持性談及暴力」，不能直接用 generic flag 當專業安全評分。

以上 2–6 是針對此 prompt 定義的本次應用分析，並非 AWS 宣稱適合家暴服務；評估設計需由領域專家校準。

## 7. 不能漏掉的 Agent 評估層

RAG 三角只包含 query、context、answer。真正 Agent 尚有 actions、tool arguments、tool results、狀態轉移、停止條件和歷史累積。Ragas 已另列 Topic Adherence、Tool Call Accuracy、Tool Call F1、Agent Goal Accuracy；這本身也表示 RAG 分數不能代表 Agent 整體能力。[官方 Agent metrics](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/agents/)

本次建議的獨立評估設計：

| 層 | 測試證據 | 適合判定 | 常見假成功 |
|---|---|---|---|
| Outcome | 工具環境最終 state、產物 | 必需 postconditions 全部成立 | 回答說已完成但資料未寫入 |
| Trajectory | 有序 tool calls／results | 選工具、參數、必要先後依賴 | 名稱對但參數錯／步驟漏 |
| Policy | 決策時的可用資訊與授權 | 是否遵守限制、是否需轉人工 | 最終答案好看卻越權 |
| Recovery | timeout、空結果、工具異常 | 重試有界、fallback 合理、不中斷狀態 | 無限 loop／把錯誤當成功 |
| Multi-turn | 完整 episode | 記住目標、接受更正、更新狀態、適當終止 | 單輪高分但跨輪矛盾 |
| Efficiency | wall time、tokens、calls、成本 | 成功條件下 P50／P95、每次成功成本 | 只比較較短但未完成的 run |

Tool F1 可按 `2TP/(2TP+FP+FN)`，但必須指定匹配是否考慮參數、次數及順序；完全 trace match 對多種合理路徑過苛刻，宜採必要偏序與狀態約束。例：2 個必要 calls 都完成、另多 1 call，則 P=2/3、R=1、F1=0.8。

原文品質檢查：Ragas Agent 頁面的 `Example: Extra Tool Called` 展示上述 TP=2／FP=1／FN=0 卻寫 F1=0.67，與 F1 公式不符；這是本次算術核對，不能據此判定其 runtime 實作。該頁 `ToolCallAccuracy` 不同段落對二元／部分分的描述亦應配合安裝版本源碼驗證，不能只抄文件介紹。

## 8. 評估器本身如何驗證

LLM Judge 是量測工具，不是 ground truth。MT-Bench 研究分析 position、verbosity、self-enhancement 等偏差；其人機 agreement 結果有特定測試、模型和題型範圍。[原論文](https://arxiv.org/abs/2306.05685)

ARES 的重要補充是以少量人工標註校正大量模型預測並建立不確定性，不是「多找幾個模型投票就準」。該研究配置約 150 或以上人工驗證點及少量領域示例；這是研究設定，不是 XiaoAn 最低樣本保證。[ARES 方法](https://arxiv.org/html/2311.09476v2)

本次建議按以下順序驗收：

1. **標準可理解。** 每個 metric 定義對象、輸入、不可判定条件、尺度 anchors、嚴重錯誤 gate。用專家分歧改良定義，不先追求總分。
2. **證據忠實。** Judge 只看決策時存在且 allowlisted 的 evidence；避免模型身份、路由標籤、expected score 洩漏。Gold 可交 Judge，但不可交 subject 當作輸入。
3. **人工校準。** 同一批 answer/evidence 由至少兩位評分者盲評；保留原始分歧與 adjudication。抽樣涵蓋低分、高分、拒絕、邊界、錯引及運行缺失，不能只抽成功例。
4. **絕對與配對分开。** Absolute rubric 看達標；pairwise 看同題 A/B 偏好。後者交換 A/B 次序、允許 tie，不能拿排序相關性替代絕對一致性。
5. **一致不等於有效。** 五個 Judge 同意同一錯誤不會令錯誤變真；檢查自評偏好、同供應商偏差及共享 reference 錯誤。
6. **評分重複。** 固定 subject response 重複 Judge，量測裁判變異；另重複 subject run 測系統變異，兩個方差來源不能混淆。
7. **統計單位明確。** 兩個 case × 五個 subject × 五個 judge 不等於 50 個獨立情境。Bootstrap 或比較應以 case／episode 群集，報有效樣本與缺失矩陣，不給兩題結果外推整個部署的信心。
8. **盲保留集。** Development、calibration、holdout 分開；同一事件的重寫題留在同一 split，避免 leakage。回報切片與 worst cases，勿只看平均。

## 9. 一個可執行的分層評估流程（本次整合方案）

### 階段 A：建立測試資料

每個 case 至少記 `case_id`、`dataset_version`、q、h、任務目的、所需 evidence、可接受策略、禁止結果、reference validity date、jurisdiction、criticality。檢索測試加 relevant source/fact IDs；工具測試加初始狀態、允許工具、postconditions；多輪測試加 stop／handoff 條件。合成資料需人工審核，並檢查答案是否洩漏到 query。

覆蓋至少：單事實、多文件、無答案、矛盾／過期資料、數字否定、模糊問題、繁簡及口語、多輪更正、合理澄清、適當拒絕、錯誤工具回傳、工具不可用。題數按切片與錯誤置信需求决定，不能照抄「50 題已足夠」。

### 階段 B：重現運行

固定 corpus snapshot、chunker、embedding、reranker、prompt、subject model、工具版本和 feature flags；保存 ranked retrieved candidates、post-rerank、實際 admitted context 三層，標記截斷與空值。以 immutable run ID 關聯回答／trace。原始工具 secret 不進 evidence bundle。

### 階段 C：分層評分

先檢查 transport 和 schema；再評 retrieval、support、correctness、completeness、safety、agent state。provider failure 保留 UNAVAILABLE；retriever 成功回空但應有答案則是實際檢索失敗，兩者不可混淆。安全 critical failure 獨立列出，不用 average 抵銷。

### 階段 D：診斷與歸因

低 recall 優先檢查 gold、ingest、切塊、query、filter、retriever；高 recall 低 faithfulness 檢查實際 prompt 截斷、生成遵循及 evidence 衝突；高 faithfulness 低 correctness 檢查來源錯誤／過期；回答高分但 state failure 檢查工具執行。這些都只是排查路徑。

要作因果歸因，固定同一 snapshot 與 case，採 single-variable ablation：正常 context、去 context、替換無關 context、替換衝突 fact、gold context；比較同一 outcome／facts 的變化並重複。一次改模型、prompt 和檢索不能歸因任一項。

### 階段 E：報告與持續監控

每張表同時列 eligible N、scored N、缺失原因、分布、CI、critical failures、版本及代表案例。成本含 subject、Judge、retry；品質均值以有效評分為分母，availability 另用所有預定 runs。上線後回報案例先去識別化與審核再入庫，避免讓敏感原對話直接成為所有外部 Judge 的輸入。

## 10. 主張對照與不可跨越的結論

| 常見說法 | 核對後可以說甚麼 | 不可以說甚麼 |
|---|---|---|
| Ragas 不需要 ground truth | 部分 metrics 可無 reference | 全部 metrics 都不需 reference |
| Context Precision 高 | relevant chunks 排得好，依變體而定 | 必要證據都齊全 |
| Groundedness 高 | 回答受到指定 context 支持 | 來源真實、系統一定使用此資料 |
| 引文合法 | ID／URL 有效 | 引文支持該主張 |
| Correctness 高 | 相對特定基準／Judge 定義高 | 基準必然正確 |
| 多 Judge 一致 | 評分者在此樣本較一致 | 已有 domain validity |
| RAG 高分 | query–context–answer 三角表現佳 | 工具、狀態、授權、多輪都合格 |
| 每次只花少量 token | 某次模型輸出成本低 | 全流程成本低或完成率高 |
| 文章或官方範例有分數 | 可核對文件展示值 | 已驗證實際 library／service runtime |

文中的來源閱讀與方法核對已完成；repository 的 `evaluation`、`evaluation_multimodels` 是否遵守上述條件，應以同日獨立 code audit 的源碼行號、可重現反例和測試結果判定。
