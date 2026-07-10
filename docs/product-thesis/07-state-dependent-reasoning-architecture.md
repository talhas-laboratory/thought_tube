# State-Dependent Reasoning Architecture

Date: 2026-06-13

Related docs:

- [Product Thesis](../../PRODUCT_THESIS.md)
- [Chat Bridge Requirements](03-chat-bridge-requirements.md)
- [Reasoning Pipeline Build Report](../research/2026-06-10-reasoning-pipeline-build-report.md)
- [Reasoning Pipeline Implementation Plan](../plans/2026-06-10-reasoning-pipeline-implementation-plan.md)
- [Repo Organization And Self-Updating Index Plan](../plans/2026-06-11-repo-organization-and-self-updating-index-plan.md)

## Purpose

This document captures the target architecture for the whole system as it has
emerged through the reasoning-pipeline, bridge-layer, knowledge-ocean, and
TouchDesigner-style state-graph discussions.

The central design claim is:

`Each user turn is new evidence that updates a live state, and that state should determine both the next reasoning transformation and how much context is disclosed to the main intelligence model.`

The system should not behave like a static prompt template, a generic memory
dump, or a single chatbot persona. It should behave like a state-aware field of
transformations. The user enters material. The bridge detects the current state
of the thought, selects the right operation, discloses the smallest useful
context, and lets the main model execute inside those constraints.

## Surrounding Context

The current product thesis already says that the system is a semantic operating
layer:

`raw thought -> structured semantics -> retrievable context -> executable guidance -> evaluated feedback -> updated world`

The reasoning-pipeline work sharpened that into:

`fragment -> active field -> operator sequence -> evaluation -> integration -> learning`

The chat-bridge work added the runtime constraint:

`use the knowledge ocean as a context source, not as a per-turn compute obligation`

The user's later correction added the missing architectural center:

`not just a navigable field of transformation, but state-aware and state-dependent fields of transformations`

The TouchDesigner comparison clarified the implementation metaphor:

- The system is a graph of small transformation nodes.
- The material flowing through the graph is not pixels, audio, or geometry. It is thought-state.
- Each node reads the current state, transforms one part of it, and emits a new state.
- Routing is not hardcoded once forever. It is selected from state, confidence, goal, and context.
- Modulators change node behavior without rewriting the node.

The small-model steering discussion clarified the control-plane split:

- A smaller model can reliably classify, route, budget, and produce structured control packets.
- The main model should do deeper reasoning, synthesis, explanation, coding, and writing.
- The small model should not try to be a weaker version of the main model.
- The small model should be a state controller.

## Current Implemented Substrate

The repo already contains a first version of this system shape.

Hot-path reasoning modules:

- `src/conversation_os/reasoning_bridge.py`
- `src/conversation_os/active_field.py`
- `src/conversation_os/reasoning_router.py`
- `src/conversation_os/reasoning_runtime.py`
- `src/conversation_os/reasoning_evaluator.py`
- `src/conversation_os/reasoning_learning.py`
- `src/conversation_os/operators.py`
- `src/conversation_os/pipelines.py`

Cold-path and knowledge substrate:

- `src/conversation_os/knowledge_layer.py`
- `src/conversation_os/context_bubbles.py`
- `src/conversation_os/meta_layer.py`
- `src/conversation_os/conversation_threads.py`
- `src/conversation_os/conversation_synthesis.py`
- `src/conversation_os/thread_abstractions.py`
- `src/conversation_os/library_tracker.py`

Runtime layout substrate:

- `src/conversation_os/runtime_layout.py`
- `src/conversation_os/repo_index.py`

The existing runtime already performs these steps:

1. Accept a `ReasoningRequest`.
2. Classify the turn into a `ContextState`.
3. Assemble a bounded context bundle.
4. Build an `ActiveFieldState`.
5. Route to a reasoning pipeline.
6. Run the pipeline.
7. Evaluate the result.
8. Optionally persist learning from feedback.

This is the correct spine. The architecture below generalizes and hardens it.

## Architectural Thesis

The best architecture is a two-plane system:

`control plane -> execution plane`

The control plane is the bridge. It decides what the current turn means for the
system state.

The execution plane is the main intelligence model and tools. It performs the
actual reasoning, writing, coding, retrieval synthesis, or product work.

The control plane should be small, inspectable, schema-bound, and conservative.
The execution plane can be powerful, flexible, and expressive because the
control plane gives it a bounded field to work inside.

In practical terms:

`user input -> evidence capture -> state update -> control packet -> context disclosure -> main agent execution -> evaluation -> learning`

The bridge should not answer the user. It should shape the conditions under
which the answer is generated.

## Core Object Model

### 1. Evidence

Evidence is what actually happened.

Examples:

- raw user text
- assistant answer
- user correction
- accepted answer
- imported document
- linked artifact
- tool result
- source reference

Evidence should be append-only where possible. It should not be overwritten by
later interpretations.

### 2. State

State is the bounded mutable control surface for the current moment.

Examples:

- active topic
- active object
- active goal
- object scope
- dimension axis
- tension
- depth mode
- ambiguity
- reasoning posture
- bridge behavior
- context policy
- confidence

State can change every turn, but it should not reset every turn.

### 3. Shape

Shape is the arrangement of state variables.

Examples:

- "same main object, new dimension"
- "new main object, product scope"
- "same topic, shifted from creative expansion to implementation"
- "imported sidecar, not yet merged"
- "low factual anchor, high symbolic interpretation"

Shape is what determines the next transformation.

### 4. Operator

An operator is a reusable transformation applied to thought-state.

Examples:

- capture intuition
- clarify object scope
- extract abstract mechanism
- map system dynamics
- expand possible paths
- evaluate novelty
- check feasibility
- translate into architecture
- compress into instructions
- integrate into product spine

An operator should be treated like a node in a graph.

### 5. Pipeline

A pipeline is an ordered or conditional sequence of operators.

It is not just a prompt. It is a controlled path through state transformations.

Examples:

- `intuition_expansion_v1`
- `symbolic_interpretation_v1`
- `candidate_evaluation_v1`
- `idea_embedding_v1`
- `problem_reframing_v1`

### 6. Bridge Behavior

A bridge behavior is a state-dependent modifier that changes posture, operator
bias, context policy, or answer shape.

Example:

When the user is in low-factual-anchor creative interpretation mode, prefer
expansion and connection over caveats.

This should not be hardcoded as one special case. It should be one bridge
behavior among many.

### 7. Context Policy

Context policy decides what memory to disclose to the main model.

It should answer:

- which layers are allowed?
- how deep should retrieval go?
- what is the token budget?
- is cross-ocean retrieval allowed?
- should evidence be quoted, summarized, or only used as routing signal?
- should the system abstain from memory use?

### 8. Control Packet

The control packet is the handoff from the bridge to the main model.

It should be strict, inspectable JSON. The main model uses it as steering
context.

Minimal shape:

```json
{
  "active_topic": "state-dependent reasoning architecture",
  "object_scope": "same_main",
  "object_id": "product:reasoning-bridge",
  "parent_object_id": "product:inner-world",
  "dimension_axis": "architecture",
  "user_goal": "design",
  "current_tension": "maximum flexibility vs reliable small-model control",
  "reasoning_posture": "architectural",
  "factual_anchor_level": "medium",
  "bridge_behaviors": ["implementation_scaffold"],
  "next_operator": "translate_to_architecture",
  "pipeline_id": "idea_embedding_v1",
  "context_policy": {
    "mode": "graph_contextual",
    "depth_mode": "deep",
    "token_budget": 2400,
    "include_layers": ["recent_session", "product_thesis", "reasoning_runtime", "knowledge_capsules"],
    "exclude_layers": ["unapproved_sidecars"],
    "cross_ocean": false
  },
  "steering_constraints": [
    "preserve provenance",
    "separate evidence from inference",
    "prefer smallest sufficient context",
    "do not over-psychologize the user"
  ],
  "confidence": 0.82
}
```

## State Variables

The system should track these variables as first-class control variables.

### Topic And Object

- `active_topic`: what the current turn appears to be about.
- `object_id`: the current main object, idea, artifact, project, or thread.
- `object_scope`: whether the turn is same main, sub-object, parallel object,
  or new main object.
- `parent_object_id`: the larger object this turn belongs under, if any.
- `dimension_axis`: the dimension being explored, such as architecture,
  marketing, myth, interface, implementation, tone, or evaluation.

This directly addresses the user's requirement:

`there should also be a way to recognize main idea/thread/theme/goal but also different sub versions of this main object`

The bridge should decide whether a turn is:

- same object, same dimension
- same object, new dimension
- sub-object of current object
- parallel object
- new main object
- imported sidecar awaiting reintegration

### Goal And Motion

- `user_goal`: explore, understand, evaluate, build, decide, name, compress,
  expand, or implement.
- `answer_shape`: explanation, artifact, plan, critique, architecture,
  expansion, summary, or direct edit.
- `reasoning_posture`: expansive, evaluative, explanatory, implementation,
  symbolic, architectural, or corrective.
- `next_operator`: the immediate transformation most likely to help.

### State Quality

- `confidence`: how sure the bridge is about the state.
- `ambiguity_level`: how underdetermined the turn is.
- `factual_anchor_level`: whether the turn is grounded in facts, code, docs,
  or mostly intuition/interpretation.
- `fixation_risk`: whether the system is likely to keep repeating one shallow
  frame.
- `novelty_confidence`: whether the idea seems new relative to available memory.
- `staleness`: whether reused context may be outdated.

### Context And Memory

- `depth_mode`: focused, contextual, deep, or incognito.
- `retrieval_mode`: none, semantic narrow, graph contextual, cross ocean, or
  evidence strict.
- `context_budget`: maximum amount of context allowed.
- `bundle_layers`: current turn, recent window, working context, session,
  workspace, user patterns, knowledge ocean, source evidence.
- `source_refs`: provenance for included material.

### Learning And Governance

- `feedback_kind`: accepted, rejected, corrected, expanded, compressed, or
  deferred.
- `accepted_direction`: what the user approved.
- `rejected_direction`: what the user pushed away from.
- `durability`: ephemeral, session-local, provisional, promoted, or durable.
- `privacy_mode`: normal or incognito.

## Runtime Flow

### Step 1. Capture Evidence

The raw turn enters as evidence.

The system preserves:

- raw text
- timestamp
- session id
- surface
- source refs
- explicit tags
- caller hints

Tags such as `#meta` should be treated as routing operators, not ordinary text.

### Step 2. Classify State

The bridge classifies the turn into a `ContextState`.

This is where the system detects:

- active topic
- object scope
- user goal
- current tension
- answer shape
- depth mode
- reasoning posture
- factual anchor level
- bridge behaviors

The output must include confidence.

### Step 3. Select Context Policy

The bridge decides what context, if any, should be disclosed.

Default rule:

`disclose the smallest context bundle that materially improves the next transformation`

The system should not pull from the whole knowledge ocean just because it can.

### Step 4. Build Active Field

The active field is the local transformation environment for the turn.

It contains:

- fragment role
- candidate parent ideas
- active dimensions
- active tensions
- constraints
- fit targets
- ambiguity level
- fixation risk
- novelty confidence
- retrieval summary
- bridge behaviors
- perturbation markers

This is the equivalent of the current TouchDesigner network state.

### Step 5. Route To Operator Or Pipeline

The router chooses:

- next operator
- pipeline id
- operator overrides
- response directives
- learning hooks

The router should consider both:

- direct intent from the current user turn
- global state shape from the active field

### Step 6. Execute With Main Model

The main model receives:

- user request
- control packet
- bounded context bundle
- tool constraints
- output target

The main model should not need the entire knowledge ocean. It should receive
the right local field.

### Step 7. Evaluate

The evaluator checks whether the answer:

- preserved the user's intended movement
- used enough context, but not too much
- avoided flattening the tension
- avoided false certainty
- produced an actionable next state
- respected bridge behavior

### Step 8. Learn Conservatively

Learning should be based on:

- explicit correction
- repeated pattern
- accepted output
- rejected output
- confidence thresholds

One-off behavior should remain session-local unless the user confirms it or it
recurs.

## Context Disclosure Policy

The mechanism for "which context and how much" should be explicit and
state-dependent.

Recommended modes:

### `none`

Use no stored memory.

Use when:

- incognito mode is active
- the user asks a direct self-contained question
- confidence is too low
- memory would likely pollute the answer

### `recent_local`

Use only the current turn and recent conversation window.

Use when:

- the topic is local to the current exchange
- the user says "this" or "that" and recent context is enough
- the task is lightweight

### `semantic_narrow`

Retrieve a small number of directly related capsules or docs.

Use when:

- active topic is clear
- object scope is same main or sub-object
- the user asks for continuity
- the task benefits from one known project area

### `graph_contextual`

Retrieve related capsules, adjacent concepts, parent object, and relevant
bridge behaviors.

Use when:

- the user asks for architecture, synthesis, or evaluation
- the turn touches multiple dimensions of the same object
- the system needs to know how this relates to prior product spine

### `cross_ocean_exploration`

Allow broader retrieval across ponds or domains.

Use when:

- the user asks for analogies, mythic parallels, marketing concepts, or broad
  creative exploration
- the turn is explicitly exploratory
- the answer should connect distant material

This mode should be budgeted and provenance-heavy because it has higher drift
risk.

### `evidence_strict`

Use only source-backed context and quote/attribute carefully.

Use when:

- the user asks for factual accuracy
- code, legal, financial, scientific, or technical correctness matters
- the system is evaluating claims rather than expanding possibilities

## Small-Model Controller Design

The smaller model should be used as a control-plane classifier and router.

It should produce structured output only.

It should not:

- generate the final answer
- invent durable user psychology
- summarize the entire knowledge ocean
- make irreversible memory updates
- override explicit user instructions

It should:

- classify the current turn
- update state variables
- select bridge behaviors
- choose context policy
- choose next operator or pipeline
- assign confidence
- mark uncertainty
- request fallback when unsure

The smaller model can be reliable if it operates inside strict schemas and
small enumerations.

Recommended controller output:

```json
{
  "state_update": {
    "active_topic": "string",
    "object_scope": "same_main|sub_object|parallel_object|new_main|sidecar",
    "object_id": "string",
    "parent_object_id": "string",
    "dimension_axis": "string",
    "user_goal": "explore|understand|evaluate|build|decide|name|compress|expand|implement",
    "current_tension": "string",
    "reasoning_posture": "expansive|evaluative|explanatory|implementation|symbolic|architectural|corrective",
    "factual_anchor_level": "low|medium|high"
  },
  "routing": {
    "bridge_behavior_ids": ["string"],
    "pipeline_id": "string",
    "next_operator": "string"
  },
  "context_policy": {
    "retrieval_mode": "none|recent_local|semantic_narrow|graph_contextual|cross_ocean_exploration|evidence_strict",
    "depth_mode": "focused|contextual|deep|incognito",
    "token_budget": 0,
    "capsule_limit": 0,
    "neighbor_limit": 0,
    "include_layers": ["string"],
    "exclude_layers": ["string"]
  },
  "confidence": {
    "overall": 0.0,
    "topic": 0.0,
    "object_scope": 0.0,
    "retrieval_policy": 0.0
  },
  "safety": {
    "requires_human_confirmation": false,
    "do_not_learn": false,
    "fallback_reason": ""
  }
}
```

## Bridge Behaviors As Modular Rules

A bridge behavior should be a small declarative object, not scattered if/else
logic.

Recommended shape:

```json
{
  "behavior_id": "creative_expansion",
  "version": "1.0",
  "activation": {
    "routing_tags": ["metathought"],
    "factual_anchor_level": ["low"],
    "user_goal": ["explore", "understand"],
    "reasoning_posture": ["expansive"],
    "required_signal_count": 2
  },
  "effects": {
    "preferred_pipeline": "intuition_expansion_v1",
    "routing_mode": "override",
    "retrieval_mode_bias": "cross_ocean_exploration",
    "response_directives": [
      "connect_adjacent_paths",
      "explain_signal_shape",
      "preserve_creative_spark",
      "avoid_unnecessary_caveats"
    ],
    "operator_biases": {
      "prefer_expansion": true,
      "prefer_connection_over_caveat": true,
      "prefer_interpretation_over_closure": true
    }
  },
  "limits": {
    "do_not_apply_when": ["evidence_strict", "technical_debugging"],
    "requires_confidence_at_least": 0.68
  }
}
```

This makes bridge behavior authoring modular. New behaviors can be added
without rewriting the whole router.

## Operator Design

Each operator should declare:

- `operator_id`
- `purpose`
- `input_state`
- `activation_conditions`
- `state_sensitivities`
- `context_requirements`
- `output_shape`
- `state_effects`
- `evaluation_hooks`

Example:

```json
{
  "operator_id": "extract_abstract_mechanism",
  "purpose": "turn a raw intuition into the underlying dynamic it points at",
  "activation_conditions": {
    "fragment_role": ["idea_fragment", "question"],
    "reasoning_posture": ["expansive", "architectural"],
    "ambiguity_level_min": 0.35
  },
  "state_sensitivities": {
    "if_factual_anchor_low": "preserve speculative language",
    "if_user_goal_build": "include implementation consequences",
    "if_fixation_risk_high": "generate alternate mechanisms"
  },
  "context_requirements": {
    "retrieval_mode": "semantic_narrow",
    "capsule_limit": 4
  },
  "output_shape": {
    "mechanism": "string",
    "supporting_signals": ["string"],
    "uncertainty": "string",
    "next_operator_candidates": ["string"]
  }
}
```

This is the practical version of "reasoning pipelines direct the intelligence
model's reasoning." They do not control hidden neural computation directly.
They control:

- what state is foregrounded
- what context is included
- what operation is requested
- what output shape is expected
- what constraints should be respected
- what evaluator will judge afterward

## TouchDesigner Pattern, Correctly Applied

The useful lesson from TouchDesigner is not that the product needs a visual
node editor immediately.

The useful lesson is architectural:

- small specialized nodes
- explicit wires between nodes
- state flowing through transformations
- inspectable intermediate outputs
- reusable components
- modulators that alter behavior
- subgraphs for common patterns
- feedback loops

The difference is equally important:

- TouchDesigner nodes are mostly deterministic.
- Reasoning nodes are probabilistic and language-mediated.
- Therefore every reasoning node needs confidence, provenance, fallback, and
  evaluation.

The target abstraction is:

`state-aware transformation graph`

Not:

`static prompt chain`

Not:

`agent does everything every turn`

## Knowledge Ocean Connection

The knowledge ocean should become the substrate for bridge-governed retrieval.

It should not be injected wholesale.

The bridge should ask:

1. What is the active object?
2. What dimension is active?
3. What is the user trying to do?
4. What context mode is warranted?
5. Which sources are allowed?
6. What budget is enough?
7. What should remain excluded?

Then it should produce a retrieval bundle.

The retrieval bundle should include:

- query
- seed capsules
- related capsules
- parent object
- relevant bridge behaviors
- source refs
- confidence
- omitted context reason, when useful

Context should be disclosed as an instrument, not as a flood.

## Cross-Dimensional Semantic Interdependence

This architecture should also govern multimodal tool use across dimensions such
as:

- video
- music
- image
- voice
- writing
- interaction
- motion

The key rule is:

`different tools should not receive separate disconnected prompts when they are expressing the same object`

Instead, they should receive different translations of the same shared semantic
state.

The correct model is:

`shared semantic state -> dimension-specific translator -> tool packet`

This means the system should preserve one canonical object identity and let
each medium act as a projection of that object.

Examples of dimensions that may remain interdependent:

- visual language
- sound world
- rhythm and pacing
- symbolism
- narrative role
- emotional pressure
- brand or product meaning

If one dimension changes the meaning of the object, the system should decide
whether that change should propagate into the others.

Example:

- object: `backrooms-style product identity`
- visual state: fluorescent decay, liminal emptiness, institutional repetition
- sound state: low hum, sparse pulses, unresolved tension, spatial unease
- motion state: slow drift, loop logic, delayed reveal
- language state: calm but uncanny explanation

If the active interpretation changes from `institutional dread` to
`dream-navigation infrastructure`, the bridge should not only update the image
prompt. It should also update the downstream music, motion, wording, and
symbolic framing if those dimensions are coupled to the changed variable.

This is semantic interdependence.

It requires these architectural rules:

- keep one shared object state
- track each dimension as a bounded projection of that state
- distinguish locked invariants from free variables
- record which variables each tool packet reads
- record which outputs are allowed to write back into shared state
- propagate only relevant changes across dimensions
- require confirmation before a provisional tool output rewrites canonical
  shared meaning

The bridge should therefore maintain:

- `shared object state`
- `dimension states`
- `dependency edges`
- `translation rules`
- `writeback policy`

Recommended packet structure for multimodal MCP calls:

- `object_id`
- `object_version`
- `dimension_id`
- `shared_invariants`
- `dimension_variables`
- `locked_constraints`
- `free_variables`
- `semantic_dependencies`
- `source_refs`
- `confidence`
- `writeback_mode`

Recommended writeback modes:

- `read_only`
- `provisional`
- `propose_update`
- `confirmed_update`

This matters because multimodal systems drift very quickly when every tool is
allowed to invent semantics independently.

The bridge should decide:

1. which semantic variables are canonical
2. which dimensions depend on which other dimensions
3. whether a change is local or cross-dimensional
4. whether a tool output is only an expression of current state or a proposed
   state mutation
5. whether the mutation should remain provisional or update the object spine

For MCP-connected generation tools, the product should prefer:

- one shared semantic core
- multiple dimension translators
- narrow tool packets
- explicit dependency mapping
- governed writeback into the shared field

Not:

- one independent prose prompt per tool
- unconstrained cross-tool mutation
- silent semantic drift
- no provenance for why a dimension changed

## MCP And External Steering

An external MCP server or self-made sidecar agent can support this architecture.

Its best role is:

- read the conversation
- classify state
- inspect memory
- produce a control packet
- provide bounded context packets
- expose tools for querying the knowledge ocean

Its role should not be:

- silently replace the main agent's judgment
- inject huge hidden context
- make unreviewed durable memory changes
- become an uninspectable personalization layer

External steering should be advisory by default.

Every injected packet should carry:

- source
- timestamp
- confidence
- provenance
- intended use
- expiry
- reason for inclusion

## Reliability Strategy

Reliability comes from constraining the control plane, not from making the
controller "smarter" in an open-ended way.

Required reliability mechanisms:

- strict schemas
- small enums
- confidence thresholds
- deterministic fallback
- inspectable logs
- provenance preservation
- stale-state expiry
- no durable learning below threshold
- explicit correction handling
- separation of raw evidence from inferred state
- per-turn context budgets
- evaluation after execution

Fallback rules:

- If object scope is unclear, stay on `same_main` only when recent context
  strongly supports it.
- If retrieval confidence is low, use `recent_local` or `none`.
- If the user asks for objective evaluation, suppress creative-expansion
  behaviors unless explicitly requested.
- If the user marks `#meta`, attach the turn to the product spine unless another
  primary topic is clearly marked.
- If the user imports external material, isolate it as sidecar until explicitly
  promoted or clearly integrated.
- If the system is tempted to infer hidden psychology, downgrade to observable
  behavior and ask for confirmation only when needed.

## Efficiency Strategy

The system should separate hot path and cold path.

Hot path:

- classify current turn
- update state
- choose context policy
- retrieve small bundle
- route to operator or pipeline
- execute answer
- log result

Cold path:

- build or rebuild knowledge graph
- cluster reasoning trajectories
- summarize long conversations
- promote provisional memories
- update durable profile
- run large evaluations
- regenerate repo index

The hot path should never depend on full cold-path recomputation.

Recommended hot-path budgets:

- focused: recent turn window only, no global retrieval
- contextual: small semantic bundle plus user patterns
- deep: broader graph bundle with strict cap
- incognito: no memory retrieval and no learning

## Implementation Implications

### 1. Runtime Path Debt

Some reasoning and knowledge modules still hardcode legacy paths under:

`product/inner_world_v1/data`

The cleanup introduced canonical runtime layout helpers:

`src/conversation_os/runtime_layout.py`

Reasoning, knowledge, meta, and library runtime paths should converge on
`product_runtime_dir(root, "inner_world_v1", "data")`.

This matters because a state-dependent bridge cannot be reliable if different
modules read and write different runtime locations.

### 2. Control Packet Contract

Add a first-class control packet dataclass or schema.

It should sit between:

- `ContextState`
- `ActiveFieldState`
- `ReasoningResult`

The current system has most fields distributed across state objects. The next
step is to make the handoff explicit.

### 3. Context Policy Contract

Move context budget logic from ad hoc depth-mode defaults into a named
`ContextPolicy`.

It should include:

- retrieval mode
- depth mode
- token budget
- capsule limit
- neighbor limit
- layer allowlist
- layer blocklist
- provenance requirements

### 4. Declarative Bridge Behaviors

Move `BRIDGE_BEHAVIOR_RULES` toward data-backed behavior specs.

Behavior specs should be loadable, testable, and authorable as modular bridge
elements.

### 5. Bridge-Aware Retrieval

`build_retrieval_bundle` should eventually accept a context policy instead of
only query, limit, neighbor limit, and cross-pond flags.

Retrieval should be shaped by:

- active object
- dimension axis
- user goal
- bridge behaviors
- source policy
- context budget

### 6. Inspectability Surface

Expose a simple "why this answer was shaped this way" packet.

It should show:

- active state
- selected bridge behaviors
- selected context mode
- included layers
- omitted layers
- route
- confidence

This is critical because hidden steering will feel unreliable even when it is
technically working.

## Best-Case User Experience

The user can write:

`#meta this reminds me of TouchDesigner, but state dependent`

The bridge detects:

- product scope
- same main object
- architecture dimension
- user goal: design
- tension: flexible field vs reliable control
- retrieval mode: graph contextual
- bridge behavior: implementation scaffold

The main model receives only the right context:

- product thesis
- chat bridge requirements
- reasoning pipeline report
- current runtime module map
- recent user corrections

The answer then produces:

- architecture artifact
- implementation implications
- unresolved risks
- next build step

The user does not have to restate the whole project every time.

## Anti-Patterns

Avoid these.

### Memory Dumping

Pulling every possibly related note into every answer creates noise and false
continuity.

### Hidden Psychology

The system should model observable reasoning moves, corrections, preferences,
and accepted outputs. It should not claim to know the user's hidden mind.

### Static Pipelines

The same pipeline should not run blindly every time a trigger word appears.
State should modulate the pipeline.

### Unbounded Autonomy

The bridge should not silently promote durable memories or mutate product
direction without explicit evidence.

### One Giant Agent

Asking one model to retrieve, classify, route, reason, evaluate, learn, and
write in one hidden pass is hard to debug and hard to trust.

## Acceptance Criteria

The architecture is working when:

- Each turn produces an inspectable state update.
- The system can distinguish new main objects from sub-objects and dimensions.
- Context depth changes with the task instead of staying fixed.
- Bridge behaviors are modular and testable.
- A smaller model can produce valid control packets without writing final prose.
- The main model receives enough context to be useful but not enough to drift.
- User corrections become structured learning events.
- External or imported material is isolated until reintegrated.
- The system can explain why it routed a turn a certain way.
- Runtime state is stored in canonical runtime locations.

## Near-Term Build Order

Recommended implementation sequence:

1. Fix runtime path consistency for reasoning, knowledge, meta, and library
   runtime artifacts.
2. Add `ContextPolicy` and `ControlPacket` schemas.
3. Make bridge classification emit a control packet.
4. Refactor retrieval to consume context policy.
5. Move bridge behaviors into modular declarative specs.
6. Add tests for state-dependent routing and context disclosure.
7. Add an inspectability command or artifact for each reasoning run.
8. Add optional small-model controller behind the same schema.
9. Add MCP-facing tools only after the local control packet is stable.

## Final Architecture Statement

The system should be built as a state-dependent reasoning instrument.

The user does not interact with a generic assistant. The user enters material
into a live semantic field. The bridge reads the field state, selects the next
transformation, discloses the smallest useful context, and steers the main
model through a bounded operation. The result is evaluated, corrections update
the field, and durable learning happens only through governed promotion.

This is how the product becomes "cognitive clay" without becoming chaotic:

`flexible transformation field + strict control packet + bounded context disclosure + inspectable learning`
