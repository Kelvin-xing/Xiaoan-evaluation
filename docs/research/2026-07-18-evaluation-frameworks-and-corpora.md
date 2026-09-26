# Evaluation frameworks and corpora for the AWS GraphRAG chatflow

**Research date:** 2026-07-18  
**Scope:** Phoenix + OpenInference, Ragas, Promptfoo, CounselBench, CPsyCoun,
`harm-conversations`, LexEval, LegalAgentBench, LawBench and LAiW only.  
**Evidence rule:** Conclusions below use official documentation, official repositories,
paper pages, or first-party dataset cards. License observations are engineering risk
notes, not legal advice; licenses and dataset terms must be rechecked at the pinned
revision before download.

This note supports the evaluation deployment plan for
[`tech/chatflow-AWS/design-doc.md`](../../tech/chatflow-AWS/design-doc.md). The local
expert rubric remains authoritative: six non-waivable safety red lines and seven
weighted quality dimensions in the external `rating_rule.md`, plus TTFT, context
memory and token-cost requirements in `requirements.md`. External frameworks and
corpora may supply execution machinery, diagnostic metrics or candidate cases. They
do not redefine those product requirements.

## Decision vocabulary

- **Adopt:** put on the target implementation path now.
- **Pilot:** time-box and calibrate against project-owned expert labels before making
  it a dependency or release signal.
- **Seed-only:** use selected records or task patterns to draft project-owned cases;
  do not report the external benchmark score as product readiness.
- **Reject:** do not ingest or use for this evaluation unless the stated blocker is
  resolved.

## Recommendation summary

| Item | Decision | Evaluation layer | Why | License / download risk |
|---|---|---|---|---|
| OpenInference | **Adopt** | All process layers and cost/latency | OpenTelemetry-compatible semantic conventions cover LLM, retrieval and tool context; backend-neutral | Apache-2.0. Auto-instrumentation can capture prompts and retrieved text, so capture must occur only after redaction or be disabled per span. |
| Phoenix | **Pilot** | Trace storage, experiment inspection, human failure analysis | Suitable for linking route, retrieval, compose and guard spans into one trace | Phoenix is now Elastic License 2.0, not Apache-2.0. Self-hosting and internal-use terms require review. Trace storage creates a high-impact PII/secrets store. |
| Ragas | **Pilot** | Retrieval, Compose, limited agent diagnostics | Provides context precision/recall, faithfulness, factual correctness and agent/tool metrics | Apache-2.0. LLM-backed metrics send eval content to the configured judge provider; optional analytics must be disabled. Judge scores need expert calibration. |
| Promptfoo | **Adopt** | Offline scenario runner, regression CI, Guard/Safety red-team adjunct | Declarative cases, assertions, model/provider comparison, non-zero CI failure and red teaming | MIT. Node/runtime dependency and generated red-team cases are manageable; cloud sharing must remain disabled for sensitive artifacts. |
| CounselBench | **Pilot, method only** | Compose quality and Safety | Expert ratings expose empathy, specificity, factual consistency, inappropriate medical advice and toxicity; adversarial set targets six observed failure modes | Official repo/Hugging Face pages do not declare a dataset license. **Reject direct data ingestion until written rights are confirmed.** English US counseling data is not a Chinese domestic-violence release set. |
| CPsyCoun | **Pilot** | Multi-turn Compose, psychological strategy, privacy/safety | Chinese multi-turn evaluation covers comprehensiveness, professionalism, authenticity and privacy protection | Repository is CC-BY-4.0. Open CPsyCounD is reconstructed data; CPsyCounR requires a signed Privacy Data Protection Agreement. Do not request or ingest CPsyCounR in the MVP. |
| `mfarme/harm-conversations` | **Seed-only** | Safety routing, false-positive/false-negative fixtures | Labels suicidal ideation, non-suicidal self-harm, harm to others, false positives and benign cases with three severity levels | MIT but gated behind contact-information sharing and contains sensitive content. Fully synthetic, English-only, seven personas and three turns; cannot validate real-world Chinese crisis performance. |
| LexEval | **Seed-only** | Planner legal-intent discrimination, legal Compose preflight | 23 Chinese legal tasks span memorization, understanding, inference, discrimination, generation and ethics | MIT and directly downloadable. Broad Chinese-law benchmark, not domestic-violence retrieval grounding; legal currency and jurisdiction must be checked by counsel. |
| LegalAgentBench | **Pilot, concepts only** | Planner, Retrieval/tool selection and process scoring | 300 tasks, 37 tools, and intermediate-step process rate closely match process-level Agentic RAG evaluation | README displays an MIT badge but the official repo has no `LICENSE` file; 17 underlying corpora and external tools add inherited terms and availability risk. **Reject vendoring code/data until clarified.** |
| LawBench | **Seed-only** | Legal retrieval/knowledge component preflight | 20 Chinese-law tasks include article prediction, marriage-dispute identification, QA and consultation | Repository is Apache-2.0, but its README explicitly requires following each source dataset creator's license. Mixed provenance prevents bulk vendoring without a per-task rights manifest. |
| LAiW | **Seed-only** | Retrieval article recommendation and legal Compose preflight | 14 tasks across information retrieval, foundation inference and complex legal application, including legal consultation | Repository is MIT, but LED reorganizes many third-party datasets. Each selected task needs source-license and legal-currency review. |

## Target integration

The frameworks should have distinct responsibilities rather than forming a second
application stack:

```text
versioned eval case
  -> Promptfoo / Python release runner
  -> deployed or local chatflow endpoint
  -> OpenInference trace (redacted fields only)
       safety -> planner -> capsule -> retrieval -> compose -> guard/fallback
  -> self-hosted Phoenix pilot for trace inspection
  -> deterministic scorers + source validators
  -> Ragas diagnostic metrics (retrieval/grounding only)
  -> calibrated domain LLM judges
  -> human expert review queue
  -> immutable report joined to trace_id and component versions
```

Promptfoo is the scenario and CI orchestrator, not the system of record. Phoenix is
the trace viewer and experiment-analysis pilot, not the release-gate owner. The
project's Python release runner must remain the source of truth for case versions,
deterministic assertions, zero-tolerance gates and signed reports.

### OpenInference trace contract

Adopt OpenInference span kinds and OpenTelemetry IDs, but define project-owned
attributes for the GraphRAG chatflow. A turn trace should include:

| Span | Required safe attributes | Never record |
|---|---|---|
| `safety` | policy version, labels, hard-risk boolean, latency | raw message or matched raw substring |
| `planner` | route mode, confidence, capsule candidates, prompt/model version, token counts | raw message/history, unrestricted chain of thought |
| `retrieval` | redacted query hash, index/sidecar version, node/source IDs, scores, graph hops, latency | raw production PII, secrets, unapproved source text |
| `compose` | evidence IDs/hashes, prompt/model version, TTFT, total time, input/output tokens | hidden reasoning; raw unredacted prompt |
| `guard` | policy version, violations, regeneration count, fallback reason | raw blocked content unless it is an approved synthetic eval fixture |
| root turn | case/session pseudonymous ID, build SHA, config versions, total cost | name, phone, address, vendor credentials |

Auto-instrumentation must not be enabled before the redaction boundary. For a
production-derived trace, store hashes and stable IDs rather than prompt/context
bodies. Synthetic offline evaluation may store approved fixture text in a separate,
access-controlled project with a shorter retention policy. Phoenix telemetry should
be disabled, and access, encryption, retention and deletion should be configured
before the pilot.

Official basis: OpenInference describes itself as OpenTelemetry-compatible
conventions for LLM invocations, vector-store retrieval and tool use, and can export
to any OpenTelemetry-compatible backend. Its repository is Apache-2.0. Phoenix
supports tracing, evaluations and experiments, but its current repository is
licensed under Elastic License 2.0 and documents opt-out telemetry.

Sources: [OpenInference repository](https://github.com/Arize-ai/openinference),
[OpenInference specification](https://arize-ai.github.io/openinference/spec/),
[Phoenix repository](https://github.com/Arize-ai/phoenix),
[Phoenix privacy documentation](https://arize.com/docs/phoenix/self-hosting/security/privacy).

### Ragas as a diagnostic adapter

Pilot only these mappings:

| Project layer | Candidate Ragas metrics | Required project control |
|---|---|---|
| Retrieval | context precision, context recall, context-entity recall, noise sensitivity | Lawyer-authored reference node/source IDs; report per route and source type, not one aggregate score |
| Compose | faithfulness, response relevancy, factual correctness | Every legal claim still needs deterministic citation resolution and lawyer review |
| Agent process | tool-call accuracy/F1, goal accuracy, topic adherence | Expected route/capsule/tool sequence must come from expert-labelled cases |

Do not use Ragas to score crisis routing, PII leakage, false legal citations,
resource validity, discriminatory language or the six safety red lines. Those require
deterministic checks and/or domain experts. Before accepting any Ragas metric, run a
calibration set with at least two experts, measure agreement and inspect failures by
Chinese language, route and risk stratum. Pin the Ragas version, judge model, metric
prompt and provider; set `RAGAS_DO_NOT_TRACK=true`.

Sources: [Ragas repository](https://github.com/vibrantlabsai/ragas),
[official metrics catalogue](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/).

### Promptfoo as the CI scenario runner

Adopt Promptfoo for:

- executing frozen JSONL/YAML cases against local, staging and candidate builds;
- matrix comparison of prompt/model/index versions;
- deterministic assertions on structured route, capsule, citation, fallback and
  safety outputs through a project-owned provider adapter;
- latency/token/cost budgets and regression thresholds;
- adversarial generation as a source of review-queue candidates, never as an
  automatically trusted release set;
- non-zero CI exit when any non-waivable release gate fails.

Keep authoritative scoring in project code. Promptfoo's generic red-team plugins do
not encode trauma-informed domestic-violence practice or current Chinese/Hong Kong
law. Generated attacks must be labelled `candidate`, reviewed, de-duplicated and
promoted to the golden set only through the HITL approval trail.

Sources: [Promptfoo repository](https://github.com/promptfoo/promptfoo),
[getting started](https://www.promptfoo.dev/docs/getting-started/),
[red-team documentation](https://www.promptfoo.dev/docs/red-team/),
[CI/CD documentation](https://www.promptfoo.dev/docs/integrations/ci-cd/).

## Corpora and benchmark findings

### CounselBench: pilot the rubric, block the download

CounselBench provides two datasets: 2,000 evaluations by 100 mental-health
professionals over 100 CounselChat questions/responses, and 120 professional-written
adversarial questions targeting six observed failure modes. The evaluation fields
cover overall quality, empathy, specificity, inappropriate medical advice, factual
consistency and toxicity. This is useful evidence for designing expert instructions,
judge explanations and disagreement analysis.

It is not a product-ready benchmark here: it is English, therapy-oriented and not
specific to domestic violence, Chinese law, GraphRAG, citations or crisis SOPs. More
importantly, the official repository has no license file and the linked Hugging Face
dataset page does not declare a license. Until the owner supplies applicable terms,
do not download, redistribute or commit the rows. The method and public schema may
inform a project-owned pilot; counsel must approve any later data use.

Sources: [official repository](https://github.com/llm-eval-mental-health/CounselBench),
[project page](https://llm-eval-mental-health.github.io/counselbench-2025/),
[CounselBench-Eval card](https://huggingface.co/datasets/izi-ano/CounselBench-Eval),
[CounselBench-Adv card](https://huggingface.co/datasets/izi-ano/CounselBench-Adv).

### CPsyCoun: Chinese multi-turn pilot with strict provenance controls

CPsyCoun is the closest listed corpus to the multi-turn psychological-support layer.
It offers 3,134 reconstructed multi-turn consultation dialogues (CPsyCounD), a
nine-topic evaluation set (CPsyCounE), and turn-by-turn evaluation of
comprehensiveness, professionalism, authenticity and privacy protection. Those
dimensions can be cross-walked to the local expert rubric's basic ability,
expression, richness and accessibility dimensions.

Pilot a small, stratified CPsyCounE/CPsyCounD sample only after attribution and
provenance review. Do not treat reconstructed responses as golden answers. Have
trauma-informed experts relabel cases for domestic-violence risk, user autonomy,
support-network discovery and unsafe confrontation. CPsyCounR is a separate report
dataset available only after a signed Privacy Data Protection Agreement; it is not
needed for the MVP and should not be requested.

Sources: [official repository and CC-BY-4.0 license](https://github.com/CAS-SIAT-XinHai/CPsyCoun),
[official paper](https://aclanthology.org/2024.findings-acl.830/),
[CPsyCounD card](https://huggingface.co/datasets/CAS-SIAT-XinHai/CPsyCoun),
[gated CPsyCounR card](https://huggingface.co/datasets/CAS-SIAT-XinHai/CPsyCounR).

### `harm-conversations`: crisis case seeds only

The HERALD card describes about 1,000 synthetic, English, three-turn conversations
across suicidal ideation, non-suicidal self-harm, harm to others, false positives and
benign content. Labels include severity 0 (no risk), 1 (follow-up) and 2 (immediate
risk). This is useful for drafting hard-negative, delayed-signal and escalation
fixtures.

The card itself warns against direct deployment without human oversight and against
evaluation without real-world validation. Generation used Qwen 3 235B, only seven
personas and automatic labels later enhanced by two experts. Use the task patterns,
not its score, and have bilingual crisis experts rewrite and approve every promoted
case. Access is gated and requires sharing contact information, so record the
acceptance identity and terms in the data manifest.

Source: [official Hugging Face dataset card](https://huggingface.co/datasets/mfarme/harm-conversations).

### Chinese legal benchmarks: component seeds, not legal-grounding gates

**LexEval** has 14,150 questions over 23 tasks organized into memorization,
understanding, logic inference, discrimination, generation and ethics. Its MIT
license and direct Hugging Face release make it the lowest-friction legal seed. Use
selected discrimination/ethics/generation cases for base-model preflight and to
draft adversarial legal-intent cases. Do not mix benchmark recall with GraphRAG
groundedness. Sources: [official repository](https://github.com/CSHaitao/LexEval),
[official dataset](https://huggingface.co/datasets/CSHaitao/LexEval).

**LegalAgentBench** is conceptually the best match to process evaluation: 300
annotated tasks, 37 tools, 17 corpora, multi-hop reasoning/writing and a process rate
based on intermediate steps. Pilot its expected-step representation and process
scoring against project-owned planner/retrieval traces. Do not vendor it yet: the
repository shows an MIT badge but no license file, the underlying corpora have mixed
terms, and external law tools may change. Sources:
[official repository](https://github.com/CSHaitao/LegalAgentBench),
[official ACL paper](https://aclanthology.org/2025.acl-long.116/).

**LawBench** covers 20 tasks under legal knowledge memorization, understanding and
application, including marriage-dispute identification and legal consultation. It
can seed deterministic component tests, but its own README states that it mixes
created and transformed datasets and users must follow each original creator's
license. Select per task; never bulk-import on the repository's Apache-2.0 license
alone. Sources: [official repository](https://github.com/open-compass/LawBench),
[official English README license notice](https://github.com/open-compass/LawBench/blob/main/README_EN.md#-licenses),
[official paper](https://aclanthology.org/2024.emnlp-main.452/).

**LAiW** defines 14 tasks across Basic Information Retrieval, Legal Foundation
Inference and Complex Legal Application. Legal article recommendation, case
understanding and consultation can seed retrieval and compose preflight tests. Its
reported F1/ROUGE/accuracy metrics are insufficient for safe user-facing responses,
and LED is reconstructed from many third-party public datasets. Apply per-task
license, legal-currency and jurisdiction review before selecting records. Sources:
[official repository](https://github.com/Dai-shen/LAiW),
[official dataset inventory](https://github.com/Dai-shen/LAiW/blob/main/data/README.md),
[official paper](https://aclanthology.org/2025.coling-main.716/).

## Data intake and download policy

Do not commit third-party corpora to this repository. Create a separate encrypted,
access-controlled evaluation bucket and an immutable manifest for each acquisition:

```yaml
dataset_id: cpsycoun-e-v1
source_url: https://github.com/CAS-SIAT-XinHai/CPsyCoun
source_revision: <commit-or-HF-revision>
sha256: <archive-hash>
license: CC-BY-4.0
accepted_terms_by: <reviewer-id-or-null>
approved_uses: [offline-eval-seed]
prohibited_uses: [production-context, model-training]
contains_sensitive_content: true
legal_review: <approval-id>
domain_review: <approval-id>
retention_until: <date>
```

Apply this staged intake:

1. **Metadata review:** pin official URL/revision, license, provenance, language,
   jurisdiction, PII/sensitive-content status and source dataset terms.
2. **Quarantine:** scan schema/content; do not expose rows to application RAG,
   production tracing or external judge APIs.
3. **Candidate conversion:** map only selected records into the project case schema;
   preserve the external ID and transformation history.
4. **Expert relabelling:** lawyer, trauma-informed counselor or crisis specialist
   supplies expected route, evidence, prohibited actions and rubric labels.
5. **Golden promotion:** a second authorized reviewer approves; record reviewer,
   timestamp, rubric/policy/source versions and the resulting case hash.

Initial download decision:

- Safe to pilot after ordinary dependency review: OpenInference, Ragas and Promptfoo.
- Phoenix requires ELv2 and security/privacy approval before deployment.
- CPsyCounD/E may enter quarantine after CC-BY attribution and domain approval.
- `harm-conversations` requires a named terms acceptance and may enter quarantine as
  safety seeds only.
- LexEval may enter quarantine as legal seeds after jurisdiction/currency review.
- LawBench and LAiW require per-task source-license manifests before any rows are
  fetched.
- CounselBench and LegalAgentBench data/code downloads remain blocked until their
  missing or ambiguous license terms are resolved.

## What these resources cannot prove

Passing any external benchmark does not prove that this product:

- catches all immediate danger, self-harm or harm-to-others signals in Chinese;
- avoids all six expert red lines;
- provides current, jurisdiction-correct family-violence law and resource details;
- preserves raw-PII leakage at zero across vendor payloads, logs and traces;
- retrieves the correct GraphRAG node, edge and source for each claim;
- respects user agency, accessibility constraints and trauma-informed practice;
- meets TTFT, total latency, token/cost and multi-turn continuity gates.

Those remain project-owned, versioned release tests. External resources improve
coverage and diagnosis; they cannot be used to waive safety, privacy, source validity
or unsupported-legal-claim failures.
