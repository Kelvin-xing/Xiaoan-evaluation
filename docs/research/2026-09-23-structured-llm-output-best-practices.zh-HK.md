# 大模型輸出規範化：Chatflow 與多模型評估的落地建議

研究日期：2026-09-23。本文是工程研究與建議；未修改執行程式，未新增付費模型呼叫。

可靠的做法是把輸出視為需要驗收的資料介面：**供應商端約束結構 → 確認回應完整 → 本地驗證型別與業務規則 → 驗證來源 → 保存結果 → 確定性呈現**。提示詞仍用來解釋判斷任務，但結構完整性應由 schema 和程式承擔。官方文件支持優先採用原生結構化輸出，同時保留應用層驗證。[LangChain](https://docs.langchain.com/oss/python/langchain/structured-output)、[Gemini](https://ai.google.dev/gemini-api/docs/structured-output)

## 原廠能力與工程邊界

| 方式 | 適用場景 | 應驗證的條件 |
|---|---|---|
| 提示詞要求 JSON | 尚未支援結構化輸出的探索階段 | 語法、欄位、型別均由本地檢查 |
| JSON mode | 要求有效 JSON | 另外驗證 schema；成功 parse 尚未完成驗收 |
| 原生 JSON Schema 約束 | Judge、分類、資料抽取、報告資料 | 核對精確模型、端點、schema 子集及完成狀態 |
| Tool calling | 模型要選擇操作，或以工具提交結構化結果 | forced tool 只要求選用工具；schema 保證取決於是否啟用受支援的 strict 模式 |

Claude 提供 `output_config.format` 的 JSON schema 輸出及 `strict: true` 工具輸入約束。SDK 會把部分不支援約束改寫為描述，再用原始 schema 本地驗證；因此必須保留完整本地契約。拒絕、輸出上限及文件列出的 enum 大小寫例外仍需處理。[Claude Structured outputs](https://platform.claude.com/docs/en/build-with-claude/structured-outputs)

Gemini 支援 JSON Schema 子集，過深或過大的 schema 可能被拒絕。官方明確要求應用驗證欄位值及語義。原生介面與相容介面的欄位不同，實作應按實際端點文件映射，不能直接套用其他供應商參數。[Gemini Structured outputs](https://ai.google.dev/gemini-api/docs/structured-output)

LangChain 區分原生 `ProviderStrategy` 與 `ToolStrategy`，可對特定驗證錯誤提供重試回饋。這提供整合模式，並非必須引入的新框架；專案可以在既有 transport 實作同樣邊界。[LangChain Structured output](https://docs.langchain.com/oss/python/langchain/structured-output)

**第三方網關的能力需要獨立驗證。** 以下是本專案建議：以 `base_url + endpoint/protocol + model + schema_version` 建立能力記錄，保存實際送出的結構化參數、回應完成狀態及驗證結果。原廠文件支持某項能力，只能作為測試依據；KaroAPI、GlobalAI 的實際轉接是否保留該能力，仍以該路徑測試為準。

## 建議的共同資料契約

以下是針對本專案的設計提案，並非目前全部已實作的功能。

1. **一份本地完整契約。** 用 Pydantic 等型別系統定義 required、enum、數值範圍、nullable 及跨欄位規則。對分數和布林值啟用嚴格型別，避免字串被悄悄轉成數字；日期等 JSON 型別有各自規則，需要測試實際驗證行為。[Pydantic Strict mode](https://docs.pydantic.dev/latest/concepts/strict_mode/)
2. **供應商 schema 是衍生產物。** 適配器只移除原廠不支援的結構約束，記錄差異；本地驗收仍使用完整契約。缺資料用明確 `null` 或狀態，不用假分數、空字串或補造證據湊齊欄位。
3. **結構與業務分開驗證。** Judge 檢查 rubric ID 集合、分數範圍、case/turn/judge 綁定；claim 檢查 ID 唯一性及引文是否對應凍結文字；Report 檢查引用來自已讀取的工作簿快照。本地可透過 field/model validators 表達這些規則。[Pydantic Validators](https://docs.pydantic.dev/latest/concepts/validators/)
4. **模型選證據，程式取原文。** Report 優先返回穩定的 evidence ID 或已驗證 span，程式從快照提取精確引文、分數及分母，再渲染 Markdown。對模型生成的分析文字另做依據驗證。這能減少不存在的 cell、重寫引文及算術錯誤。
5. **短任務、明確輸出。** `read`、`search`、`finish` 各自有清楚的合法欄位與 action 值；不要把整段自由 Markdown 同時當成機器協議。資料量大時分成有限批次，最後用程式合併。

## 錯誤分類與有限重試

以下是建議策略。重試必須共享總次數、時間及費用上限；SDK、HTTP client 與業務層的重試要一併計數。

| 錯誤 | 建議處理 |
|---|---|
| 認證失敗、無權模型、schema 參數不支援 | 停止該路徑，修正配置；不要原樣循環呼叫 |
| 暫時性限流、服務失敗、連線中斷 | 在上限內退避；保存每次 attempt 與已知 request ID |
| 拒絕 | 記錄獨立狀態；依產品規則處理，不當成 JSON 修復問題 |
| 輸出截斷 | 記錄 incomplete；可縮短輸出或在預算內提高上限，完整重做該份結構資料 |
| JSON/schema 驗證失敗 | 若路徑允許修正，最多增加一輪具體欄位錯誤回饋；仍失敗則 UNAVAILABLE |
| 引用不存在、分數越界、證據不匹配 | 拒收；有限重新生成或交人工查核；不得自動改成看似合理值 |
| 多個物件串接、疑似重複串流事件 | 先保留事件序列和原始資料，檢查 assembler；不任意截取第一個可 parse 物件 |

規範化只能包含預先定義、可追蹤且不改變語義的轉換。若導入 JSON repair，應保存原文、修復結果、差異及工具版本，重新通過全部驗證；評估分數、引文、claim ID 或判斷被更動時，不應作為無痕修復接受。重試生成的新分數也是新 attempt，不可挑選較高分或拼接不同 attempt。

## 本次 TC-52 的實際故障與優先修改點

以下是 2026-09-23 本地程式及凍結產物的檢查結果；樣本只有一個兩輪案例，尚無足夠數據估計格式錯誤率。

| 已確認的現象 | 證據 | 工程判斷與建議 |
|---|---|---|
| 臨時適配器 Claude 僅文字要求 JSON，GPT 使用 `json_object` | [run_staged.py](../../evaluation_multimodels/runs/20260923-tc52-gpt6-three-judges/private/run_staged.py)，47、68–71 行 | 這次試跑繞過了已有的結構化 Judge 傳輸約束。優先回到共用適配器，再驗證實際網關能力。 |
| 正式 matrix Judge 有較強的輸出契約 | [company_eval_plugins.py](../../evaluation_multimodels/company_eval_plugins.py)，179–182 行 | Claude 設有 tool/input_schema/強制 tool_choice，但此處沒有 `strict:true`；非 Claude 設有 strict json_schema。forced tool 本身不等同嚴格解碼。 |
| Claude T2 JSON 解析失敗，即使 stop_reason 為 end_turn | `private/calls/e08b9bee4f006d6baed7695a8cf429abfcc52a26916d0b95c92289361eca15ae.raw-0.json` | 完成標記與 JSON／業務契約都要檢查。修復嘗試未恢復有效 Judge，維持 UNAVAILABLE。 |
| 一份 Report 回應連續包含三個相同 JSON 物件 | `private/calls/89d322132e2c64f3cab95f0225cafe2be9c1019ace8c06609b600284f5f91ba1.raw.json` | 現有 raw 是拼接後文字；缺少完整事件軌跡，尚無法區分模型、網關或 collector 原因。不得用「截第一個 JSON」掩蓋問題。 |
| 報告另有引用驗證失敗、讀取逾時；Gemini 為 HTTP 401 | [本次報告](../../evaluation_multimodels/runs/20260923-tc52-gpt6-three-judges/report.md)、`private/report-audit/*/manifest.json` | 引用錯誤屬證據一致性；401／timeout 屬可用性。分開計數與處理。 |

上表 private 路徑均相對於 `evaluation_multimodels/runs/20260923-tc52-gpt6-three-judges/`。現有 [report_agent.py](../../evaluation_multimodels/xiaoan_eval/report_agent.py) 的 `_validate_final` 已檢查引用是否讀過、引文是否存在於單一 cell；應保留這道驗證。其 default provider 仍用 JSON mode，可優先改成經驗證的結構化 action 契約。

## OpenAI 與串流的補充規範

OpenAI 建議可用時採 Structured Outputs；JSON mode 主要約束 JSON 語法，strict schema 約束欄位結構。Responses 使用 `text.format`，Chat Completions 使用 `response_format`。schema 須符合供應商支援子集，並另處理拒絕與 incomplete。[官方 Structured Outputs](https://developers.openai.com/api/docs/guides/structured-outputs)

Responses 串流有 typed events，包括文字 delta、completed 和 error。[官方串流文件](https://developers.openai.com/api/docs/guides/streaming-responses)

**本專案建議**：保留所需串流協議；按 response／item／content 身分組裝，記錄事件序號（若提供），以最終成功狀態才提交完整結果。若使用 final response 文字，勿再加上已收集的 deltas。只有事件身分可證明重送時才去重，不能按相同文字片段去重。缺少完成事件、完整結果與 delta 不一致、或出現多個頂層 JSON，均保存原始證據並報錯。下一次受控診斷才收集完整事件，不為研究重發敏感案例。

## 建議的最小落地順序與驗收

以下是待實作提案，並非本次已改動的功能。

1. **統一契約與實際傳輸入口**：Judge、claim extractor、Report action 各有一個 typed contract；由契約生成請求 schema 和本地驗證。模型／地址／協議／key 沿用各自指定 `.env`，不在新模組加入 fallback。將 endpoint、model、協議、SDK 版本及 schema hash 納入能力驗證記錄；原廠文件不能替代 Karo 實測。
2. **完整回應後分層驗證**：傳輸 → completion/refusal → JSON → schema → case/turn/judge/oracle 身分、claim 覆蓋及引用有效性 → 持久化。通過所有必要檢查才進品質統計。refusal、缺少 context、認證失敗、格式失敗各有明確狀態，UNAVAILABLE 留在可用性分母，排除品質分母。
3. **縮小模型必須生成的內容**：Report 讓模型輸出分析與 evidence ID，由程式查原文、計算聚合並產生 Markdown／表格。仍由模型提出解讀；確定性 renderer 處理排版和原文引用。schema 正確不能代替證據是否支持結論的審核。
4. **限定重試和修復權限**：建議每個邏輯呼叫最多兩次實際嘗試，SDK 與框架共用預算。401／不支援 schema 先修配置，refusal 不以改寫繞過；暫時網路錯誤採有上限退避。格式重試附精確 validator 錯誤，凍結題目、證據和評分契約。保存每次 raw、解析結果、錯誤、request ID、schema hash；成功快取不被失敗覆蓋。`json_repair` 僅作診斷或單獨標註的修復產物，不靜默改寫分數、證據與原始回應。
5. **先離線回歸，再小型真實探測**：重播本次 raw，以及缺欄位／額外欄位／錯型別／越界分數／不存在引用／錯誤 case ID／拒絕／截斷／重複事件／401／逾時。驗收要求所有無效 fixture 被正確分類、有效 fixture 完整保留，重試不超預算。其後在已授權 endpoint 做最小非敏感能力探測，分別記錄首次格式通過率、最終語義通過率、重試率、延遲和成本；小樣本只驗證兼容性，不宣稱生產可靠率。

本次交付為官方文件研究與本地證據核對；沒有修改 runtime、重跑評分或證明 Karo 的 strict schema 支援。
