# Connections

This file is the map that prevents isolated subprojects from drifting.

## Core Flow

```text
Evidence
  -> PurposeState
  -> ObjectTopology
  -> ContextFrame
  -> ContextPolicy
  -> SessionEnvelope
  -> Execution
  -> SemanticGate
  -> PromotionPolicy
  -> WorkPacket or durable memory
```

## Interface Rules

- `PurposeState` informs routing, answer shape, and lens selection.
- `ObjectTopology` decides whether material belongs to the main spine, a sub-object, a sidecar, or a new object.
- `ContextFrame` decides what belongs in the reasoning environment.
- `FrameSpec` is the declarative membership request for a frame.
- `FrameBundle` is the compiled and provenance-tagged result of frame assembly.
- `ContextPolicy` decides what can be disclosed to execution.
- `SessionEnvelope` enforces boundary and learning rules.
- `LensPack` contributes domain-specific extraction, schemas, evaluators, and packet templates.
- `SemanticGate` determines whether an output can be trusted, revised, handed off, or promoted.
- `PromotionPolicy` decides whether material stays ephemeral, becomes provisional, or enters durable memory.
- `WorkPacket` turns approved context into scoped agent work.
- `FreshnessRecord` warns when reused context may be stale or conflicting.
- `SurfaceProfile` maps the same substrate into the affordances of each tool.
- `WorkspaceBinding` defines how the same objective is represented across the product spine, Holodeck, workboard, task pack, and linked sessions.
- `ElementBinding` defines which product element (`frontend`, `backend`, `marketing`, `monetization`) a session or Holodeck belongs to.
- `ElementProposal` proposes element membership for ingests and unbound turns; it does not imply durable promotion.
- `ElementCapture` stores provisional element-scoped material before promotion gates pass.
- `ElementPromotion` moves approved captures into durable element memory with provenance and rollback path.

## Anti-Drift Rules

- A subproject may add a field to a shared contract only if it updates this file.
- A task crossing two or more systems must name the connection it is changing.
- Durable memory promotion must pass through capture/promotion and correction/reversibility gates.
- Agent work must carry the source frame and verification gates that justified it.
- Surface-specific behavior must not fork the ontology; it belongs in `SurfaceProfile`.
- Shared work must not create competing sources of truth; workspace ownership must follow `SHARED_WORKSPACES.md`.
