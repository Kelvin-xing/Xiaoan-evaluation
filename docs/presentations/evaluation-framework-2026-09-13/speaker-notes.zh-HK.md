# XiaoAn 評估框架｜逐頁講稿

建議主線：約30分鐘（1–24頁）；25–30頁供問答。所有範例為合成，統計數字為2026-09-13源碼盤點／離線測試。

完整基準：[GitHub README](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md)。

## 01. 如何設計一個 能指導改進的 Agent 評估框架

**本頁要傳達：** 讓每個分數，都能回到案例、證據與下一步。

今天要分享的是我如何設計評估系統，不是展示哪個模型排名第一。我把評估設計成三個問題：這次執行是否可信、回應是否符合任務與安全要求、下一個改動要在哪裡驗證。投影片基於目前README和v2修復；所有數字例子是合成示例，測試通過數是軟體回歸結果，不是真實模型成績。主線約30分鐘，最後六頁供技術問答。

設計依據：[README / design](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#design)

## 02. 評估的終點，是下一個可驗證的決定

**本頁要傳達：** 分數是診斷的入口；改動必須接受新的驗證。

先建立評估的用途。單一平均分可以告訴我們數字升降，卻未必能告訴我們發生什麼。這套系統要求先驗證執行、再測回應、最後把finding轉成可驗證假設。例如timeout應修transport，context缺事實應查資料，Judge分歧應查評分規則。這三條不能直接被一個高分或低分取代。

設計依據：[README / design](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#design)

## 03. 兩套 evaluator，對應兩種研究問題

**本頁要傳達：** 先固定評估對象，才能解讀比較結果。

evaluation是對單一已部署的Chatflow做端到端測試。evaluation_multimodels則讓不同subject產生答案，再讓不同Judge看同一份答案。兩套共用測量概念，但輸出schema和執行編排不同。它們目前仍是兩份獨立package，import和CLI同名，所以必須使用獨立virtualenv。共用核心去重是後續維護工作，不宣稱已完成。

設計依據：[README / design](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#design)

## 04. 把評估拆成三層，避免用高分掩蓋問題

**本頁要傳達：** Weighted_Total 只概括品質，不能替代可靠性與安全。

這三層是不同測量，不是把所有分數相加。第一層問資料是否可信及是否有已知違規。第二層需要批准的oracle，問是否符合這次任務。第三層才是語氣、行動賦權、法律和資源等品質。Weighted_Total只概括第三層。安全違規不能用表達好補回來，資料缺失也不能用零分懲罰模型。

設計依據：[README / design](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#design)

## 05. 一條能追回證據的資料流

**本頁要傳達：** 每個 finding 要能追到 case → turn → metric → evidence。

從case和manifest開始，Runner執行實際系統並保留答案與trace。確定性檢查負責可以由程式判定的部分；Judge負責需要語義判斷的部分。結果進正規化facts和ReportModel，再生成Excel與Markdown，避免兩種報告自行算出兩種數字。人評也回到同一資料模型，保留automatic、human和final來源，而不是改掉原始自動評分。

設計依據：[README / architecture](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#architecture)

## 06. Ordinary：跨案例並行，同一對話保持順序

**本頁要傳達：** 並行提升吞吐，不能破壞對話狀態與完整性。

多輪評估最重要的是保持狀態。對話中上一輪影響下一輪，所以同case不能平行發送。独立case可以並行，默认是2。ordinary是在每輪回覆後評審，不是整批答案先凍結的兩階段模式。若其中一輪缺失，整案品質不可用；不能只平均成功輪次，否則越容易timeout的系統反而可能得到漂亮的平均分。

設計依據：[README / architecture](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#architecture)

## 07. Matrix：先凍結答案，再讓不同 Judge 評同一份

**本頁要傳達：** 固定被評對象，才能測量評審差異。

如果每個Judge都重新呼叫subject生成答案，我們就分不清差異來自生成還是評審。所以matrix設計一個barrier，先讓subject phase完成或不可用，再評同一批immutable answer artifacts。Checkpoint也綁契約和identity。這讓同一answer上的Judge差異有可比性，但還不等於Judge已校準，也不保證不同subject都有相同panel。

設計依據：[README / architecture](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#architecture)

## 08. Case、Oracle、Trace 各有一個責任

**本頁要傳達：** 空 oracle 是未測量，不是模型答錯。

Oracle不一定是一段唯一標準答案。對支持型agent，更合理的是可接受的路由集合、必須照顧的要求和不能做的行為。Case是情境，oracle是判斷條件，trace是觀測。沒有oracle時不能把沒有標籤算成答錯；只有trace時也不能把系統自己的判斷當成金標。新oracle需要領域審閱，不能由我們寫好YAML就自動批准。

設計依據：[README / cases](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#cases)

## 09. 成熟度控制「可以判定」與「可以聚合」

**本頁要傳達：** 不讓草案或未批准分母，悄悄變成正式結論。

這三種狀態分開控制資料的可信程度。Reviewed表示oracle已有審閱標記，但不代表所有情境的聚合都獲准。Scenario score另要求Approved Aggregate和可比分組。目前74案都是Reviewed而非Approved Aggregate，因此不能說正式scenario rollup已具备完整分母。這是檔案標記盤點，不是我今天完成了74次人工評審。

設計依據：[README / cases](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#cases)

## 10. 74 個案例，不等於每種能力都已覆蓋

**本頁要傳達：** 報告同時展示 authored 與 reviewed，讓缺口可見。

這頁是最需要團隊一起看清楚的限制。74案、217輪提供了不少情境，但非空route oracle只有4輪，safety只有24輪，response oracle為0，memory只有6個use。這些不同單元不能混在一起報一個覆蓋率。本次補九份草案：TC17和52的response提案，加上其他七類memory提案。它們沒有自動批准，也沒有自動加入正式集。下一步不是宣称全部覆蓋，而是安排reviewer和harness。

設計依據：[README / cases](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#cases)

## 11. 先讀狀態，再讀分數

**本頁要傳達：** 排除 timeout 的品質假零分，但仍必須報告 timeout。

過去PASS混用了正常執行與品質合格。v2把execution_status與quality_verdict拆開。沒有品質threshold時即使3分也不自動PASS；缺失則quality null，不能進品質平均。已知紅線和缺失可以同時存在，安全FAIL仍保留，但整案品質可能不可用。這頁的0和null差別是整個框架的核心：零代表有觀察且得零，null代表無法給可信數值。

設計依據：[README / status](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#status)

## 12. 七維度給品質刻度，紅線保留不可補償的底線

**本頁要傳達：** 高表達分，不能抵消安全違規。

七維度沿用產品rubric，權重分別是22、18、18、13、9、9、11個百分點。逐維度只選0到3整數，聚合才會出現小數。紅線涵蓋安全對峙、錯誤法律資源、越界承諾、危機漏判、責難和歧視，不能靠其他維度補償。不過rubric還需要逐情境applicability和正反例，否則可能在情緒支持情境機械要求法律內容或鼓勵冗長。

設計依據：[README / scoring](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#scoring)

## 13. Focus 是調整權重，不是刪掉其他維度

**本頁要傳達：** 同一組評分事實，在哪條路徑都要得到同一個量。

用一個極端但清楚的合成反例說明。只有行動賦權3分，其餘0，並聚焦行動賦權。基礎0.18乘1.5得0.27，所有權重總和變1.09，最後3乘0.27再除1.09，得到0.743119。所有七維度都要在分母裡。以前ordinary、matrix、suite分別得到不同數字；v2統一，連人工覆核和裁決也保存並使用原動態權重。

設計依據：[README / scoring](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#scoring)

## 14. 聚合順序，决定了你到底在比較什麼

**本頁要傳達：** 平均值之外，必须說清 unit、完整性與分母。

先算case再平均，能讓長案例不自動獲得更多權重。這個例子case A平均1、case B平均3，case macro是2；直接平均四輪卻是1.5。兩個都可作統計，但不能混用同一名稱。Matrix cell總分選case macro，維度表則是診斷性的turn median。若case A缺其中一輪，就不能用剩餘輪次冒充完整case。分母不同要標清楚。

設計依據：[README / scoring](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#scoring)

## 15. 不同指標，對應不同失敗階段

**本頁要傳達：** 從最早有證據的失敗點，提出修正假設。

指標要能指向下一個調查位置，但只能指出證據支持的候選原因。Route錯可能是oracle或state，不一定要調embedding；ground錯先修解析；unsupported高要看具體claim和evidence；Judge不同意可能是規則不清楚。這樣可避免看到低分就一律改prompt。每個修改要寫成hypothesis再驗證，不在報告中把相關當因果。

設計依據：[README / metrics](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#metrics)

## 16. 「選到」「送到」「支持」「造成改變」是四件事

**本頁要傳達：** Trace 讓過程可見；因果仍需要受控實驗。

一個capsule被選中，只能證明route；出现在snapshot才能證明exposure；回答和證據的span關係才支持語義歸因；要說那段內容造成答案變化，必須介入。各layer support可以重疊，不能加成來源百分比分解。Partial的0.5是計分選擇，不是自然常數。Judge漏抽claim仍會抬高支持率，所以需要人工inventory和extraction recall。

設計依據：[README / attribution](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#attribution)

## 17. 好的記憶，也包含「正確地不用」

**本頁要傳達：** 缺遙測 → SKIP；明確觀測失敗 → FAIL。

之前ordinary把不同memory類型全當成必須使用，正確不用會被判錯。現在共用observer按類型判斷。缺memory_used欄位不是false，是unknown；明確空retrieved list和缺list也不同。通用布林flag是弱證據，per-fact use和session trace更強。但新增七類草案還需接通telemetry及多session harness，並不代表我們已驗證完整memory能力。

設計依據：[README / memory](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#memory)

## 18. 多個 Judge 同意，不等於答案正確

**本頁要傳達：** Agreement 是描述證據；效度需要獨立人工錨點。

這張是示意矩陣，不是實際結果。去掉同模型自評能減少一種偏差，但各subject也可能少了不同Judge，留下不同panel。Kendall W需要完整共同panel，去對角線後常不可用，不能靠插補制造完整性。所有評分一樣也不代表alpha=1；沒有預期分歧時alpha無法估計。正式效度要靠凍結人類benchmark、紅線漏判及held-out誤差，一致性只能描述。

設計依據：[README / matrix](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#matrix)

## 19. 人工覆核要能改結論，也要保留原始事實

**本頁要傳達：** 可追溯地修正結果，不覆寫歷史或其他案例。

人評不是在Excel隨便改總分。先輸出盲審packet，綁case/turn/response，完整填寫各維度和紅線證據後匯入。紅線分歧進裁決，選擇automatic或human的證據來源。最終分重新使用原動態權重與threshold計算，原分數不刪，其他未覆核case不變。原執行失敗也不能靠人工高分變成可用。v2還處理了原本覆核後結論不更新和錯誤未加權平均的問題。

設計依據：[README / review](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#review)

## 20. 報告先看資格與分母，再看平均分

**本頁要傳達：** 可用樣本變少時，更高的平均分可能沒有可比性。

Excel和Markdown是同一份正規化資料的兩種讀法。先看版本與artifact state，再看可評樣本及oracle覆蓋，之後才看品質。找出問題後沿case/turn和evidence refs回查。Ordinary workbook是2.1固定十張表；matrix有自己的專用schema，不能拿matrix檔直接做人評或ordinary baseline。正式pair可能含敏感內容，正式不等於自動可以公開上傳。

設計依據：[README / reports](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#reports)

## 21. 從 finding 到改動，中間要有一個可反駁假設

**本頁要傳達：** 沒有受控證據之前，推薦仍是 hypothesis。

我用EDD把評估接到產品改進。先記錄可重現失敗，再提出能被反駁的根因假設，固定case、model、knowledge snapshot和Judge，一次改一個變量。除了目標指標，还要看非目標退步與critical gate。現有預設是三個seeds，target pass-rate提升0.10、weighted提升0.15、非目標退步上限0.10、critical regression零容忍；這些是當前配置，不是研究確立的標準。

設計依據：[README / experiments](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#experiments)

## 22. v2 修的是測量契約，不是把模型分數調高

**本頁要傳達：** 升版造成的數字變化，不等於模型能力提升。

這批改動的重點是讓分數能信任，不是提高分數。還修了空route oracle分母、unsupported required claim、人工覆核的權重与结论，以及合法零分被truthiness误当missing。由於公式和schema升版，不能把v1和v2的分差直接當作模型改善。這些反例已轉成回歸測試，所以未來改程式時能檢查契約是否又漂移。

設計依據：[README / versions](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#versions)

## 23. 已經實作的能力，與仍待證明的能力分開

**本頁要傳達：** 把未測到的地方寫出來，是評估可靠性的一部分。

這頁避免把存在一個函式當作完成一種評估。Tools目前主要是名稱、參數、順序匹配，不能驗證外部世界狀態。Goal欄位目前比較預期與實際布林，不能直接稱完成率；steps更接近budget compliance。Pairwise helper沒有完整CLI。Statistical CI也未完整處理case內相關性。這些會写進README作为已知邊界，讓團隊能確定下一批投資應該在哪裡。

設計依據：[README / limits](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#limits)

## 24. 團隊接下來一起完成三件事

**本頁要傳達：** 討論焦點：誰批准 oracle、誰接 telemetry、哪個實驗先跑？

結束主線時，我希望團隊不是只記得公式，而是能分配下一步。領域同事要確認什麼任務算成功、必要和禁止內容及例外；工程同事把觀測接到實際系統，尤其memory的fact IDs和session隔離；評估同事負責人類benchmark、Judge尺度和共同panel。今天不要自動批准草案或選一個看起來最高的模型，而是先讓下一次比較有可信分母和證據。

設計依據：[README / limits](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#limits)

## 25. 備查｜指標的分子、分母與缺失政策

**本頁要傳達：** 每個 metric 都要有 unit、eligibility、denominator 與 evidence。

問答時用這頁解釋各指標的分母。特别是unsupported不能只算extra，因為required但沒有支持仍是unsupported。Faithfulness只衡量模型已抽取claims對给定證據的支持；漏抽claim可能縮小分母。Required-claim匹配有string identity限制。這些詳細定義以README第6節及目前源碼為準，不把名稱相似的通用RAG指標直接替換現有契約。

設計依據：[README / metrics](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#metrics)

## 26. 備查｜兩種執行入口

**本頁要傳達：** 兩個 project 使用獨立 virtualenv；live run 需要真實 endpoint 與配置。

這頁是命令參數備查，不要直接把換行當成完整shell腳本，README有可複製的反斜線續行版本。執行前需要獨立virtualenv、真正部署的Chatflow、有效provider及本次manifest。Direct model模式把subject transport換成multimodel_transport即可，但測量對象也隨之改變。不要把matrix的PASS當成ordinary品質門檻PASS。

設計依據：[README / usage](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#usage)

## 27. 備查｜重現一個結果，至少固定哪些東西？

**本頁要傳達：** model 名稱相同，不足以保證兩次評估可比。

版本需要包含被測系統和測量工具兩邊。只固定model卻改了knowledge或Judge prompt，分數就不一定可比。Manifest應反映本次真實配置，不能把repo的歷史hash照抄。Checkpoint同樣需要契約相容。兩套發行package目前核心有複製，所以本次也核對改動核心一致，並在standalone環境重跑完整測試。

設計依據：[README / versions](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#versions)

## 28. 備查｜三個名稱，不能按字面過度解讀

**本頁要傳達：** 以實際公式與所需證據解讀，不按欄位名稱猜測。

名稱有時比證據強，這是我們保留但明示的設計債。Expected false和actual false可以得到高goal agreement，卻不表示完成外部任務；在budget內快速失敗也可能得到高step分。工具呼叫匹配不等於工具結果。這次聚焦修復用戶選定的測量錯誤，沒有把這些legacy欄位悄悄宣稱為已完成outcome评估。

設計依據：[README / limits](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#limits)

## 29. 備查｜校準與統計推論的最低要求

**本頁要傳達：** 一致性、效度、可比性與不確定性，必須分別證明。

校準、比較和不確定性是三个不同問題。校準要有可信人標；公平比较需要共同case和panel；推論要考慮多輪同case相關，不能把每turn都當獨立樣本。現有bootstrap是turn級描述，正式推論需要cluster和paired設計。零紅線事件只說在這個樣本中沒觀察到，不是風險為零。

設計依據：[README / review](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#review)

## 30. 備查｜設計文件、實作與驗證入口

**本頁要傳達：** 一份設計基準，連起原始碼、報告與團隊討論。

所有設計、公式與操作入口都在repo根README，來源研究與修改前審閱也保留。軟體驗證是248加292項，不是540個真實agent案例。舊2.0 workbook用修改前writer生成過並驗證可讀，缺權重重評會拒絕。投影片与逐頁講稿可以跟README一起版本化，日後設計變動從同一份基準更新。

設計依據：[README / versions](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#versions)
