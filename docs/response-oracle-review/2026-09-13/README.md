# Response oracle 已審核套件

**使用者已於2026-09-13回覆「全部審核通過」。審核人沿用repo身份mat；81案231輪全部記錄為reviewed。**

- [Excel核准紀錄](response-oracle-review.xlsx)：231輪均為通過，附審核人及日期。
- [逐案核准內容](review.zh-HK.md)：必要項、禁止項、來源與仍需留意的案例假設。
- [核准回寫紀錄](approval-receipt.json)：原檔與現檔雜湊、授權文字及修改範圍。
- [載入與覆蓋驗證](validation.json)。

| 範圍 | 案數 | 輪數 | 目前位置 |
|---|---:|---:|---|
| TC-01～74 | 74 | 217 | 已回寫兩個project的test-cases頂層，預設suite可讀取 |
| TC-75～81 | 7 | 14 | 內容已核准，仍在proposed，等待memory harness/telemetry完善 |
| 獨立案例合計 | 81 | 231 | 全部REVIEWED；APPROVED_AGGREGATE仍為0 |

TC-17/52在proposed中的同ID鏡像亦已更新，勿重複計數。`response-oracle-drafts`目錄保留已核准的81份版本，名稱沿用以維持連結；不是另一套需再審的資料。

## 核准範圍

每輪兩項required_claims及兩項forbidden_claims，共462項必要內容、462項禁止內容。允許同義表達、合理選項與條件化說明；引用錯誤說法加以否定不算支持禁止主張。只能使用截至該輪已出現的資訊，跨輪可簡短承接，不要求機械重複。

回寫只改response oracle與審核metadata；原台詞、route/safety標籤、memory checkpoints及既有legal_effective_date均保留。原來源字串保留並追加本次review識別。新增草稿原本沒有法規生效日的仍為null；不把審核日期偽裝成法律生效日期。[來源依據](sources.md)逐文件記錄適用地區與施行日。

本次核准是內容審核，不是模型結果通過、專業資質聲明、case aggregate admission或法律時點的另行核驗。沒有新增live model調用。

## 欄位及執行界限

- 未設定整輪should_abstain：局部拒絕危險／越權要求後繼續支持，不等同全輪拒答。
- 未虛構reference_answer、must_cite、expected_tools、goal_completed、max_chars或max_steps；語意契約保留多種可接受回應。
- 現有claim與禁止主張計算依賴Judge觀測及字串對齊；填完oracle不代表已完成語意校準。缺觀測不能當作模型符合所有要求。
- TC-08狗的歸屬、TC-62婚姻狀態、TC-70「掐我」等原台詞歧義依核准稿採釐清或條件式回應，未自行改寫台詞。
- TC-77仍缺具體工作fact種子；TC-79仍需跨session harness；其他memory類型仍需對應telemetry。缺遙測保持SKIP/UNAVAILABLE。

原74案新增了內容契約，舊評估輸出不能據此宣稱已測過新標準。下一次實跑應使用新case版本及重新生成baseline／Judge校準資料；本次不自動觸發付費評估。

## 追溯與檢查

[review-manifest.json](review-manifest.json)保留原來源雜湊及先前provenance，並記錄本次核准。原始雜湊是核准前快照；現檔雜湊見approval-receipt，不要求現檔仍等於舊雜湊。

`validate_review.py`驗證核准後case狀態、回寫一致性、Excel與YAML內容及預設suite覆蓋。`validation.pre-approval.json`、`validate_pre_approval.py`與`README.pre-approval.md`只作核准前歷史記錄，舊驗證條件不適用於現檔。`authored-oracles.txt`與`build_review.py`保存初稿產生過程，請勿重建覆蓋核准紀錄。
