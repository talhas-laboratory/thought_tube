# Conversation Concept Synthesis Design

## Scope

This design implements the first usable bridge from `session memory` into the Inner World runtime.

V1 scope is intentionally narrow:

- source type: conversations only
- durable anchor: `ConceptNode`
- per-session interpretation object: `SynthesisPacket`
- explicit update semantics: `TouchOperation`
- configurable governance: merge policy thresholds
- first consumer surfaces:
  - agent retrieval for task packs
  - runtime/export visibility for Inner World

It does **not** yet attempt universal source ingestion across all Inner World inputs.

## Core model

### Durable anchor

`ConceptNode` is the durable knowledge object.

Each node stores:

- stable id
- canonical label
- summary
- abstract pattern
- transfer shape
- aliases
- artifact refs
- source/session refs
- confidence
- status
- timestamps
- extensible attributes for future manual curation

### Per-session synthesis

`SynthesisPacket` captures what one conversation contributed.

Each packet stores:

- source session id
- session summary
- confirmed / inferred / contested / open buckets
- concept candidates extracted from the conversation
- touch operations proposed or executed against the concept graph
- conversation analysis signals already derived from the session layer

### Update semantics

`TouchOperation` makes concept updates inspectable.

V1 touch types:

- `spawns_new_node`
- `reinforces`
- `clarifies`
- `extends`
- `reframes`
- `contradicts`
- `changes_priority`

Each touch operation records:

- target concept id
- candidate label
- confidence
- decision
- status
- evidence/source refs
- supporting attributes

## Merge policy

Merge policy is configuration-driven.

V1 thresholds:

- `auto_merge_threshold`
- `review_threshold`
- `minimum_threshold`

Behavior:

- at or above `auto_merge_threshold`: apply merge automatically
- between `review_threshold` and `auto_merge_threshold`: persist as reviewable touch
- between `minimum_threshold` and `review_threshold`: keep in packet history only
- below `minimum_threshold`: discard

The policy file lives in:

- `product/inner_world_v1/config/concept_merge_policy.json`

## Extraction strategy

V1 extraction is heuristic and deterministic.

The goal is not perfect ontology construction. The goal is to produce useful concept anchors from conversations without introducing opaque LLM steps.

Candidate signals:

- repeated multi-word phrases
- backticked terms
- code/module identifiers
- file references
- conversation-analysis translation pressure
- cross-role recurrence across user and assistant turns

Each candidate also derives:

- a short summary
- an `abstract_pattern`
- a `transfer_shape`
- transfer/mechanism terms
- artifact refs

## Graph construction

The concept graph is rebuilt deterministically from closed sessions.

Why rebuild instead of incremental patching:

- easier to keep deterministic
- avoids duplicate touch accumulation
- keeps V1 logic simple while session counts remain manageable

Runtime artifacts:

- `product/inner_world_v1/data/concept_graph/concept_nodes.jsonl`
- `product/inner_world_v1/data/concept_graph/concept_edges.jsonl`
- `product/inner_world_v1/data/concept_graph/synthesis_packets.jsonl`
- `product/inner_world_v1/data/concept_graph/touch_operations.jsonl`
- `product/inner_world_v1/data/concept_graph/review_queue.jsonl`

Per-session artifact:

- `memory/sessions/<session_id>/analysis/concept_synthesis.json`

## Retrieval

V1 retrieval is layered but still lightweight.

Scoring stages:

1. literal label / alias overlap
2. abstract pattern overlap
3. transfer-shape / mechanism overlap
4. one-step graph neighbor boost across concept edges
5. status/confidence weighting

This is enough to make task-pack retrieval concept-aware without replacing the whole routing system.

## Integration points

### Session path

`session_close` should:

1. close the manifest first
2. rebuild conversation concepts
3. attach the session’s `concept_synthesis.json` artifact
4. then build any task pack

### Runtime path

The modular runtime pipeline gets a new component:

- `conversation_concepts`

This keeps the concept graph rebuildable through runtime orchestration and configurable alongside the other Inner World components.

### Task packs

`build_task_pack()` should add:

- `relevant_concepts`

This is the first agent-facing consumer surface.

## What remains unchanged

- raw session events remain append-only
- existing session analysis and placeholder cards remain intact
- the current Inner World thought/review pipeline remains separate
- V1 does not yet ingest non-conversation sources into concept synthesis

## Success criteria

- closing or importing a conversation produces a session-level `concept_synthesis.json`
- repeated conversation concepts consolidate into stable concept nodes instead of isolated transcript artifacts
- task packs can surface relevant concepts for future work
- medium-confidence merges are reviewable instead of silently committed
- runtime/export surfaces expose concept graph counts and artifacts
