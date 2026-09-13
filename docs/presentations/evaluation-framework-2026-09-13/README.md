> 2026-09-13核准後更新：本投影片保留起草時盤點；其中response oracle=0已被後續核准取代。現行正式套件217輪response oracle已reviewed，另7案14輪memory提案仍待harness。詳見[核准紀錄](../../response-oracle-review/2026-09-13/README.md)。

# 團隊分享｜XiaoAn Agent 評估框架

2026-09-13，基於評分契約 `response-effectiveness/v2` 與最新完整設計 README。

- [可編輯 PowerPoint](xiaoan-evaluation-framework.pptx)：30頁，文字、表格和流程圖均為可編輯物件；包含逐頁speaker notes。
- [PDF](xiaoan-evaluation-framework.pdf)：相同30頁，供開會／跨裝置閱讀。
- [逐頁講稿](speaker-notes.zh-HK.md)：每頁主旨、講解段落與設計文件章節。
- [Slides data](slides.json)：同一份内容來源。

建議1–24頁作約30分鐘主線，25–30頁供問答。主線依序說明：用途、兩套分工、三層測量、執行與資料流、case/oracle/maturity、coverage、狀態／計分／分母、metrics、attribution、memory、Judge、人評、報告、EDD與團隊下一步。

所有算分及矩陣例子為合成示例，沒有用私有對話、個資或provider回應。74案／217輪與oracle數為程式盤點；248／292為離線軟體測試數，不是模型評估成績。新草案仍未獲領域批准。

## 重新生成

環境需要 Python 3、Node.js、`pptxgenjs`，以及含繁體中文的字型（原版使用Heiti TC）。

```bash
python3 build_content.py
node build_slides.cjs
soffice --headless --convert-to pdf --outdir . xiaoan-evaluation-framework.pptx
```

`pptxgenjs`可安裝在使用者自己的Node環境；不需要網路圖片。若在Linux或container轉PDF，先安裝並配置Noto Sans CJK TC等中文字型，並同步修改生成器的fontFace；字型缺失會導致中文不顯示。轉檔後需檢查頁數、中文、換行與表格邊界。PowerPoint直接播放不依賴此轉檔工具。

完整設計基準：[公開 repo README](https://github.com/Kelvin-xing/Xiaoan-evaluation/blob/master/README.md)。
