# Symbiotic Reasoning Pipelines and Personal Idea Formation

**Status:** Framework extension for review  
**Date:** 2026-07-10  
**Workspace:** `unified-framework-synthesis-4f48`

## Purpose

This document adds a runtime philosophy to the Unified Framework Synthesis.

The existing synthesis establishes what a thought is, how it can be captured, how it persists, how it moves, and how recurring reasoning patterns can be represented. This extension addresses a more specific product question:

> How should the system help a person take an incomplete fragment and work it into their larger conceptual world, while gradually learning the person's own repeatable ways of doing that?

The answer is a symbiotic reasoning architecture. It begins with guided co-processing rather than autonomous imitation.

## Core Claim

The product should not mainly automate answers. It should assist and gradually learn the user's repeated **idea-forming transformations**.

A user often does not begin with a finished proposition. They begin with a phrase, image, tension, memory, lyric, scene, analogy, mood, or vague cognitive pressure. The fragment may matter because it belongs to a larger idea, work, worldview, project, song, film, or personal inner topology.

The system's task is to help the user determine whether the fragment should be:

- expanded
- narrowed
- restricted
- translated
- connected
- held as tension
- suspended
- integrated
- rejected

This is not a new ontology. It is a runtime process for moving existing framework objects through time and context.

## Terminology

### `IdeaWorld`

An `IdeaWorld` is the user's larger evolving conceptual environment. Depending on the context, it may be a product thesis, a research program, a song, a film, a worldview, or a personal formation.

It is not a second persistence system. In the Unified Framework, it is a bounded projection over existing `ThoughtObject`, `Formation`, `Shape`, `StateClaim`, relation, workspace, and provenance records.

### `ThoughtFragment`

A `ThoughtFragment` is incoming material that has not yet earned a stable place in a formation. It may correspond to a raw `ReasoningStep` with a `Hold` state.

### `TransformationOperator`

A `TransformationOperator` is a controlled reasoning move that changes the relationship between a fragment and its current `IdeaWorld`.

Examples:

- `expand_dimension`
- `narrow_claim`
- `preserve_tension`
- `find_structural_analogy`
- `translate_symbol_to_structure`
- `suspend_placement`
- `integrate_into_parent`
- `release_or_reject`

### `ContextState`

A `ContextState` is the bounded turn-time control object that determines what world is active before the system reasons.

Its minimum shape is:

```text
active_topic
object_scope
object_id
parent_object_id
dimension_axis
user_goal
current_tension
answer_shape
active_workspace_id
depth_mode
confidence
```

### `ActiveFieldState`

An `ActiveFieldState` is the smaller semantic working set selected from the current `ContextState`: the relevant fragment, candidate parents, dimensions, tensions, constraints, evidence, and potential next moves.

## Alignment With The Unified Framework

The existing unified framework should remain canonical. This extension adds control flow around it.

| Existing primitive or layer | Role in symbiotic reasoning |
|---|---|
| `Field` | Holds pre-clear possibility without forcing interpretation. |
| `ReasoningStep` | The atomic observable record of a user's move. |
| `Hold` | A valid outcome when placement or meaning is not ready. |
| `Dimension`, `Station`, `Facet` | The axes through which a fragment can be expanded, constrained, or translated. |
| `StateClaim` | A provisional or confirmed assertion created by a transformation. |
| `Tension` | A first-class signal that may be preserved rather than resolved. |
| `Relation`, `Shape`, `Stencil` | The structural basis for integration and cross-domain transfer. |
| `Formation` | A stabilized larger whole that can absorb or be revised by fragments. |
| `ReasoningSignature` | The gradually inferred recurring sequence of user moves. |
| SDS overlay | On-demand support for loops, constraints, absences, anti-matches, and interventions. |
| MTSF substrate | Canonical event, assertion, graph, provenance, and discovery persistence. |

The central invariant remains:

`one ontology, multiple projections, no parallel stores`

`IdeaWorld`, `ContextState`, and `ActiveFieldState` must be projections and runtime packets over the canonical object model, not competing registries.

## What This Adds

The Unified Framework already establishes a capture loop:

```text
Drop -> Hold -> Trace -> Mirror -> Prompt -> Repeat
```

This extension makes the prompt and next-step selection more explicit:

```text
fragment
-> classify current context
-> assemble bounded field
-> choose transformation operator
-> produce a probe or integration move
-> evaluate
-> record user response
-> update reasoning signature conservatively
```

It therefore connects three existing ideas that otherwise remain separate:

1. `ReasoningStep` capture records what happened.
2. `ReasoningSignature` identifies recurring move patterns over time.
3. Symbiotic reasoning pipelines use the current context and those patterns to choose a useful next prompt or transformation.

## The Symbiotic Principle

The initial system must not claim that it can fully mimic a person's hidden cognition.

Instead, it should learn from visible interaction:

1. A user brings a fragment.
2. The system identifies candidate contexts, dimensions, and tensions.
3. The system proposes a small number of possible moves.
4. The user accepts, rejects, reframes, or redirects.
5. The system stores the correction with provenance.
6. Only repeated, consistent evidence changes user-local routing or operator preferences.

This produces a progression:

```text
guided co-processing
-> repeated correction evidence
-> pattern capture
-> partial anticipation
-> personalized reasoning assistance
```

The product is not thinking instead of the user. It is helping the user see, continue, and inspect their own recurring transformations.

## Bridge-Owned Runtime

The bridge should be the turn-time control plane. It should not become a second knowledge ocean.

It owns:

- turn classification
- workspace binding
- context-depth selection
- bounded context-bundle assembly
- context-switch logging
- handoff to the active-field and pipeline runtime
- safe feedback and promotion boundaries

The bridge must keep four context spaces distinct:

| Space | Meaning | Default durability |
|---|---|---|
| Session-local | Current turns, unresolved references, temporary working context | Ephemeral |
| Workspace-local | Bounded project, formation, or initiative context | Scoped and durable |
| User-local | Preference and reasoning-signature evidence | Slowly durable |
| Global | MTSF / knowledge graph fallback context | Read-only fallback |

Depth modes should remain explicit:

- `Focused`: use current exchange unless more context is requested or clearly required
- `Contextual`: use the smallest relevant supporting bundle
- `Deep`: use broader bounded reasoning context when justified
- `Incognito`: do not save, learn, or promote

The bridge emits a `ContextSwitchEvent` whenever the active topic, object, workspace, depth, or goal changes meaningfully. This makes movement through the user's conceptual topology inspectable and reversible.

## Reasoning Pipeline Mechanics

A reasoning pipeline is an ordered sequence of state transformations, not a generic prompt template and not a hidden chain-of-thought transcript.

```text
ReasoningRequest
-> ContextState
-> bounded context bundle
-> ActiveFieldState
-> pipeline route
-> TransformationOperator sequence
-> evaluator
-> user-facing response + machine verdict
-> learning event
```

The first generic pipeline is `idea_embedding_v1`.

| Stage | Question | Typical output |
|---|---|---|
| Frame | What kind of fragment is this? | role, current pressure, provisional parent ideas |
| Activate | What dimensions and evidence matter now? | active field |
| Transform | What move should be tried? | expansion, translation, tension preservation, suspension, integration |
| Evaluate | Did the move preserve signal and fit? | integrate, suspend, preserve tension, reject, probe |
| Learn | What did the user teach the system? | provenance-backed preference evidence |

The system should prefer a probe over an assertion when confidence is low, ambiguity is high, or multiple parent formations are plausible.

## User-Specific Reasoning Signatures

The existing framework defines `ReasoningSignature` as recurring move sequences. This extension makes that usable in the live system.

For example, a user may repeatedly:

```text
ground mechanism
-> triangulate alternatives
-> seek concrete evidence
-> bridge domains
-> formalize shape
-> preserve or invert tension
-> seek a reusable canon
```

Another user may repeatedly:

```text
felt sense
-> image
-> metaphor
-> narrative movement
-> aesthetic selection
-> composition
```

The system should not hard-code either path as superior. It should only use a signature as a weak, revisable prior when current context supports it.

Signature evidence should include:

- observed `ReasoningStep` move types
- user-confirmed links and corrections
- preferred abstraction levels
- tolerance for ambiguity and preserved tension
- successful versus rejected prompt forms
- contexts in which a move worked or failed

One conversation must never rewrite a person's signature.

## Latent Processing And Resurfacing

The system should not claim literal subconscious access. The practical target is a software analogue to incubation:

```text
experience
-> episodic trace
-> deferred replay / comparison
-> candidate link or schema update
-> resurfacing under a later matching context
```

This belongs to a later slow path, after the fast symbiotic runtime is reliable.

The slow path may:

- sample unresolved or suspended fragments
- compare their shapes and stencils to older material
- generate provisional bridge links
- surface a candidate only when a later `ActiveFieldState` makes it relevant
- preserve uncertainty and allow dismissal

No candidate link becomes canonical without evidence, review, or repeated support.

## Invariants And Anti-Goals

The following guardrails are required.

1. Save before interpret.
2. Hold is a valid state.
3. Do not flatten ambiguity to manufacture a clean answer.
4. Do not resolve productive contradiction by default.
5. Keep raw user language separate from inferred structure.
6. Keep session, workspace, user, and global context separate until intentionally bridged.
7. Do not learn durable preferences from a single turn.
8. Do not treat a reasoning signature as a personality diagnosis.
9. Do not create a separate ontology for runtime packets.
10. Do not let global retrieval override active workspace or current-turn evidence without an explicit reason.

## Build Implication

The immediate build sequence is:

1. Extend the canonical schema with runtime references, not parallel objects.
2. Add `ReasoningRequest`, `ContextState`, `ContextSwitchEvent`, `ActiveFieldState`, `ReasoningResult`, and `ReasoningLearningEvent` contracts.
3. Build a deterministic bridge that classifies turns, binds workspace context, and assembles a bounded bundle.
4. Build one `idea_embedding_v1` pipeline over the existing packet runner and operator registry.
5. Add evaluation and conservative learning persistence.
6. Add slow replay and resurfacing only after the fast loop is inspectable and useful.

The existing [Reasoning Pipeline Implementation Plan](../../../plans/2026-06-10-reasoning-pipeline-implementation-plan.md) contains the repo-specific module and test sequence.

## Final Position

The Unified Framework describes a thought as a dynamic multidimensional meaning-shape and gives the system one shared ontology for capture, persistence, motion, and curation.

This extension defines how the system should meet a person in the middle of a living thought: keep the right context active, identify the next useful transformation, preserve uncertainty when it is meaningful, and learn from the user's own acts of formation over time.
