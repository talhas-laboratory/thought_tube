# Workspace Sync Contract

Workspace ID: `<workspace-id>`

Copy this file to `docs/workspaces/<workspace-id>/derived/sync-contract.md` when creating a new workspace.

## Authority model

- Semantic authority: `<path-to-canonical-source>`
- Coordination authority: live workspace service at `INNER_WORLD_WORKSPACE_API_BASE`
- Git projection: `docs/workspaces/<workspace-id>/`, workboard, and generated continuity exports

## Hard rules

1. Query the live workspace before claiming or editing task-scoped work.
2. Treat `CONTINUITY.md` and workboard task status as projections — not writable sources of truth.
3. Record task, run, blocker, decision, and verification mutations through the live workspace service only.
4. After **every** live coordination mutation, run projection sync before handoff or commit.
5. Commit and push synced projections so cloud reviewers read the same state as the live service.

## Boot order

```bash
git fetch origin && git checkout main && git pull origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true

python3 tools/workspace_coordination.py context \
  --workspace-id <workspace-id> \
  --agent-id <agent> --surface <surface> --session-id <session>

python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
```

## After coordination mutations

```bash
python3 tools/workspace_projection_sync.py publish --workspace-id <workspace-id>
python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
git add docs/workspaces/<workspace-id>/ docs/workboards/<board>/
git commit -m "Sync workspace projections for <workspace-id>"
```

## Projection obligations

- `manifest.json` must point at the active live `workspace_id`.
- `CONTINUITY.md` must be refreshed after live coordination changes.
- Workboard `TASKS.md` and `tasks/*.md` status lines must match live tasks (via sync, not hand edits).
- Universal protocol: [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../WORKSPACE-AGENT-PROTOCOL.md)
