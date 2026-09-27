# Minimal33 八模型、四評委評測與研究報告

本目錄公開同一批凍結評測的結果與研究產物。先閱讀
[完整研究報告](report-research-full-33/report.md)；
[原評分報告](report-agent-field-diagnosis-20260927/report-full-33-cases.md)
提供其沿用的評分矩陣與案例分析。研究目錄中的 `manifest.json`、
`validation.json`、逐評委觀察、逐輪研究及請求紀錄保留在原有結構中。

`results.xlsx` 可直接開啟。為避免將超過一般 Git 單檔限制的 JSON 直接提交，
`results.json` 與 `frozen-input.json` 以 zstd 壓縮；還原方式：

```sh
zstd -d results.json.zst -o results.json
zstd -d frozen-input.json.zst -o frozen-input.json
```

| 原始檔 | SHA-256 |
| --- | --- |
| `results.json` | `b97ecd736d9a81aecca8ee370a921a06cc9ec59a215696ecd98b9556772ca45b` |
| `frozen-input.json` | `9bbf3f8798617a58ac4306dad9389e1ac8388594eafa1ad1d6048461dfb5d710` |
| `results.xlsx` | `300e9a2e8676356f5118cc567c8c9001a7f08e5096def62442efc790a85d3a42` |
| `report-agent-field-diagnosis-20260927/report-full-33-cases.md` | `9c68419f4c21f7b56d4972562d51ad54f5938dd0b51b2be345eb08d9445a04eb` |

這是有意限定的公開結果集，不是原始執行目錄的逐檔鏡像：不包含
`checkpoint/`、`provider-artifacts/`、重試選擇檔、鎖檔或其他中間續跑材料。
它們不是閱讀報告與核對凍結結果所需的依賴。研究報告仍以原始 JSON
的 SHA-256 綁定，解壓後可直接比對。
