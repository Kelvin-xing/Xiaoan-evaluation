# Evaluation methods v3 implementation specification

Base: 66ea510. User request: implement the nine evaluation methods identified in the 2026-09-13 audit in both packages. No live external calls, deployment or fabricated human labels/results.

Acceptance:
1. Semantic oracle judgments bind stable R/F IDs to the exact oracle and answer. Validate complete unique IDs, verdict enums, quoted answer spans and uncertainty. Missing judgments remain unavailable; no exact-string matching masquerading as semantic task correctness. Integrate primary ordinary/matrix judge and reports.
2. Ranked retrieval computes precision/recall@k, reciprocal rank, AP/MAP@k and graded nDCG, with explicit judged universe and corpus/chunk/retriever/reranker metadata. Missing or unjudged candidates cannot be silently scored irrelevant. Expose batch CLI and pipeline summaries.
3. Pairwise CLI binds question/history/rubric and frozen same-condition answers, masks version IDs, counterbalances both orders, supports ties and order inconsistency, maps winners back to versions and reports case-cluster intervals.
4. Case-cluster bootstrap reports case macro statistics, paired differences, missing pairs and n; one case cannot produce a misleading confidence interval. Retain provider failures separately.
5. Verified tool/outcome evidence uses independent observer identity and before/after conditions, explicit authorization, outcome and side-effect assertions, and prerequisite partial order. Missing facts are unavailable; self-reported completion cannot pass.
6. Adversarial/metamorphic runner executes declared baseline/variant sessions using an injected harness, checks expected invariant/change assertions, preserves errors, supports isolation and retry/timeout/partial-success scenarios without fabricating telemetry.
7. Human calibration CLI accepts frozen disjoint calibration/held-out partitions with independent reviewer/adjudicator provenance; computes red-line confusion, dimension MAE, claim extraction recall and relation agreement with counts and intervals.
8. Online/shadow event analysis accepts pseudonymous session-level events with explicit assignment and observation completeness; reports task outcomes, appropriate handoff, exit success, failures, latency tails and cost. It does not claim real-world safety improvement or deploy traffic.
9. Both CLIs have executable synthetic examples, strict validation, report JSON/Markdown, docs with implemented versus real-data validation status, focused tests then full standalone regressions. Existing default cases stay unchanged; do not manufacture retrieval labels or oracle approvals. Public sync excludes credentials/runs/private traces.
