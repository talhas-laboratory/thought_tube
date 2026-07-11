# Decisions

Durable decisions only. Keep entries short and cite the source when possible.

## 2026-06-26 — Create Product Spine

Decision: create `docs/product/semantic-operating-layer/` as the coordination spine for bridge-adjacent product systems.

Reason: building the whole semantic operating layer in one pass is too large; separate but connected subprojects preserve modularity while keeping the overall picture coherent.

Implications:

- Each domain gets a subproject packet.
- Shared gates and connection rules apply to all domains.
- Agent work should update this folder when changing product-level architecture.

Status: `accepted`

## 2026-06-26 — Use Holodeck As Shared Workspace Infrastructure

Decision: treat Holodeck as the bounded shared workspace layer for active build objectives inside this product spine.

Reason: Holodeck already provides typed, evidence-linked, rebuildable workspace records, contextualization, constraints, tests, promotions, materialized views, and task-pack generation. Those are infrastructure concerns, not optional add-ons.

Implications:

- The product folder remains the strategic and architectural spine.
- Holodeck becomes the execution and incubation workspace for active objectives.
- Workboards remain human- and agent-readable coordination surfaces derived from or linked to active workspace state.
- Task packs remain handoff packets, not the canonical workspace.

Status: `accepted`
