# Workspace Sync Contract

Workspace ID: `shape-intelligence-population`

## Authority model

- Semantic authority: `docs/workspaces/unified-framework-synthesis/` and its canonical sources.
- Coordination authority: the live workspace service at `INNER_WORLD_WORKSPACE_API_BASE`.
- Git projection: this workspace, `docs/workboards/shape-intelligence-population/`, and generated continuity exports.

## Hard rules

1. Query the live workspace before claiming or editing task-scoped work.
2. Treat `CONTINUITY.md` and workboard task status as generated projections, never as writable truth.
3. Record task, run, blocker, decision, and verification mutations through the live workspace service only.
4. After every live coordination mutation, publish and check projections.
5. Commit and push the synced workspace/workboard projections for cloud-agent continuity.

## Boot order

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id shape-intelligence-population \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check \
  --workspace-id shape-intelligence-population
```

## After a live mutation

```bash
python3 tools/workspace_projection_sync.py publish \
  --workspace-id shape-intelligence-population \
  --agent-id <agent> --session-id <session>
python3 tools/workspace_projection_sync.py check \
  --workspace-id shape-intelligence-population
```

Universal protocol: [Workspace Agent Protocol](../../WORKSPACE-AGENT-PROTOCOL.md).
