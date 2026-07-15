# Block Report — UMF Program Coordination Outage

**Status:** **blocking** — live workspace API unreachable; git/live ledger diverged from implementation  
**Report date:** 2026-07-15  
**Formal blocker id (proposed):** `blocker-umf-coord-20260715`  
**Affected workspaces:** `metaphysical-kernel-ontology`, `metaphysical-branch-reasoning`, `metaphysical-vocabulary-governance`  
**Repair packet:** [`UMF-COORDINATION-RECONCILIATION-2026-07-15.md`](../../../workboards/unified-metaphysical-foundation/UMF-COORDINATION-RECONCILIATION-2026-07-15.md)

## Purpose

This report records why the Kernel → Branch → Vocabulary program chain cannot be closed on the **live workspace ledger** despite implementation and test evidence landing on GitHub PR branches. It supersedes any implication that git `TASKS.md` rows alone reflect current coordination truth.

**Do not** mark program tasks `done` in git projections only. **Do not** treat open draft PRs as released G5 contracts until merged and reconciled on the live API.

---

## Executive summary

| Layer | State | Trust level |
|---|---|---|
| **Code + tests** | KERNEL-001–005, BRANCH-001–005, VOCAB-001–005 implemented on stacked PR branches (#15–#29) | High — pytest ladders pass on branches |
| **GitHub PRs** | Fifteen open draft PRs, unmerged | Medium — review/merge pending |
| **Live workspace API** | Unreachable from Cursor Cloud agent (SSL/Tailscale) | **Blocked** |
| **Live task ledger** | Kernel/branch/vocab tasks still `ready`/`backlog`/`done` (stale vs implementation) | **Untrusted** |
| **Git projections** | `TASKS.md` claims “refreshed from live coordination state” but lags implementation | **Misleading until reconciled** |

---

## Blocking gap 1 — Live workspace API unreachable (P0)

**Severity:** P0 — no coordination mutations possible from cloud agent surfaces

### Symptom

From the Cursor Cloud VM (2026-07-15):

```text
python3 tools/workspace_coordination.py context --workspace-id metaphysical-vocabulary-governance ...
→ Workspace service unavailable: [SSL: UNEXPECTED_EOF_WHILE_READING] EOF occurred in violation of protocol

curl "${INNER_WORLD_WORKSPACE_API_BASE}/health"
→ curl: (35) OpenSSL SSL_connect: SSL_ERROR_SYSCALL
```

`INNER_WORLD_WORKSPACE_API_BASE` is configured (via `~/.config/inner-space-workspace.env`) but TLS handshake to the tailnet host fails before `/health` succeeds.

### Impact

Cannot execute mandatory protocol steps:

- `claim` / `in-progress` / `verify` / `complete` on KERNEL-003–005, BRANCH-003–005, VOCAB-001–005
- `blocker` / `resolve-blocker` on live service
- `workspace_projection_sync.py publish` from authoritative live state
- Republish `CONTINUITY.md` for affected workspaces

### Required repair (infrastructure)

Run from a surface that **can** reach the API (home LAN host, OpenClaw box, or cloud agent after tailnet fix):

1. Confirm tailnet path: `bash tools/setup_cursor_tailnet.sh` (requires `TAILSCALE_AUTHKEY`)
2. Verify health: `curl -fsS "${INNER_WORLD_WORKSPACE_API_BASE}/health"`
3. Verify context: `python3 tools/workspace_coordination.py context --workspace-id metaphysical-kernel-ontology --agent-id <agent> --surface local --session-id reconcile`
4. If SSL persists: inspect reverse proxy / cert on the workspace service host; confirm tailnet DNS and firewall allow 443 from agent tag `tag:cursor-agent`

### Acceptance

- `/health` returns 200 from cloud agent **and** from operator machine
- `workspace_coordination.py context` returns task list without SSL errors
- `workspace_projection_sync.py check` can run connected (not offline)

---

## Blocking gap 2 — Live ledger vs implementation divergence (P1)

**Severity:** P1 — coordination state lies about program progress

### Symptom

Git-tracked projections (last live sync) still show early statuses while PR branches contain full program delivery:

| Workspace | Live ledger (projection) | Implementation reality (open PRs) |
|---|---|---|
| `metaphysical-kernel-ontology` | KERNEL-001 `ready`; KERNEL-002–005 `backlog` | #15–#20 implement KERNEL-001–005 through G5 release |
| `metaphysical-branch-reasoning` | BRANCH-001–002 `done`; BRANCH-003–005 `backlog` | #17, #21–#24 implement BRANCH-001–005 (003–005 not live-completed) |
| `metaphysical-vocabulary-governance` | VOCAB-001 `ready`; VOCAB-002–005 `backlog` | #25–#29 implement VOCAB-001–005 through G5 release |

Conversation summary also noted KERNEL-001–005 were marked done on live API at an earlier point; current `TASKS.md` projections on `main` do not reflect that — **another sign of projection drift**.

### Impact

- Reviewers cannot trust `docs/workboards/*/TASKS.md` for merge gates
- G5 release SHAs in contract JSON on branches are not anchored to live `complete` evidence
- Downstream programs cannot safely pin provider releases from the ledger

### Required repair (coordination)

After gap 1 is fixed, run the per-workspace reconciliation in [`UMF-COORDINATION-RECONCILIATION-2026-07-15.md`](../../../workboards/unified-metaphysical-foundation/UMF-COORDINATION-RECONCILIATION-2026-07-15.md):

1. Record formal blocker `blocker-umf-coord-20260715` on each affected workspace (or parent `unified-framework-synthesis` if using program-level tracking)
2. For each merged task: `claim` → `verify` (with pytest command + branch SHA) → `complete` → `publish` projections
3. Republish `CONTINUITY.md` for kernel, branch, and vocabulary workspaces
4. Resolve blocker only when live statuses match merged SHAs

### Acceptance

- Live task statuses match post-merge reality for all fifteen tasks
- Verification evidence refs point at merge commits on `main`
- `workspace_projection_sync.py check` reports fresh / `changed: []` for all three workspaces

---

## Blocking gap 3 — PR stack unmerged (P1)

**Severity:** P1 — dependency tree fragmented on `main`

### Open draft PR stack (2026-07-15)

**Kernel** (merge order):

| Task | PR | Branch |
|---|---|---|
| KERNEL-001 | #15 | `cursor/umf-kernel-001-56ce` |
| KERNEL-002 | #16 | `cursor/umf-kernel-002-56ce` |
| KERNEL-003 | #18 | `cursor/umf-kernel-003-56ce` |
| KERNEL-004 | #19 | `cursor/umf-kernel-004-56ce` |
| KERNEL-005 | #20 | `cursor/umf-kernel-005-56ce` |

**Branch** (stacks on kernel G5):

| Task | PR | Branch |
|---|---|---|
| BRANCH-001 | #17 | `cursor/umf-branch-001-56ce` |
| BRANCH-002 | #21 | `cursor/umf-branch-002-56ce` |
| BRANCH-003 | #22 | `cursor/umf-branch-003-56ce` |
| BRANCH-004 | #23 | `cursor/umf-branch-004-56ce` |
| BRANCH-005 | #24 | `cursor/umf-branch-005-56ce` |

**Vocabulary** (stacks on branch G5):

| Task | PR | Branch |
|---|---|---|
| VOCAB-001 | #25 | `cursor/umf-vocab-001-56ce` |
| VOCAB-002 | #26 | `cursor/umf-vocab-002-56ce` |
| VOCAB-003 | #27 | `cursor/umf-vocab-003-56ce` |
| VOCAB-004 | #28 | `cursor/umf-vocab-004-56ce` |
| VOCAB-005 | #29 | `cursor/umf-vocab-005-56ce` |

### Release revision pins (on branch tips — update after merge)

| Program | Contract version | Release SHA (branch tip) | Consumes |
|---|---|---|---|
| Kernel G5 | `1.1.0` | `27df9332f8035b66867b7962aff5392e37f8bae3` (`cursor/umf-kernel-005-56ce`) | — |
| Branch G5 | `1.0.0` | `ca73c10a7fc3f5dc4d077393358103455e63acbb` (`cursor/umf-branch-005-56ce`) | Kernel `4830b81…` (per contract on branch) |
| Vocabulary G5 | `1.0.0` | `22fa9ebe69ec0115bf6b0d0247b704638bba2add` (in `VOCAB_RELEASE_DEPENDENCY_CONTRACT.json` on #29) | Kernel `4830b81…`, Branch `e3784b7…` |

**Note:** Branch and vocabulary release JSON files on PR branches may cite earlier implementation SHAs than branch tips; after merge, re-record `release_git_revision` to the **merge commit on `main`** and re-run release contract tests.

### Required repair (merge)

1. Merge kernel stack #15 → #16 → #18 → #19 → #20 to `main`
2. Merge branch stack #17 → #21 → #22 → #23 → #24 (rebase if needed on post-kernel `main`)
3. Merge vocabulary stack #25 → #29 similarly
4. Re-run full verification ladders on `main` after each G5 merge
5. Update release contract JSON `release_git_revision` fields to merged SHAs

### Acceptance

- `main` contains all three G5 release packets
- Cross-program consumer smokes pass on `main`
- Release contract tests (`test_branch_release_contract.py`, `test_vocab_release_contract.py`, kernel equivalent) pass against merged SHAs

---

## Non-blocking strengths (preserve)

- Table-driven and adversarial conformance suites exist for kernel, branch, and vocabulary
- G5 release dependency contracts mirror the foundation Gap 2 repair pattern
- Branch ↔ vocabulary consumer acknowledgment is already documented
- Engineering guard and repo-overview tooling are in place

---

## Recommended repair sequence

```text
1. Fix tailnet / workspace API TLS (Gap 1)
2. Merge kernel PR stack to main (Gap 3a)
3. Reconcile kernel live ledger + publish projections (Gap 2)
4. Merge branch PR stack; reconcile branch ledger
5. Merge vocabulary PR stack; reconcile vocabulary ledger
6. Resolve blocker-umf-coord-20260715
7. Unblock downstream programs (Conversation/Formation, Shape/Pattern, Agent)
```

---

## Verification commands (post-merge on main)

```bash
# Kernel ladder
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py \
  tests/test_metaphysical_kernel_profile_registry.py

# Branch ladder
pytest -q tests/test_metaphysical_branch_reasoning.py tests/test_metaphysical_branch_conformance.py \
  tests/test_metaphysical_branch_consumer_smoke.py tests/test_branch_release_contract.py

# Vocabulary ladder
pytest -q tests/test_metaphysical_vocabulary_governance.py tests/test_metaphysical_vocabulary_conformance.py \
  tests/test_vocab_contract_fixtures.py tests/test_vocab_release_contract.py tests/test_vocab_consumer_smoke.py \
  tests/test_metaphysical_branch_consumer_smoke.py
```

---

## Owner actions

| Owner | Action |
|---|---|
| **Infrastructure / operator** | Restore workspace API reachability from Cursor Cloud; confirm `TAILSCALE_AUTHKEY` and service TLS |
| **Reviewer** | Merge PR stacks in dependency order; require green pytest on each G5 PR |
| **Connected agent** | Execute reconciliation script; record verification + complete tasks on live API |
| **Cloud agent** | Pause live coordination claims until `/health` succeeds; continue code review via PR diffs only |

---

## Done when

- [ ] `/health` succeeds from cloud agent
- [ ] Blocker recorded and later resolved on live API
- [ ] KERNEL-001–005, BRANCH-001–005, VOCAB-001–005 show `done` with merge SHA evidence on live ledger
- [ ] `CONTINUITY.md` fresh for all three workspaces
- [ ] `TASKS.md` projections match live after `publish`
- [ ] G5 release revisions on `main` match merge commits
