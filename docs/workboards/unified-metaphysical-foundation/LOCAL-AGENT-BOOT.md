# Local Agent Boot — Close Phase 1 Foundation Gaps

> **Visibility:** This file is on `main` (since PR #13, commit `0080fa7`). If your agent cannot find it, your local clone is stale — run `git fetch origin && git checkout main && git pull origin main` before searching again.

**Audience:** a fresh local agent with no prior chat context  
**Mission:** close Gap 2 (live ledger reconciliation) on a connected machine  
**Branch:** `main`  
**Live workspace id:** `unified-framework-synthesis`  
**Formal blocker:** `blocker-7f7662afad54` (resolve via live API)

---

## 0. Success criteria (definition of done)

You are finished when **all** of the following are true:

| # | Criterion | How to verify |
|---|-----------|---------------|
| 1 | Code on branch passes automated review | `python3 tools/conversation_os.py foundation review` → `"passed": true` (all 10 steps) |
| 2 | Gap 1 (state adoption) holds under adversarial fixtures | Step `adversarial_state_fixtures` passes; spot-check §4 below |
| 3 | Gap 2 (live ledger) reconciled | `foundation reconcile-ledger` succeeds in `connected` mode **or** manual commands in GAP-2 doc executed |
| 4 | Live blocker resolved | `blocker-7f7662afad54` resolved in live workspace |
| 5 | Live tasks match git | TASK-001–005 at `review` (or `done` after human merge approval) with verification evidence recorded |
| 6 | Continuity refreshed | `docs/workspaces/unified-framework-synthesis/CONTINUITY.md` republished via `foundation sync-projections` (or `workspace_projection_sync.py publish`) after mutations |

**Do not merge** until rows 1–5 pass. Row 6 should follow every live coordination mutation.

---

## 1. Check out the correct branch (terminal, not Cursor UI)

Use **`main`** at `0080fa7` or later.

```bash
cd /path/to/thought_tube
git fetch origin
git checkout main
git pull origin main
git log --oneline -1
# expect: 0080fa7 or later — "Merge unified framework sync (Phase 1 foundation) to main"
```

If Cursor shows `stdout maxBuffer length exceeded` on checkout, **ignore the UI** and use the terminal commands above.

---

## 2. Where truth lives (authority map)

| Need | Authoritative source | Git projection (read, do not treat as live state) |
|------|----------------------|---------------------------------------------------|
| **Semantics** (what records mean) | Framework v1.1 paper | same file in repo |
| **Coordination** (task status, blockers, runs, evidence) | Live workspace API `INNER_WORLD_WORKSPACE_API_BASE` | `docs/workboards/…`, `CONTINUITY.md` |
| **Code + tests** | Branch `cursor/metaphysical-kernel-contracts-423a` | PR #11 |
| **Audit repair packet** | `GAP-REPORT-2026-07-12.md` | same |
| **What to do next** | This file + `GAP-2-RECONCILIATION.md` | `TASKS.md`, `UPDATES.jsonl` |

**Rule:** Query the live workspace **before** mutating task state. After mutations, run projection sync — see [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../workspaces/WORKSPACE-AGENT-PROTOCOL.md). Git workboard files are projections; the audit explicitly blocked merge when git said `review` but live said `backlog`.

---

## 3. Boot sequence (read in this order)

### Step A — Repo discipline (5 min)

1. [`/AGENTS.md`](../../../AGENTS.md) — required agent rules
2. [`docs/cross-agent/README.md`](../../cross-agent/README.md) — foreign agent entry

### Step B — Workspace + framework (15 min)

3. [`docs/workspaces/unified-framework-synthesis/README.md`](../../workspaces/unified-framework-synthesis/README.md) — workspace purpose
4. [`docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) — normative semantics (§4–6, §5.16, §6.11, §20, Appendix F)
5. [`docs/workspaces/unified-framework-synthesis/derived/handoff.md`](../../workspaces/unified-framework-synthesis/derived/handoff.md) — workspace handoff
6. [`docs/workspaces/unified-framework-synthesis/derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md) — build sequencing

### Step C — Phase 1 workboard (10 min)

7. **This file** — mission and close-out checklist
8. [`GAP-REPORT-2026-07-12.md`](./GAP-REPORT-2026-07-12.md) — what the audit found
9. [`REVIEWER-START.md`](./REVIEWER-START.md) — code verification protocol
10. [`GAP-2-RECONCILIATION.md`](./GAP-2-RECONCILIATION.md) — live ledger steps
11. [`PHASE-1-IMPLEMENTATION-REVIEW.md`](./PHASE-1-IMPLEMENTATION-REVIEW.md) — architecture + module map
12. [`TASKS.md`](./TASKS.md) + [`tasks/TASK-001`](./tasks/TASK-001-lock-kernel-contracts-and-lifecycles.md) … [`TASK-005`](./tasks/TASK-005-prove-application-sdk-with-two-consumers.md)
13. [`TOOLS.md`](./TOOLS.md) — CLI reference
14. [`UPDATES.jsonl`](./UPDATES.jsonl) — append-only activity (latest rows at bottom)

### Step D — Live workspace (before editing tasks)

```bash
# Ensure API is configured (~/.config/inner-space-workspace.env or env var)
source ~/.config/inner-space-workspace.env 2>/dev/null || true

python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id local-agent \
  --surface cursor \
  --session-id local-foundation-closeout

python3 tools/workspace_coordination.py tasks \
  --workspace-id unified-framework-synthesis

# Verify git projections match live before trusting markdown status
python3 tools/workspace_projection_sync.py check --workspace-id unified-framework-synthesis
```

If context/tasks commands fail, run `bash tools/setup_cursor_tailnet.sh` then retry. **Stop and fix connectivity before claiming task state is current.**

After any live mutation in this session:

```bash
python3 tools/conversation_os.py foundation sync-projections
```

---

## 4. Gap status and your todos

### Gap 1 — State adoption cross-links (P1) — **CODE DONE, YOU VERIFY**

| Item | Detail |
|------|--------|
| Problem | State, StateCommitment, BranchMembership could disagree on branch/scope |
| Fix | `validate_state_adoption_links()` in `metaphysical_kernel_contracts.py` |
| Your todo | Re-run review; spot-check adversarial fixtures (do not skip) |

```bash
python3 tools/conversation_os.py foundation review --verbose
```

Adversarial fixtures (must be **rejected**):

- `tests/fixtures/metaphysical_kernel/invalid_state_branch_membership_mismatch.json`
- `tests/fixtures/metaphysical_kernel/invalid_state_scope_membership_mismatch.json`
- `tests/fixtures/metaphysical_kernel/invalid_state_missing_commitment_link.json`
- `tests/fixtures/metaphysical_kernel/invalid_state_unknown_source_claim.json`

Valid path (must **pass**): `tests/fixtures/metaphysical_kernel/valid_state_commitment_path.json`

---

### Gap 2 — Live workspace ledger (P1) — **YOUR PRIMARY WORK**

| Item | Detail |
|------|--------|
| Problem | Git workboard and live workspace diverged; no verification evidence recorded live |
| Blocker | `blocker-7f7662afad54` |
| Dependency chain | TASK-001 → TASK-002 → TASK-003 → TASK-004 → TASK-005 |
| Your todo | Record verification, resolve blocker, set tasks to `review` |

```bash
# Dry-run first
python3 tools/conversation_os.py foundation reconcile-ledger --dry-run

# Execute (requires live API)
python3 tools/conversation_os.py foundation reconcile-ledger
```

Full manual command list: [`GAP-2-RECONCILIATION.md`](./GAP-2-RECONCILIATION.md)

**After reconcile:** confirm live tasks show `review`, blocker resolved, and refresh continuity from the service.

---

### Gap 3 — Module manifests (P2) — **OPTIONAL BEFORE MERGE**

| Item | Detail |
|------|--------|
| Problem | Repo-wide manifest index incomplete; kernel files lacked manifests |
| Partial fix | Tracked manifests in [`manifests/`](./manifests/) |
| Your todo | Install locally if running engineering guard / repo overview |

```bash
mkdir -p context/substrate/modules
cp docs/workboards/unified-metaphysical-foundation/manifests/*.json context/substrate/modules/
python3 tools/conversation_os.py repo-overview refresh
```

**Kernel tests and `foundation review` are the authoritative Phase 1 gate** even if manifests are not installed.

---

## 5. Execution checklist (run in order)

```bash
# ── 1. Orient ─────────────────────────────────────────────
git checkout cursor/metaphysical-kernel-contracts-423a
git pull origin cursor/metaphysical-kernel-contracts-423a

# ── 2. Connect live workspace ─────────────────────────────
bash tools/setup_cursor_tailnet.sh    # if needed
python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id local-agent --surface cursor --session-id local-foundation-closeout

# ── 3. Verify code (Gap 1) ───────────────────────────────
python3 tools/conversation_os.py foundation review
PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_cli -v

# ── 4. Reconcile live ledger (Gap 2) ─────────────────────
python3 tools/conversation_os.py foundation reconcile-ledger --dry-run
python3 tools/conversation_os.py foundation reconcile-ledger

# ── 5. Confirm live state ────────────────────────────────
python3 tools/workspace_coordination.py tasks --workspace-id unified-framework-synthesis
# expect: TASK-001..005 → review; blocker resolved

# ── 6. Optional manifests (Gap 3) ────────────────────────
mkdir -p context/substrate/modules
cp docs/workboards/unified-metaphysical-foundation/manifests/*.json context/substrate/modules/
python3 tools/conversation_os.py repo-overview refresh
```

---

## 6. What was already built (do not rebuild)

Phase 1 on this branch includes:

| Task | Deliverable |
|------|-------------|
| TASK-001 | Kernel contracts + validators + fixtures |
| TASK-002 | Migration fixtures (MTSF, ThoughtShape, SDS, Conversation OS) |
| TASK-003 | Append-only store + vertical slice runtime |
| TASK-004 | Profile registry + Field/Formation bootstrap |
| TASK-005 | Application SDK + World Studio / Workspace Curator proofs |

**CLI:** `python3 tools/conversation_os.py foundation …`  
**Tests:** 63 total (58 kernel + 5 CLI)

---

## 7. Do NOT do (scope traps)

- Do not implement Shape / Conversation / Pattern profiles
- Do not wire `session_append --foundation-capture` unless explicitly scoped
- Do not treat git `TASKS.md` status as merge approval without live workspace confirmation
- Do not mark tasks `done` without verification evidence in the live service
- Do not merge historical frameworks (MTSF, SDS, ThoughtShape) as parallel runtime layers
- Do not expand kernel scope while closing gaps — this is a **close-out** pass

---

## 8. Key file map (implementation)

```
src/conversation_os/
  metaphysical_kernel.py              # record dataclasses
  metaphysical_kernel_contracts.py    # validators (Gap 1 fix here)
  metaphysical_kernel_migration.py
  metaphysical_kernel_store.py
  metaphysical_kernel_runtime.py
  metaphysical_kernel_profile_registry.py
  metaphysical_kernel_application_sdk.py
  metaphysical_kernel_cli.py          # foundation review, reconcile-ledger

docs/workboards/unified-metaphysical-foundation/
  LOCAL-AGENT-BOOT.md                 # this file
  GAP-REPORT-2026-07-12.md
  GAP-2-RECONCILIATION.md
  REVIEWER-START.md
  PHASE-1-IMPLEMENTATION-REVIEW.md
  TOOLS.md
  tasks/TASK-001 … TASK-005
```

---

## 9. After gaps are closed

1. Human or reviewer approves PR #11
2. Merge `cursor/metaphysical-kernel-contracts-423a` → `codex/unified-framework-sync`
3. Move live tasks from `review` → `done` with merge SHA as evidence
4. Append a row to `UPDATES.jsonl` documenting close-out

---

## 10. If something fails

| Symptom | Action |
|---------|--------|
| `foundation review` fails on `adversarial_state_fixtures` | Gap 1 regression — fix `metaphysical_kernel_contracts.py`, do not reconcile ledger yet |
| `reconcile-ledger` returns `mode: offline` | Fix Tailscale / `INNER_WORLD_WORKSPACE_API_BASE`; use manual commands in GAP-2 doc |
| Live tasks still `blocked` after reconcile | Re-run with `--verbose`; check blocker id; inspect live workspace runs endpoint |
| Engineering guard `needs_index` | Expected repo-wide; kernel tests still authoritative for Phase 1 |
| Wrong branch / maxBuffer on checkout | Use §1 terminal checkout of `cursor/metaphysical-kernel-contracts-423a` |

**Escalate with:** command output, `git rev-parse HEAD`, live workspace task snapshot, and which checklist step failed.
