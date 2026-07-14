# Workspace Sync Contract

Workspace ID: `unified-framework-synthesis`

**Universal rules:** [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../WORKSPACE-AGENT-PROTOCOL.md)

## Authority model

- Semantic authority: `sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`
- Coordination authority: canonical workspace service at `INNER_WORLD_WORKSPACE_API_BASE`
- Git projection: this folder, the workboard, and generated continuity exports

## Hard rules

1. Query the live workspace before claiming or editing task-scoped work.
2. Treat `CONTINUITY.md` and workboard task status as projections — not writable sources of truth.
3. Record task, run, blocker, decision, and verification mutations through the live workspace service only.
4. After **every** live coordination mutation, run projection sync before handoff or commit.
5. If the canonical paper version or workspace goal changes materially, create a successor workspace instead of mutating the old workspace identity.

## Boot order

```bash
git fetch origin && git checkout main && git pull origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true

python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id <agent> --surface <surface> --session-id <session>

python3 tools/workspace_projection_sync.py check --workspace-id unified-framework-synthesis
```

## After coordination mutations

```bash
python3 tools/workspace_projection_sync.py publish --workspace-id unified-framework-synthesis
# or: python3 tools/conversation_os.py foundation sync-projections

python3 tools/workspace_projection_sync.py check --workspace-id unified-framework-synthesis
git add docs/workspaces/unified-framework-synthesis/ docs/workboards/unified-metaphysical-foundation/
git commit -m "Sync workspace projections for unified-framework-synthesis"
```

`foundation reconcile-ledger` runs `sync-projections` automatically after a successful connected reconcile.

## Projection obligations

- `manifest.json` must point at the active live workspace id.
- `CONTINUITY.md` must be refreshed after live coordination changes.
- Workboard `TASKS.md` and `tasks/*.md` must match live tasks via sync — never hand-edited status lines.
- The current task pack path must stay valid.
