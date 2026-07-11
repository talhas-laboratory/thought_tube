# Reasoning Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` when implementing this plan. Steps use checkbox syntax for tracking.

**Goal:** Add a bridge-owned hot-path reasoning runtime that helps users move partial thought fragments into larger idea structures by classifying the turn, binding bounded context, building a live active field, routing to the right reasoning pipeline, evaluating the result, and learning conservatively from user corrections.

**Architecture:** Preserve the repo's current cold-path substrate and derived artifact model. Add a bridge-owned runtime layer that composes workspace-local, session-local, user-local, and global fallback context into a bounded turn packet, then hands that packet into new kernel-owned reasoning modules without overloading existing extraction or retrieval owners.

**Tech Stack:** Python 3.11, existing JSON/JSONL artifact storage, current packet runner and pipeline specs, dataclasses in `models.py`, deterministic heuristics first, optional LLM-backed operators later

---

## Scope and sequencing

This plan intentionally does **not** start with:

- a new external database
- a new orchestrator framework
- UI-first implementation
- full subconscious incubation simulation
- domain-specific pipelines for every creative field

First implementation target:

- explicit bridge-facing runtime contracts
- `ContextState` construction
- explicit runtime contracts
- `ActiveFieldState` construction
- pipeline routing
- one end-to-end `idea_embedding_v1` pipeline
- evaluator output
- conservative learning persistence

Deferred:

- incubation scheduler
- resurfacing engine
- DSPy optimization
- graph-algorithm upgrades
- creative-domain specializations like lyrics, film, or music

## Execution gates

Before any code task starts, run the repo-required guard with the smallest
plausible edit surface for that task.

Required preflight:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "<task-specific request>" \
  --purpose "<concrete user/system effect>" \
  --proposed-paths "<comma-separated task paths>"
```

Rules:

- If the guard is not `ready`, narrow the task before editing code.
- Run `repo-overview refresh` again after adding new modules or manifests.
- Run `repo-overview validate` before handoff.
- Do not casually expand past the declared owner modules if a test failure suggests a wider refactor.

## Problem statement

The system already captures and organizes thought well enough to build a durable substrate. What it does not yet do well is help a user process a live fragment in the moment.

The missing system behavior is:

1. identify what the fragment is really about
2. identify which larger idea or workspace it belongs to
3. choose the smallest useful context bundle
4. activate the right dimensions, tensions, and constraints
5. choose the correct reasoning family
6. produce a useful integration move
7. learn from the user's approval, rejection, or reframing

The implementation should therefore target:

`fragment -> ContextState -> bounded bundle -> active field -> routed pipeline -> evaluation -> outcome -> learning`

The runtime must treat each new turn as new evidence, not as a full reset.

Implementation rule:

- preserve append-only evidence
- update only the affected state variables
- emit structural switch artifacts only when the active topic, goal, object scope, or reasoning mode changes meaningfully

## Existing repo owners to preserve

### Cold path owners that should remain unchanged in responsibility

- `src/conversation_os/storage.py`
- `src/conversation_os/analysis.py`
- `src/conversation_os/analysis_units.py`
- `src/conversation_os/meta_layer.py`
- `src/conversation_os/thread_abstractions.py`
- `src/conversation_os/context_bubbles.py`
- `src/conversation_os/knowledge_layer.py`
- `src/conversation_os/conversation_synthesis.py`
- `src/conversation_os/runtime_pipeline.py`
- `src/conversation_os/library_tracker.py`

### Hot path surfaces to reuse, not replace

- `src/conversation_os/pipelines.py`
- `src/conversation_os/pipeline_runner.py`
- `src/conversation_os/operators.py`
- `src/conversation_os/personal_interface.py`
- `src/conversation_os/personal_interface_mcp.py`
- `src/conversation_os/holodeck.py`

### Important design rule

Do **not** move runtime reasoning into:

- `meta_layer.py`
- `knowledge_layer.py`
- `runtime_pipeline.py`

Those are already clean owners for extraction, retrieval, and rebuild orchestration.

## File map

### New files

- `src/conversation_os/reasoning_bridge.py`
  - classify turns, bind workspace context, assemble bounded context bundles, and record context switches
- `src/conversation_os/active_field.py`
  - compile live runtime context into `ActiveFieldState`
- `src/conversation_os/reasoning_router.py`
  - choose the pipeline family and operator overrides
- `src/conversation_os/reasoning_evaluator.py`
  - judge fit, novelty, ambiguity handling, and integration readiness
- `src/conversation_os/reasoning_learning.py`
  - persist approval/rejection/reframing events into conservative learning artifacts
- `context/substrate/modules/kernel.reasoning.active_field.json`
  - module manifest
- `context/substrate/modules/kernel.reasoning.reasoning_bridge.json`
  - module manifest
- `context/substrate/modules/kernel.reasoning.reasoning_router.json`
  - module manifest
- `context/substrate/modules/kernel.reasoning.reasoning_evaluator.json`
  - module manifest
- `context/substrate/modules/kernel.reasoning.reasoning_learning.json`
  - module manifest
- `tests/test_reasoning_pipeline_runtime.py`
  - end-to-end runtime tests

### Modified files

- `src/conversation_os/models.py`
  - add dataclasses for reasoning request, context state, active field, result, and learning signals
- `src/conversation_os/pipelines.py`
  - add default specs for new reasoning pipelines
- `src/conversation_os/operators.py`
  - add runtime reasoning operators
- `src/conversation_os/personal_interface.py`
  - optional thin hook for consuming reasoning results and bridge-state updates
- `src/conversation_os/personal_interface_mcp.py`
  - optional MCP exposure for bridge-facing tools
- `src/conversation_os/product_inner_world.py`
  - optional later integration point for invoking the new runtime

## Runtime artifact layout

New file-backed artifacts should live under:

- `product/inner_world_v1/data/reasoning_runtime/context_states.jsonl`
- `product/inner_world_v1/data/reasoning_runtime/context_switch_events.jsonl`
- `product/inner_world_v1/data/reasoning_runtime/active_fields.jsonl`
- `product/inner_world_v1/data/reasoning_runtime/reasoning_results.jsonl`
- `product/inner_world_v1/data/reasoning_runtime/reasoning_learning_events.jsonl`
- `product/inner_world_v1/data/reasoning_runtime/reasoning_evaluations.jsonl`

Session-local optional artifacts:

- `memory/sessions/<session_id>/analysis/reasoning_runtime.json`

## Contracts

### `ReasoningRequest`

Purpose:

- the smallest stable object that enters the hot reasoning runtime

Required fields:

- `request_id`
- `session_id`
- `surface`
- `raw_text`
- `source_refs`
- `timestamp`
- `domain_hints`
- `caller_hints`

### `ContextState`

Purpose:

- the bounded turn-time control object that decides what world is active before reasoning begins

Required fields:

- `context_id`
- `request_id`
- `active_topic`
- `object_scope`
- `object_id`
- `parent_object_id`
- `dimension_axis`
- `user_goal`
- `current_tension`
- `answer_shape`
- `active_workspace_id`
- `depth_mode`
- `confidence`
- `bundle_layers`
- `source_refs`
- `attributes`

These fields distinguish whether the current turn belongs to:

- the same main object
- a sub-object on another dimension
- a parallel adjacent object
- a new main object

This is required for stable routing and clean context switching.

### `ActiveFieldState`

Purpose:

- a bounded semantic state for the current turn

Required fields:

- `field_id`
- `request_id`
- `context_id`
- `fragment_role`
- `candidate_parent_ideas`
- `active_dimensions`
- `active_tensions`
- `constraints`
- `ambiguity_level`
- `fixation_risk`
- `novelty_confidence`
- `fit_targets`
- `suggested_reasoning_family`
- `perturbation_markers`
- `state_update_scope`
- `source_refs`
- `retrieval_bundle_summary`
- `attributes`

`perturbation_markers` captures meaningful outside influences on the field.
`state_update_scope` records whether the turn caused a local adjustment, field-level reshaping, or a structural object/context switch.

### `ContextSwitchEvent`

Purpose:

- an inspectable record of meaningful bridge-level state changes

Required fields:

- `event_id`
- `request_id`
- `previous_context_id`
- `new_context_id`
- `trigger`
- `switch_kind`
- `confidence`
- `retrieval_sources`
- `rollback_path`
- `timestamp`
- `attributes`

`switch_kind` should distinguish:

- `local_adjustment`
- `field_reshape`
- `object_shift`
- `workspace_shift`

Not every turn that changes state should be treated as a full context switch.

### `ReasoningResult`

Purpose:

- the machine-facing result of one routed reasoning pass

Required fields:

- `result_id`
- `request_id`
- `field_id`
- `pipeline_id`
- `response_text`
- `integration_verdict`
- `fit_score`
- `novelty_score`
- `confidence`
- `recommended_next_action`
- `operator_trace`
- `attributes`

### `ReasoningLearningEvent`

Purpose:

- a conservative record of how the user responded to the system's reasoning move

Required fields:

- `learning_event_id`
- `request_id`
- `result_id`
- `feedback_kind`
- `accepted_framing`
- `rejected_framing`
- `reframing_text`
- `preferred_abstraction_shift`
- `evidence_refs`
- `sequence_signature`
- `timestamp`
- `attributes`

The learning layer should store observable evidence for why a learning event was inferred.
It should not store broad psychological claims as first-class learned objects in the first version.

## Pipeline families

### First pipeline to implement

`idea_embedding_v1`

Use when:

- the user has a fragment that appears to belong to a larger idea
- ambiguity is moderate to high
- the main task is integration, not factual lookup

Suggested operator steps:

- `classify_fragment_role`
- `identify_parent_ideas`
- `activate_dimensions`
- `detect_fixation_risk`
- `generate_candidate_transformations`
- `score_candidate_transformations`
- `choose_probe_or_integration`
- `build_user_response`

### Second pipeline

`problem_reframing_v1`

Use when:

- the user is solving the wrong problem cleanly
- ambiguity is high but idea placement is premature

Suggested operator steps:

- `extract_problem_surface`
- `detect_problem_mismatch`
- `generate_counterframes`
- `rank_counterframes`
- `build_reframing_probe`

### Third pipeline

`candidate_evaluation_v1`

Use when:

- the user already has a candidate direction
- the main task is whether to keep, suspend, reject, or elaborate it

Suggested operator steps:

- `extract_candidate_claim`
- `score_novelty_vs_fit`
- `check_ambiguity_preservation`
- `check_signal_loss`
- `build_evaluation_summary`

## Module responsibilities

### `reasoning_bridge.py`

Responsibilities:

- classify the turn into a bounded `ContextState`
- bind or confirm the active workspace
- choose `Focused`, `Contextual`, `Deep`, or `Incognito`
- assemble the smallest useful bundle across four layers:
  - session-local
  - workspace-local
  - user-local
  - global fallback
- emit a `ContextSwitchEvent` when topic, goal, depth, or workspace changes

Suggested public API:

```python
def classify_turn(root: Path, request: Dict[str, Any]) -> Dict[str, Any]:
    ...

def bind_workspace(root: Path, context_state: Dict[str, Any]) -> Dict[str, Any]:
    ...

def get_context_bundle(root: Path, context_state: Dict[str, Any], *, budget: Dict[str, Any] | None = None) -> Dict[str, Any]:
    ...

def record_context_switch(root: Path, event: Dict[str, Any]) -> Dict[str, Any]:
    ...
```

Design rules:

- do not create a second knowledge ocean
- keep the bundle smaller than the spec allows by default
- degrade depth before delaying the answer
- preserve source boundaries between session, workspace, user, and global context
- distinguish retrieval context from shaping context

Retrieval context answers: what relevant material should be present?
Shaping context answers: what reasoning environment, abstraction level, and object scope should guide the transformation?

The bridge must own both decisions.

### `active_field.py`

Responsibilities:

- build the `ActiveFieldState`
- merge runtime context from `ContextState`, retrieval bundle, bridge state, thread context, and shape hints
- keep this bounded and inspectable

Suggested public API:

```python
def build_active_field(
    root: Path,
    request: Dict[str, Any],
    *,
    include_cross_pond: bool = False,
) -> Dict[str, Any]:
    ...
```

Inputs it should use:

- retrieval bundle from `knowledge_layer.build_retrieval_bundle`
- bridge state from `personal_interface.load_bridge_state`
- context bundle from `reasoning_bridge.get_context_bundle`
- optional thread packet from `thread_context.build_thread_packet`
- shape hints from existing shape-signature artifacts

### `reasoning_router.py`

Responsibilities:

- inspect `ActiveFieldState`
- select the reasoning family
- optionally set operator overrides or fallback routes

Routing factors:

- ambiguity level
- fixation risk
- fragment role
- candidate parent idea count
- whether the field suggests expansion, reframing, or evaluation

### `reasoning_evaluator.py`

Responsibilities:

- score useful transformation rather than raw textual plausibility

Required checks:

- novelty preservation
- fit to parent idea
- ambiguity handling
- tension preservation
- generic flattening risk
- integration readiness

Output verdicts:

- `integrate`
- `suspend`
- `reject`
- `preserve_tension`
- `needs_more_probe`

### `reasoning_learning.py`

Responsibilities:

- persist user corrections
- update long-lived behavioral tendencies conservatively
- never rewrite the whole profile from one turn

Learning categories:

- accepted framing
- rejected framing
- preferred abstraction depth
- tolerance for preserved tension
- repeated transformation choices

Important limit:

The first version should learn routing and transformation preferences conservatively.
It should not claim to model the user's full latent operator system yet.

## Implementation tasks

## Task 1: Add runtime dataclasses

**Files:**
- Modify: `src/conversation_os/models.py`
- Create: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing contract tests**

Add tests for:

- `ReasoningRequest`
- `ContextState`
- `ContextSwitchEvent`
- `ActiveFieldState`
- `ReasoningResult`
- `ReasoningLearningEvent`

Assert:

- required fields exist
- `to_dict()` round-trips cleanly
- optional attributes default sanely
- values remain JSON-serializable
- `object_scope` round-trips cleanly
- `parent_object_id` and `dimension_axis` behave sanely when absent
- `state_update_scope` stays JSON-serializable
- `perturbation_markers` defaults to an empty list

- [ ] **Step 2: Implement dataclasses**

Add the new runtime dataclasses to `models.py`.

- [ ] **Step 3: Run contract tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k contract -v
```

## Task 2: Implement `reasoning_bridge.py`

**Files:**
- Create: `src/conversation_os/reasoning_bridge.py`
- Modify: `src/conversation_os/models.py`
- Modify: `src/conversation_os/personal_interface_mcp.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing bridge tests**

Cover:

- topic classification into `ContextState`
- workspace binding with and without an active workspace
- depth-mode selection
- bounded bundle assembly across layers
- context-switch event emission on topic or workspace change
- same main object, different dimension
- promotion from sub-object to new main object
- local adjustment that does not emit a structural switch

- [ ] **Step 2: Implement bridge runtime**

Rules:

- do not query the whole library directly
- reuse `build_retrieval_bundle()`, `load_bridge_state()`, and Holodeck workspace state
- keep all scoring deterministic in the first pass
- keep output bounded and inspectable

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k bridge -v
```

## Task 3: Implement `active_field.py`

**Files:**
- Create: `src/conversation_os/active_field.py`
- Modify: `src/conversation_os/models.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing active-field tests**

Cover:

- request with one clear parent idea
- request with multiple possible parent ideas
- request with high ambiguity and no strong parent
- retrieval-bundle integration
- bridge-state integration
- `ContextState` integration

- [ ] **Step 2: Implement active-field builder**

Rules:

- depend on `reasoning_bridge.get_context_bundle()`
- do not query the whole library directly
- keep all scoring deterministic in the first pass
- keep output bounded and inspectable

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k active_field -v
```

## Task 4: Implement router and pipeline specs

**Files:**
- Create: `src/conversation_os/reasoning_router.py`
- Modify: `src/conversation_os/pipelines.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing routing tests**

Cases:

- high ambiguity fragment routes to `problem_reframing_v1`
- clear placement fragment routes to `idea_embedding_v1`
- candidate-rich fragment routes to `candidate_evaluation_v1`

- [ ] **Step 2: Add pipeline specs**

Add defaults for:

- `idea_embedding_v1`
- `problem_reframing_v1`
- `candidate_evaluation_v1`

- [ ] **Step 3: Implement router**

Keep the routing deterministic at first.

- [ ] **Step 4: Run tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k routing -v
```

## Task 5: Extend operator registry

**Files:**
- Modify: `src/conversation_os/operators.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing operator tests**

Cover the first runtime operators:

- `classify_fragment_role`
- `identify_parent_ideas`
- `activate_dimensions`
- `detect_fixation_risk`
- `generate_candidate_transformations`
- `score_candidate_transformations`
- `choose_probe_or_integration`
- `build_user_response`

- [ ] **Step 2: Implement operators**

Rules:

- follow current patch-based operator style
- keep outputs additive to the packet
- do not hide important reasoning state in freeform text

- [ ] **Step 3: Run operator tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k operators -v
```

## Task 6: Implement evaluator

**Files:**
- Create: `src/conversation_os/reasoning_evaluator.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing evaluator tests**

Cases:

- novelty preserved but fit low
- fit high but generic collapse
- good integration candidate
- productive unresolved tension

- [ ] **Step 2: Implement evaluator**

Keep the first version deterministic and file-backed.

- [ ] **Step 3: Run evaluator tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k evaluator -v
```

## Task 7: Add learning-event persistence

**Files:**
- Create: `src/conversation_os/reasoning_learning.py`
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Write failing persistence tests**

Cases:

- accepted framing
- rejected framing
- reframing note
- repeated transformation updates

- [ ] **Step 2: Implement conservative update logic**

Rules:

- no full-profile overwrite
- weighted accumulation over repeated signals
- preserve provenance on every learning event
- derive learning only from observable corrections, approvals, reframings, and repeated transformation choices
- avoid storing ungrounded personality or cognition claims

- [ ] **Step 3: Run tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k learning -v
```

## Task 8: End-to-end runtime path

**Files:**
- Modify: `src/conversation_os/product_inner_world.py` or a thin runtime entrypoint module
- Modify: `src/conversation_os/personal_interface_mcp.py` if MCP exposure is part of the slice
- Test: `tests/test_reasoning_pipeline_runtime.py`

- [ ] **Step 1: Wire a thin entrypoint**

Suggested orchestration:

1. build `ReasoningRequest`
2. classify turn into `ContextState`
3. bind workspace and assemble bounded bundle
4. build `ActiveFieldState`
5. route pipeline
6. run packet pipeline
7. evaluate result
8. persist runtime artifacts
9. persist context-switch event when emitted

- [ ] **Step 2: Add end-to-end tests**

Use a synthetic fragment such as:

- vague product idea
- lyric line with ambiguous role
- tension-heavy research fragment

- [ ] **Step 3: Run targeted tests**

Run:

```bash
pytest tests/test_reasoning_pipeline_runtime.py -k end_to_end -v
```

## Validation

Before claiming readiness:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
pytest tests/test_reasoning_pipeline_runtime.py -v
```

If `product_inner_world.py` is touched:

```bash
pytest tests/test_conversation_os.py -k inner_world -v
```

## Success criteria

The first slice is successful if:

- a fragment can be turned into a bounded `ContextState`
- the bridge can bind or confirm the right workspace and depth mode
- a fragment can be turned into a bounded active field
- the system can route to the correct reasoning family
- the packet runner can execute a reasoning pipeline end to end
- the evaluator can distinguish integrate vs suspend vs reject
- user correction can be persisted as a learning signal
- the implementation does not overload current cold-path owners

## Deferred work

After the first slice works, the next major step is:

- `incubation.py`
- `resurfacing.py`

Those should implement:

- unresolved-fragment replay
- latent link generation
- resurfacing triggers under matched active fields

Do not start there. The hot path must become correct before the slow path becomes clever.

## Philosophical alignment note

This implementation order matches the framework established in the conversation:

- start with symbiotic steering, not full automation
- keep the main runtime bounded and inspectable
- learn user-specific transformation habits gradually from conversation
- separate fast conscious-turn support from slower resurfacing and incubation

The bridge layer solves turn-time orientation and bounded context.
The reasoning runtime solves structured transformation.
The later slow loop will address resurfacing and latent recombination.
