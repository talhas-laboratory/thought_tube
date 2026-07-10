# Shape Signature Layer Design

Date: 2026-05-24
Status: proposed
Scope: kernel-level structural reasoning layer for Inner World and Conversation OS

## Purpose

Define the cleanest way to integrate a typed shape reasoning framework into the
existing modular system without breaking the repo's current architecture.

The target is not a separate reasoning product. The target is a new kernel
layer that:

- turns messy source-backed material into typed system-dynamic signatures
- strengthens structural retrieval and shape matching
- supports cross-domain analogy generation and evaluation
- stores validated patterns, anti-matches, and intervention memory
- remains evidence-bound, reviewable, and rebuildable from canonical source

This layer should make the current system more rigorous without turning it into
an ontology project or replacing the conversation substrate.

## Architectural judgment

The repo already has most of the surrounding scaffolding:

- canonical source substrate
- analysis units
- conversation delta extraction
- meta-layer records
- thread abstractions
- concept synthesis
- knowledge graph and retrieval
- review and governance surfaces
- runtime pipeline orchestration

What is missing is one explicit owner for typed structural interpretation.

Today, "shape" is spread across:

- meta records such as `tension`, `contradiction`, `shared_primitive`, and
  `transfer_target`
- thread abstractions organized by project lenses
- `ConceptNode.abstract_pattern`
- `ConceptNode.transfer_shape`
- `match_shapes()` in the synthesis layer

Those pieces are useful but not yet sufficient for stable structural reasoning.
They are mostly summaries, heuristics, and transfer hints. They are not yet a
durable typed signature.

The clean move is therefore:

- add a new kernel layer for `SystemDynamicSignature`
- feed it from existing analysis and meta artifacts
- let synthesis and knowledge layers consume it
- keep all user-facing surfaces unchanged at first

## Existing reusable owners

### 1. Source substrate

Canonical raw material already exists and should remain unchanged.

Primary owners:

- `memory/events/`
- `memory/sessions/`
- source imports and chunk indexes
- [src/conversation_os/analysis_units.py](/Users/talhauddin/software/inner_space/src/conversation_os/analysis_units.py)

Use:

- raw user input remains append-only
- analysis units remain the smallest stable textual reasoning units
- shape signatures must always point back to source refs and evidence spans

### 2. Meta-layer extraction

The meta layer already extracts provisional semantic structure from units.

Primary owners:

- [src/conversation_os/meta_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/meta_layer.py)
- [src/conversation_os/meta_objects.py](/Users/talhauddin/software/inner_space/src/conversation_os/meta_objects.py)

Existing useful kinds:

- `tension`
- `contradiction`
- `shared_primitive`
- `transfer_target`
- `guardrail`
- `question`
- `signal_frame`
- `interpretation`

Use:

- meta records become inputs to signature extraction
- meta records remain atomic and provisional
- meta layer should not become the owner of full shape signatures

### 3. Abstraction layer

Thread abstractions already compress fine-grained traces into reusable
project-lens abstractions.

Primary owner:

- [src/conversation_os/thread_abstractions.py](/Users/talhauddin/software/inner_space/src/conversation_os/thread_abstractions.py)

Use:

- thread abstractions can provide high-level context and project lenses
- answer-shape constraints and lens groupings can influence observer lens
- they should not be overloaded into structural signatures

### 4. Concept synthesis layer

The synthesis layer already owns the explicit staged interpolation pipeline.

Primary owner:

- [src/conversation_os/conversation_synthesis.py](/Users/talhauddin/software/inner_space/src/conversation_os/conversation_synthesis.py)

Existing reusable contracts:

- `FormationCandidate`
- `ShapeMatch`
- `OperatorDecision`
- `SynthesisCandidate`
- `StressTestResult`

Use:

- keep this module as the owner of formation matching and synthesis decisions
- change its inputs so matching can rely on structural signatures instead of
  mostly lexical overlap
- do not make this module the owner of signature extraction itself

### 5. Knowledge and retrieval layer

The knowledge layer already owns durable graph assembly, retrieval bundles,
semantic capsules, and link governance.

Primary owner:

- [src/conversation_os/knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py)

Existing useful behaviors:

- broad retrieval
- candidate pair selection
- governed links
- semantic capsules
- alias resolution

Use:

- keep broad retrieval here
- add signature-aware reranking later
- allow signature-derived bridges and capsules to feed into this layer
- do not move raw signature storage into the knowledge layer

### 6. Governance

Review and promotion paths already exist.

Primary owners:

- [src/conversation_os/review_queue.py](/Users/talhauddin/software/inner_space/src/conversation_os/review_queue.py)
- concept touch operations in `conversation_synthesis`
- link governance in `knowledge_layer`

Use:

- weak signatures, poor analogies, anti-matches, and disputed interventions
  should reuse existing review patterns
- shape reasoning should not silently commit new truth

### 7. Runtime orchestration

The runtime pipeline is already the correct place to wire a new rebuild stage.

Primary owner:

- [src/conversation_os/runtime_pipeline.py](/Users/talhauddin/software/inner_space/src/conversation_os/runtime_pipeline.py)

Use:

- insert a new component after `meta_layer` and before
  `conversation_concepts`
- keep it rebuildable, optional, and status-visible

## New owner layer

Add a new module family:

- `kernel.shape.shape_signatures`

Suggested initial files:

- `src/conversation_os/shape_signatures.py`
- `src/conversation_os/shape_memory.py`
- `src/conversation_os/shape_graph.py`

Optional later split:

- `shape_analogies.py`
- `shape_evaluation.py`

Ownership boundaries:

- `shape_signatures.py`
  - extract and persist `SystemDynamicSignature`
  - own evidence spans, alternative interpretations, and confidence
  - own conversion from source-backed material into typed structural records
- `shape_graph.py`
  - turn signatures into typed graph rows
  - validate node and edge references
  - expose deterministic overlap helpers
- `shape_memory.py`
  - own reusable shape memory items
  - store anti-matches, validated analogies, intervention memories, and
    repeated missing constraints

Why a new owner is cleaner than extending existing modules:

- extending `meta_layer` would overload atomic semantic extraction with
  graph-oriented structural interpretation
- extending `conversation_synthesis` would collapse extraction and synthesis
  into one owner
- extending `knowledge_layer` would mix durable retrieval graph assembly with
  earlier interpretive work

## Core contracts

### 1. SystemDynamicSignature

This is the central new artifact.

Purpose:

- represent one structural interpretation of a source-backed problem or
  formation
- preserve evidence, uncertainty, and alternatives
- provide a stable input for matching, analogy generation, and intervention
  transfer

Required fields:

- `signature_id`
- `source_ref`
- `source_kind`
- `source_anchor_id`
- `title`
- `summary`
- `system_boundary`
- `observer_lens`
- `entities`
- `states`
- `relations`
- `feedback_loops`
- `constraints`
- `absences`
- `affordances`
- `failure_mode`
- `desired_transformation`
- `candidate_shapes`
- `alternative_interpretations`
- `evidence_spans`
- `missing_information`
- `confidence`
- `status`
- `version`
- `created_at`
- `updated_at`

Important rule:

- `candidate_shapes` are labels applied to the signature
- they are not the signature itself

### 2. SignatureGraph

Each signature should also have a graph projection.

Purpose:

- support deterministic fit checks
- normalize roles, edge kinds, and movement primitives
- make feedback loops, blocked transitions, and leverage points queryable

Required graph concepts:

- typed nodes
- typed edges
- movement operations
- role labels
- loop membership
- leverage point tags

### 3. AnalogyEvaluationPacket

This is the evaluator artifact, not just a score.

Required fields:

- `evaluation_id`
- `signature_id`
- `analogy_id`
- `deterministic_score`
- `role_fit`
- `causal_fit`
- `feedback_fit`
- `leverage_fit`
- `material_transfer_fit`
- `anti_match_penalty`
- `llm_rationale`
- `transfers`
- `does_not_transfer`
- `intervention_risks`
- `verdict`
- `confidence`

### 4. ShapeMemoryItem

This is the durable memory object for recurring structural knowledge.

Required fields:

- `memory_id`
- `scope`
- `scope_key`
- `shape_name`
- `shape_definition`
- `validated_examples`
- `anti_matches`
- `interventions`
- `missing_constraints`
- `validation_count`
- `rejection_count`
- `last_validated_at`
- `updated_at`

Scopes:

- `global_seed`
- `domain_lens`
- `user`
- `project`

## Filesystem and artifact layout

To stay consistent with the repo's current architecture, first implementation
should use derived JSONL and JSON artifacts, not Postgres as the primary store.

Suggested paths:

```text
product/inner_world_v1/data/shape_reasoning/
  shape_signatures.jsonl
  shape_graph_nodes.jsonl
  shape_graph_edges.jsonl
  analogy_candidates.jsonl
  analogy_evaluations.jsonl
  transfer_ledgers.jsonl
  shape_memory.jsonl
  review_queue.jsonl
product/inner_world_v1/config/
  shape_reasoning_policy.json
  shape_seed_library.json
memory/sessions/<session_id>/analysis/
  shape_signatures.json
  shape_reasoning.json
```

This keeps the new layer:

- inspectable
- rebuildable
- portable
- aligned with the current source/derived discipline

## Runtime integration

Add a new runtime component:

- `shape_signatures`

Recommended order:

1. `analysis_units`
2. `conversation_deltas`
3. `meta_layer`
4. `thread_abstractions`
5. `shape_signatures`
6. `conversation_concepts`
7. `context_bubbles`
8. `knowledge_layer`

Rationale:

- shape signatures depend on units, deltas, and meta records
- concept synthesis should consume shape signatures
- context bubbles and knowledge layer can later consume promoted shape outputs

The new layer should not depend on:

- surface modules
- browser adapters
- worldbuilding-specific logic
- personal-interface-specific policy

## Retrieval integration

The new layer should improve retrieval in two phases.

### Phase 1

Keep broad retrieval in `knowledge_layer`.

Behavior:

- `build_retrieval_bundle()` remains cheap and broad
- `select_candidate_pairs()` remains the broad pair selector
- signatures are used as a second-pass reranking and filtering layer

This preserves the repo's current "retrieve broadly, verify structurally"
direction.

### Phase 2

Add signature-aware retrieval helpers:

- candidate retrieval by recurring shape name
- role overlap filters
- edge-type overlap reranking
- feedback-loop presence reranking
- project-specific anti-match penalties

This allows the system to find structurally related material even when lexical
overlap is weak.

## Synthesis integration

`conversation_synthesis` should change in one important way:

- `FormationCandidate` should be able to carry signature refs and signature
  summaries
- `match_shapes()` should score signatures first and text overlap second

Recommended evolution:

### Current behavior

- token overlap
- kind overlap
- source overlap
- contradiction hints

### Target behavior

- signature role overlap
- edge type overlap
- operation overlap
- loop compatibility
- leverage point compatibility
- anti-match penalties
- lexical overlap as a fallback or tiebreaker

This preserves the existing staged synthesis architecture while making it
structurally stronger.

## Knowledge-layer integration

The knowledge layer should consume shape reasoning outputs selectively.

Add later:

- signature-derived semantic capsules
- bridges such as `shares_shape`, `shares_failure_mode`,
  `shares_leverage_pattern`, `anti_matches`
- governed cross-domain links informed by transfer ledgers

Do not do first:

- do not replace current `KnowledgeNode` and `KnowledgeEdge` shapes
- do not make the knowledge layer responsible for signature extraction

The clean contract is:

- shape layer interprets
- knowledge layer materializes durable retrieval views from promoted outputs

## Governance integration

Shape reasoning should adopt the repo's existing governance posture:

- preserve source evidence
- keep provisional outputs reversible
- route weak outputs into review, not silent storage
- treat rejection as useful memory

Recommended review categories:

- weak structural match
- wrong shape
- wrong analogy
- missing constraint
- wrong intervention
- better alternative shape

Memory consequences:

- accepted matches increase validation counts
- rejected matches become anti-matches
- wrong-shape feedback lowers confidence or adds alternative interpretations
- repeated missing constraints become reusable memory hints

## Design rules

1. Do not edit raw events or raw source material.
2. Do not collapse signature storage into the same files as concept nodes or
   meta records.
3. Do not put project-specific or founder-specific branching into the kernel
   signature schema.
4. Do not require exact graph isomorphism for all useful analogies.
5. Do not let LLM analogy proposals bypass deterministic checks and evidence
   grounding.
6. Do not require a giant generic library before the system becomes useful.

## Recommended implementation slices

### Slice 1: kernel contracts

Add the new dataclasses and artifact paths.

Success:

- signatures, graph rows, evaluations, transfer ledgers, and memory items have
  stable internal schemas

### Slice 2: signature extraction

Build source-backed signatures from existing units and meta records.

Success:

- one session or source can produce provisional signatures with evidence spans,
  alternatives, and confidence

### Slice 3: graph projection and deterministic checks

Add graph rows and basic structural scoring.

Success:

- roles, edges, operations, and loop presence can be compared without an LLM

### Slice 4: synthesis integration

Update `match_shapes()` and related synthesis steps to consume signatures.

Success:

- structural reranking improves candidate quality without breaking existing
  surface contracts

### Slice 5: memory and review

Add shape memory items, anti-matches, and validation loops.

Success:

- accepted and rejected reasoning artifacts influence future matching

## Non-goals for v1

- full graph algebra
- ontology editor
- universal proof system for analogies
- giant manual shape library
- separate service architecture as primary source of truth
- direct UI redesign

## Bottom line

The repo already has the substrate, extraction, synthesis, knowledge, and
governance layers needed to support shape reasoning.

The cleanest integration is to add one new kernel owner for typed
system-dynamic signatures and let the existing synthesis and knowledge modules
consume it.

That gives the system:

- stronger structural matching
- better cross-domain reasoning
- inspectable analogy evaluation
- reusable user and project shape memory

without breaking the existing modular architecture or turning the whole repo
into a formal symbolic engine too early.
