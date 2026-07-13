# Gap 2 Reconciliation — Live Workspace Ledger

**Blocker:** `blocker-7f7662afad54`  
**Workspace:** `unified-framework-synthesis`  
**Prerequisite:** Gap 1 repair merged on branch; `foundation review` passes.

## Automated path (connected surface)

From repo root on a host that can reach `INNER_WORLD_WORKSPACE_API_BASE`:

```bash
# Optional: join tailnet first
bash tools/setup_cursor_tailnet.sh

# Dry-run (prints commands, checks /health)
python3 tools/conversation_os.py foundation reconcile-ledger --dry-run

# Execute live ledger updates
python3 tools/conversation_os.py foundation reconcile-ledger
```

This records verification for TASK-001–005, logs the Gap 1 decision, resolves the blocker
(if `foundation review` passed), and sets tasks to `review`.

## Manual path (same commands)

```bash
HEAD=$(git rev-parse HEAD)
VERIFY="python3 tools/conversation_os.py foundation review"

for TASK in \
  TASK-001-lock-kernel-contracts-and-lifecycles \
  TASK-002-build-historical-and-current-migration-fixtures \
  TASK-003-implement-phase-1-foundation-vertical-slice \
  TASK-004-build-profile-registry-and-conformance \
  TASK-005-prove-application-sdk-with-two-consumers
do
  python3 tools/workspace_coordination.py verify \
    --workspace-id unified-framework-synthesis \
    --task-id "$TASK" \
    --agent-id cursor-cloud-agent \
    --test-name foundation_phase1_review \
    --result pass \
    --evidence-ref "$HEAD" \
    --command-or-protocol "$VERIFY"
done

python3 tools/workspace_coordination.py decision \
  --workspace-id unified-framework-synthesis \
  --task-id TASK-001-lock-kernel-contracts-and-lifecycles \
  --agent-id cursor-cloud-agent \
  --summary "Gap 1 state adoption cross-link validation repaired" \
  --reasoning "foundation review passed at $HEAD"

python3 tools/workspace_coordination.py resolve-blocker \
  --workspace-id unified-framework-synthesis \
  --blocker-id blocker-7f7662afad54 \
  --agent-id cursor-cloud-agent \
  --reasoning "Gap 1 repaired; adversarial state fixtures reject cross-branch adoption."

for TASK in TASK-001-lock-kernel-contracts-and-lifecycles \
  TASK-002-build-historical-and-current-migration-fixtures \
  TASK-003-implement-phase-1-foundation-vertical-slice \
  TASK-004-build-profile-registry-and-conformance \
  TASK-005-prove-application-sdk-with-two-consumers
do
  python3 tools/workspace_coordination.py update-task \
    --workspace-id unified-framework-synthesis \
    --task-id "$TASK" \
    --task-status review \
    --reasoning "Phase 1 verified; pending merge approval."
done
```

## Cloud agent limitation

Cursor Cloud agents may be unable to reach the private workspace API (Tailscale auth /
SSL). In that case `reconcile-ledger` returns `mode: offline` with the exact command list
above. Run those commands from a connected machine.

## Done when

- Live workspace shows verification evidence on all five tasks
- Blocker resolved
- `CONTINUITY.md` republished from live service
- Git workboard `TASKS.md` matches live task status
