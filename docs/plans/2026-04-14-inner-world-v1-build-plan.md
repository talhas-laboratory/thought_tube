# Inner World v1 Build Plan

Date: 2026-04-14
Status: review
Owner: Inner World v1

## Purpose

Build the first usable version of Inner World v1 directly from the conversation artifacts and this chat.

This plan assumes:

- one product, not separate products per domain
- one core loop
- OpenClaw as substrate and wiring backend
- a personal social-style thought feed as the primary experience
- domain specialization through overlays for research, art, and entrepreneurship

## Source Artifacts

- `output/meta_observatory/.../session_synthesis.md`
- `output/meta_observatory/.../decision_attachments.md`
- `docs/plans/2026-04-13-inner-world-product-gap-log.md`
- `PRODUCT_THESIS.md`
- `product/inner_world_v1/CONTRACT.md`

## v1 Product Shape

Inner World v1 is a private cognitive layer that turns saved conversations, notes, and imports into a personal thought feed where each thought appears as a short post, expands into a longform explanation, and can be discussed in a thought-native chat.

Core loop:

1. Ingest source material.
2. Normalize it into source items.
3. Derive concepts, connections, and reasoning primitives.
4. Rank insight candidates by evidence, relevance, and surprise.
5. Surface thoughts as short post-like items in the feed.
6. Expand selected thoughts into detailed article views.
7. Let the user chat with a specific thought using routed context.
8. Save or delete the thought thread and learn from explicit feedback.

## Build Domains

- Product and UX
- OpenClaw Substrate
- Intake and Normalization
- Analysis and Ranking
- Delivery and Feedback
- Domain Overlays
- Trust and Governance
- Evaluation and Operations

## Optimal Slices

The slices are ordered to maximize proof of value early and avoid dead-end infrastructure work.

### Slice S1: Product Contract Lock

Primary domain: Product and UX

Goal:
Lock the user, job-to-be-done, output shape, and v1 boundaries before feature expansion.

Action items:

- S1.1 Lock the v1 user and job.
  Requirements:
  - primary user is a solo high-cognitive-load worker
  - v1 job is surfacing non-obvious, evidence-backed connections across saved material
  - product sentence is short and externally understandable
  Verification:
  - thesis and plan docs agree on user, job, and sentence
  - no conflicting v1 target user remains in active docs

- S1.2 Lock the insight contract.
  Requirements:
  - each surfaced thought must have a short-form post version and a longform article version
  - each surfaced insight must include title, what changed, source refs, reasoning primitive, surprise, confidence, evidence status, why now, next action, and feedback controls
  - insights that cannot satisfy the contract do not surface
  Verification:
  - contract doc is final
  - feed card, article view, and data schema enforce the fields

- S1.3 Lock v1 boundaries.
  Requirements:
  - no social/shared inner worlds
  - no autonomous web research by default
  - no graph-first primary UI
  - no real-time interruption by default
  Verification:
  - scope doc lists these as deferred
  - no active implementation task depends on deferred features

- S1.4 Lock the feed-native UI pattern.
  Requirements:
  - home view is a personal thought feed, not a dashboard
  - each thought appears in a tweet-like compact format first
  - expansion opens a substack-like article view
  - each expanded thought supports thought-native chat
  Verification:
  - UI spec and route map agree on feed, article, and chat surfaces
  - no conflicting dashboard-first UI remains in active docs

### Slice S2: OpenClaw Substrate Integration

Primary domain: OpenClaw Substrate

Goal:
Run Inner World inside the existing OpenClaw instance rather than as a separate stack.

Action items:

- S2.1 Define runtime placement in the existing OpenClaw workspace.
  Requirements:
  - Inner World has a clear home inside `/home/talha/.openclaw/workspace`
  - the miniapp, backend service, and product state paths are explicit
  - no duplicate second workspace is required
  Verification:
  - server layout doc exists
  - every component has a target path and runtime owner

- S2.2 Define OpenClaw gateway integration.
  Requirements:
  - gateway is used as transport/orchestration plumbing
  - Inner World does not replace gateway responsibilities
  - auth, local-only access, and service boundaries are explicit
  Verification:
  - integration doc specifies which components talk to port `18789`
  - request/response flow is documented

- S2.3 Define miniapp surface.
  Requirements:
  - v1 UI is a miniapp, not a separate product shell
  - the miniapp supports thought feed, longform article view, thought chat, source drill-down, save thread, delete thread, and feedback
  Verification:
  - route map exists
  - screen list is final for v1

### Slice S3: Intake and Source Normalization

Primary domain: Intake and Normalization

Goal:
Turn raw material into a clean, trustworthy source layer.

Action items:

- S3.1 Define supported v1 inputs.
  Requirements:
  - inputs are limited to conversations, markdown notes, and explicit imports
  - every input preserves raw source and source ref
  - unsupported inputs fail safely
  Verification:
  - input matrix exists
  - ingestion tests cover each supported type

- S3.2 Implement semantic chunking.
  Requirements:
  - source items are not only line-based
  - chunking respects headings, lists, paragraphs, and conversation turns
  - chunking remains deterministic and exportable
  Verification:
  - same source produces same chunk boundaries
  - chunk previews are inspectable

- S3.3 Add provenance guarantees.
  Requirements:
  - every source item stores source path, source type, and stable item id
  - raw artifacts are never mutated by downstream stages
  Verification:
  - idempotence tests pass
  - sampled source items can be traced to raw files

### Slice S4: Analysis and Insight Engine

Primary domain: Analysis and Ranking

Goal:
Produce grounded insight candidates that are good enough to surface.

Action items:

- S4.1 Improve concept and connection derivation.
  Requirements:
  - duplicate fragments are suppressed
  - cross-document links are preferred over same-document repetition
  - connection strength is explainable
  Verification:
  - repeated bullets do not dominate output
  - test corpus produces cross-document links

- S4.2 Add reasoning-primitives mapping.
  Requirements:
  - every surfaced insight maps to a reasoning primitive
  - primitive selection is overlay-aware
  - fallback primitive behavior is explicit
  Verification:
  - each batch item includes a primitive
  - overlay tests show different primitives for the same corpus shape

- S4.3 Separate ranking dimensions.
  Requirements:
  - ranking distinguishes evidence, novelty, usefulness, and surprise
  - grounded and speculative insights are separate classes
  - speculative items cannot outrank grounded items by default
  Verification:
  - score breakdown is inspectable
  - ranking tests enforce grounded-first behavior

- S4.4 Define evidence thresholds.
  Requirements:
  - a grounded insight threshold is explicit
  - unsupported claims are labeled speculative or withheld
  - contradiction handling does not silently flatten conflicts
  Verification:
  - threshold values are documented
  - negative tests confirm weak candidates do not surface as grounded

### Slice S5: Morning Batch and Archive

Primary domain: Delivery and Feedback

Goal:
Ship the core user-facing product loop through feed, article, and thought chat.

Action items:

- S5.1 Build thought feed generation.
  Requirements:
  - the feed presents compact post-like thoughts
  - the feed stays selective and quiet
  - high-confidence grounded items surface first
  - feed items satisfy the short-form contract
  Verification:
  - generated feed has no malformed items
  - feed ordering and compact rendering tests pass

- S5.2 Build longform article expansion.
  Requirements:
  - tapping or clicking a thought expands it into a substack-like article view
  - article view explains the short thought in detail
  - article view exposes source refs and reasoning details
  Verification:
  - article view loads from any thought
  - article detail contains inspectable evidence and reasoning data

- S5.3 Build thought-native chat.
  Requirements:
  - user can chat with a single thought from the article view
  - chat context is scoped to the thought, its source refs, relevant conversations, and reasoning primitives
  - system prompt and assistant character are built from that scoped context
  Verification:
  - context pack for thought chat is inspectable
  - chat responses stay on-topic to the selected thought

- S5.4 Build thread persistence controls.
  Requirements:
  - user can save a thought chat back into the same conceptual space
  - saved chat becomes new source material linked to the thought
  - user can delete a chat thread without damaging the original thought artifacts
  Verification:
  - save writes a new linked source artifact
  - delete removes the thread artifact only
  - source and thought provenance remain intact

- S5.5 Build archive and thread history.
  Requirements:
  - user can revisit older surfaced thoughts
  - user can revisit saved thought chats
  - surfaced thoughts, saved threads, and deleted threads have distinct states
  Verification:
  - archive view lists past thoughts
  - saved thought threads are discoverable from the thought they belong to

- S5.6 Build feedback actions.
  Requirements:
  - v1 feedback actions: `relevant`, `dismiss`, `revisit_later`
  - feedback changes future ranking
  - feedback does not mutate source artifacts
  Verification:
  - reranking tests pass
  - feedback event log is append-only

### Slice S6: Domain Overlays

Primary domain: Domain Overlays

Goal:
Keep one product core while making output feel domain-native.

Action items:

- S6.1 Research overlay.
  Requirements:
  - emphasizes mechanisms, contradictions, assumptions, and synthesis
  - surfaces evidence and uncertainty clearly
  Verification:
  - research fixture produces mechanism-oriented insights

- S6.2 Art overlay.
  Requirements:
  - emphasizes motifs, references, mood, material, composition, and direction
  - avoids pretending aesthetic judgments are objective facts
  Verification:
  - art fixture produces direction-oriented insights with softer evidence language where appropriate

- S6.3 Entrepreneurship overlay.
  Requirements:
  - emphasizes wedge, friction, retention, distribution, and strategic pattern detection
  - distinguishes observation from recommendation
  Verification:
  - entrepreneurship fixture produces decision-useful strategic insights

- S6.4 Cross-domain consistency.
  Requirements:
  - same core insight contract across all overlays
  - same core pipeline across all overlays
  - no domain forks in substrate logic
  Verification:
  - overlay tests reuse the same batch and feedback pipeline

### Slice S7: Trust, Quietness, and Export

Primary domain: Trust and Governance

Goal:
Make the product feel selective, transparent, and reversible.

Action items:

- S7.1 Add attention budget policy.
  Requirements:
  - explicit feed cadence rules
  - the thought feed stays quiet by default
  - low-value thoughts are withheld
  Verification:
  - policy doc exists
  - feed generator respects configured caps and ranking thresholds

- S7.2 Add explainability surfaces.
  Requirements:
  - every surfaced insight can answer "why am I seeing this?"
  - provenance and score breakdown are inspectable
  Verification:
  - drill-down exposes source refs and score factors

- S7.3 Add clean export.
  Requirements:
  - synthetic artifacts export to markdown/json
  - no lock-in to hidden graph-only state
  Verification:
  - export command produces complete human-readable state

### Slice S8: Evaluation and Ops

Primary domain: Evaluation and Operations

Goal:
Measure whether the product is getting smarter or just getting busier.

Action items:

- S8.1 Define north star and support metrics.
  Requirements:
  - north star is `weekly accepted high-value insights per active user`
  - support metrics include time to first accepted insight, false positive rate, revisit rate, action taken, week 4 retention, week 8 retention
  Verification:
  - metric spec exists
  - data needed for each metric is stored

- S8.2 Build evaluation fixtures.
  Requirements:
  - research, art, and entrepreneurship fixtures exist
  - each fixture has expected grounded and speculative examples
  Verification:
  - regression tests run on fixed corpora

- S8.3 Define deployment and recovery.
  Requirements:
  - runbook covers miniapp, service, gateway integration, and state storage
  - failure modes and recovery steps are explicit
  Verification:
  - deploy checklist exists
  - service restart and state recovery can be simulated locally

## Release Gates

Alpha is complete only when:

- OpenClaw-backed miniapp is running in the existing workspace
- user can ingest real material without losing provenance
- thought feed produces valid compact thought cards
- article expansion works
- thought chat works with scoped context
- save/delete thread behavior works
- feedback changes later ranking
- archive and drill-down work
- all three overlays run on the same core pipeline
- export is clean and reversible
- evaluation fixtures and regression tests are in place

## Immediate Build Order

1. S1 Product Contract Lock
2. S2 OpenClaw Substrate Integration
3. S3 Intake and Source Normalization
4. S4 Analysis and Insight Engine
5. S5 Feed, Article, and Thought Chat
6. S6 Domain Overlays
7. S7 Trust, Quietness, and Export
8. S8 Evaluation and Ops

## Non-Goals For This Plan

- collective or social inner worlds
- autonomous web research by default
- graph-first primary interface
- multimodal synesthesia as a shipping promise
- team collaboration features
