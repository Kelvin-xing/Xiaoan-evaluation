# XiaoAn Legal Mechanism Wiki Guidelines

## Purpose and authority

Read immutable sources and maintain a source-grounded legal mechanism graph.
This file and `content/knowledge/source/source-文件处理规范.md` are the persistent methodology:
keep them outside generated `content/knowledge/wiki/` so a new session can rebuild from
an empty wiki. The rebuild policy below supersedes historical schema counts,
type lists, and instructions copied into old generated pages.

```text
content/knowledge/source/           # user-owned, LLM read-only
        |
        v
content/knowledge/wiki/             # generated legal knowledge
        |-- nodes/          # necessary legal entities/concepts
        |-- edges.md        # sourced legal relationships
        |-- legal-mechanism-tree.md
```

Wiki extraction is independent of downstream consumers. Do not read, modify,
or preserve a graph shape to satisfy capsules, prompts, or runtime routing.
Downstream adaptation is a separate task, not a wiki acceptance criterion.
`content/knowledge/knowledge_strategy.md` is product background, not a competing
extraction schema. `content/knowledge/LLM_Wiki.md` describes the generic pattern; these
project-specific rules take precedence.

## Methodology references and adopted scope

These are references for how to organize and maintain knowledge, not legal
evidence for wiki claims. The operational rules are recorded here so rebuilding
does not depend on session memory or access to an external website.

| Reference | What XiaoAn adopts | What not to inherit |
| --- | --- | --- |
| [Andrej Karpathy, LLM Wiki](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f), also retained in `content/knowledge/LLM_Wiki.md` | Read-only sources; an LLM-maintained persistent wiki; Ingest / Query / Lint; cross-references, content index, and activity log. | Generic example page layers or entity counts are not required. Incremental maintenance is distinct from the explicitly requested empty-wiki rebuild. |
| [siyubian/legalwiki](https://github.com/siyubian/legalwiki), forked from CSlawyer1985/legalwiki | Organize legal knowledge by concepts, integrate material across documents, and connect related concepts with meaningful references. | Do not copy its corpus, legal conclusions, domain taxonomy, node counts, or website structure. Its published `build.py` / `scripts/rebuild.sh` build a site from existing concept Markdown; they are not XiaoAn's source-to-node generator. |
| [CSlawyer1985/china-lawyer-analyst](https://github.com/CSlawyer1985/china-lawyer-analyst), the separate legal-reasoning reference recorded in the original project history | Claim-basis analysis (请求权基础分析): identify claims, elements, defenses, and supporting evidence. | Do not confuse this with legalwiki, copy case-specific conclusions, or require every wiki page to reproduce a six-part case-analysis template. |

Apply the local minimal-modeling and citation rules when adapting these ideas.
External examples and model prior knowledge do not substitute for the current
source corpus. Do not silently add external legal material or modify sources.

## Layers and ownership

- `content/knowledge/source/`: immutable sources. Never edit, rename, normalize, or rewrite them unless the user explicitly authorizes source work. Preserve numbered filenames and `目录.md`.
- `content/knowledge/wiki/nodes/`: generated pages for independently useful legal concepts, with source-backed claims.
- `content/knowledge/wiki/edges.md`: generated edge catalog. Each edge identifies its source and target, relationship, claim, exact supporting source references, and review status.
- `content/knowledge/wiki/legal-mechanism-tree.md`: generated browsing entry point.
- `content/knowledge/wiki/source-registry.md`: generated current-source inventory, classification status, and per-source processing coverage.
- `content/knowledge/wiki/syntheses/`: cross-source comparisons only when necessary; do not create a separate page layer for every legal mechanism.
- `content/knowledge/index.md`: generated content catalog; synchronize it with the current graph.
- `content/knowledge/log.md`: append-only activity history. Record ingests, rebuilds, and reviews, but never treat old completion records as current acceptance.

Do not create source-summary pages under `content/knowledge/wiki/sources/` or generate
user-facing scripts, scenario capsules, or uncited action recommendations as
part of wiki work.

## Page and citation conventions

- Use Markdown with YAML frontmatter; prefer Chinese for domain knowledge.
- Use stable, lowercase, hyphenated filenames within the new graph.
- Each substantive claim must be traceable to an exact source excerpt. Map claims to references in the text, rather than attaching unrelated citations to the whole page.
- Node/synthesis `source_refs` must contain complete `knowledge/source/...md#heading/path` references. This is a stable logical namespace mapped by runtime code to `content/knowledge/source/`; do not prefix stored refs with `content/`. Each edge's source-reference column must identify the excerpt supporting that relationship.
- Bibliographic document listings belong in ordinary catalog text, not in `source_refs`; a document-only reference is not an extraction address.
- Distinguish source statements, legal interpretation, and uncertainty. Never smooth over a conflict or turn a tentative inference into a verified fact.
- New sourced claims start as `draft`; cross-source interpretations and unresolved issues start as `needs-review`. Do not mark work `reviewed` merely because a script passed.

Example node frontmatter, not a prescribed node kind for every page:

```yaml
---
type: legal-node
node_kind: element
title: ""
source_refs:
  - "knowledge/source/002-中华人民共和国反家庭暴力法.md#第四章 人身安全保护令/第二十三条"
updated: YYYY-MM-DD
status: draft
---
```

Other page roles include `legal-edge-catalog`, `legal-mechanism-tree`, and
`legal-synthesis`. These describe file roles, not a closed ontology of legal
entities. Select `node_kind` from the vocabulary justified by the new corpus.

## Content-driven schema (rebuild policy, 2026-09-07)

There is no fixed target, minimum, or maximum for node count, edge count, node
kinds, or relation types. Historical v0.4's 12 node kinds and 9 relation types
are neither quotas nor a closed whitelist. Do not recreate the old graph,
populate every old type, or invent entities to make a diagram look complete.
This freedom concerns graph modeling, not the separate A–K source classification.

### Create only necessary entities

- Start from the legal content and claim/element analysis, not article order or a list of nouns. One article need not become one node; multiple articles may support one concept.
- Before creating a node, check whether an existing node in the new graph, a paragraph, an attribute, a cited condition, or a comparison entry already expresses it accurately.
- Create a separate entity only when it is needed for independent legal reasoning, meaningful reuse, or a necessary sourced relationship. State that role clearly in the page.
- Do not create standalone nodes for every actor, document, province, definition, example, or procedural detail. A mention alone is not justification.
- Merge equivalent concepts across sources; preserve legally significant differences in jurisdiction, time, conditions, exceptions, and consequences. Sparsity is not permission to omit material law or conflate distinct elements.

### Separate retention, incorporation, and retrieval

Make these three decisions independently:

1. **Source retention** — keep a source when at least one trustworthy passage has
   unique legal, procedural, case, historical, or empirical value. A source is not
   a retirement candidate merely because it is general rather than
   domestic-violence-specific, non-binding, older, lower-authority, long, or
   substantially overlapping at document level. Before recommending retirement,
   identify the exact stronger passages that replace each potentially useful
   contribution. If provenance, completeness, or currentness is unresolved, retain
   the source as `needs-review` and do not present the uncertain passage as current.
2. **Wiki incorporation** — incorporate only net-new claims, qualifications,
   conflicts, examples, or observations. A retained source may legitimately produce
   no new node or edge. Record the sections reviewed and the reason for
   `covered-no-new-content`, `retained-reference-only`, or `needs-repair` in the
   source registry instead of inventing content to prove coverage.
3. **Runtime retrieval** — this is a downstream decision. Source retention and wiki
   incorporation do not make a whole document runtime-eligible. Retrieve only the
   smallest exact passages needed for the current question; do not delete sources or
   distort the graph merely to reduce prompt context.

### Use the smallest adequate relationship vocabulary

- Prefer fewer relation types. Reuse one precisely defined relation for the same meaning and direction; avoid synonyms, redundant inverse types, and source-specific or case-specific labels.
- Add an edge only for a meaningful source-supported relationship, not because two concepts share a topic or appear in the same document.
- Add a relation type only when the content requires a distinction that the current vocabulary or an edge's claim/conditions cannot express faithfully. Briefly explain the need and record its meaning and direction in `edges.md`.
- Record the actual node kinds and relation vocabulary for this rebuild in `edges.md`; document only types that are used. Reuse their meanings consistently across all batches.
- Labels from older schemas may be reused when they fit, but are not mandatory. Do not force a relation into an inaccurate old label or collapse every legal distinction into a vague "related to".
- If the legal relationship is uncertain, record the uncertainty with its sources for review. `needs-review` is not permission to fabricate an entity, edge, or type.

### Preserve legal-element reasoning (请求权基础分析)

Identify from the sources the right/remedy or legal consequence, its applicable
conditions and constitutive elements, relevant exceptions/defenses, and what
evidence can support each element. Do not infer missing elements from a
template or treat evidence as a guarantee of obtaining a remedy.

The reasoning pattern is:

```text
record-producing actor/procedure -> evidence -> element -> right/remedy
definition or scope condition -> meaning/applicability of the element
```

When these distinctions need explicit graph representation, labels such as
`provides_evidence_for`, `proves`, and `is_element_of` can express them. These
are examples, not required types or instructions to instantiate every box.
Keep essential element analysis in the claims even when a separate node is
unnecessary. A direct evidence-to-remedy shortcut must not erase the element
that the evidence actually supports.

## Source classification and references

- Follow `content/knowledge/source/source-文件处理规范.md`: sources use lawyer-confirmed `source_code` (A–K) and `source_tier` (A–F: 1, G–I: 2, J–K: 3). The old four-tier scale is retired.
- Source frontmatter is authoritative for confirmed metadata. Record missing or uncertain classifications explicitly; do not guess codes from filenames or copy retired registry tiers. Frontmatter `notes` are curation metadata rather than source evidence: honor their restrictions, but never cite them as source text or attribute them to the source issuer.
- Source files are flat under `content/knowledge/source/` with numbered filenames;
  classification lives in each file's `source_code`, not in the folder. `source_ref`
  paths are `knowledge/source/NNN-name.md#heading`. Agents must not re-code, move, or
  strip metadata without a new explicit decision. No `track` field is required.
- Before inventory or ingest, read `重建风险清单（持久化）` in
  `content/knowledge/source/source-文件处理规范.md`. Copy every unresolved risk ID,
  status, affected scope, and handling restriction into the fresh
  `source-registry.md`. GitHub issues and session history are supplementary only;
  they cannot be the sole location of a rebuild blocker.
- Use confirmed source authority, jurisdiction, temporal applicability, and scope when comparing claims. Record unresolved conflicts for review instead of silently choosing a result.
- NGO reports, channel directories, and other practice materials must not establish legal duties. They can supply clearly identified context where relevant; do not force them into a legal graph.
- Preserve numbered filenames and `目录.md`. Catalog files are for human completeness checks, not source excerpts.
- New references use exact Markdown heading paths; repeated titles are allowed under distinct parents. Validate with `wiki_update.py --strict-headings`. Default legacy compatibility is not new-wiki acceptance.

## Legal effect, source roles, and the core legal tree

`source_code` (A–K) is the input to modeling, not the whole story. Never conflate a
source's **binding effect** with its **role in a given node's reasoning**. Folder
layout carries neither (sources are flat); both are decided per claim from
`source_code` plus the cited text.

### Binding effect (per claim)

- `external` — binds the public: A constitution, B law, C administrative
  regulation, D local regulation, E rule.
- `adjudicative` — binds adjudication and attaches to the law it construes: F
  judicial interpretation. This is a separate axis, not "one rung below E".
- `institutional` — binds organs internally, not a formal external source of law: G
  multi-department opinions / normative documents, and the operational parts of I
  official practice manuals.
- `non_binding` — no binding force: H typical/reference cases (illustrative) and K
  (commentary, academic writing, monitoring, media). Guiding cases (指导性案例), if
  any, carry only a "should refer to" weight, not a statutory rule.
- International instruments: J treaties (canonical 068–071; legacy 70–73) are `international_obligation` with
  domestic applicability `requires_review` (a treaty obligation is not by itself a
  directly invocable domestic remedy); J declarations/platforms (canonical 072–073; legacy 74–75) are
  non-binding soft law.

`source_tier` only groups materials; do not read tier as a linear power ranking.

### One graph; every node is anchored in current law

There is a single graph. Every page under `wiki/nodes/` must center on a reusable
legal question whose core claim rests on at least one in-force A–F source with
`effect ∈ {external, adjudicative}`. Practice, commentary, cases, and empirical
findings may enrich that legal node, but may not form a node on their own.
Cross-source non-binding comparisons or observations belong in `wiki/syntheses/`
when a separate page is necessary.

### 六类 `source_roles`（受控词表）

Each node records which sources play which role in *that node's* argument. Only
these roles are allowed:

| 字段 | 中文含义 | 典型来源 | 效力 | 能否单独支撑节点 |
| --- | --- | --- | --- | --- |
| `legal_basis` | 法源／请求权基础：直接支撑法律规则、权利、义务、要件、程序或救济 | A–F | external / adjudicative | **可以；这是唯一承重角色** |
| `doctrinal_foundation` | 法理／学理渊源：解释规则的理论或历史背景 | K academic；K074（legacy K76）立法背景 | non_binding | 不可以 |
| `authoritative_commentary` | 权威解读：权威主体对法律的说明 | K074（legacy K76；法工委） | non_binding（高权重） | 不可以 |
| `institutional_implementation` | 机关实施：说明机关如何执行或落实规则 | G 意见；I 手册 | institutional | 不可以 |
| `case_application` | 案例适用：展示规则在具体案件中的认定和适用 | H；K080–082（legacy K82–84） | illustrative | 不可以 |
| `empirical_findings` | 实证观察：记录调研、统计或监测发现 | K083–084（legacy K85–86）；K085（legacy K88） | non_binding | 不可以 |

`doctrinal_foundation` sits **upstream in the explanation** (why a rule is framed as
it is) but stays **non-binding and below** the statute in effect: it explains a
legal claim, it never overrides one.

### Load-bearing invariant

- Only an in-force claim with `effect ∈ {external, adjudicative}` may occupy a
  node's `legal_basis`.
- Every legal node must have at least one valid `legal_basis`.
- A page supported only by G/H/I/J/K material cannot live under `wiki/nodes/`.
- Serialize this as `source_roles` on the node (role → list of `source#anchor`), on
  top of the full `source_refs` the script validates.

### Select sources and deduplicate at claim/case level

- Integrate by legal claim, mechanism, or case identity, never by document count.
  For each claim, choose the best primary support using binding effect and authority,
  proximity to the original, currentness, jurisdiction and scope match,
  completeness, and exact extractability. This is a per-claim choice; no source is
  globally primary for every proposition it mentions.
- Put an equivalent legal claim in one node. Put the same underlying case in one
  case node. To identify a case, compare docket number, court, date, parties, facts,
  requested remedy, and outcome; a similar anonymized name or topic alone is not
  enough. If identity remains uncertain, flag a possible overlap instead of merging.
- Use the strongest source for the rule, case facts, and disposition. Add a
  lower-authority source only for its distinct commentary, implementation detail,
  historical framing, critique, or aggregate finding, under the correct
  `source_roles` entry. Lower authority is not a reason to discard a genuinely
  unique contribution.
- If a secondary source merely restates what the primary source already supports,
  record that it was reviewed but do not create another node, duplicate the case, or
  add a redundant citation. If it contradicts the primary source or adds a material
  perspective, preserve that difference with explicit attribution and review status.
- A newer report does not automatically supersede an older report. Compare their
  time windows, sectors, samples, methods, and findings, and retain each report's
  non-overlapping contribution.

Current-corpus applications:

- Canonical 084 repeats the 谌某某、邱某某、彭某某 matters published in canonical
  059. Build only one node for each case. Use 059 for the official case facts,
  disposition, and legal application; cite 084 only for a distinct NGO monitoring
  observation under `empirical_findings`. A restatement in 084 is coverage, not a
  second case node.
- Canonical 084 does not replace 083 merely because it is newer: 083 retains
  non-overlapping sectors and examples. Compare and extract their net additions.
- Canonical 058 has been human-verified as a 2002 excerpt of
  公通字〔2002〕13号《公安派出所执勤规范》. Its general dispatch,
  report-taking, emergency-handling, and recording passages may be retained only as
  explicitly historical `institutional_implementation`; they are not proof of
  current procedure and must never serve as `legal_basis`.
- Canonical 063 is an incomplete excerpt of the 2020 legal-aid service guideline.
  Keep its four intact provisions as `institutional_implementation` after provenance
  verification; never infer omitted provisions or treat the fragment as the complete
  guideline.
- Canonical 066 is a 2021 local women's federation manual. Retain its distinct
  intake, autonomy, privacy-exception, service-planning, resource-linking, and
  follow-up workflow as local `institutional_implementation`; do not duplicate the
  national manual that its omitted second section merely points to.
- Canonical 075 is an attributed expert news summary. Use only a genuinely distinct,
  attributed expert interpretation as non-binding commentary; statutory
  restatements already supported by 002/074/077 do not create nodes or citations.
- Canonical 076 is a contemporaneous first-person account by the then national
  women's federation leader of that institution's participation in the legislative
  process. Keep only its attributable institutional-history passages as
  `doctrinal_foundation`; do not create current legal rules from its promotional
  framing, future work plans, or statutory restatements.
- Canonical 079 is a secondary theory/comparative-law chapter. Retain it as
  `doctrinal_foundation` only where cited claims can be traced and remain accurate;
  unsupported statistics, factual errors, and outdated comparative claims are
  `needs-review` and must not enter nodes or retrieval.
- Canonical 081 contains four secondary case narratives. Use only traceable,
  non-duplicative facts as `case_application`; if an official or primary source
  covers the same case, it becomes primary and this source contributes only distinct
  attributed analysis.
- Canonical 082 is a long secondary case commentary with unique local intervention
  histories but extensive old law, OCR damage, untraceable facts, and harmful
  victim-blaming passages. Retain it as `needs-review`; only independently verified
  unique facts or mechanisms may become `case_application`. Never ingest or retrieve
  victim-blaming, obsolete-law advice, or unsupported legal conclusions.
- Canonical 086 is the current 2025 amended text of the Jiangsu anti-domestic-
  violence regulation. Its explicit sexual-violence and economic-control definitions
  are `legal_basis` only for conduct within Jiangsu while that text is effective;
  never restate them as the nationwide definition.

### How non-binding material attaches (two forms only)

Covering a source does not require a node. Attach it to the law claim it serves:

- **Form A — a role block inside an existing legal node** (most practice/K): the
  source becomes a sourced paragraph under a role heading; it is neither a new node
  nor an edge. Example: G048's (legacy G49) inter-agency handling becomes an
  `institutional_implementation` block under the protection-order node.
- **Form B — a synthesis page**: use this only when several sources must be compared
  across jurisdictions, time periods, methods, or institutions. A synthesis is not a
  legal node and must state that its non-binding material does not create a rule.

Do not create a practice-only node or an edge merely to make a non-binding source
appear in the graph. Practice, commentary, cases, and findings never rewrite a law
claim.

### Conflicts and supersession (立法法 98–103)

Between two in-force binding claims: (1) hierarchy (constitution > law >
administrative regulation > local regulation > lower rule); (2) at the same rank,
special over general and newer over older; (3) genuinely un-orderable conflicts —
e.g. a local regulation vs a department rule — are recorded as pending conflicts for
human/authority decision, not auto-resolved. Superseded claims are kept as
historical context, not deleted and not used to answer.

### No routine currency field

The corpus is curated to current versions, so a per-file currency flag is noise.
The residual risk is K/commentary naming a repealed instrument (e.g. the Marriage
Law). Handle it point-wise: `legal_basis` may cite only in-force A–F already in the
corpus, and where a passage names superseded law, add a single `superseded_by →
current provision` note at that spot. No corpus-wide field.

### K074 / legacy K76 (legislative-body reading)

Canonical source 074 (legacy 76) — the NPC Standing Committee Legislative Affairs Commission social-law
office reading of the Anti-Domestic-Violence Law — stays K/3. Formal statutory
interpretation power belongs to the NPC Standing Committee (立法法 art. 48); this
解读 is written by staff who drafted the law, so it is non-binding but a high-weight
`authoritative_commentary`. Use it to explain legislative intent and term meaning
and to surface candidate nodes; do not let it create rights/duties the statute
omits, override later law or interpretation, or stand alone as a citizen-facing
legal conclusion. Statute text it reprints defers to canonical source 002 (legacy 02); its 条文解读
attaches as commentary to the relevant article node; legislative history / 审议意见
belongs to a legislative-history layer.

## Full rebuild from replaced sources

A full rebuild starts from an empty generated wiki and the current source
corpus. It is not incremental repair of the old graph. If old output is still
present, confirm its removal separately; changing these instructions alone
does not authorize deletion.

1. Read this file and the source guide first. Do not use old nodes, edges, syntheses, schema copies, index, registry, or logs as facts, schema constraints, or a checklist of entities to recreate. Retain only the extraction methodology.
2. Inventory the current source files, their hashes, classification status, and section structure. Compare with `目录.md`; report missing or unreadable material. Load the persistent source-risk list into the new registry before extracting claims. Do not modify source text to make checks pass.
3. Initialize fresh processing records in the new `source-registry.md`. Do not inherit old `done`, `reviewed`, or source-manifest acceptance. Recreate the content index; retain any historical activity log only as history.
4. Read sources one at a time and long documents section by section. Extract candidate claims, legal elements, and case-identity signals; compare them across the processed corpus, select claim-level primary support, and reuse/merge within the newly built graph before adding nodes or edges. Preserve cross-source distinctions and conflicts.
5. Record each source's coverage: relevant sections processed, resulting nodes/edges, net-new supporting material, or a reason no content was incorporated. Distinguish `covered-no-new-content`, `retained-reference-only`, and `needs-repair`; log section-level progress so another session can resume this rebuild without guessing.
6. Generate the new node pages, edge catalog, browsing root, and index from the new corpus. Old node IDs, counts, topology, and types impose no constraint. Keep actual type definitions and graph links consistent.
7. Perform the acceptance checks below. Only after reference, coverage, and content review should the new source manifest be accepted. Do not equate generated files with a completed, legally reviewed wiki.

## Acceptance for a rebuilt wiki

| Check | Required evidence |
| --- | --- |
| Source integrity | The final inventory and hashes match the rebuild's starting source snapshot; numbering and catalogs are unchanged. Empty or incomplete input is reported, not accepted as a successful rebuild. |
| Coverage | Every source has a processing outcome or an explicit unresolved issue; long documents have section coverage. Exclusion requires a reason, not an invented node to make coverage look complete. |
| Risk propagation | Every open persistent source-risk ID appears in `source-registry.md` with the same affected scope and handling restriction. Blocked passages do not support nodes, edges, syntheses, or runtime retrieval. |
| Exact citations | All declared excerpt references resolve uniquely in strict mode and contain the intended section without adjacent-section leakage. Check edge references as well as node references. |
| Graph consistency | Edge endpoints and internal links exist; node relations and the edge catalog agree; labels match the vocabulary actually used in this rebuild, not the old schema. |
| Minimal modeling | No duplicate concepts, redundant relation labels, or unjustified standalone entities. Do not add an edge solely to hide an isolated node; useful sourced nodes need not all be connected. |
| Cross-source deduplication | Equivalent claims and identical cases are integrated once; primary support is selected per claim, and secondary sources contribute only distinct, attributed material under the correct role. Possible rather than proven overlaps remain flagged for review. |
| Legal support | Review each substantive claim and relationship against its cited text: legal elements, evidence, conditions, exceptions, "may" versus "must", jurisdiction, and time. Citation existence alone is insufficient. |
| Load-bearing basis | Every node has at least one in-force `legal_basis` from A–F. G/H/I/J/K appear only as `source_roles` blocks or synthesis material, never as a node's sole support. |
| Clean rebuild | No inherited old conclusions, broken old paths, or unverified approval/completion states. Important unresolved legal judgments are listed for human review and not presented as verified. |

The agent checks every claim against its evidence; material legal judgments,
conflicts, and uncertainties require qualified human review. Report separately
what passed structural checks and what still needs legal review.

The existing script detects source changes and reference-resolution errors;
it does not generate the wiki or automatically verify all coverage, edge
semantics, graph consistency, or legal entailment. Perform and report the other
checks explicitly; do not claim nonexistent automated validation.
Its affected-page list follows discovered direct source references, not every
semantic dependency. Check relationship citations and related claims separately;
an empty affected-page list does not establish that a new source has no impact.

```bash
.venv/bin/python tech/chatflow/poc/wiki_update.py --strict-headings
```

Source drift is expected before accepting a replaced corpus. Resolve broken
references and review the inventory and content first. Only then:

```bash
.venv/bin/python tech/chatflow/poc/wiki_update.py --strict-headings --write-manifest
.venv/bin/python tech/chatflow/poc/wiki_update.py --strict-headings --fail-on-drift
```

The final command must succeed, but that success does not replace the other
acceptance checks. Never delete citations, ignore unread sections, or accept
a manifest merely to hide failures.

## Incremental ingest after a rebuild

This mode updates an accepted current wiki; it is not a full rebuild. Apply the
same minimal-modeling, citation, and review rules. Reusing the current graph here
does not authorize inheriting old output during a full rebuild.

1. Compare current source hashes with the last accepted manifest. Distinguish added, modified, deleted, and renamed/moved sources; a detected delete/add pair is not automatically a substantive legal change.
2. For additions, read the new source and search current concepts and claims it may support, qualify, or contradict. No existing citation can be assumed, so direct-reference lookup alone is insufficient.
3. For modifications, use direct references to find initial candidates, then inspect the changed text, affected claims, and dependent relationships. Check whether a change affects legal meaning, applicability, or only paths/heading anchors.
4. For deletions, identify which claims lose support and check their remaining sources. Do not delete every referencing node: retain still-supported claims and remove, revise, or flag only unsupported parts and affected edges.
5. Reuse or merge current concepts before creating new ones. Synchronize node relationships, the edge catalog, browsing root, index, and source coverage records; append a log entry explaining material changes and unresolved issues.
6. Review the diff and repeat the acceptance checks. Do not advance the accepted manifest for a partial or failed update. Keep unverified changes distinguishable from legally reviewed content.

## Automation boundary and resumable draft workflow

The intended first automation level is a manually triggered, resumable draft
update, not unattended legal approval or publication. Source-change detection,
direct-reference lookup, and strict heading checks exist today; an end-to-end
job that invokes the agent and coordinates all wiki edits is not implemented.
A skill can describe repeatable steps, but is not itself a scheduler or validator.

When carrying out or implementing an update task:

- Make the mode explicit: empty-wiki rebuild or incremental update. Never infer permission to erase an existing wiki from a request to update sources.
- Work in an isolated branch/worktree with source files read-only. Process bounded source/section batches, then integrate and deduplicate their claims; do not have parallel writers independently overwrite shared nodes or `edges.md`.
- Record progress in the current registry/log: task mode, source snapshot, processed sections, changed pages, pending work, and errors. On resume, verify the snapshot and completed writes before continuing; do not duplicate nodes or assume partial work completed.
- If a source changes during the run, stop to reassess the affected work instead of mixing snapshots or accepting a stale manifest. Report failures explicitly and retain resumable progress.
- Produce a draft diff, source/section coverage results, validation results, and unresolved legal-review items. The agent performs claim-to-source checks; legal judgments and uncertainties still require qualified human review.
- Do not automatically mark content `reviewed`, accept the source manifest, push a branch, create/update a PR, or publish comments. Remote actions require Siyu's explicit confirmation; manifest acceptance follows the review steps above.

## Graph representation

- Legal mechanisms are sourced edges, not a separate page layer.
- Express graph links using Obsidian-style links such as `[[domestic-violence-definition]]` in node pages.
- Graph edges are represented by node-to-node `wikilink` entries in each node's `## 机制关系` section. Every catalog edge must have a corresponding link, with matching direction and relationship semantics.
- `edges.md` and `source-registry.md` reference nodes/sources as plain inline code, not `wikilinks`, so catalogs do not become graph hubs.
- Node pages reference the catalog as plain `edges.md`, not `[[edges]]`.
- For a pure node-only Obsidian view, use `path:nodes`. Native graph edges are unlabeled; their legal meaning remains in the node entries and edge catalog.

## Query and maintenance

1. Read the current `content/knowledge/index.md`, then relevant nodes and relationships.
2. Answer with source-grounded synthesis and distinguish uncertainty.
3. If a query produces durable legal knowledge, verify its sources before updating the graph and log; do not create user-facing product content by default.
4. Periodically check coverage gaps, stale claims, duplicates, invalid links, and overstated relationships using the acceptance criteria above.

## Safety and legal boundaries

- In live user support, immediate danger takes priority over legal completeness; this does not define the extraction graph's shape.
- Never invent institutions, hotline numbers, shelter addresses, case law, or local procedures.
- Do not promise police handling, court approval, or other individual outcomes.
- Frame individual legal strategy as rights education and suggest professional legal aid when needed.
- Preserve privacy: do not store raw user PII in wiki pages or examples.
