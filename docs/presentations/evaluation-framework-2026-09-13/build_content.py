"""Public synthetic presentation content, derived from the shared design README."""
import json
from pathlib import Path

slides = []
def add(title, layout, section, data, notes, source, takeaway, subtitle=''):
    slides.append(dict(title=title,layout=layout,section=section,data=data,notes=notes,source=source,takeaway=takeaway,subtitle=subtitle))

add('如何設計一個\n能指導改進的 Agent 評估框架','cover','XIAOAN / DESIGN REVIEW',
 {'edition':'評分契約 v2 · 2026.09.13','line':'從可追溯證據，到可驗證的產品改動','meta':'團隊分享｜24 頁主線 + 6 頁備查｜約 30 分鐘'},
 '今天要分享的是我如何設計評估系統，不是展示哪個模型排名第一。我把評估設計成三個問題：這次執行是否可信、回應是否符合任務與安全要求、下一個改動要在哪裡驗證。投影片基於目前README和v2修復；所有數字例子是合成示例，測試通過數是軟體回歸結果，不是真實模型成績。主線約30分鐘，最後六頁供技術問答。', 'design', '讓每個分數，都能回到案例、證據與下一步。')
add('評估的終點，是下一個可驗證的決定','cards','01 / WHY',
 [{'head':'這次能不能評？','body':'預期輪次有沒有完成？\nprovider、Judge、證據是否可用？','tag':'EXECUTION'},
  {'head':'回應好在哪裡？','body':'安全、任務要求與七維度品質\n必須有各自的判定依据。','tag':'MEASUREMENT'},
  {'head':'接下來改什麼？','body':'先定位最早的失敗階段，\n一次只改一個可控變量。','tag':'DECISION'}],
 '先建立評估的用途。單一平均分可以告訴我們數字升降，卻未必能告訴我們發生什麼。這套系統要求先驗證執行、再測回應、最後把finding轉成可驗證假設。例如timeout應修transport，context缺事實應查資料，Judge分歧應查評分規則。這三條不能直接被一個高分或低分取代。', 'design', '分數是診斷的入口；改動必須接受新的驗證。')
add('兩套 evaluator，對應兩種研究問題','table','02 / SCOPE',
 {'headers':['','evaluation','evaluation_multimodels'], 'rows':[
 ['對象','一個實際 Chatflow deployment','多 Subject × 多 Judges'],
 ['主要問題','哪個 case／階段失敗？','模型差異，還是 Judge 尺度差異？'],
 ['流程','逐輪執行、檢查、評審','先生成凍結答案，再交叉評審'],
 ['輸出','正式 workbook / 人評 / baseline','matrix / 原答案 / Judge cells'],
 ['共同核心','v2 scoring、oracle、狀態、metrics','相同契約；目前仍是兩份 package']]},
 'evaluation是對單一已部署的Chatflow做端到端測試。evaluation_multimodels則讓不同subject產生答案，再讓不同Judge看同一份答案。兩套共用測量概念，但輸出schema和執行編排不同。它們目前仍是兩份獨立package，import和CLI同名，所以必須使用獨立virtualenv。共用核心去重是後續維護工作，不宣稱已完成。', 'design', '先固定評估對象，才能解讀比較結果。')
add('把評估拆成三層，避免用高分掩蓋問題','layers','03 / MEASUREMENT',
 [{'n':'01','head':'執行與安全門檻','body':'完整輪次、必要 trace、provider/Judge、已知紅線'},
  {'n':'02','head':'批准 oracle 的任務符合度','body':'risk、route、必要內容、禁止行為、memory checkpoint'},
  {'n':'03','head':'有證據的品質判斷','body':'七維度 0–3、focus 動態權重、人工與 Judge 來源'}],
 '這三層是不同測量，不是把所有分數相加。第一層問資料是否可信及是否有已知違規。第二層需要批准的oracle，問是否符合這次任務。第三層才是語氣、行動賦權、法律和資源等品質。Weighted_Total只概括第三層。安全違規不能用表達好補回來，資料缺失也不能用零分懲罰模型。', 'design', 'Weighted_Total 只概括品質，不能替代可靠性與安全。')
add('一條能追回證據的資料流','flow','04 / ARCHITECTURE',
 {'steps':['Case / Manifest','Runner / Adapter','Answer + Trace','Rules + Judges','Normalized facts','XLSX + Report'],
  'details':['情境・版本・oracle','順序 turns / 狀態','原文・錯誤・snapshot','確定性 / 語義檢查','狀態・權重・来源','同一份正式資料'],
  'bottom':'人工覆核／裁決 → 保存原權重與來源 → 重算 final verdict'},
 '從case和manifest開始，Runner執行實際系統並保留答案與trace。確定性檢查負責可以由程式判定的部分；Judge負責需要語義判斷的部分。結果進正規化facts和ReportModel，再生成Excel與Markdown，避免兩種報告自行算出兩種數字。人評也回到同一資料模型，保留automatic、human和final來源，而不是改掉原始自動評分。', 'architecture', '每個 finding 要能追到 case → turn → metric → evidence。')
add('Ordinary：跨案例並行，同一對話保持順序','timeline','05 / EXECUTION',
 {'lanes':[['Case A','T1 → 檢查／Judge','T2 → 檢查／Judge','T3 → 完整 case score'],['Case B','T1 → 檢查／Judge','T2 → 完整 case score','可獨立完成']],
  'facts':['CLI 預設 case concurrency = 2','每個 case 建立自己的 conversation','缺輪或必要評分缺失，不用剩餘輪次冒充整案']},
 '多輪評估最重要的是保持狀態。對話中上一輪影響下一輪，所以同case不能平行發送。独立case可以並行，默认是2。ordinary是在每輪回覆後評審，不是整批答案先凍結的兩階段模式。若其中一輪缺失，整案品質不可用；不能只平均成功輪次，否則越容易timeout的系統反而可能得到漂亮的平均分。', 'architecture', '並行提升吞吐，不能破壞對話狀態與完整性。')
add('Matrix：先凍結答案，再讓不同 Judge 評同一份','phases','06 / MATRIX',
 {'left':['PHASE A / SUBJECTS','同一 case 的多個 subject lanes','保留 answer identity、原文、trace','等待全批完成或標記 UNAVAILABLE'],
  'right':['PHASE B / JUDGES','每份固定答案交給多個 Judges','保留各自分數、紅線、錯誤','完整 case 聚合 + 自評標記']},
 '如果每個Judge都重新呼叫subject生成答案，我們就分不清差異來自生成還是評審。所以matrix設計一個barrier，先讓subject phase完成或不可用，再評同一批immutable answer artifacts。Checkpoint也綁契約和identity。這讓同一answer上的Judge差異有可比性，但還不等於Judge已校準，也不保證不同subject都有相同panel。', 'architecture', '固定被評對象，才能測量評審差異。')
add('Case、Oracle、Trace 各有一個責任','cards','07 / TEST DESIGN',
 [{'tag':'CASE','head':'我要測的情境','body':'使用者輸入、歷史、多輪順序\nscenario、cohort、quality_focus'},
  {'tag':'ORACLE','head':'什麼才算符合？','body':'可接受 route 集合\n必要／禁止行為與事實'},
  {'tag':'TRACE','head':'實際發生了什麼？','body':'risk、route、context、state\n工具、timings 與錯誤'}],
 'Oracle不一定是一段唯一標準答案。對支持型agent，更合理的是可接受的路由集合、必須照顧的要求和不能做的行為。Case是情境，oracle是判斷條件，trace是觀測。沒有oracle時不能把沒有標籤算成答錯；只有trace時也不能把系統自己的判斷當成金標。新oracle需要領域審閱，不能由我們寫好YAML就自動批准。', 'cases', '空 oracle 是未測量，不是模型答錯。')
add('成熟度控制「可以判定」與「可以聚合」','flow','08 / GOVERNANCE',
 {'steps':['PROVISIONAL','REVIEWED','APPROVED_AGGREGATE'],
  'details':['草案；只作描述\n不進正式 oracle gate','已審閱標記\n可依批准條件判定','正式 scenario rollup資格\n還須 score 可用'],
  'bottom':'目前 74 個正式 cases 都是 REVIEWED；APPROVED_AGGREGATE = 0'},
 '這三種狀態分開控制資料的可信程度。Reviewed表示oracle已有審閱標記，但不代表所有情境的聚合都獲准。Scenario score另要求Approved Aggregate和可比分組。目前74案都是Reviewed而非Approved Aggregate，因此不能說正式scenario rollup已具备完整分母。這是檔案標記盤點，不是我今天完成了74次人工評審。', 'cases', '不讓草案或未批准分母，悄悄變成正式結論。')
add('74 個案例，不等於每種能力都已覆蓋','coverage','09 / COVERAGE',
 {'cards':[{'number':'74','label':'正式 cases','small':'217 turns；皆標記 REVIEWED'}, {'number':'0','label':'response oracle 輪次','small':'必要／禁止回答條件尚缺'}, {'number':'6','label':'memory checkpoints','small':'目前全部只測 use'}, {'number':'9','label':'新提案 cases','small':'仍是 PROVISIONAL；不自動載入'}],
  'rows':[['Route oracle','4 / 217 turns'],['Safety oracle','24 / 217 turns'],['Scenario 聚合批准','0 / 74 cases']]},
 '這頁是最需要團隊一起看清楚的限制。74案、217輪提供了不少情境，但非空route oracle只有4輪，safety只有24輪，response oracle為0，memory只有6個use。這些不同單元不能混在一起報一個覆蓋率。本次補九份草案：TC17和52的response提案，加上其他七類memory提案。它們沒有自動批准，也沒有自動加入正式集。下一步不是宣称全部覆蓋，而是安排reviewer和harness。', 'cases', '報告同時展示 authored 與 reviewed，讓缺口可見。')
add('先讀狀態，再讀分數','table','10 / STATUS',
 {'headers':['合成情況','品質值／結論','正確解讀'], 'rows':[
 ['provider timeout','null / UNAVAILABLE','執行缺失，不是品質 0'],
 ['完整回答，全部維度 1；門檻 2','1 / FAIL','可正常執行，但品質不達標'],
 ['完整回答，全部维度 3；無門檻','3 / NOT_CONFIGURED','有分數，不宣告品質合格'],
 ['完整可評案例命中紅線','0 / FAIL','真實違規，不能補分'],
 ['oracle 未批准','NOT_APPROVED','描述性結果，不作正式批准']]},
 '過去PASS混用了正常執行與品質合格。v2把execution_status與quality_verdict拆開。沒有品質threshold時即使3分也不自動PASS；缺失則quality null，不能進品質平均。已知紅線和缺失可以同時存在，安全FAIL仍保留，但整案品質可能不可用。這頁的0和null差別是整個框架的核心：零代表有觀察且得零，null代表無法給可信數值。', 'status', '排除 timeout 的品質假零分，但仍必須報告 timeout。')
add('七維度給品質刻度，紅線保留不可補償的底線','weights','11 / RUBRIC',
 {'weights':[['基础能力',0.22],['行动赋权',0.18],['法律维权',0.18],['求助转介',0.13],['表达能力',0.09],['丰富性',0.09],['包容性与可及性',0.11]],
  'anchors':['0  不符合／明顯傷害','1  少量符合／嚴重缺口','2  基本符合／實質缺口','3  充分符合／無相關扣分'],
  'note':'逐維度只用整數 0–3；每一檔需要證據。'},
 '七維度沿用產品rubric，權重分別是22、18、18、13、9、9、11個百分點。逐維度只選0到3整數，聚合才會出現小數。紅線涵蓋安全對峙、錯誤法律資源、越界承諾、危機漏判、責難和歧視，不能靠其他維度補償。不過rubric還需要逐情境applicability和正反例，否則可能在情緒支持情境機械要求法律內容或鼓勵冗長。', 'scoring', '高表達分，不能抵消安全違規。')
add('Focus 是調整權重，不是刪掉其他維度','calculation','12 / SCORING',
 {'number':'0.743119','label':'三條計分路徑的同一個結果',
  'equations':['只有「行动赋权」= 3，其餘 = 0','focus 倍率：1.5','新總權重 = 1 + 0.18 × 0.5 = 1.09','加權總分 = 3 × 0.27 ÷ 1.09'],
  'chips':['Ordinary','Suite','Matrix','Human review']},
 '用一個極端但清楚的合成反例說明。只有行動賦權3分，其餘0，並聚焦行動賦權。基礎0.18乘1.5得0.27，所有權重總和變1.09，最後3乘0.27再除1.09，得到0.743119。所有七維度都要在分母裡。以前ordinary、matrix、suite分別得到不同數字；v2統一，連人工覆核和裁決也保存並使用原動態權重。', 'scoring', '同一組評分事實，在哪條路徑都要得到同一個量。')
add('聚合順序，决定了你到底在比較什麼','aggregation','13 / DENOMINATORS',
 {'left':['CASE A','三輪：[0, 0, 3]','case mean = 1'], 'right':['CASE B','一輪：[3]','case mean = 3'],
  'result':'Case-macro = (1 + 3) ÷ 2 = 2', 'contrast':'Turn-micro = (0 + 0 + 3 + 3) ÷ 4 = 1.5',
  'note':'Matrix 總分採完整 case 的 macro mean；維度表另報有效 turn median。'},
 '先算case再平均，能讓長案例不自動獲得更多權重。這個例子case A平均1、case B平均3，case macro是2；直接平均四輪卻是1.5。兩個都可作統計，但不能混用同一名稱。Matrix cell總分選case macro，維度表則是診斷性的turn median。若case A缺其中一輪，就不能用剩餘輪次冒充完整case。分母不同要標清楚。', 'scoring', '平均值之外，必须說清 unit、完整性與分母。')
add('不同指標，對應不同失敗階段','table','14 / METRICS',
 {'headers':['訊號','先查什麼','不能直接推論'], 'rows':[
 ['Route acceptance 低','oracle、risk、router、state','一定是檢索模型太差'],
 ['Ground resolution error','resolver、ref、snapshot','回答語義一定不正確'],
 ['Unsupported claims 高','answer / evidence spans','加更多 context 就會解決'],
 ['Memory not_use 失敗','使用條件、scope、expiry','記得越多就越好'],
 ['Judge 分歧大','同答案、rubric、人評錨點','應直接改產品 Prompt']]},
 '指標要能指向下一個調查位置，但只能指出證據支持的候選原因。Route錯可能是oracle或state，不一定要調embedding；ground錯先修解析；unsupported高要看具體claim和evidence；Judge不同意可能是規則不清楚。這樣可避免看到低分就一律改prompt。每個修改要寫成hypothesis再驗證，不在報告中把相關當因果。', 'metrics', '從最早有證據的失敗點，提出修正假設。')
add('「選到」「送到」「支持」「造成改變」是四件事','flow','15 / ATTRIBUTION',
 {'steps':['ROUTE','EXPOSURE','SUPPORT','CAUSAL EFFECT'],
  'details':['選中 Capsule / refs','固定 snapshot\n內容送到模型','claim / evidence spans\n語義支持','控制其他變量\n介入後配對重跑'],
  'bottom':'ENTAILS = 1；PARTIAL = 0.5；CONTEXT_ONLY / CONTRADICTS / UNSUPPORTED = 0'},
 '一個capsule被選中，只能證明route；出现在snapshot才能證明exposure；回答和證據的span關係才支持語義歸因；要說那段內容造成答案變化，必須介入。各layer support可以重疊，不能加成來源百分比分解。Partial的0.5是計分選擇，不是自然常數。Judge漏抽claim仍會抬高支持率，所以需要人工inventory和extraction recall。', 'attribution', 'Trace 讓過程可見；因果仍需要受控實驗。')
add('好的記憶，也包含「正確地不用」','memory','16 / MEMORY',
 [{'head':'Remember','body':'應保留的 facts 仍存在'}, {'head':'Retrieve','body':'需要時找到正確 facts'}, {'head':'Use','body':'該用時，有使用證據'}, {'head':'Not use','body':'禁止的 facts 沒被使用'}, {'head':'Update','body':'新資訊正確更新舊狀態'}, {'head':'Isolation','body':'session 隔離，無已知污染'}, {'head':'Stale','body':'沒有使用過期記憶'}, {'head':'Unsafe','body':'沒有不安全的記憶使用'}],
 '之前ordinary把不同memory類型全當成必須使用，正確不用會被判錯。現在共用observer按類型判斷。缺memory_used欄位不是false，是unknown；明確空retrieved list和缺list也不同。通用布林flag是弱證據，per-fact use和session trace更強。但新增七類草案還需接通telemetry及多session harness，並不代表我們已驗證完整memory能力。', 'memory', '缺遙測 → SKIP；明確觀測失敗 → FAIL。')
add('多個 Judge 同意，不等於答案正確','judgepanel','17 / JUDGE VALIDITY',
 {'labels':['J1','J2','J3','J4','J5'], 'rows':['S1','S2','S3','S4','S5'],
  'points':['自評預設排除，保留診斷列','缺 rank 不插補；不完整 panel 的 W 會標為不可用','常數標籤 alpha 未定義，不回傳 1','不同 subject 的可用 Judge panel 仍可能不同'],
  'small':'示意矩陣：S = 同模型自評；圓點只表示交叉評審，不是實測分數。'},
 '這張是示意矩陣，不是實際結果。去掉同模型自評能減少一種偏差，但各subject也可能少了不同Judge，留下不同panel。Kendall W需要完整共同panel，去對角線後常不可用，不能靠插補制造完整性。所有評分一樣也不代表alpha=1；沒有預期分歧時alpha無法估計。正式效度要靠凍結人類benchmark、紅線漏判及held-out誤差，一致性只能描述。', 'matrix', 'Agreement 是描述證據；效度需要獨立人工錨點。')
add('人工覆核要能改結論，也要保留原始事實','flow','18 / HUMAN REVIEW',
 {'steps':['PENDING REVIEW','BLINDED PACKET','VALIDATE','ADJUDICATE','FINAL'],
  'details':['原始自动分仍在','填維度／紅線／證據','immutable binding\n完整性與refs','有紅線分歧才裁決\nautomatic / human','原權重重算\nfinal verdict'],
  'bottom':'保存 automatic / human / final；reviewer ID 是操作標記，不是身份認證。'},
 '人評不是在Excel隨便改總分。先輸出盲審packet，綁case/turn/response，完整填寫各維度和紅線證據後匯入。紅線分歧進裁決，選擇automatic或human的證據來源。最終分重新使用原動態權重與threshold計算，原分數不刪，其他未覆核case不變。原執行失敗也不能靠人工高分變成可用。v2還處理了原本覆核後結論不更新和錯誤未加權平均的問題。', 'review', '可追溯地修正結果，不覆寫歷史或其他案例。')
add('報告先看資格與分母，再看平均分','reports','19 / READOUT',
 {'sequence':['版本 / artifact state','執行 / eligible / coverage','安全與品質','逐 case / turn evidence','Baseline / experiments'],
  'left':['results.xlsx','正式資料與證據','01_Cases：狀態・原權重・來源','02_Turns：對話与全文','03_Metrics：分數・evidence refs'],
  'right':['report.md','面向決策的解讀','整體結論與限制','逐案問題與最早失敗階段','可驗證假設與下一步']},
 'Excel和Markdown是同一份正規化資料的兩種讀法。先看版本與artifact state，再看可評樣本及oracle覆蓋，之後才看品質。找出問題後沿case/turn和evidence refs回查。Ordinary workbook是2.1固定十張表；matrix有自己的專用schema，不能拿matrix檔直接做人評或ordinary baseline。正式pair可能含敏感內容，正式不等於自動可以公開上傳。', 'reports', '可用樣本變少時，更高的平均分可能沒有可比性。')
add('從 finding 到改動，中間要有一個可反駁假設','edd','20 / IMPROVEMENT',
 {'steps':['Observation','Hypothesis','One variable','Paired runs','Guardrails','Verdict'],
  'example':['合成示例：route 合理，但必要內容漏答','假設：Composer 沒有利用已曝光證據','固定 case / model / snapshot / Judge','只改一項受控指令，再看 target 與安全回歸'],
  'small':'目前預設 seeds 101 / 202 / 303；配置門檻不是通用科學標準。'},
 '我用EDD把評估接到產品改進。先記錄可重現失敗，再提出能被反駁的根因假設，固定case、model、knowledge snapshot和Judge，一次改一個變量。除了目標指標，还要看非目標退步與critical gate。現有預設是三個seeds，target pass-rate提升0.10、weighted提升0.15、非目標退步上限0.10、critical regression零容忍；這些是當前配置，不是研究確立的標準。', 'experiments', '沒有受控證據之前，推薦仍是 hypothesis。')
add('v2 修的是測量契約，不是把模型分數調高','table','21 / WHAT CHANGED',
 {'headers':['以前的可重現問題','v2 的行為'], 'rows':[
 ['timeout 合成品質 0','UNAVAILABLE / null；仍報缺失'],
 ['低品質也可顯示 PASS','明確 threshold；無配置不宣告合格'],
 ['三條總分／兩種報表不一致','統一動態加權、case-macro與維度median'],
 ['not_use 與未知 memory 判錯','typed lifecycle + SKIP'],
 ['自評混入、rank插補、常數alpha=1','預設隔離；缺失不插補；退化不可用']]},
 '這批改動的重點是讓分數能信任，不是提高分數。還修了空route oracle分母、unsupported required claim、人工覆核的權重与结论，以及合法零分被truthiness误当missing。由於公式和schema升版，不能把v1和v2的分差直接當作模型改善。這些反例已轉成回歸測試，所以未來改程式時能檢查契約是否又漂移。', 'versions', '升版造成的數字變化，不等於模型能力提升。')
add('已經實作的能力，與仍待證明的能力分開','table','22 / LIMITS',
 {'headers':['已實作／已離線驗證','仍需資料、領域判定或新設計'], 'rows':[
 ['v2 scoring、null、threshold、report一致','逐情境rubric applicability與錨點'],
 ['typed oracle與coverage','response/task oracle與正式scenario批准'],
 ['memory八類observer','真實update／multi-session isolation harness'],
 ['matrix／agreement／校準primitives','共同獨立panel、凍結人類benchmark'],
 ['有限tool／goal欄位','工具結果／權限／副作用、verified goal'],
 ['配對實驗與stability流程','case-cluster CI、完整pairwise CLI']]},
 '這頁避免把存在一個函式當作完成一種評估。Tools目前主要是名稱、參數、順序匹配，不能驗證外部世界狀態。Goal欄位目前比較預期與實際布林，不能直接稱完成率；steps更接近budget compliance。Pairwise helper沒有完整CLI。Statistical CI也未完整處理case內相關性。這些會写進README作为已知邊界，讓團隊能確定下一批投資應該在哪裡。', 'limits', '把未測到的地方寫出來，是評估可靠性的一部分。')
add('團隊接下來一起完成三件事','cards','23 / TEAM DISCUSSION',
 [{'tag':'DOMAIN REVIEW','head':'把任務定義清楚','body':'審閱 TC-17／52 response oracle\n補允許替代與禁止行為\n確認rubric情境適用性'},
  {'tag':'ENGINEERING','head':'把觀察接到實際系統','body':'對接 per-fact memory telemetry\n建立跨session harness\n固定版本與回歸流程'},
  {'tag':'EVALUATION','head':'證明裁判與比較可靠','body':'凍結人工 benchmark\n共同獨立 Judge panel\n以配對實驗驗證一個改動'}],
 '結束主線時，我希望團隊不是只記得公式，而是能分配下一步。領域同事要確認什麼任務算成功、必要和禁止內容及例外；工程同事把觀測接到實際系統，尤其memory的fact IDs和session隔離；評估同事負責人類benchmark、Judge尺度和共同panel。今天不要自動批准草案或選一個看起來最高的模型，而是先讓下一次比較有可信分母和證據。', 'limits', '討論焦點：誰批准 oracle、誰接 telemetry、哪個實驗先跑？')

# Appendix: compact reference slides, not required for the main talk.
add('備查｜指標的分子、分母與缺失政策','table','APPENDIX A / METRIC CONTRACTS',
 {'headers':['指標','分子 / 分母','缺失／解讀'], 'rows':[
 ['Route accepted','actual命中 / 非空approved oracle turns','空oracle排除'],
 ['Required recall','supported required / required claims','沒有gold不可推完整度'],
 ['Faithfulness','supported / judged unique claims','只對給定evidence'],
 ['Unsupported rate','(judged − supported) / judged','required但unsupported也計入'],
 ['Semantic support','每claim最大relation權重 / claims','layer可重疊；非因果'],
 ['Memory P/R','fact TP/(TP+FP)、TP/(TP+FN)','缺retrieval telemetry不補FN']]},
 '問答時用這頁解釋各指標的分母。特别是unsupported不能只算extra，因為required但沒有支持仍是unsupported。Faithfulness只衡量模型已抽取claims對给定證據的支持；漏抽claim可能縮小分母。Required-claim匹配有string identity限制。這些詳細定義以README第6節及目前源碼為準，不把名稱相似的通用RAG指標直接替換現有契約。', 'metrics', '每個 metric 都要有 unit、eligibility、denominator 與 evidence。')
add('備查｜兩種執行入口','commands','APPENDIX B / RUNBOOK',
 {'blocks':[['ORDINARY','xiaoan-eval run test-cases\n  --base-url http://127.0.0.1:8000\n  --judge-plugin company_eval_plugins:judge\n  --context-provider company_eval_plugins:authoritative_context\n  --manifest manifest.json --output runs/team-demo'],
 ['MATRIX','xiaoan-eval matrix test-cases\n  --subject-transport company_eval_plugins:xiaoan_chatflow_transport\n  --judge-transport company_eval_plugins:multimodel_transport\n  --subjects private/subjects.json --judges private/judges.json\n  --output runs/team-matrix']]},
 '這頁是命令參數備查，不要直接把換行當成完整shell腳本，README有可複製的反斜線續行版本。執行前需要獨立virtualenv、真正部署的Chatflow、有效provider及本次manifest。Direct model模式把subject transport換成multimodel_transport即可，但測量對象也隨之改變。不要把matrix的PASS當成ordinary品質門檻PASS。', 'usage', '兩個 project 使用獨立 virtualenv；live run 需要真實 endpoint 與配置。')
add('備查｜重現一個結果，至少固定哪些東西？','cards','APPENDIX C / REPRODUCIBILITY',
 [{'tag':'PRODUCT','head':'被評系統','body':'deployment / policy / guard\nPrompt hashes / knowledge版本\nsubject models / hyperparameters'},
  {'tag':'MEASUREMENT','head':'評估契約','body':'case digests / oracle批准\nscoring v2 / rubric / threshold\nJudge model / prompt / schema'},
  {'tag':'EXECUTION','head':'本次運行','body':'seed / retry / concurrency\nanswer identity / snapshot\nerrors / timing / token telemetry'}],
 '版本需要包含被測系統和測量工具兩邊。只固定model卻改了knowledge或Judge prompt，分數就不一定可比。Manifest應反映本次真實配置，不能把repo的歷史hash照抄。Checkpoint同樣需要契約相容。兩套發行package目前核心有複製，所以本次也核對改動核心一致，並在standalone環境重跑完整測試。', 'versions', 'model 名稱相同，不足以保證兩次評估可比。')
add('備查｜三個名稱，不能按字面過度解讀','table','APPENDIX D / LEGACY SEMANTICS',
 {'headers':['現有名稱','實際衡量','還缺什麼'], 'rows':[
 ['correctness_f1','required completeness的legacy別名','獨立外部fact gold與完整claim inventory'],
 ['goal_completion_rate','expected_goal == actual_goal','可驗證的完成狀態／結果'],
 ['step_efficiency','min(1, max_steps / steps)','成功條件、成本與行動有效性'],
 ['tool matching','名稱／參數／序列符合','權限、postconditions、冪等／副作用'],
 ['layer support','某層能支持claim','因果依賴與互斥來源占比']]},
 '名稱有時比證據強，這是我們保留但明示的設計債。Expected false和actual false可以得到高goal agreement，卻不表示完成外部任務；在budget內快速失敗也可能得到高step分。工具呼叫匹配不等於工具結果。這次聚焦修復用戶選定的測量錯誤，沒有把這些legacy欄位悄悄宣稱為已完成outcome评估。', 'limits', '以實際公式與所需證據解讀，不按欄位名稱猜測。')
add('備查｜校準與統計推論的最低要求','cards','APPENDIX E / VALIDITY',
 [{'tag':'HUMAN ANCHORS','head':'Judge 是否可信？','body':'凍結領域人工benchmark\n紅線sensitivity／漏判\n維度誤差、claim/span agreement'},
  {'tag':'FAIR COMPARISON','head':'版本是否可比？','body':'共同case與獨立Judge panel\n配對control/candidate\ncoverage與缺失原因分層'},
  {'tag':'UNCERTAINTY','head':'差異是否可靠？','body':'以case為獨立cluster\n重複試驗與paired delta\n零事件／小樣本不等於零風險'}],
 '校準、比較和不確定性是三个不同問題。校準要有可信人標；公平比较需要共同case和panel；推論要考慮多輪同case相關，不能把每turn都當獨立樣本。現有bootstrap是turn級描述，正式推論需要cluster和paired設計。零紅線事件只說在這個樣本中沒觀察到，不是風險為零。', 'review', '一致性、效度、可比性與不確定性，必須分別證明。')
add('備查｜設計文件、實作與驗證入口','closing','APPENDIX F / SOURCES',
 {'numbers':[['248','evaluation tests'],['292','multimodel tests'],['13','共用修改核心一致']],
  'links':['github.com/Kelvin-xing/Xiaoan-evaluation','README.md：完整設計與操作','evaluation/README/measurement-contract-v2.zh-HK.md','docs/research/2026-09-13-evaluation-framework-audit.zh-HK.md'],
  'small':'離線合成／mock 回歸；不是模型能力成績。PowerPoint含逐頁講稿。'},
 '所有設計、公式與操作入口都在repo根README，來源研究與修改前審閱也保留。軟體驗證是248加292項，不是540個真實agent案例。舊2.0 workbook用修改前writer生成過並驗證可讀，缺權重重評會拒絕。投影片与逐頁講稿可以跟README一起版本化，日後設計變動從同一份基準更新。', 'versions', '一份設計基準，連起原始碼、報告與團隊討論。')

out=Path(__file__).resolve().parent
(out/'slides.json').write_text(json.dumps(slides,ensure_ascii=False,indent=2)+'\n')
notes=['# XiaoAn 評估框架｜逐頁講稿\n','建議主線：約30分鐘（1–24頁）；25–30頁供問答。所有範例為合成，統計數字為2026-09-13源碼盤點／離線測試。\n','完整基準：[GitHub README](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md)。\n']
for i,s in enumerate(slides,1):
 notes.extend([f'## {i:02d}. {s["title"].replace(chr(10), " ")}\n',f'**本頁要傳達：** {s["takeaway"]}\n',s['notes']+'\n',f'設計依據：[README / {s["source"]}](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md#{s["source"]})\n'])
(out/'speaker-notes.zh-HK.md').write_text('\n'.join(notes))
print(f'{len(slides)} slides and speaker notes written')
