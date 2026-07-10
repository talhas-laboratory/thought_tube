# Semantic Operating Layer

Owner: `talha`  
Created: `2026-06-26T16:37:49Z`  
Status: `active-spine`

## Purpose

Build Inner Space as a small system of interconnecting systems: a portable semantic operating layer that turns raw thought into structured context, executable guidance, evaluated feedback, and durable project/world memory.

This folder is the product spine for that work. It keeps the domains separate enough for agents to work independently, but connected enough that decisions, gates, and progress do not drift.

## Pillars

- `elegance`: prefer small durable contracts over sprawling process.
- `modularity`: each domain owns a narrow surface and clear interfaces.
- `reliability`: every task has gates, verification evidence, and residual-risk notes.
- `continuity`: updates are append-only; decisions are logged before they are relied on.
- `provenance`: separate raw evidence, interpretation, inference, and promoted structure.
- `reversibility`: support correction, demotion, rollback, and isolation by design.

## Operating Model

1. Start with the spine: read `README.md`, `SYSTEMS.md`, `CONNECTIONS.md`, `GATES.md`, and recent `UPDATES.jsonl`.
2. Choose one subproject packet in `subprojects/`.
3. Add or claim a task in that packet before implementation.
4. Record architectural decisions in `DECISIONS.md`.
5. Append meaningful activity to `UPDATES.jsonl`.
6. Do not mark work complete unless the gates in `GATES.md` are satisfied.

## Product Shape

The core loop:

`Evidence -> State -> Frame -> Policy -> Envelope -> Execution -> Evaluation -> Promotion`

The bridge remains the control plane. The knowledge ocean remains raw material. Frames, envelopes, lenses, evaluators, and workboards shape that material into useful action.

## Files

- `SYSTEMS.md`: canonical list of subprojects and their responsibilities.
- `ELEMENTS.md`: product element registry (frontend, backend, marketing, monetization).
- `ELEMENT_CONTRACTS.md`: contracts for element binding, capture, and promotion.
- `CONNECTIONS.md`: interface map between subprojects.
- `SHARED_WORKSPACES.md`: shared workspace stack and source-of-truth rules.
- `FRAME_CONTRACTS.md`: detailed contracts for `FrameSpec`, `FrameBundle`, and `SessionEnvelope`.
- `GATES.md`: mandatory quality and completion gates.
- `DECISIONS.md`: durable product and architecture decisions.
- `UPDATES.jsonl`: append-only change history.
- `ROADMAP.md`: phased build sequence.
- `AGENTS.md`: agent rules for this product folder.
- `subprojects/`: one packet per domain.
- `artifacts/`: plans, evidence, diagrams, and generated outputs.
- `inbox/`: untriaged notes or imported sidecar material.
