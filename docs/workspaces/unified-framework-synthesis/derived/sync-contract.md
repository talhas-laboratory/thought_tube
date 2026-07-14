# Workspace Sync Contract

Workspace ID: `unified-framework-synthesis`

## Authority model

- Semantic authority: `sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`
- Coordination authority: canonical workspace service at `INNER_WORLD_WORKSPACE_API_BASE`
- Git projection: this folder, the workboard, and generated continuity exports

## Hard rules

1. Query the live workspace before claiming or editing task-scoped work.
2. Treat `CONTINUITY.md` as a projection of live state, not a writable source of truth.
3. Record task, run, blocker, decision, and verification mutations through the live workspace service.
4. After live workspace mutations, republish `CONTINUITY.md`.
5. If the canonical paper version or workspace goal changes materially, create a successor workspace instead of mutating the old workspace identity.

## Boot order

1. `python3 tools/workspace_coordination.py status --workspace-id unified-framework-synthesis`
2. `python3 tools/workspace_coordination.py context --workspace-id unified-framework-synthesis --agent-id <agent> --surface <surface> --session-id <session>`
3. Read the canonical paper.
4. Read `derived/handoff.md`.
5. Read `derived/foundation-build-plan.md`.
6. Read `CONTINUITY.md`.

## Projection obligations

- `manifest.json` must point at the active live workspace id.
- `CONTINUITY.md` must be refreshed after live coordination changes.
- The workboard must match the live workspace focus task and decision surface.
- The current task pack path must stay valid.
