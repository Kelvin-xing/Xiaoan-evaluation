# Test Case Coverage Analysis

Source workbook: 咨询数据库-反家暴.xlsx

Analysis date: 2026-08-19

## Method

The workbook contains 344 consultation rows. Coverage counts use
privacy-preserving keyword classification. Visitor-topic signals use 案由 and
咨询内容; adviser-response signals use 法律建议 and are reported separately.
Names, telephone numbers, addresses, and row-level narratives are not copied
into test cases or this report. Counts are overlapping signals rather than
mutually exclusive labels.

The reproducible aggregate script is
`tools/analyze_workbook_coverage.py`. It emits no row content:

```bash
python tools/analyze_workbook_coverage.py 咨询数据库-反家暴.xlsx \
  --output coverage-signals.json
```

The workbook is a historical consultation sample. It cannot prove that the
suite covers every problem a future visitor may encounter. It is used to find
gaps and skew, while safety, accessibility, and adversarial cases remain
necessary even when rare in the workbook.

## Workbook Signals And Case Coverage

| Visitor topic signal | Rows | Existing coverage | Added coverage | Assessment |
| --- | ---: | --- | --- | --- |
| Divorce procedure | 336 | TC-06, TC-14, TC-16, TC-61, TC-67 | TC-69 | Add protocol-choice and cooling-off distinction |
| Referral channels | 150 | TC-01, TC-05, TC-10, TC-28, TC-29, TC-63 | TC-69, TC-74 | Broad coverage |
| Child custody/visitation | 145 | TC-12, TC-13, TC-16, TC-44, TC-64, TC-65 | TC-72 | Add safe visitation hand-off |
| Immediate danger/injury | 143 | TC-01 to TC-03, TC-23, TC-46 to TC-50 | TC-73, TC-74 | Strong safety coverage |
| Evidence preservation | 87 | TC-06, TC-41, TC-45, TC-62, TC-63 | TC-70, TC-73 | Add no-visible-injury evidence chain |
| Property division/transfer | 83 | TC-19, TC-40, TC-61, TC-68 | TC-71 | Add alleged debt and basic living needs |
| Mental violence/control | 42 | TC-17 to TC-20, TC-51 to TC-55 | TC-70 | Broad coverage |
| Compensation | 26 | TC-43, TC-67 | None | Covered provisionally |
| Economic control/support | 26 | TC-11, TC-19, TC-58, TC-68 | TC-71 | Covered |
| Protection order | 22 | TC-42, TC-65, TC-66 | TC-69 | Covered |
| Cohabiting/unmarried | 16 | TC-14 | None | Covered with low depth |
| Disability/illness | 9 | TC-05, TC-26, TC-56 | TC-74 | Covered |
| Older people | 9 | TC-11, TC-60 | None | Covered |
| Sexual violence | 3 | TC-22 | None | Covered with low depth |
| Sexual/gender minority | 3 | TC-07, TC-25, TC-57 | None | Covered |
| Cross-border | 2 | TC-21, TC-62 | None | Covered |

## Additions

- TC-69: divorce route, cooling-off-period misconception, and safety.
- TC-70: evidence chain where visible injury is absent.
- TC-71: alleged marital debt, financial control, and basic living needs.
- TC-72: safe child-visitation hand-off after violence.
- TC-73: strangulation risk, medical care, reporting, and evidence.
- TC-74: safe recovery of identity documents, medicine, and belongings.

All additions are synthetic and have provisional oracle provenance. Their
expected outcomes require test-case-owner review and, for legal assertions, a
qualified legal reviewer before release gating.

## Residual Limits

- Keyword counts measure presence, not legal or psychosocial complexity.
- Historical data is dominated by divorce consultations and may underrepresent
  people who cannot reach legal services.
- Trace attribution shows whether capsule and ground refs were used; it cannot
  prove the provenance of every generated claim.
- Coverage should be reviewed against new anonymized incidents, domain
  feedback, and observed production failures.
