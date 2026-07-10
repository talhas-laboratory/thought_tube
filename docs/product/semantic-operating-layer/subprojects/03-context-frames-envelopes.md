# Context Frames and Envelopes

Status: `active-workspace`  
Owner: `codex`  
First contracts: `FrameSpec`, `FrameBundle`, `SessionEnvelope`

## Responsibility

Define the reasoning environment and enforce its boundaries.

Detailed contract reference: [FRAME_CONTRACTS.md](/Users/talhauddin/software/inner_space/docs/product/semantic-operating-layer/FRAME_CONTRACTS.md:1)

## Scope In

- prompt-compiled frame selectors
- frame preview
- provenance-tagged frame bundles
- session isolation modes
- pin-only execution

## Scope Out

- full web/upload ingestion
- durable promotion policy
- lens-specific extraction

## Integration

Consumes purpose, topology, session corpus, and freshness. Feeds execution and evaluator gates.

## Active Workspace

- Holodeck workspace: `sol-context-frames`
- Linked workboard: `docs/workboards/semantic-operating-layer-context-frames/`
- Linked session: `session-gpt-bridge-2026-04-24`
- Materialized view: [brief.md](/Users/talhauddin/software/inner_space/context/workspaces/sol-context-frames/brief.md:1)

## First Tasks

- Fix candidate retrieval timing.
- Unify bridge session corpus.
- Add preview-only `FrameSpec` and `FrameBundle`.
- Define `SessionEnvelope` modes: `open`, `bounded`, `strict`, `incognito`.
- Keep task-pack handoff blocked until the repo atlas/manifests are ready again.

## Acceptance Criteria

- Frame membership is separate from disclosure policy.
- Strict mode excludes global/user/workspace unless explicitly selected.
- Preview shows included blocks, rejected selectors, and provenance.

## Contract Summary

### `FrameSpec`

Declarative request for frame assembly.

- names selectors, pins, exclusions, and assembly budgets
- decides what context should be considered
- does not carry raw retrieved payloads or execution-only instructions

### `FrameBundle`

Compiled frame result.

- records included blocks, rejected selectors, suppressed blocks, and provenance
- keeps membership visible even when disclosure later narrows execution context
- is the basis for preview and inspection

### `SessionEnvelope`

Boundary and learning contract.

- `open`: broad normal work
- `bounded`: narrow default work
- `strict`: session-first isolation, others only by explicit selection
- `incognito`: no durable learning or broad retrieval side effects
