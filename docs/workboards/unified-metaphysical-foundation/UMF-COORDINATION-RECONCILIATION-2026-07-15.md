# UMF Coordination Reconciliation — 2026-07-15

**Status:** **blocked** — waiting on live workspace API  
**Parent report:** [`BLOCK-REPORT-2026-07-15-umf-coordination-outage.md`](../../workspaces/unified-framework-synthesis/derived/BLOCK-REPORT-2026-07-15-umf-coordination-outage.md)  
**Proposed blocker id:** `blocker-umf-coord-20260715`

Run this procedure from a host where `curl -fsS "${INNER_WORLD_WORKSPACE_API_BASE}/health"` succeeds.

---

## 0. Boot

```bash
cd /path/to/thought_tube
git fetch origin && git checkout main && git pull origin main
source ~/.config/inner-space-workspace.env

curl -fsS "${INNER_WORLD_WORKSPACE_API_BASE}/health"
python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id local-operator --surface local --session-id umf-reconcile-20260715
```

Optional tailnet join on Cursor Cloud:

```bash
export TAILSCALE_AUTHKEY='tskey-...'
bash tools/setup_cursor_tailnet.sh
```

---

## 1. Record blocker (each workspace)

```bash
AGENT=local-operator
SESSION=umf-reconcile-20260715
REASON="Live API was unreachable from Cursor Cloud (SSL/TLS). Git TASKS.md diverged from PR implementation #15-#29. See BLOCK-REPORT-2026-07-15-umf-coordination-outage.md"
NEXT="Restore API reachability; merge PR stacks; verify+complete tasks with merge SHAs; publish projections"

for WS in metaphysical-kernel-ontology metaphysical-branch-reasoning metaphysical-vocabulary-governance; do
  python3 tools/workspace_coordination.py blocker \
    --workspace-id "$WS" \
    --task-id "$(python3 -c "import json; print({'metaphysical-kernel-ontology':'KERNEL-001-atomic-obligation-and-contract-lock','metaphysical-branch-reasoning':'BRANCH-003-merge-and-inference-policy','metaphysical-vocabulary-governance':'VOCAB-001-atomic-obligation-and-governance-lock'}['$WS'])")" \
    --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --reasoning "$REASON" \
    --next-action "$NEXT"
done
```

Store returned `blocker_id` values; use the same id across workspaces if the service generates per-workspace ids.

---

## 2. Merge PR stacks (GitHub)

Merge in order (rebase each branch on updated `main` before merge if needed):

```text
Kernel:   #15 → #16 → #18 → #19 → #20
Branch:   #17 → #21 → #22 → #23 → #24
Vocab:    #25 → #26 → #27 → #28 → #29
```

After each G5 merge (#20, #24, #29), capture merge SHA:

```bash
git checkout main && git pull origin main
MERGE_SHA=$(git rev-parse HEAD)
echo "$MERGE_SHA"
```

Update release contract JSON on `main` if `release_git_revision` ≠ merge SHA, then commit fix before live `complete`.

---

## 3. Kernel workspace reconciliation

```bash
WS=metaphysical-kernel-ontology
AGENT=local-operator
SESSION=umf-reconcile-20260715
MERGE_SHA=$(git rev-parse HEAD)   # after KERNEL-005 merge

KERNEL_VERIFY='pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py tests/test_metaphysical_kernel_profile_registry.py tests/test_metaphysical_kernel_application_sdk.py'

for TASK in \
  KERNEL-001-atomic-obligation-and-contract-lock \
  KERNEL-002-migration-and-persistence-fixtures \
  KERNEL-003-minimal-kernel-runtime-operations \
  KERNEL-004-kernel-conformance-suite \
  KERNEL-005-release-kernel-dependency-contract
do
  python3 tools/workspace_coordination.py claim --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION"
  python3 tools/workspace_coordination.py verify \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --test-name kernel_phase1_ladder --result pass --evidence-ref "$MERGE_SHA" \
    --command-or-protocol "$KERNEL_VERIFY"
  python3 tools/workspace_coordination.py complete \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --summary "Merged on main at $MERGE_SHA" --reasoning "See PR stack #15-#20 and BLOCK-REPORT-2026-07-15"
done

python3 tools/workspace_projection_sync.py publish --workspace-id "$WS" --agent-id "$AGENT" --session-id "$SESSION"
python3 tools/workspace_projection_sync.py check --workspace-id "$WS"
```

Adjust per-task `MERGE_SHA` if you complete tasks incrementally at each PR merge instead of one shot at G5.

---

## 4. Branch workspace reconciliation

```bash
WS=metaphysical-branch-reasoning
MERGE_SHA=$(git rev-parse HEAD)   # after BRANCH-005 merge

BRANCH_VERIFY='pytest -q tests/test_metaphysical_branch_reasoning.py tests/test_metaphysical_branch_conformance.py tests/test_metaphysical_branch_consumer_smoke.py tests/test_branch_release_contract.py tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py'

for TASK in \
  BRANCH-001-atomic-obligation-and-interface-lock \
  BRANCH-002-support-and-inheritance-semantics \
  BRANCH-003-merge-and-inference-policy \
  BRANCH-004-adversarial-branch-conformance \
  BRANCH-005-release-branch-dependency-contract
do
  python3 tools/workspace_coordination.py claim --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION"
  python3 tools/workspace_coordination.py verify \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --test-name branch_phase1_ladder --result pass --evidence-ref "$MERGE_SHA" \
    --command-or-protocol "$BRANCH_VERIFY"
  python3 tools/workspace_coordination.py complete \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --summary "Merged on main at $MERGE_SHA" --reasoning "See PR stack #17,#21-#24"
done

python3 tools/workspace_projection_sync.py publish --workspace-id "$WS" --agent-id "$AGENT" --session-id "$SESSION"
```

---

## 5. Vocabulary workspace reconciliation

```bash
WS=metaphysical-vocabulary-governance
MERGE_SHA=$(git rev-parse HEAD)   # after VOCAB-005 merge

VOCAB_VERIFY='pytest -q tests/test_metaphysical_vocabulary_governance.py tests/test_metaphysical_vocabulary_conformance.py tests/test_vocab_contract_fixtures.py tests/test_vocab_release_contract.py tests/test_vocab_consumer_smoke.py tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_profile_registry.py tests/test_metaphysical_branch_consumer_smoke.py'

for TASK in \
  VOCAB-001-atomic-obligation-and-governance-lock \
  VOCAB-002-type-registry-and-nondestructive-mapping \
  VOCAB-003-promotion-and-evolution-workflow \
  VOCAB-004-vocabulary-conformance-suite \
  VOCAB-005-release-vocabulary-dependency-contract
do
  python3 tools/workspace_coordination.py claim --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION"
  python3 tools/workspace_coordination.py verify \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --test-name vocab_phase1_ladder --result pass --evidence-ref "$MERGE_SHA" \
    --command-or-protocol "$VOCAB_VERIFY"
  python3 tools/workspace_coordination.py complete \
    --workspace-id "$WS" --task-id "$TASK" --agent-id "$AGENT" --surface local --session-id "$SESSION" \
    --summary "Merged on main at $MERGE_SHA" --reasoning "See PR stack #25-#29"
done

python3 tools/workspace_projection_sync.py publish --workspace-id "$WS" --agent-id "$AGENT" --session-id "$SESSION"
```

---

## 6. Resolve blocker

```bash
python3 tools/workspace_coordination.py resolve-blocker \
  --workspace-id metaphysical-kernel-ontology \
  --blocker-id blocker-umf-coord-20260715 \
  --agent-id "$AGENT" --surface local --session-id "$SESSION" \
  --reasoning "API restored; PR stacks merged; live ledger matches main; projections published."

# Repeat resolve-blocker for branch and vocabulary workspaces if separate blocker ids were issued.
```

---

## 7. Commit git projections

```bash
git add docs/workspaces/ docs/workboards/
git commit -m "Sync UMF program projections after coordination reconciliation"
git push origin main
```

---

## Cloud agent limitation

Cursor Cloud agents currently fail with:

```text
Workspace service unavailable: [SSL: UNEXPECTED_EOF_WHILE_READING]
```

Until infrastructure repair (Gap 1 in block report), cloud agents should:

- Use PR diffs and pytest on branches for implementation review
- **Not** hand-edit `Status:` in `docs/workboards/*/tasks/*.md`
- **Not** claim tasks `done` without live API evidence

---

## Done when

- All three workspaces: tasks `done`, blocker resolved, `check` fresh
- `main` contains merged G5 contracts with correct `release_git_revision`
- Block report header updated to **resolved** with resolution date and operator note
