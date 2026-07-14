# Reviewer Start — Phase 1 Metaphysical Foundation

**For:** any agent reviewing TASK-001 through TASK-005  
**Branch:** `cursor/metaphysical-kernel-contracts-423a`  
**PR:** [#11](https://github.com/talhas-laboratory/thought_tube/pull/11)  
**Normative authority:** [Framework v1.1](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)  
**Live workspace:** `unified-framework-synthesis`

---

## 0. Current status (read first)

| Area | Status |
|------|--------|
| Phase 1 code (TASK-001–005) | Implemented on branch |
| Foundation review | **Passes** (10 steps, including 58 kernel tests and adversarial state fixtures) |
| CLI handler tests | Run separately; reconciliation coverage is environment-sensitive when a live API is configured |
| `foundation review` | Passes (includes adversarial state fixtures) |
| **P1 Gap 1** — state adoption cross-links | **Repaired** on branch (pending your re-check) |
| **P1 Gap 2** — live workspace ledger | **Reconciled** — all five tasks are `review`; no open blocker |
| **P2 Gap 3** — module manifests | Kernel tranche in [`manifests/`](./manifests/); repo-wide recovery open |
| GitHub PR comments | None — audit feedback is in [`GAP-REPORT-2026-07-12.md`](./GAP-REPORT-2026-07-12.md) |

**Authority split:** The live workspace service (`INNER_WORLD_WORKSPACE_API_BASE`) is coordination truth. Git workboard files are projections. Do not treat git task status alone as merge approval.

**Merge gate:** `foundation review` passes, the live workspace ledger is reconciled per [`GAP-2-RECONCILIATION.md`](./GAP-2-RECONCILIATION.md), and the P1 repair work packages A–C below are independently verified.

**Integrity repair plan:** [`artifacts/phase-1-integrity-repair-plan-2026-07-14.md`](./artifacts/phase-1-integrity-repair-plan-2026-07-14.md) defines the required P1 repairs before tasks can move from `review` to `done`.

---

## 1. One command to verify code

From repo root:

```bash
python3 tools/conversation_os.py foundation review
```

This runs, in order:

| Step | What it checks |
|------|----------------|
| `unit_tests` | 58 tests across 5 unittest modules |
| `bootstrap_profile` | `profile:field_formation` v1.0.0 registration |
| `vertical_slice` | capture → referent → claim → bounded view → provenance |
| `validate_bundle` | folded kernel bundle invariants |
| `consumer_world_studio` | `app:world_studio` proof on shared store |
| `consumer_workspace_curator` | `app:workspace_curator` proof on shared store |
| `profile_conformance` | bundle vs Field/Formation profile |
| `migration_fixtures_validate` | all four Appendix F fixtures |
| `adversarial_state_fixtures` | **Gap 1 repair** — four invalid state-adoption bundles must be rejected |
| `migration_fixture_execute` | MTSF fixture maps to kernel records |

**Expected:** top-level `"passed": true` and every step `"passed": true`.

Uses an **ephemeral temp directory** by default (does not mutate `memory/foundation/`):

```bash
python3 tools/conversation_os.py foundation review --verbose
python3 tools/conversation_os.py foundation review --in-place   # uses repo store
```

CLI handler tests (not included in `foundation test`):

```bash
PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_cli -v
```

---

## 2. Reading order

0. **[`LOCAL-AGENT-BOOT.md`](./LOCAL-AGENT-BOOT.md)** — if you are a **fresh local agent** closing gaps (start here)
1. **This file** — fast path for code review and merge gates
2. [`GAP-REPORT-2026-07-12.md`](./GAP-REPORT-2026-07-12.md) — audit findings (Gap 1 repaired; Gap 2 reconciled)
3. [`GAP-2-RECONCILIATION.md`](./GAP-2-RECONCILIATION.md) — live workspace ledger steps
4. [`PHASE-1-IMPLEMENTATION-REVIEW.md`](./PHASE-1-IMPLEMENTATION-REVIEW.md) — architecture, invariants, module map
5. [`TOOLS.md`](./TOOLS.md) — individual CLI commands
6. [`tasks/TASK-001`](./tasks/TASK-001-lock-kernel-contracts-and-lifecycles.md) … [`TASK-005`](./tasks/TASK-005-prove-application-sdk-with-two-consumers.md)
7. [`../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md)

---

## 3. What was built (one paragraph)

Phase 1 implements the **universal record kernel** from framework v1.1 §4–6: machine-readable contracts and validators (TASK-001), migration fixtures from MTSF / ThoughtShape / SDS / Conversation OS (TASK-002), an append-only event store and vertical-slice runtime (TASK-003), a profile registry with Field/Formation bootstrap (TASK-004), and an application SDK with World Studio and Workspace Curator consumer proofs (TASK-005). Historical frameworks are migration sources only; they are not runtime layers.

---

## 4. Gap 1 — what to re-check (P1, repaired)

The audit found that `State`, `StateCommitment`, and `BranchMembership` could disagree on branch/scope and still pass validation.

**Repair:** `validate_state_adoption_links()` in `metaphysical_kernel_contracts.py`.

**Spot-check as reviewer:**

```bash
# Valid path must return no errors
PYTHONPATH=src python3 -c "
import json
from pathlib import Path
from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle
bundle = json.loads(Path('tests/fixtures/metaphysical_kernel/valid_state_commitment_path.json').read_text())
assert validate_fixture_bundle(bundle) == [], validate_fixture_bundle(bundle)
print('valid_state_commitment_path: OK')
"

# Each adversarial fixture must be rejected
for name in \
  invalid_state_branch_membership_mismatch \
  invalid_state_scope_membership_mismatch \
  invalid_state_missing_commitment_link \
  invalid_state_unknown_source_claim
do
  PYTHONPATH=src python3 -c "
import json
from pathlib import Path
from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle
p = Path('tests/fixtures/metaphysical_kernel/${name}.json')
errs = validate_fixture_bundle(json.loads(p.read_text()))
assert errs, 'expected rejection for ${name}'
print('${name}: REJECTED')
"
done
```

**Key files:** `metaphysical_kernel_contracts.py`, `metaphysical_kernel_runtime.py` (`commit_state_from_claims` attaches commitment membership).

---

## 5. Gap 2 — coordination reconciliation (P1, complete)

**Blocker id:** `blocker-7f7662afad54`  
**Resolution:** The live workspace ledger now records verification for TASK-001 through TASK-005, all five tasks are `review`, and `blocker-7f7662afad54` is resolved. The continuity projection has been refreshed from the live service.

**Important:** `foundation reconcile-ledger` is a state-changing connected-surface command. Do not invoke it from a routine automated test or while merely inspecting the workspace.

**If a future ledger reconciliation is explicitly required** on a connected surface:

```bash
bash tools/setup_cursor_tailnet.sh   # if needed
python3 tools/conversation_os.py foundation reconcile-ledger --dry-run
python3 tools/conversation_os.py foundation reconcile-ledger
```

**Reviewer without API access:** treat the live ledger as unavailable; do not infer coordination state from stale Git projections.

---

## 6. Locked invariants (do not regress)

- **State ≠ Claim** — `State` requires `StateCommitment`
- **State adoption coherence** — commitment, state membership, scope, and source claims must align (Gap 1)
- **Branch-bound records** require `BranchMembership`
- **Lifecycle axes** (maturity, epistemic, governance) are orthogonal
- **Profiles** cannot redefine kernel record kinds
- **Raw capture** works without inference services
- **Provenance** must close at `SourceFragment`

---

## 7. Manual spot-check commands

```bash
python3 tools/conversation_os.py foundation test --verbose
python3 tools/conversation_os.py foundation status
python3 tools/conversation_os.py foundation bootstrap
python3 tools/conversation_os.py foundation slice \
  --content "Reviewer spot-check." \
  --referent-label "Review subject"
python3 tools/conversation_os.py foundation validate
python3 tools/conversation_os.py foundation consumer world-studio \
  --content "Scene." --referent-label "Element"
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/sds_signal_dilution.json
```

---

## 8. Source files to read first

| Priority | File | Why |
|----------|------|-----|
| 1 | `metaphysical_kernel_contracts.py` | Validators including `validate_state_adoption_links` |
| 2 | `metaphysical_kernel_runtime.py` | Vertical slice + state commit path |
| 3 | `metaphysical_kernel_migration.py` | Appendix F mappers |
| 4 | `metaphysical_kernel_application_sdk.py` | Application boundary |
| 5 | `metaphysical_kernel_cli.py` | `foundation review`, `reconcile-ledger` |

---

## 9. Fixtures index

| Path | Role |
|------|------|
| `tests/fixtures/metaphysical_kernel/valid_state_commitment_path.json` | Valid adoption path |
| `tests/fixtures/metaphysical_kernel/invalid_state_branch_membership_mismatch.json` | Gap 1 adversarial |
| `tests/fixtures/metaphysical_kernel/invalid_state_scope_membership_mismatch.json` | Gap 1 adversarial |
| `tests/fixtures/metaphysical_kernel/invalid_state_missing_commitment_link.json` | Gap 1 adversarial |
| `tests/fixtures/metaphysical_kernel/invalid_state_unknown_source_claim.json` | Gap 1 adversarial |
| `tests/fixtures/migration/*.json` | Four source-family migrations |

---

## 10. Module manifests (Gap 3 partial)

Tracked source: [`manifests/`](./manifests/) (8 kernel modules).  
Install locally for repo overview:

```bash
python3 tools/conversation_os.py repo-overview refresh
```

Kernel tests remain the authoritative Phase 1 gate if manifests are not installed.

---

## 11. Review outcome actions

| Outcome | Action |
|---------|--------|
| `foundation review` passes + Gap 1 spot-checks OK + live ledger reconciled | Approve PR #11; merge to `codex/unified-framework-sync` |
| `foundation review` passes and live ledger is reconciled | Approve PR #11 when branch review accepts the evidence |
| Adversarial fixtures accepted | **Block merge** — Gap 1 regression |
| Contract mismatch vs v1.1 | File issue citing § section; do not merge |
| Test failure | Fix on branch or request author fix |
| Scope creep | Note in PR; kernel must stay minimal |

---

## 12. Intentionally out of scope (Phase 1)

- Shape / Conversation / Pattern profile registration beyond Field/Formation
- `session_append --foundation-capture` CLI hook
- Production auth (SDK uses `ApplicationContext.authorized` flag only)
- Repo-wide module manifest recovery (kernel tranche only)
- Wiring World Studio / workspace services to SDK at app boundaries

See [`PHASE-1-IMPLEMENTATION-REVIEW.md` §6](./PHASE-1-IMPLEMENTATION-REVIEW.md#6-known-limitations-intentional-phase-1-scope).
