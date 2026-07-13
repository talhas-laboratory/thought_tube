# Reviewer Start — Phase 1 Metaphysical Foundation

**For:** any agent reviewing TASK-001 through TASK-005  
**Branch:** `cursor/metaphysical-kernel-contracts-423a`  
**PR:** [#11](https://github.com/talhas-laboratory/thought_tube/pull/11)  
**Normative authority:** [Framework v1.1](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)

---

## 1. One command to verify everything

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
| `migration_fixture_execute` | MTSF fixture maps to kernel records |

**Expected:** top-level `"passed": true` and every step `"passed": true`.

Uses an **ephemeral temp directory** by default (does not mutate `memory/foundation/`). To exercise the repo store instead:

```bash
python3 tools/conversation_os.py foundation review --in-place
```

---

## 2. Reading order

1. **This file** — fast path
2. [`PHASE-1-IMPLEMENTATION-REVIEW.md`](./PHASE-1-IMPLEMENTATION-REVIEW.md) — architecture, invariants, module map, file index
3. [`TOOLS.md`](./TOOLS.md) — individual CLI commands and Python imports
4. [`tasks/TASK-001`](./tasks/TASK-001-lock-kernel-contracts-and-lifecycles.md) … [`TASK-005`](./tasks/TASK-005-prove-application-sdk-with-two-consumers.md) — per-task acceptance + evidence
5. [`../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md) — normative sequencing

---

## 3. What was built (one paragraph)

Phase 1 implements the **universal record kernel** from framework v1.1 §4–6: machine-readable contracts and validators (TASK-001), migration fixtures from MTSF / ThoughtShape / SDS / Conversation OS (TASK-002), an append-only event store and vertical-slice runtime (TASK-003), a profile registry with Field/Formation bootstrap (TASK-004), and an application SDK with World Studio and Workspace Curator consumer proofs (TASK-005). Historical frameworks are migration sources only; they are not runtime layers.

---

## 4. Locked invariants (do not regress in review)

- **State ≠ Claim** — `State` requires `StateCommitment`
- **Branch-bound records** require `BranchMembership`
- **Lifecycle axes** (maturity, epistemic, governance) are orthogonal
- **Profiles** cannot redefine kernel record kinds
- **Raw capture** works without inference services
- **Provenance** must close at `SourceFragment`

---

## 5. Manual spot-check commands

```bash
# Tests only (verbose)
python3 tools/conversation_os.py foundation test --verbose

# Inspect repo store (may have prior demo data)
python3 tools/conversation_os.py foundation status

# Interactive vertical slice on repo store
python3 tools/conversation_os.py foundation bootstrap
python3 tools/conversation_os.py foundation slice \
  --content "Your review content." \
  --referent-label "Review subject"
python3 tools/conversation_os.py foundation validate

# Single migration fixture
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/sds_signal_dilution.json
```

CLI handler tests (not included in `foundation test`):

```bash
PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_cli -v
```

---

## 6. Source files to read first

| Priority | File | Why |
|----------|------|-----|
| 1 | `src/conversation_os/metaphysical_kernel_contracts.py` | All kernel validators |
| 2 | `src/conversation_os/metaphysical_kernel_runtime.py` | Vertical slice + provenance |
| 3 | `src/conversation_os/metaphysical_kernel_migration.py` | Appendix F mappers |
| 4 | `src/conversation_os/metaphysical_kernel_application_sdk.py` | Application boundary |
| 5 | `src/conversation_os/metaphysical_kernel_cli.py` | Tooling handlers |

---

## 7. Review outcome actions

| Outcome | Action |
|---------|--------|
| `foundation review` passes + spot-checks OK | Approve PR #11; merge to `codex/unified-framework-sync` |
| Contract mismatch vs v1.1 | File issue on specific § section; do not merge |
| Test failure | Fix on branch or request author fix |
| Scope creep found | Note in PR comment; kernel must stay minimal |

---

## 8. Intentionally out of scope (Phase 1)

- Shape / Conversation / Pattern profile registration
- `session_append --foundation-capture` CLI hook
- Production auth (SDK uses `ApplicationContext.authorized` flag)
- Module manifests for new kernel files
- Wiring World Studio / workspace services to SDK at app boundaries

See [`PHASE-1-IMPLEMENTATION-REVIEW.md` §6](./PHASE-1-IMPLEMENTATION-REVIEW.md#6-known-limitations-intentional-phase-1-scope) for full list.
