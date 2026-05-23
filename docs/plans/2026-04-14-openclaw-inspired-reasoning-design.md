# OpenClaw-Inspired Reasoning Design For Inner World

## Why this exists

The current Inner World prototype has the right product shell, but the reasoning layer is still too shallow. It can ingest, connect, rank, and surface thoughts, yet the knowledge layer is still mostly driven by heuristic overlap and lightweight synthesis.

The OpenClaw and Thought Tube materials suggest a stronger pattern:

- keep the substrate bounded and inspectable
- assemble context as a bundle, not a dump
- derive typed graph structure from sessions and decisions
- preserve ambiguity early and commit memory late
- treat contradictions as first-class knowledge objects
- pause for review or external reasoning before durable memory writes

Inner World should adopt those ideas without turning itself into Thought Tube.

## Core diagnosis

Current gaps in Inner World:

- Retrieval is still too lexical.
- The graph is still too flat.
- Conflicts and contradictions are not represented explicitly.
- Memory commits are too direct.
- The system can surface thoughts, but it does not yet assemble the best bundle of evidence around them.

OpenClaw already demonstrates better patterns for all five.

## Recommended architecture

Build the reasoning layer as four modules:

1. `VaultAdapter`
Normalizes any vault or corpus into the canonical source-item contract.

Inputs:
- markdown notes
- transcripts
- imported documents
- future adapters such as Obsidian, Notion, Drive, or exported chat logs

Outputs:
- `SourceChunk`
- `SourceDocument`
- `Session`
- `ImportRecord`

2. `ContextBundleAssembler`
Builds a bounded, task-scoped context bundle for a thought, a chat thread, or a graph update.

Bundle fields:
- `session_context`
- `canon_refs`
- `graph_neighbors`
- `decision_links`
- `guardrails`
- `conflicts`
- `retrieval_meta`

This should replace the current pattern of relying mainly on overlap between chunks.

3. `KnowledgeGraphEngine`
Maintains a typed graph rather than a flat concept-connection list.

Recommended node kinds:
- `Session`
- `SourceDocument`
- `SourceChunk`
- `Thought`
- `Concept`
- `ReasoningPrimitive`
- `Frame`
- `Guardrail`
- `DecisionResolution`
- `Conflict`
- `FeedbackEvent`

Recommended edge kinds:
- `DERIVES_FROM`
- `MENTIONS`
- `RELATES_TO`
- `RESOLVED_IN_SESSION`
- `DEFINES`
- `OPERATES_IN`
- `PROTECTS`
- `IMPLEMENTS`
- `SHAPES`
- `SUPPORTS`
- `CONTRADICTS`
- `EXPANDS`
- `REINFORCED_BY_FEEDBACK`

4. `MemoryCommitGate`
Controls when candidate structure becomes durable memory.

Stages:
- decompose
- cross-pollinate
- contradiction check
- confidence and novelty scoring
- review gate
- commit

This module should support a paused state so uncertain updates can stay inspectable before they are promoted.

## Cross-pollination mechanism

The main reasoning upgrade should be a cross-pollination pass that works like this:

1. Parse a new chunk or saved thought thread.
2. Extract candidate concepts, frames, decisions, tensions, and primitives.
3. Assemble a context bundle using:
   - nearby session material
   - canonical product documents
   - graph neighbors
   - contradiction records
4. Generate candidate bridges at multiple levels:
   - concept-to-concept
   - decision-to-guardrail
   - frame-to-frame
   - thought-to-session
   - contradiction-to-resolution
5. Score each candidate bridge on:
   - evidence strength
   - novelty
   - contradiction pressure
   - user relevance
   - temporal freshness
6. Promote only the strongest candidates into:
   - surfaced thoughts
   - article expansions
   - graph update plans
7. Hold weaker candidates in a pending state instead of immediately writing them into durable memory.

This is the core mechanism that can make the system feel like it is actually thinking across the corpus rather than just clustering text.

## Contradiction layer

Inner World should add a dedicated contradiction index.

Each contradiction object should contain:
- `conflict_id`
- `left_ref`
- `right_ref`
- `reason`
- `similarity`
- `status`
- `resolution_ref`
- `created_at`
- `updated_at`

Statuses:
- `unresolved`
- `soft_resolved`
- `resolved`
- `dismissed`

Why this matters:

- contradictions create some of the highest-value thoughts
- contradictions should influence ranking and article generation
- a thought chat should be able to say not just what aligns, but what pushes against itself

## Retrieval bundle design

For any expanded thought or thought chat, the system should no longer pull context from generic neighbors only.

It should assemble:

- direct source chunks for the thought
- sibling chunks from the same documents or sessions
- decision resolutions touching the same concepts
- guardrails linked to those decisions
- conflicts touching those concepts
- recent user feedback on related thoughts

This becomes the system prompt substrate for the thought chat.

A thought chat should feel like:
- the thought speaking from its own evidence
- aware of nearby decisions and tensions
- bounded by its own guardrails
- able to admit uncertainty

## Product implication

This architecture improves three visible product surfaces at once:

1. Feed quality
Thoughts become less random and more like real perspective shifts.

2. Article quality
Expanded thoughts become evidence-backed and tension-aware rather than generic prose.

3. Thought chat quality
The chat becomes scoped, grounded, and more coherent because it can reason over a bundle instead of a loose prompt.

## OpenClaw role

OpenClaw should remain the substrate:

- miniapp host
- gateway
- bounded context service
- artifact sync
- external reasoning pause points

Inner World should remain the ontology owner:

- thought model
- knowledge graph semantics
- feed ranking
- article synthesis
- thought chat personality and scope
- memory promotion rules

The substrate must not define the meaning layer.

## Implementation order

1. Add typed graph schema and storage.
2. Add contradiction index and conflict detection pass.
3. Add context bundle assembler for thought detail and thought chat.
4. Replace direct bridge generation with graph update plans.
5. Add paused memory-commit flow for uncertain updates.
6. Re-rank the thought feed using typed graph signals instead of mostly lexical overlap.

## Success criteria

This reasoning layer is successful when:

- surfaced thoughts feel less random and more personally diagnostic
- expanded articles cite stronger evidence and acknowledge tensions
- thought chats stay coherent without drifting into generic assistant behavior
- contradictions can be surfaced and resolved explicitly
- new vaults can be ingested through adapters without rewriting the core reasoning system
