# Anthropic Prompt Evaluations 課程研究筆記

> 研究日期：2026-07-18  
> 範圍：只研究 Anthropic 官方 `anthropics/courses` repo 的 `prompt_evaluations` README，以及第 01、03、04、07、08、09 課。  
> 固定版本：commit [`f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77`](https://github.com/anthropics/courses/tree/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations)（2025-11-13）。  
> 注意：以下「官方做法」是課程直接展示的內容；「融入本專案」是根據課程模式作出的工程建議，不代表 Anthropic 官方對本專案的背書。

## 1. 結論摘要

Anthropic 課程把 evaluation 定義為針對特定使用場景的系統化測試，而不是通用模型 benchmark。每個 evaluation 最少包含四個概念：代表性輸入、golden answer、模型輸出和分數。課程建議通常準備至少 100 組 test-case／golden-answer；教學示例為控制成本而刻意使用較少資料。[來源：01 Evaluations 101](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)

評分方法依客觀程度分層：

1. 能用 deterministic code 判定的項目，優先 exact match、集合相等、關鍵字、regex 或自訂程式 grader。
2. 語氣、適切性、相關性等難以程式化的項目，可用 `llm-rubric` 或自訂 model grader。
3. 專業領域事實性、複雜推理與細微語氣仍以人類，尤其領域專家評審為 gold standard；缺點是成本、速度和評審間一致性。[來源：01 Evaluations 101](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)

課程展示的核心閉環是：建立測試集 -> 寫初版 prompt -> 取得 baseline -> 檢視逐例失敗 -> 修改 prompt -> 用同一測試集重跑比較。Promptfoo 用設定檔把 prompts、providers、tests 和 assertions 組成可重複執行的矩陣，並以 `promptfoo eval` 執行、`promptfoo view` 檢視逐例輸入、輸出、分數與原因。[來源：課程 README](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/README.md)、[第 07 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/lesson.ipynb)

這套方法適合作為本專案 evaluation harness 的「資料集、grader 和回歸比較」層，但課程沒有示範多節點 Agent trace、檢索歸因、PII-safe observability、版本快照或 HITL 審批。因此不能只部署 Promptfoo 就聲稱已完成高風險 Agentic RAG 的問責與可觀測性架構。

## 2. Dataset Structure

### 2.1 最小資料單位

第 01 課的最小模型是：

```python
{
    "complaint": "The app crashes every time I try to upload a photo",
    "golden_answer": ["Software Bug"],
}
```

其中輸入欄位名稱可以依任務改變，`golden_answer` 是正確或理想輸出。開放式任務未必能用單一 golden text 判定，這時可改以 rubric 和專家評分。[來源：01 Evaluations 101](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)

### 2.2 Exact-match dataset

第 03 課使用 list of dictionaries，每列包含：

```python
{
    "animal_statement": "The animal is a human.",
    "golden_answer": "2",
}
```

輸入經 prompt function 轉為 model messages，模型輸出再和 `golden_answer` 逐字相等比較。當 prompt 改成輸出 `<answer>...</answer>` 時，grader 先用 regex 擷取答案，再進行 exact match。[來源：03 Code-graded eval](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/03_code_graded_evals/03_code_graded.ipynb)

### 2.3 Multi-label classification dataset

第 04 課把 `golden_answer` 定義為一到兩個分類的 list：

```python
{
    "complaint": "The app is crashing and my phone is overheating",
    "golden_answer": ["Software Bug", "Hardware Malfunction"],
}
```

此結構允許多標籤，但評分仍是整列 exact set equality，而不是每個 label 各自計 precision／recall。[來源：04 Classification eval](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/04_code_graded_classification_evals/04_code_graded_classification_evals.ipynb)

### 2.4 Promptfoo dataset

Promptfoo 將測試資料放在 `tests[].vars`，並用 `{{variable}}` 注入 prompt：

```yaml
tests:
  - vars:
      topic: sheep
      count: 3
```

長輸入可以使用檔案引用，避免把全文塞入 YAML：

```yaml
tests:
  - vars:
      article: file://articles/article1.txt
```

課程示例還展示：

- prompt 可直接內嵌於 YAML，或引用 `prompts.py:function_name`。
- 多個 prompt 可在同一組 tests 上比較。
- 多個 provider 可在同一組 tests 上比較。
- 共用 grader 可放在 `defaultTest.assert`，自動套用到所有測試列。

[來源：07 設定檔](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/promptfooconfig.yaml)、[09 設定檔](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/promptfooconfig.yaml)

### 2.5 融入本專案的 dataset 建議

Anthropic 的四元素可保留，但 Agentic RAG 每列還需要加入可判定過程正確性的期望值：

```yaml
id: local-police-dismissal-001
input:
  message: "警察說是家務事不處理，我可以怎麼辦？"
  history: []
expected:
  route: local
  intents: [police_dismissal]
  capsule_ids: [N3a]
  required_node_ids: [node:...]
  forbidden_claims: []
  safety_action: continue
rubric_id: trauma_informed_v1
tags: [local, legal, police, zh-hk]
```

這是本專案擴充，不是課程原有 schema。關鍵是同一列同時支援 router、retrieval、generation 和 end-to-end grader，而非只保存「問題 + 最終理想答案」。

## 3. Code Grader

### 3.1 Exact match

第 03 課的最小 grader 是：

```python
def grade_completion(output, golden_answer):
    return output == golden_answer
```

所有 boolean grades 取平均即可形成 accuracy。這適合固定 ID、固定枚舉、格式與必須完全一致的結構化輸出，不適合評估自然語言回答品質。[來源：03 Code-graded eval](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/03_code_graded_evals/03_code_graded.ipynb)

### 3.2 先解析，再判分

當模型輸出包含 reasoning 和最終答案時，第 03 課先擷取 `<answer>` 標籤內容，再比對 golden answer。這個模式可轉用於本專案的 structured planner JSON、citation IDs 和 fallback reason：先 schema validate／normalize，再做 deterministic assertion，不應讓 LLM judge 猜測 JSON 是否「大致正確」。[來源：03 Code-graded eval](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/03_code_graded_evals/03_code_graded.ipynb)

### 3.3 Promptfoo 自訂 Python grader

第 07 課讓 Promptfoo 呼叫 `get_assert(output, context)`：

```python
def get_assert(output, context):
    topic = context["vars"]["topic"]
    goal_count = int(context["vars"]["count"])
    # deterministic regex calculation...
    return {
        "pass": goal_count == actual_count,
        "score": 1 if goal_count == actual_count else 0,
        "reason": f"Expected {goal_count}; actual {actual_count}",
    }
```

`context` 提供 test variables 和生成 prompt 所需上下文；grader 可回傳 boolean、float，或包含 `pass`、`score`、`reason` 的 grading result。設定如下：

```yaml
defaultTest:
  assert:
    - type: python
      value: file://count.py
```

[來源：07 自訂 grader 程式](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/count.py)、[07 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/lesson.ipynb)

對本專案，`reason` 應使用 machine-readable failure code 加簡短細節，例如 `ROUTE_MISMATCH`、`MISSING_REQUIRED_SOURCE`、`RAW_PII_LEAK`。這樣低分才能直接歸入 router、retrieval、compose、guard 或 privacy 模組。

## 4. Classification Grader

第 04 課的分類 grader 做三步：

1. 將 golden labels 全部 lowercase 後轉成 set。
2. 將模型用逗號分隔的輸出 trim、lowercase 後轉成 set。
3. 只有兩個 set 完全相等才算該列正確。

```python
golden_set = set(category.lower() for category in item["golden_answer"])
prediction_set = set(category.strip().lower() for category in response.split(','))
is_correct = golden_set == prediction_set
```

這比 raw exact string match 更能容忍順序與大小寫差異，但仍會同時懲罰漏標和多標。[來源：04 Classification eval](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/04_code_graded_classification_evals/04_code_graded_classification_evals.ipynb)

融入本專案時，可用同一模式計算 planner 的整列 exact match，但 release report 還應另計：

- 每個 route 的 precision／recall／F1 和 confusion matrix。
- `multi_local` 的多標籤 precision／recall，而不只 subset accuracy。
- safety false negative 和 privacy leakage 以獨立零容忍 gate 呈現，不被總平均稀釋。

後三項是針對高風險系統的工程擴充；Anthropic 教學示例只計整體 accuracy。

## 5. Built-in Model Grader

第 08 課使用 Promptfoo 的 `llm-rubric`，為每項主觀標準建立一個 assertion：

```yaml
defaultTest:
  assert:
    - type: llm-rubric
      provider: anthropic:messages:claude-3-opus-20240229
      value: Refuses to answer the question and instead redirects to academic topics
    - type: llm-rubric
      provider: anthropic:messages:claude-3-opus-20240229
      value: Is not apologetic
```

課程同時比較三個 prompt，用相同五個 off-topic questions 和相同兩項 rubric 評分。Web view 可以展開單一格，查看模型輸出及 judge 的評分理由。[來源：08 設定檔](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/promptfooconfig.yaml)、[08 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/lesson.ipynb)

適合本專案的維度包括創傷知情語氣、是否說教、是否清晰、是否造成過量認知負擔。法條是否有 source support、citation ID 是否有效、PII 是否洩漏，應優先交給 code grader，而不是 `llm-rubric`。

## 6. Custom Model Grader

第 09 課展示完整自訂 LLM-as-a-judge：

1. 把原始 article 和待評 summary 一起交給 judge。
2. 為 conciseness、accuracy、tone 定義 1-5 分 rubric anchors。
3. 提供兩個已評分 few-shot examples。
4. 要求 judge 回傳固定 JSON，包括三個數值和 explanation。
5. 設 `temperature=0`，用 assistant prefill `<json>` 及 stop sequence `</json>` 約束輸出。
6. 解析 JSON，取所有數值平均。
7. 平均分 `>= 4.5` 才 pass，並把 judge 原始 JSON 放入 `reason`。

Promptfoo 仍透過相同介面呼叫：

```python
def get_assert(output: str, context, threshold=4.5):
    article = context["vars"]["article"]
    score, evaluation = llm_eval(output, article)
    return {
        "pass": score >= threshold,
        "score": score,
        "reason": evaluation,
    }
```

[來源：09 自訂 model grader](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/custom_llm_eval.py)、[09 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/lesson.ipynb)

本專案不應直接複製「多維度取平均 >= threshold」作唯一門檻。法律錯誤、安全 false negative 或 PII leakage 不能被高語氣分抵銷。較合理的是：每個維度保留獨立分數，硬性風險維度使用 veto gate，只有軟品質維度才計 weighted aggregate。

## 7. 官方課程 Workflow

綜合第 01、03、04、07、08、09 課，工作流如下：

```text
定義 use case 與成功標準
  -> 建立代表性 inputs + golden answers / rubrics
  -> 寫初版 prompt
  -> 固定 model/provider 與執行參數
  -> 批次產生 outputs
  -> code / classification / model / human grading
  -> 記錄 baseline 和逐例 failure reasons
  -> 修改 prompt
  -> 在同一資料集重跑
  -> 比較 prompts / models 的分數與失敗案例
```

Promptfoo 的最小操作流程：

```bash
npx promptfoo@latest init
npx promptfoo@latest eval
npx promptfoo@latest view
```

課程示例的 config 組成：

```yaml
description: evaluation name
prompts: [prompt variants]
providers: [model variants]
defaultTest:
  assert: [shared graders]
tests: [input variables]
```

[來源：07 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/lesson.ipynb)、[08 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/lesson.ipynb)、[09 課](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/lesson.ipynb)

## 8. 融入 Agentic GraphRAG Evaluation 的位置

| Agent 階段 | 課程中可直接借用的 evaluator pattern | 本專案需要新增的資料 |
|---|---|---|
| Router / Planner | classification set equality、自訂 code grader | route、intent、capsule 的期望 JSON；confusion matrix |
| Retrieval | 自訂 Python grader | query、returned node/source IDs、required/forbidden nodes、relevance labels |
| Compose | custom model grader、HITL | 回答、evidence bundle、逐維度專家 rubric、golden trajectory |
| Citation / Privacy / Safety | exact match、regex、schema validator | citation validity、PII canaries、safety expected action、veto reason |
| Prompt / Model 比較 | Promptfoo 的 prompts x providers x tests matrix | prompt/model/index snapshot IDs 與成本、延遲欄位 |

建議把 Promptfoo 當成離線 regression runner 和比較 UI；完整 trace 由獨立 observability store 提供。每條 eval result 只需要保存 `trace_id`，即可從低分結果跳回 router output、retrieval query/context、compose prompt、token 和 latency。這個 trace 架構不是 Anthropic 課程涵蓋內容，但能補足課程只觀察 prompt/output 的限制。

## 9. 採用限制與防誤用

1. **示例資料量不足。** 課程反覆聲明 5、8、12、20 條示例只是教學用途，正式 evaluation 通常建議至少 100 組 test-case／golden-answer。[來源：01](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)、[04](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/04_code_graded_classification_evals/04_code_graded_classification_evals.ipynb)、[09](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/lesson.ipynb)
2. **不要用 LLM grader 取代可程式化判斷。** 第 08 課明確指出 code grader 最簡單且成本最低，只是無法處理主觀項目。[來源：08](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/lesson.ipynb)
3. **不要把平均分當成高風險 gate。** 第 09 課的平均 4.5 是摘要教學案例，不代表法律／安全系統的 release policy。[來源：09](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/lesson.ipynb)
4. **Model grader 仍需校準。** 第 01 課指出 model grading 可能引入 judge 自身偏差；高風險專業事實和細微情境仍需專家評審。[來源：01](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)
5. **課程不提供 process observability。** Promptfoo view 能展示 prompt、output、assertion score 和 reason，但指定課程沒有設計 Router、retrieval、context、compose 等多節點 trace。此部分必須由本專案另行實作。

## 10. 官方來源索引

- [Prompt evaluations README](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/README.md)
- [01 Evaluations 101](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/01_intro_to_evals/01_intro_to_evals.ipynb)
- [03 Simple code-graded evaluation](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/03_code_graded_evals/03_code_graded.ipynb)
- [04 Code-graded classification evaluation](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/04_code_graded_classification_evals/04_code_graded_classification_evals.ipynb)
- [07 Promptfoo custom graders lesson](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/lesson.ipynb)
- [07 Python grader implementation](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/07_prompt_foo_custom_graders/count.py)
- [08 Promptfoo model-graded lesson](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/lesson.ipynb)
- [08 `llm-rubric` configuration](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/08_prompt_foo_model_graded/promptfooconfig.yaml)
- [09 Custom model-graded lesson](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/lesson.ipynb)
- [09 Custom LLM grader implementation](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/custom_llm_eval.py)
- [09 Promptfoo configuration](https://github.com/anthropics/courses/blob/f4dbb137d7b02dddaf3cc73e32e20a702d3b5e77/prompt_evaluations/09_custom_model_graded_prompt_foo/promptfooconfig.yaml)
