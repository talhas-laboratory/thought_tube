# Workspace Sync Contract

Workspace ID: `holodeck-productization`

## Authority model

- Semantic authority: [`../README.md`](../README.md)
- Coordination authority: live workspace service at `INNER_WORLD_WORKSPACE_API_BASE`
- Git projection: this directory and `docs/workboards/holodeck-productization/`

## Hard rules

1. Query the live workspace before claiming task-scoped work.
2. Treat `CONTINUITY.md` and workboard task status as projections, not writable sources of truth.
3. Record coordination mutations through the live workspace service only.
4. Publish projections after every live mutation.

See the universal [workspace protocol](../../WORKSPACE-AGENT-PROTOCOL.md).
