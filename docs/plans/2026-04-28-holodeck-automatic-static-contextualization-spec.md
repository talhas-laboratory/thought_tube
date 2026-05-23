# Holodeck Automatic Static Contextualization Spec

## Purpose

This document defines a Holodeck enhancement that automatically runs a bounded static-knowledge contextualization pass for a workspace.

The goal is to stop treating contextualization as a manual research habit that each agent must remember to perform.

Instead, when a workspace is still maturing and enough seed information exists, Holodeck should automatically pull the most relevant existing static knowledge from the knowledge ocean, convert it into typed workspace context and knowledge anchors, and expose the result in the normal workspace surfaces.

This is specifically meant to improve the `raw -> contextualizing -> scoping` path.

## Problem

Today Holodeck already has:

- typed context records
- typed knowledge records
- stage readiness checks
- task-pack generation
- materialized workspace views

But it still relies on the agent to remember to do one important thing manually:

- search the existing knowledge ocean for relevant static context
- decide what parts are truly relevant
- convert that into typed workspace-local context

That is a real gap.

It creates three failures:

1. good related knowledge is missed
2. different agents contextualize unevenly
3. workspaces stay weaker than the repo already allows

## Desired Product Effect

When a new Holodeck or evolving Holodeck has enough seed signals, the system should automatically answer:

- what existing project philosophy applies here
- what reusable system layers already exist
- what adjacent design knowledge is relevant
- what constraints or guardrails the workspace should inherit
- what existing owner modules and artifact surfaces should shape future work

This should produce a stronger workspace without making the Holodeck into a second global memory system.

## Core Decision

Add a new bounded Holodeck capability:

`automatic static contextualization`

This capability should:

- read the workspace's current seed signals
- retrieve relevant static knowledge from existing repo and derived layers
- emit typed workspace-local anchors
- keep provenance and uncertainty visible
- rerun only when the workspace inputs materially change

It should not dump broad retrieved text into the workspace.

## Operating Law

The feature must obey the existing Holodeck rule:

`all reasoning and state inside a Holodeck must be typed, evidence-linked, and rebuildable from source records`

It must also obey the existing bounded-semantic-assist rule:

`models may improve surfaced semantics, but they must not control the core retrieval or graph truth`

So the contextualization pass should be:

- deterministic first
- bounded if semantic reranking is used
- typed in output
- conservative in promotion

## Scope

This feature is only for pulling relevant existing static knowledge into a workspace.

It is in scope to retrieve from:

- repo docs
- plan docs
- workspace-local records
- static derived product data
- knowledge-layer surfaces
- context-bubble and thread-abstraction outputs
- shared primitives, guardrails, directions, and similar structured meta records

It is not in scope to:

- rewrite the global knowledge ocean
- auto-promote workspace-local conclusions into global truth
- run expensive full-corpus semantic search on every command
- replace manual context addition when the user or agent knows something the repo does not

## Existing System Alignment

This enhancement should reuse current Holodeck and Inner World architecture rather than introducing a parallel subsystem.

Relevant existing architecture:

- Holodeck already has explicit `contextualizing` as a maturation stage and already checks for missing context.
- Holodeck already distinguishes `context records` from `knowledge records`.
- Holodeck already emits `brief.md`, `context.md`, `knowledge.md`, `handoff.md`, and task packs.
- The wider system already has structured thematic layers such as thread abstractions, context bubbles, semantic capsules, knowledge edges, shared primitives, guardrails, and directions.

This means the missing piece is not storage.

The missing piece is an automatic bridge from workspace seed signals to bounded static retrieval and typed anchor emission.

## Trigger Model

The feature should support both explicit and automatic execution.

### Explicit operator command

Add:

- `holodeck contextualize --workspace-id ...`

Suggested options:

- `--mode suggest|apply`
- `--max-anchors N`
- `--max-source-refs N`
- `--max-context-records N`
- `--max-knowledge-records N`
- `--allow-semantic-assist`
- `--reason "..."`

Default should be `apply`.

### Automatic execution

The pass should run automatically when all of these are true:

1. the workspace is `raw`, `contextualizing`, or `scoping`
2. the workspace has enough seed signals
3. contextualization is missing or stale
4. no explicit opt-out is active

Suggested automatic hooks:

- after `holodeck create`
- after `holodeck update`
- after `holodeck link-session`
- after `holodeck ingest-artifact`
- after `holodeck add-work-item` when the first substantial work item appears
- during `holodeck materialize`
- during `holodeck status`
- during `holodeck check`
- before `holodeck task-pack`

The automatic path should be bounded and cheap enough that it can safely run as a freshness check, but it should only perform a real retrieval pass when the workspace inputs have materially changed.

## Seed Signal Model

The contextualization pass should build retrieval seeds from:

- workspace title
- goal
- purpose
- success condition
- scope-in and scope-out
- linked session titles and recent summaries
- linked artifact titles and summaries
- active work item titles
- active requirement and question records
- founder template fields when present

These seeds should be normalized into a small query bundle rather than used as raw workspace text.

Suggested normalized seed outputs:

- `topic_terms`
- `domain_terms`
- `system_terms`
- `artifact_terms`
- `constraint_terms`
- `owner_module_terms`

## Retrieval Pipeline

The retrieval pipeline should be staged.

### Stage 1: deterministic source targeting

Route the query bundle to a bounded set of static layers:

1. Holodeck architecture and workspace docs
2. product thesis and product plans
3. thread abstractions and project lenses
4. context bubbles and semantic capsules
5. knowledge-layer nodes, edges, and context links
6. static meta-layer records:
   - shared primitives
   - guardrails
   - directions
   - tensions
   - questions

### Stage 2: candidate collection

Collect candidates with:

- source ref
- source layer
- candidate title
- summary or short statement
- exact matched terms
- confidence basis

### Stage 3: scoring

Score each candidate by:

- direct seed overlap
- layer priority
- thematic relevance
- recency if applicable
- structural importance
- repeated reinforcement across layers
- anti-noise penalties for generic or weakly connected hits

### Stage 4: bounded semantic assist

Optional and bounded.

If enabled, semantic assist may:

- improve candidate labels
- merge duplicates
- produce a tighter explanation of why a candidate matters to this workspace

It must not:

- invent new facts
- override provenance
- choose candidates without deterministic candidate collection first

### Stage 5: typed emission

Convert the top candidates into workspace-local records.

## Source Priority Model

Not all layers should be trusted equally for this pass.

Suggested priority order:

1. explicit repo docs and plan docs
2. structured product/runtime records
3. thread abstractions and context bubbles
4. semantic capsules and context links
5. shared primitives, guardrails, directions, and related derived meta records
6. low-confidence or weakly grounded static source items

The pass should prefer fewer high-signal anchors over many weak anchors.

## Output Model

The pass should emit two kinds of local records.

### 1. Context records

Use existing context records for placement information such as:

- `domain_context`
- `existing_system`
- `integration_context`
- `adjacent_project_context`
- `philosophy_context`

Suggested examples:

- this workspace sits on top of the existing thread abstraction and context bubble stack
- this workspace inherits the private cognitive layer philosophy
- this workspace is adjacent to bounded semantic assist rather than replacing it

### 2. Knowledge records

Use existing knowledge records for typed claims such as:

- `requirement`
- `constraint`
- `decision`
- `assumption`
- `risk`
- `insight`
- `open_question`

All auto-derived knowledge records should default to:

- `claim_posture=inferred`
- `status=active`

unless directly copied from explicit workspace decisions.

## New Supporting Source Records

Add two new workspace-local source files:

- `contextualization_runs.jsonl`
- `contextualization_candidates.jsonl`

### `contextualization_runs.jsonl`

Each run should record:

- `run_id`
- `workspace_id`
- `mode`
- `trigger`
- `reason`
- `seed_fingerprint`
- `input_summary`
- `source_layers_consulted`
- `candidate_count`
- `emitted_context_ids`
- `emitted_record_ids`
- `status`
- `started_at`
- `ended_at`

### `contextualization_candidates.jsonl`

Each candidate should record:

- `candidate_id`
- `run_id`
- `workspace_id`
- `candidate_kind`
- `source_layer`
- `source_ref`
- `title`
- `statement`
- `matched_terms`
- `score`
- `confidence`
- `disposition`
- `emitted_context_id`
- `emitted_record_id`

This preserves inspectability and gives `holodeck check` something concrete to evaluate.

## Staleness Model

Automatic contextualization must be freshness-aware.

A workspace should be considered `contextualization_stale` when:

- goal, purpose, or success condition changed
- new linked sessions were added
- new major artifacts were ingested
- scope boundaries changed
- a new dominant workstream appeared
- the most recent contextualization run used a different seed fingerprint

The system should not rerun just because a timestamp changed.

It should rerun only when the workspace meaningfully changed.

## Deduplication and Supersession

The pass should deduplicate by:

- normalized source ref
- record kind
- semantically equivalent title or statement
- repeated candidate emission from the same layer

When an old inferred anchor is replaced by a stronger one, the old record should be:

- superseded, not deleted

This preserves typed history.

## Materialized Surfaces

The enhancement should add a dedicated derived surface:

- `contextualization.md`
- `contextualization.json`

These should show:

- latest run status
- stale or fresh state
- source layers consulted
- emitted anchors
- suppressed duplicates
- unresolved low-confidence candidates

Existing surfaces should also absorb the result:

- `brief.md`
  - show contextualization freshness and top inherited anchors
- `context.md`
  - show auto-derived context records with provenance
- `knowledge.md`
  - show auto-derived inferred requirements, risks, and insights
- `handoff.md`
  - include top inherited philosophy and system anchors
- `task-pack`
  - include contextualization-derived constraints and context anchors

## Check Integration

`holodeck check` should gain contextualization checks.

Suggested outputs:

- `contextualization_ok`
- `contextualization_fresh`
- `contextualization_gaps`
- `contextualization_warnings`

Suggested gap types:

- `no_contextualization_run`
- `insufficient_seed_signals`
- `stale_contextualization`
- `no_high_signal_anchors`
- `contextualization_budget_exceeded`

Suggested warning types:

- `candidate_noise_high`
- `weak_cross_layer_support`
- `anchor_conflict_detected`

Stage readiness should use this carefully:

- `contextualizing` should not require static contextualization in all cases
- but if enough seed signals exist and no run has occurred, it should be reported as a quality gap

## Task-Pack Integration

`holodeck task-pack` should automatically include:

- top context anchors
- top inherited constraints
- relevant existing system modules
- adjacent plan docs
- confidence-marked open questions from contextualization

This is important because handoff quality is one of the main reasons to build the feature.

## Budget Model

The feature must be bounded.

Suggested limits:

- max source layers consulted per run
- max candidates per layer
- max emitted context records
- max emitted knowledge records
- max source refs per emitted record
- max semantic-assist candidates
- max runtime seconds per automatic run

Automatic mode should use tighter budgets than explicit mode.

## Reliability Rules

The system must fail conservatively.

If retrieval quality is weak:

- emit fewer anchors
- keep them inferred
- prefer open questions over strong claims
- record warnings instead of pretending confidence

The system must never:

- silently manufacture durable truth
- remove human-authored context because auto-context disagreed
- hide the source layer or provenance path

## User and Agent Controls

Suggested controls:

- manifest-level flag:
  - `auto_contextualization: enabled|disabled`
- command-level flag:
  - `--no-auto-contextualization`
- run-level reason field for manual invocation

This should default to enabled for normal workspaces.

## Non-Goals

This enhancement should not:

- become a generic search engine UI
- expose raw ocean complexity directly to the user
- retrieve every possibly related document
- substitute for explicit architectural review
- auto-create implementation work items from weak context alone
- auto-promote local inferred knowledge into global repo records

## Example

For a workspace like the chat-bridge Holodeck, the automatic pass should be able to infer and attach anchors such as:

- the product is a `private cognitive layer`
- the current project already has thread abstractions and context bubbles
- bounded semantic assist is the existing rule for model placement
- relevant project lenses include:
  - `interaction_model`
  - `cognitive_fidelity`
  - `reasoning_routing`
  - `user_model_and_taste`
  - `answer_shape_governance`
- existing static guardrails include:
  - near-zero friction capture
  - uncertainty-aware interpretation
  - lightweight thought state after capture
  - distinct interfaces for distinct jobs

These should appear as typed, evidence-linked workspace anchors, not as a pasted research summary.

## Acceptance Criteria

The enhancement is successful if:

1. a new workspace with clear seed signals gets at least one useful context anchor automatically
2. the emitted anchors are provenance-linked and claim-postured
3. rerunning without meaningful changes does not create duplicate records
4. meaningful workspace changes mark contextualization stale and rerun cleanly
5. task-pack output is measurably better because inherited context appears automatically
6. `holodeck check` can explain contextualization gaps and freshness
7. the feature stays bounded and does not do whole-ocean retrieval on ordinary runs

## Recommended Implementation Slices

### Slice 1: source records and explicit command

Build:

- `contextualization_runs.jsonl`
- `contextualization_candidates.jsonl`
- `holodeck contextualize`
- deterministic seed builder
- deterministic retrieval against a narrow source set
- typed emission into context and knowledge records

### Slice 2: materialized surfaces and check integration

Build:

- `contextualization.md`
- `contextualization.json`
- freshness and staleness reporting
- contextualization gaps in `holodeck check`
- task-pack enrichment from emitted anchors

### Slice 3: automatic hooks

Build:

- staleness fingerprinting
- auto-run on create/update/link/materialize/check/task-pack
- tight automatic budgets
- opt-out controls

### Slice 4: bounded semantic assist

Build only after the deterministic path is stable:

- bounded label improvement
- duplicate compression
- concise why-it-matters rendering

Do not build this first.

## Owner Surface

Primary owner:

- [holodeck.py](/Users/talhauddin/software/inner_space/src/conversation_os/holodeck.py)

Likely supporting reads from:

- [knowledge_layer.py](/Users/talhauddin/software/inner_space/src/conversation_os/knowledge_layer.py)
- [thread_abstractions.py](/Users/talhauddin/software/inner_space/src/conversation_os/thread_abstractions.py)
- [context_bubbles.py](/Users/talhauddin/software/inner_space/src/conversation_os/context_bubbles.py)

Primary architectural references:

- [2026-04-26-holodeck-workspace-architecture.md](/Users/talhauddin/software/inner_space/docs/plans/2026-04-26-holodeck-workspace-architecture.md)
- [2026-04-18-session-driven-semantic-update-design.md](/Users/talhauddin/software/inner_space/docs/plans/2026-04-18-session-driven-semantic-update-design.md)
- [2026-04-23-bounded-openclaw-semantic-assist-architecture.md](/Users/talhauddin/software/inner_space/docs/plans/2026-04-23-bounded-openclaw-semantic-assist-architecture.md)

## Final Recommendation

This enhancement is worth building.

It is a direct fit for Holodeck's maturation model, improves continuity and handoff quality, and makes existing static project knowledge operational instead of optional.

The right implementation is:

- bounded
- deterministic-first
- typed
- provenance-linked
- freshness-aware
- integrated into `check`, `materialize`, and `task-pack`

That would make the kind of contextualization we just did manually become a normal Holodeck behavior.
