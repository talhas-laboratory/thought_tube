# Note Agent Knowledge Ocean Architecture Plan

## Goal

Turn the notes agent into a state-sensitive interpreter for raw thought input.

Desired loop:

1. User enters a raw thought in the notes UI.
2. The system preserves the raw thought as captured input.
3. The note agent interprets the thought across semantic and emotional/state dimensions.
4. The system places the thought into the knowledge ocean and retrieves relevant material.
5. The reply is shaped by the user's current mode or mood, not just semantic similarity.

This should preserve the current strengths of the runtime:

- OpenClaw remains the primary speaker.
- The bridge/runtime stack remains the orchestration substrate.
- The knowledge ocean remains bounded by policy rather than exposed wholesale.

## Current Runtime

The current note-agent path is already close to the target architecture.

### Input path

- `append_mobile_capture(...)` in `src/conversation_os/product_inner_world.py`
  - stores the raw capture in the mobile session
  - already calls `ingest_to_element_space(...)`
- `reply_in_mobile_session(...)` in `src/conversation_os/product_inner_world.py`
  - reads the current mobile session
  - calls `_request_mobile_session_reply(...)`
  - appends user and assistant events to the same session

### Reasoning path

- `_request_mobile_session_reply(...)` in `src/conversation_os/product_inner_world.py`
  - routes the reply through `run_reasoning(...)`
- `run_reasoning(...)` in `src/conversation_os/reasoning_runtime.py`
  - classifies the turn
  - builds context state and bundle
  - builds active field
  - routes reasoning
  - uses OpenClaw via `request_bridge_execution_reply(...)`

### Context path

- `get_context_bundle(...)` in `src/conversation_os/reasoning_bridge.py`
  - can expose:
    - `session_local`
    - `workspace_local`
    - `user_local`
    - `global_fallback`
- `global_fallback` is the actual knowledge-ocean retrieval path
- current live default is `session_only` in `product/inner_world_v1/config/runtime.json`

### Important constraint

The note agent already uses OpenClaw as the primary speaker.

That means this architecture should not replace the reply layer with a deterministic state machine. It should enrich the bridge/runtime layer and let OpenClaw remain the visible conversational surface.

## Target Architecture

Add four first-class runtime objects to the note-agent flow.

### 1. Thought Interpretation

Purpose:

- transform raw capture into a structured interpretation without collapsing ambiguity too early

Fields:

- `topic_signals`
- `tension_signals`
- `intent`
- `abstraction_level`
- `emotional_weight`
- `symbolic_weight`
- `practical_weight`
- `novelty_weight`
- `continuation_pressure`

Output:

- a `thought_interpretation` object stored in runtime state and attached to the reasoning request lifecycle

### 2. User State

Purpose:

- infer the user's current mode or mood for this turn/session

Initial state categories:

- `dump`
- `reflective`
- `exploratory`
- `emotionally_loaded`
- `evaluative`
- `practical`
- `decisive`

Fields:

- `mode`
- `confidence`
- `pace`
- `response_pressure`
- `retrieval_appetite`
- `preferred_shape`

Output:

- a `user_state` object attached to `context_state.attributes`

### 3. Retrieval Policy

Purpose:

- decide how much of the knowledge ocean to expose for this turn

Fields:

- `retrieval_mode`
  - `session_only`
  - `session_plus_ocean`
  - `ocean_wide`
- `cross_ocean`
- `retrieval_limit`
- `neighbor_limit`
- `include_layers`
- `exclude_layers`
- `anchor_strategy`

Key rule:

- mood/state must drive retrieval policy
- mood is not just tone; it changes retrieval breadth and abstraction

### 4. Response Mode

Purpose:

- decide what kind of reply should be generated before text generation starts

Initial modes:

- `silent_ack`
- `resonance`
- `continuation_cue`
- `reframing`
- `synthesis`
- `evaluation`
- `action_suggestion`
- `structure_proposal`

This mode should shape:

- directness
- length
- abstraction
- whether ambiguity is preserved or reduced

## Runtime Mapping

### A. Preserve raw capture

Use:

- `append_mobile_capture(...)`

Change:

- ensure every raw note is preserved as-is before any interpretation pass
- keep interpretation as an attached layer, not a rewrite of the original capture

Files:

- `src/conversation_os/product_inner_world.py`
- possibly `src/conversation_os/element_ingest.py`

### B. Add interpretation pass before response generation

Use:

- `reply_in_mobile_session(...)`
- `_request_mobile_session_reply(...)`
- `run_reasoning(...)`

Change:

- add a note-agent-specific interpretation stage before route execution
- derive `thought_interpretation` and `user_state` from:
  - current user message
  - recent session events
  - capture mode / response contract when available

Files:

- `src/conversation_os/product_inner_world.py`
- `src/conversation_os/reasoning_runtime.py`
- new module: `src/conversation_os/note_agent_state.py`

### C. Make user state explicit in runtime models

Change:

- extend request/runtime model shapes so state can travel through the reasoning stack

Files:

- `src/conversation_os/models.py`

Recommended additions:

- `ThoughtInterpretation`
- `UserState`
- `RetrievalPolicy`
- `ResponseModeDecision`

### D. Teach the bridge to use state-sensitive retrieval

Use:

- `get_context_bundle(...)`

Change:

- allow note-agent requests to override default `session_only` when state requires broader context
- keep `session_only` for dump mode
- widen to `session_plus_ocean` for reflective/exploratory/evaluative modes
- allow `ocean_wide` only for deliberate deep retrieval modes

Suggested policy examples:

- `dump`
  - `session_only`
  - small response
  - minimal interruption
- `reflective`
  - `session_plus_ocean`
  - resonance and unresolved tension neighbors
- `practical`
  - `session_plus_ocean`
  - plans, prior decisions, action patterns
- `evaluative`
  - `session_plus_ocean`
  - objective and contrastive retrieval
- `exploratory`
  - `session_plus_ocean`
  - broader associative neighbors without flattening

Files:

- `src/conversation_os/reasoning_bridge.py`
- `src/conversation_os/bridge_controller.py`
- `product/inner_world_v1/config/runtime.json`

### E. Make response mode part of route execution

Use:

- `build_active_field(...)`
- `route_reasoning(...)`
- `request_bridge_execution_reply(...)`

Change:

- compute `response_mode` before generation
- pass that into the execution control packet / active field
- instruct OpenClaw to answer in that mode without exposing internal mechanics

Files:

- `src/conversation_os/active_field.py`
- `src/conversation_os/reasoning_router.py`
- `src/conversation_os/reasoning_runtime.py`
- `src/conversation_os/chat_backends.py`

## Recommended New Modules

### `src/conversation_os/note_agent_state.py`

Responsibilities:

- infer `ThoughtInterpretation`
- infer `UserState`
- choose `RetrievalPolicy`
- choose `ResponseModeDecision`

Public functions:

- `interpret_note_turn(...)`
- `infer_user_state(...)`
- `build_note_retrieval_policy(...)`
- `select_note_response_mode(...)`

### `product/inner_world_v1/config/note_agent.json`

Purpose:

- keep note-agent behavior separate from meta-agent behavior

Contents:

- state categories
- retrieval defaults by state
- response mode policies
- guardrails for interruption vs continuation

## Implementation Phases

### Phase 1: Runtime state layer

Goal:

- introduce `ThoughtInterpretation` and `UserState` without changing visible note replies much

Work:

- add models
- add `note_agent_state.py`
- store derived state inside `context_state.attributes`
- add tests for state inference only

### Phase 2: State-sensitive retrieval

Goal:

- let note replies use the knowledge ocean intentionally

Work:

- map user state to retrieval policy
- allow note-agent requests to move beyond `session_only`
- test retrieval layer selection and boundedness

### Phase 3: Response-mode shaping

Goal:

- control reply type by state

Work:

- add response-mode decision
- pass it into execution prompt/control packet
- adjust OpenClaw execution prompt so it responds differently for:
  - continuation
  - resonance
  - evaluation
  - structure

### Phase 4: Ocean-aware categorization persistence

Goal:

- make each note contribute durable placement into the knowledge ocean

Work:

- persist interpretation/categorization artifacts
- attach ocean placement provenance
- improve future retrieval from prior note interpretations

## Testing Plan

### Unit tests

- state inference from note text
- retrieval policy selection from user state
- response mode selection from state + interpretation

### Integration tests

- `reply_in_mobile_session(...)` with:
  - dump-mode input
  - reflective input
  - practical input
  - evaluative input
- verify bundle layer exposure changes appropriately

### Behavioral tests

- raw dump does not trigger heavy clarifying response
- reflective input can retrieve resonant prior material
- practical input returns more concrete next moves
- evaluative input returns cleaner contrast/risk framing

Files likely to extend:

- `tests/test_conversation_os.py`
- `tests/test_mobile_capture_compose.py`
- new:
  - `tests/test_note_agent_state.py`
  - `tests/test_note_agent_retrieval_policy.py`

## Product Risks

### 1. Over-reading mood

Risk:

- system becomes overly interpretive or presumptive

Mitigation:

- keep confidence scores
- use low-risk defaults
- preserve ambiguity until confidence rises

### 2. Context bloat

Risk:

- note replies become slow, muddy, or over-informed

Mitigation:

- make retrieval policy explicit and state-bounded
- keep `session_only` as valid for low-intervention modes

### 3. Visible over-structuring

Risk:

- the notes app starts feeling like a workflow tool instead of a thought surface

Mitigation:

- keep state and interpretation internal
- only expose structure when user state indicates readiness

## Recommended First Cut

Build only these pieces first:

1. `note_agent_state.py`
2. new model objects in `models.py`
3. state inference wiring inside `run_reasoning(...)`
4. retrieval-policy switching inside `get_context_bundle(...)`

Do not change the note UI contract first.
Do not replace OpenClaw as the speaker.
Do not expose mood/state labels to the user by default.

## Decision

The note agent should be built as:

- OpenClaw conversation on the surface
- state-sensitive interpretation and retrieval underneath
- knowledge-ocean categorization as durable substrate

That is the cleanest path to the product vision without repeating the meta-agent overengineering problem.
