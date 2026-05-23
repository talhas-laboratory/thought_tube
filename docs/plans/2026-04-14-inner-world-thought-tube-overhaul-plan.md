# Inner World x Thought Tube Overhaul Plan

## Purpose

This plan replaces the current `feed-first` Inner World implementation with a
`vault -> meta-layer -> reasoning pipelines -> judged thoughts` architecture.

The goal is not to copy Thought Tube literally.

The goal is to combine:

- Inner World's output surface
  - tweet-like thoughts
  - article expansion
  - scoped chat
- Thought Tube's deeper internal discipline
  - meta-layer extraction
  - explicit reasoning stages
  - fidelity checks
  - genericity checks
  - contradiction handling
  - review gates

## Recommended approach

### Option A — incremental patching

Keep the current insight pipeline and patch in better ranking, better prompts,
and more graph metadata.

Pros:
- fastest short-term
- least migration work

Cons:
- preserves the wrong center
- keeps feed generation too close to raw chunk overlap
- makes future reasoning layers harder to untangle

### Option B — full rewrite from scratch

Throw away the current Inner World product runtime and rebuild around a new
meta-layer and pipeline engine.

Pros:
- cleanest architecture
- easiest conceptual reset

Cons:
- wastes working OpenClaw integration, miniapp, storage, and thread surfaces
- higher delivery risk

### Option C — substrate-preserving overhaul

Keep the existing Conversation OS, OpenClaw packaging, miniapp shell, thread
surface, and file-based persistence model, but replace the product core with a
vault/meta-layer/pipeline architecture.

Pros:
- keeps the useful infrastructure
- replaces the weak reasoning center
- clean migration path

Cons:
- requires a staged refactor
- temporary dual-model period while migrations land

### Recommendation

Choose Option C.

It preserves what already works:

- local file truth
- session capture
- task-pack continuity
- OpenClaw miniapp delivery
- thought/article/thread UI shell

And it replaces what is currently too shallow:

- chunk-first ingestion
- lexical bridge generation
- direct promotion into feed items

## Current system diagnosis

### What exists now

- `models.py`
  - session/context/task-pack objects
  - insight and thought-feed objects
- `product_inner_world.py`
  - source ingestion
  - chunking
  - overlap-based graph derivation
  - thought/feed/article/thread generation
- `miniapp.py`
  - local/OpenClaw HTTP API
- `miniapp/`
  - feed/article/chat UI
- OpenClaw bundle packaging

### What is wrong with the current center

- The system is still built around `source items -> connections -> surfaced thoughts`.
- The meta-layer is too thin.
- Thought quality depends too much on lexical overlap.
- Weak candidate connections can become feed outputs too early.
- There is no real review queue or promotion gate.
- Chat context is better than before, but still not driven by a formal reasoning packet.

## New target model

The system should work like this:

1. User grants access to a vault.
2. The system builds a source registry and chunk index.
3. The system builds a deep meta-layer over the vault.
4. Reasoning pipelines operate over that layer.
5. A judgment layer decides whether a found connection deserves surfacing.
6. The output layer turns approved results into:
   - short thoughts
   - article expansions
   - scoped threads

## Canonical terminology

Use this vocabulary for the overhauled system:

- `Vault`
- `Source Registry`
- `Chunk Index`
- `Meta-layer`
- `Knowledge Layer`
- `Reasoning Pipeline`
- `Review Queue`
- `Thought`
- `Expansion`
- `Thread`

Avoid making user-facing terminology depend on:

- `insight candidate`
- `surfaced insight`
- `concept node`

Those can survive temporarily as migration terms if needed, but they should not
remain the main product language.

## What to keep unchanged

These parts are already useful and should remain:

- Conversation OS event/session capture
- task packs and continuity artifacts
- local JSON/JSONL/Markdown source-of-truth storage
- OpenClaw miniapp packaging and hosting path
- pluggable thought-chat backend
- current UI shell idea:
  - feed
  - expansion
  - thread

## System overhaul by module

## 1. Vault access and ingestion

### Current state

- Inputs are manually seeded into `source_items.jsonl`.
- Ingestion is file-oriented but still product-local and simplistic.

### Adjustment

Replace ad hoc product seeding with a real vault-ingest layer.

### Adjust

- `src/conversation_os/product_inner_world.py`
  - remove responsibility for being the only ingestion surface

### Add

- `src/conversation_os/vault_ingest.py`
  - vault adapter interface
- `src/conversation_os/vault_adapters/openclaw_conversations.py`
  - first real adapter
- `product/inner_world_v1/data/source_registry.jsonl`
- `product/inner_world_v1/data/chunk_index.jsonl`

### Requirements

- Can point at OpenClaw conversation exports or captured conversation artifacts.
- Produces stable source IDs and chunk IDs.
- Preserves source provenance and timestamps.
- Re-ingesting same source is deterministic.

### Verification

- Re-running ingest does not duplicate unchanged sources.
- Each chunk points back to one source document.
- Source registry can report counts by source family and sensitivity tier.

## 2. Meta-layer extraction

### Current state

- The system extracts concepts and reasoning primitives shallowly.
- Important meta fields like tensions, interpretations, and review items do not
  exist as first-class product state.

### Adjustment

Build a dedicated meta-layer extraction pipeline modeled on the Thought Tube
field contracts.

### Add

- `src/conversation_os/meta_layer.py`
- `src/conversation_os/meta_objects.py`
- `product/inner_world_v1/data/meta_layer/`
  - `signal_frames.jsonl`
  - `interpretations.jsonl`
  - `tensions.jsonl`
  - `shared_primitives.jsonl`
  - `adjacent_concepts.jsonl`
  - `transfer_targets.jsonl`
  - `why_it_matters_frames.jsonl`
  - `review_items.jsonl`
  - `contradictions.jsonl`

### Requirements

- Every processed source chunk can yield zero or more meta objects.
- Meta objects must preserve evidence refs.
- Every meta object must declare a status:
  - `stable`
  - `provisional`
  - `speculative`
- The system must extract:
  - patterns
  - themes
  - tensions
  - discussions
  - directions
  - unresolved questions
  - guardrails
  - contradictions

### Verification

- Sample vault runs produce populated meta-layer files.
- Every meta object has evidence refs and confidence.
- Contradiction objects are generated only when evidence exists on both sides.

## 3. Knowledge layer

### Current state

- `concept_nodes.json` and `connections.json` are too flat.
- The graph is mostly a derived similarity surface.

### Adjustment

Replace the flat graph with a typed knowledge layer backed by canonical files.

### Adjust

- `product/inner_world_v1/data/concept_nodes.json`
- `product/inner_world_v1/data/connections.json`

### Add

- `src/conversation_os/knowledge_layer.py`
- `product/inner_world_v1/data/knowledge_nodes.jsonl`
- `product/inner_world_v1/data/knowledge_edges.jsonl`

### Node kinds

- `source`
- `chunk`
- `pattern`
- `theme`
- `discussion`
- `direction`
- `tension`
- `decision`
- `guardrail`
- `question`
- `contradiction`
- `thought`
- `thread`

### Edge kinds

- `derived_from`
- `relates_to`
- `supports`
- `contradicts`
- `expands`
- `appears_in`
- `reframes`
- `transfers_to`
- `requires_review`

### Requirements

- Graph is typed and evidence-backed.
- Raw source is never stored only in the graph.
- Graph nodes are reconstructable from canonical files.

### Verification

- Node and edge files rebuild deterministically from meta-layer outputs.
- Every edge stores evidence refs or upstream meta refs.
- Contradiction edges are queryable separately from general relation edges.

## 4. Reasoning pipeline engine

### Current state

- The main logic is still one blended flow in `product_inner_world.py`.

### Adjustment

Split reasoning into explicit pipelines and operators.

### Add

- `src/conversation_os/pipelines.py`
- `src/conversation_os/operators.py`
- `src/conversation_os/pipeline_runner.py`
- `product/inner_world_v1/pipelines/`
  - `vault_decomposition_v1.json`
  - `cross_pollination_v1.json`
  - `thought_surfacing_v1.json`

### First pipelines

1. `vault_decomposition_v1`
   - normalize
   - infer context
   - clarify meaning
   - separate layers
   - detect shared primitives
   - build why-it-matters

2. `cross_pollination_v1`
   - select candidate node pairs or clusters
   - detect deeper shared primitive
   - detect tension or contradiction
   - assess transfer value
   - draft thought candidate

3. `thought_surfacing_v1`
   - fidelity check
   - genericity filter
   - confidence calibration
   - relevance check
   - review gate

### Requirements

- Pipelines are declarative and traceable.
- Operators have stable contracts.
- Pipeline runs emit append-only traces.

### Verification

- Each pipeline run writes:
  - `run_packet.json`
  - `trace.json`
  - `review.json`
- Failed or low-confidence runs stop at review rather than surfacing.

## 5. Judgment and review layer

### Current state

- Thoughts go too directly from candidate generation into the feed.

### Adjustment

Add a formal review queue and promotion gate.

### Add

- `src/conversation_os/review_queue.py`
- `src/conversation_os/judgment.py`
- `product/inner_world_v1/data/review_queue.jsonl`
- `product/inner_world_v1/data/promotion_packets.jsonl`

### Review statuses

- `ready_for_review`
- `approved_for_surface`
- `needs_human_review`
- `insufficient_quality`
- `dismissed`

### Requirements

- Weak connections never auto-surface as if they were mature.
- Judgment must include:
  - fidelity
  - genericity
  - confidence
  - novelty
  - relevance
- Promotion into feed is explicit.

### Verification

- A low-confidence candidate lands in review queue, not the feed.
- Generic or vague outputs fail the genericity gate.
- Review actions can approve, dismiss, or defer a candidate.

## 6. Thought generation layer

### Current state

- Thought posts are generated too early in the pipeline.
- Article generation is downstream of weak structure.

### Adjustment

Generate thoughts only from approved connection packets.

### Adjust

- `src/conversation_os/product_inner_world.py`
  - narrow responsibility to orchestration and output materialization

### Add

- `src/conversation_os/thought_factory.py`
- `product/inner_world_v1/data/thought_packets.jsonl`

### Requirements

- Every thought must come from an approved reasoning packet.
- Every article must cite both sides of the connection and the meta-layer that
  justifies the jump.
- Thought copy must be engaging but non-generic.

### Verification

- Every thought has a backing packet.
- Every article shows:
  - what is being connected
  - why the connection matters
  - evidence from both sides
  - what remains uncertain

## 7. Thread and context layer

### Current state

- Thread context is better than before, but still assembled too loosely.

### Adjustment

Make thought chat run from a formal context packet.

### Adjust

- `src/conversation_os/chat_backends.py`
- `src/conversation_os/miniapp.py`

### Add

- `src/conversation_os/thread_context.py`
- `product/inner_world_v1/data/thread_packets.jsonl`

### Thread packet contents

- thought text
- article expansion
- source refs
- connected meta-layer nodes
- tensions
- contradictions
- why-it-matters frames
- unresolved questions
- recent thread history

### Requirements

- Chat stays bounded to the selected thought packet.
- Saving a thread creates new structured material in the vault.
- Deleting a thread removes the thread artifact without harming source truth.

### Verification

- Saved threads create append-only derived artifacts.
- Deleted threads do not remove source material.
- Thought chat references packet context rather than generic neighboring text.

## 8. UI overhaul

### Current state

- The feed shell is directionally right.
- The underlying states behind it are still wrong.

### Adjustment

Keep the user-facing shape, but wire it to the new reviewable system state.

### Adjust

- `product/inner_world_v1/miniapp/index.html`
- `product/inner_world_v1/miniapp/app.js`
- `product/inner_world_v1/miniapp/styles.css`

### UI surfaces after overhaul

- `Feed`
  - approved thoughts only
- `Expansion`
  - article view for one approved thought
- `Thread`
  - scoped chat
- `Review`
  - pending but interesting candidates
- `Source`
  - vault fragment and related meta-layer

### Requirements

- Feed feels like self-social media.
- Review surface remains calm and low-noise.
- Source drill-down exposes evidence and meta-layer, not only raw text.

### Verification

- Feed contains no unreviewed weak candidates.
- Review queue items are clearly labeled as provisional.
- Source drawer shows both raw source and meta interpretation.

## 9. Policy and personalization

### Current state

- Feedback mostly reranks feed items.

### Adjustment

Promote feedback into a policy layer.

### Add

- `src/conversation_os/policy_engine.py`
- `product/inner_world_v1/data/policy_snapshot.json`
- `product/inner_world_v1/data/feedback_events.jsonl`

### High-signal behaviors

- keep
- dismiss
- revisit
- rewrite
- connect
- save thread
- ignore over time

### Requirements

- Policy affects routing, thresholds, and ranking.
- Policy does not silently rewrite source truth.

### Verification

- Repeated dismissals reduce similar future surfacing.
- Repeated saves or revisits boost related patterns.

## 10. OpenClaw integration

### Current state

- OpenClaw is currently mostly a chat backend and miniapp host.

### Adjustment

Make OpenClaw conversations the first-class input vault and keep the miniapp
host path.

### Adjust

- `src/conversation_os/openclaw_miniapp.py`
- `src/conversation_os/cli.py`

### Add

- `src/conversation_os/vault_adapters/openclaw_sessions.py`
- `src/conversation_os/services/openclaw_sync.py`

### Requirements

- Can ingest OpenClaw conversation artifacts and session logs.
- Can re-sync incrementally.
- Keeps local-first derived state inside this repo.

### Verification

- Running sync updates source registry without destroying prior derived artifacts.
- Incremental sync only adds or updates changed conversation artifacts.

## 11. Observability and logging

### Current state

- We export feed and state, but reasoning traces are not first-class enough.

### Adjustment

Add append-only meta logging and per-pipeline traces.

### Add

- `product/inner_world_v1/meta_logs/meta_log.jsonl`
- `product/inner_world_v1/runs/`

### Requirements

- Every pipeline run is replayable.
- Every promoted thought can be traced back to:
  - source refs
  - meta-layer
  - pipeline run
  - judgment outcome

### Verification

- A surfaced thought can be traced end to end from feed card to vault evidence.

## 12. Testing and migration

### Adjustment

Build the overhaul in layers with compatibility shims, then remove old objects.

### Add

- migration scripts for current `source_items`, `concept_nodes`, `connections`,
  and `thought_feed`
- new tests covering:
  - vault ingest
  - meta-layer extraction
  - contradiction generation
  - pipeline traces
  - review queue promotion
  - thought packet generation
  - thread packet generation

### Requirements

- No silent data loss.
- Old feed can coexist temporarily while new pipeline is validated.

### Verification

- Migration produces equivalent or better outputs from existing corpus.
- Tests prove no source truth mutation.

## Execution order

### Phase 1 — Replace the data model

- add source registry
- add chunk index
- add meta-layer storage
- add typed knowledge layer

### Phase 2 — Replace the reasoning core

- add operators
- add pipelines
- add run packets and traces
- add judgment and review queue

### Phase 3 — Rebuild surfacing

- add thought packets
- rebuild feed generation
- rebuild article expansion
- rebuild thread packets

### Phase 4 — Reconnect OpenClaw

- add OpenClaw conversation vault adapter
- add incremental sync
- rebuild miniapp API around new objects

### Phase 5 — Remove the old center

- deprecate flat concept-node and connection-first logic
- deprecate direct surfaced-insight pipeline
- keep compatibility exports only where still useful

## Definition of done

The overhaul is done when:

- the user can point Inner World at OpenClaw conversations as a vault
- the system builds a rich meta-layer over that vault
- reasoning pipelines find cross-vault connections using the meta-layer
- weak candidates go to review, not directly to feed
- approved candidates generate compelling short thoughts and solid articles
- thought chat runs from bounded thought packets
- saved threads feed back into the vault as structured derived artifacts
- every surfaced thought is traceable back to source evidence and pipeline steps

## First build slice after approval

Start here:

1. add `source_registry` and `chunk_index`
2. add `meta_layer` objects and extraction outputs
3. add `vault_decomposition_v1`
4. add `review_queue`
5. rewire feed generation to consume approved thought packets instead of flat
   overlap connections

That is the smallest slice that changes the center of the product without
breaking the whole system at once.
