# Agent Workspaces (Git Projection)

These folders are git-tracked projections for cross-agent continuity. They are readable by any agent, but they are not the authoritative coordination store.

Authority split:

- semantic authority: the canonical framework source in the workspace
- coordination authority: the live workspace service behind `INNER_WORLD_WORKSPACE_API_BASE`
- git authority: published continuity, handoff, plans, and source copies

Current canonical workspace:

| Workspace | Purpose |
|-----------|---------|
| [unified-framework-synthesis](./unified-framework-synthesis/README.md) | Canonical v1.1 metaphysical foundation, workboard, and continuity projection |

Agent boot order:

1. Query the live workspace service first.
2. Read the canonical framework source.
3. Read the handoff and build plan.
4. Use the git projection only as continuity, not as a substitute for live workspace state.

Foreign agents should also read [`docs/cross-agent/README.md`](../cross-agent/README.md).
