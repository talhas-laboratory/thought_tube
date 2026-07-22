# Frame Contracts

Owner: `codex`  
Status: `draft-contract`

This file defines the first detailed contracts for `FrameSpec`, `FrameBundle`, and `SessionEnvelope`.

These are build-facing contracts. They are not yet implementation schemas, but they are specific enough to drive code shape, tests, and agent handoff.

## Purpose

The bridge needs one explicit way to answer three different questions:

1. What context should be considered?
2. What context was actually assembled?
3. What boundary and learning rules govern this turn?

Those questions map to three separate contracts:

- `FrameSpec`: declarative request for context membership.
- `FrameBundle`: compiled, inspectable result of frame assembly.
- `SessionEnvelope`: boundary and learning contract for the session/turn.

The core rule is separation of concerns:

- `FrameSpec` chooses membership candidates.
- `FrameBundle` records compiled membership with provenance.
- `ContextPolicy` controls disclosure to execution.
- `SessionEnvelope` controls session boundaries, memory behavior, and learning side effects.

### Disclosure law (2026-07-17)

Program workspace: `cognitive-aperture-exceptional` (`ADR-001`).

Treat four jobs as distinct:

1. **Orient** — thin state/posture prose places the model.
2. **Grant** — layers, refs, budgets, envelope mode (`ContextPolicy` + envelope).
3. **Evidence** — high-SNR material actually opened under the grant.
4. **Receipt** — audit/handoff record (packet / `FrameBundle` / control snapshot).

Execution prompts may include orientation, thin steering constraints, and evidence only.  
Omitted or suppressed membership details belong on audit/inspect surfaces, not in the execution prompt.  
Bounded/strict retrieval should fail empty when there is no positive match.

## Relationship To Existing Bridge Objects

`ControlPacket` remains the execution handoff.

Target assembly order (normative for exceptional hardening):

```text
ReasoningRequest
  -> ActiveState / orientation
  -> FrameSpec (grant/selectors; may be preview in v1)
  -> DisclosureGrant / ContextPolicy + SessionEnvelope
  -> Evidence assembly (retrieval + layer trim + token budget)
  -> ControlPacket + FrameBundle receipt
  -> execution (orientation + evidence only)
```

Historical v1 sketch (still partially true in code):

```text
ReasoningRequest
  -> FrameSpec
  -> FrameBundle
  -> ContextPolicy
  -> SessionEnvelope
  -> ControlPacket
  -> execution
```

In v1:

- `FrameSpec` may be preview-only.
- `FrameBundle` may be materialized only for inspection/testing.
- `SessionEnvelope` may initially compile into existing `depth_mode`, retrieval budgets, and learning guards.
- Hardening work must close gaps where code retrieves before orientation or leaks suppressed blocks into execution.

## FrameSpec

### Role

`FrameSpec` is a declarative request for how a reasoning frame should be assembled.

It must not contain the final answer, hidden execution instructions, or raw retrieved payloads. It is a selection contract, not a response artifact.

### Required Fields

- `frame_id`: stable frame identifier.
- `request_id`: originating request.
- `session_id`: active session.
- `workspace_id`: active workspace if present.
- `active_topic`: current topic the frame is about.
- `object_scope`: expected topology scope such as `same_main`, `sub_object`, `sidecar`, or `new_object`.
- `object_id`: target object if already known.
- `envelope_mode`: `open`, `bounded`, `strict`, or `incognito`.
- `selectors`: ordered selector list.
- `pins`: explicitly pinned sources or blocks that must be preserved if valid.
- `exclusions`: explicitly blocked sources, layers, or objects.
- `budget_hints`: desired frame assembly limits.
- `preview_only`: whether the frame is only being assembled for inspection.

### Selector Shape

Each selector should answer:

- what layer it targets
- how strongly it is requested
- what query/filter it applies
- whether it is required, preferred, optional, or blocked

Minimum selector fields:

- `selector_id`
- `layer`: `session`, `workspace`, `user`, `global`, `artifact`, or `manual`
- `match_mode`: `required`, `preferred`, `optional`, or `blocked`
- `query`: topic, phrase, or reference target
- `filters`: tags, object ids, source refs, thought ids, or freshness limits
- `reason`: why this selector exists

### Budget Hints

`budget_hints` are assembly hints, not disclosure policy. They may include:

- `max_blocks`
- `max_session_events`
- `max_capsules`
- `max_neighbors`
- `allow_cross_pond`
- `allow_workspace_context`

### Invariants

- `FrameSpec` decides what should be considered, not what the model is allowed to see.
- `FrameSpec` may request a layer that the eventual `ContextPolicy` or `SessionEnvelope` later suppresses.
- A spec must be reproducible from request plus declared state. No hidden ambient selectors.
- Pins override preference ordering but not hard safety or boundary rules.
- Exclusions are first-class. The system must be able to say what was intentionally kept out.

## FrameBundle

### Role

`FrameBundle` is the compiled result of applying a `FrameSpec` to available evidence.

It is the answer to: "What did the system actually assemble, what was rejected, and why?"

### Required Fields

- `bundle_id`
- `frame_id`
- `request_id`
- `session_id`
- `workspace_id`
- `envelope_mode`
- `assembly_status`: `complete`, `partial`, or `empty`
- `included_blocks`
- `rejected_selectors`
- `suppressed_blocks`
- `provenance_summary`
- `assembly_metrics`

### Included Block Shape

Each included block should carry:

- `block_id`
- `layer`
- `source_ref`
- `source_kind`
- `summary`
- `reason_included`
- `selector_ids`
- `token_estimate`
- `freshness_state`
- `disclosure_state`

`disclosure_state` is important because a block may belong to the frame and still be excluded from execution.

### Rejected Selectors

The bundle must show selectors that failed and why. Common reasons:

- `no_matches`
- `blocked_by_envelope`
- `blocked_by_policy`
- `freshness_rejected`
- `budget_exhausted`
- `invalid_reference`

### Suppressed Blocks

`suppressed_blocks` represent material that matched and was assembled conceptually but was not carried forward because of:

- envelope mode
- disclosure policy
- budget truncation
- provenance failure

This is how the product preserves inspectability without leaking excluded content into execution.

### Assembly Metrics

Minimum metrics:

- `session_event_count`
- `workspace_block_count`
- `user_pattern_count`
- `global_capsule_count`
- `rejected_selector_count`
- `suppressed_block_count`
- `estimated_token_cost`

### Invariants

- Every included block must carry provenance.
- Every rejected selector must carry a reason.
- Membership and disclosure remain separate.
- A `FrameBundle` may be valid even when execution receives only a trimmed subset.
- Preview mode must be able to render bundle structure without forcing execution.

## SessionEnvelope

### Role

`SessionEnvelope` defines the boundary conditions for a turn or session.

It answers:

- what kinds of context are allowed to participate
- what kinds of learning/persistence are allowed
- how isolated the current turn should be

### Required Fields

- `envelope_id`
- `session_id`
- `request_id`
- `mode`
- `allowed_layers`
- `default_blocked_layers`
- `learning_mode`
- `persistence_mode`
- `cross_session_mode`
- `sidecar_mode`
- `explicit_includes`
- `explicit_excludes`

### Mode Semantics

#### `open`

Use for normal exploratory or implementation work.

- Allowed by default: `session`, `workspace`, `user`, `global`
- Cross-session carry: permitted if explicitly routed through existing product rules
- Learning: allowed
- Durable side effects: allowed if downstream gates pass

#### `bounded`

Use for normal product work that should stay narrow and inspectable.

- Allowed by default: `session`, `workspace`
- `user` and `global`: allowed only through bounded selectors and declared budgets
- Cross-session carry: discouraged by default
- Learning: allowed
- Durable side effects: allowed if explicit gates pass

#### `strict`

Use when the user wants high isolation but not full privacy erasure.

- Allowed by default: `session`
- `workspace`, `user`, `global`: excluded unless explicitly selected
- Cross-session carry: off by default
- Learning: allowed only for explicitly allowed local/session-scoped signals
- Durable side effects: blocked unless separately approved

#### `incognito`

Use when the user wants privacy-first ephemeral reasoning.

- Allowed by default: current turn/session-local only
- `workspace`, `user`, `global`: off unless a future explicit exception contract is introduced
- Cross-session carry: off
- Learning: off
- Durable side effects: off

### Envelope Invariants

- `incognito` leaves no durable learning side effects.
- `strict` is not the same as `incognito`; strict can still preserve narrow session continuity.
- `bounded` is the default recommended mode for product work.
- Envelope mode constrains both frame assembly and post-execution persistence.
- Envelope decisions must be inspectable from logs and test output.

## Contract Interaction Rules

### Frame membership vs disclosure

This distinction is mandatory:

- `FrameSpec` can request membership from many layers.
- `FrameBundle` records what matched.
- `ContextPolicy` decides what execution can see.
- `SessionEnvelope` may further suppress layers or side effects.

Example:

- a global capsule may appear in `FrameBundle.suppressed_blocks`
- the same capsule may never appear in the execution prompt
- the operator can still inspect why it was withheld

### Session continuity

The canonical session corpus for bridge work is `memory/events/{session_id}.jsonl`.

Bridge-only ledgers may exist for audit/provenance, but session-local retrieval should read one declared corpus path.

### Workspace binding

If a frame depends on workspace context:

- the workspace id must be explicit
- the source workspace owner must be unambiguous
- imported sidecar material must remain provenance-tagged

## Failure Modes To Design For

- selectors silently degrade and the user cannot see why
- bundle membership and execution disclosure get conflated
- strict mode accidentally leaks user/global/workspace layers
- incognito mode writes learning or promotion side effects
- bridge session evidence lands in a side ledger but not in the declared session corpus
- pinned context overrides boundary rules and creates hidden leakage

## First Test Matrix

These are the first contract tests the implementation should satisfy:

- `test-frame-contracts`
  - proves `FrameSpec`, `FrameBundle`, and `SessionEnvelope` are named consistently across the spine
  - proves membership and disclosure are described as separate responsibilities
- `test-session-corpus`
  - proves strict session retrieval reads the canonical session corpus path
- `test-retrieval-timing`
  - proves candidate retrieval can happen before final execution policy narrows disclosure
- future `test-session-envelope-modes`
  - proves `open`, `bounded`, `strict`, and `incognito` compile to distinct boundary behaviors
- future `test-frame-bundle-preview`
  - proves preview includes included blocks, rejected selectors, suppressed blocks, and provenance

## Build Order

Implement in this order:

1. contract docs and acceptance language
2. preview-only `FrameSpec` and `FrameBundle`
3. `SessionEnvelope` compilation into current bridge/runtime policy
4. explicit preview rendering
5. evaluator and promotion gates that depend on envelope mode
