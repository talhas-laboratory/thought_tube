# Agent Workspaces (Git Projection)

These folders are git-tracked projections for cross-agent continuity. They are readable by any agent, but they are **not** the authoritative coordination store.

**Read first:** [`WORKSPACE-AGENT-PROTOCOL.md`](./WORKSPACE-AGENT-PROTOCOL.md) — mandatory rules for every workspace and every agent.

Authority split:

- semantic authority: the canonical framework source in the workspace
- coordination authority: the live workspace service behind `INNER_WORLD_WORKSPACE_API_BASE`
- git authority: published continuity, handoff, plans, and source copies (mirrors only)

Current canonical workspace:

| Workspace | Purpose |
|-----------|---------|
| [unified-framework-synthesis](./unified-framework-synthesis/README.md) | Canonical v1.1 metaphysical foundation, workboard, and continuity projection |

## Agent boot order

1. `git pull` — never search for docs on a stale clone
2. Query the live workspace service (`workspace_coordination.py context`)
3. `workspace_projection_sync.py check` — publish if not fresh
4. Read the canonical framework source
5. Read handoff and build plan
6. Read git projections only as continuity exports

## After any live coordination change

```bash
python3 tools/workspace_projection_sync.py publish --workspace-id <workspace-id>
python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
```

Foreign agents should also read [`docs/cross-agent/README.md`](../cross-agent/README.md).

New workspace setup: [`templates/sync-contract.template.md`](./templates/sync-contract.template.md)
