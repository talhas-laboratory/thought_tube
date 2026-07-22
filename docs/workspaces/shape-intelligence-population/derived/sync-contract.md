# Workspace Sync Contract

Workspace ID: `shape-intelligence-population`

- Semantic authority: `docs/workspaces/unified-framework-synthesis/` and its canonical sources.
- Coordination authority: the live workspace service at `INNER_WORLD_WORKSPACE_API_BASE`.
- Git projection: this workspace and `docs/workboards/shape-intelligence-population/`.

## Rules

1. Query the live workspace before task-scoped work.
2. Task status, blockers, decisions, and verification are written through the live API only.
3. After every live mutation, run `workspace_projection_sync.py publish`, then `check`.
4. Commit and push synced projections for cloud-agent continuity.

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id shape-intelligence-population \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check --workspace-id shape-intelligence-population
```

Universal protocol: [Workspace Agent Protocol](../../WORKSPACE-AGENT-PROTOCOL.md).
