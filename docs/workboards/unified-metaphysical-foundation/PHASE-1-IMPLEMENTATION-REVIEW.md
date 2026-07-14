# Phase 1 Implementation Review — Metaphysical Foundation

**Status:** Ready for agent review  
**Implementation branch:** `cursor/metaphysical-kernel-contracts-423a`  
**Base branch:** `codex/unified-framework-sync`  
**Pull request:** [#11](https://github.com/talhas-laboratory/thought_tube/pull/11)  
**Workboard:** `unified-metaphysical-foundation`  
**Canonical authority:** [`thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)

This document is the primary handoff surface for reviewers. It describes what was built, how modules relate, which invariants are enforced, how to verify, and what remains out of scope.

---

## 1. Executive summary

Phase 1 implements the **universal record kernel** and the first **executable path** from raw capture through profile-bound application SDK — without LLM inference, embeddings, or profile surfaces beyond Field/Formation bootstrap.

```text
Framework v1.1 (paper)
  → TASK-001 machine-readable contracts + validators
  → TASK-002 migration fixtures (MTSF, ThoughtShape, SDS, Conversation OS)
  → TASK-003 append-only store + vertical slice runtime
  → TASK-004 profile registry + Field/Formation bootstrap
  → TASK-005 application SDK + two consumer proofs
```

**Verification status:** `foundation review` passes all 10 review steps, including 58 kernel tests and adversarial state fixtures. CLI handler tests are separate and include a connected-environment reconciliation path that must remain isolated from live coordination.

**Audit:** See [`GAP-REPORT-2026-07-12.md`](./GAP-REPORT-2026-07-12.md). Gap 1 is repaired on branch and Gap 2 has been reconciled in the live workspace.

**Workboard:** TASK-001 through TASK-005 are `review`; the live workspace has no open blockers.

---

## 2. Architecture

### 2.1 Layer model (do not invert)

```text
┌─────────────────────────────────────────────────────────┐
│  Applications (World Studio, Workspace Curator, …)      │
│  metaphysical_kernel_application_sdk.py                 │
├─────────────────────────────────────────────────────────┤
│  Profile runtime (Field/Formation v1.0.0)               │
│  metaphysical_kernel_profile_registry.py                │
├─────────────────────────────────────────────────────────┤
│  Kernel runtime (capture, branch, claim, state, view)  │
│  metaphysical_kernel_runtime.py + metaphysical_kernel_store.py │
├─────────────────────────────────────────────────────────┤
│  Contracts + validation                                 │
│  metaphysical_kernel.py + metaphysical_kernel_contracts.py │
├─────────────────────────────────────────────────────────┤
│  Migration evidence (historical frameworks → kernel)    │
│  metaphysical_kernel_migration.py                       │
└─────────────────────────────────────────────────────────┘
```

Historical frameworks (MTSF, SDS, ThoughtShape) are **migration sources only**. They are not runtime layers.

### 2.2 Module map

| File | MODULE_ID | Task | Responsibility |
|------|-----------|------|----------------|
| `metaphysical_kernel.py` | `kernel.metaphysical.records` | 001 | Dataclasses: envelope, Phase 1 MVP records, lifecycle literals, `FRAMEWORK_SECTIONS` |
| `metaphysical_kernel_contracts.py` | `kernel.metaphysical.contracts` | 001 | Validators, `from_dict` loaders, `validate_fixture_bundle()` |
| `metaphysical_kernel_migration.py` | `kernel.metaphysical.migration` | 002 | Family mappers, `MappingRule`, loss reports, Gate F1 |
| `metaphysical_kernel_store.py` | `kernel.metaphysical.store` | 003 | Append-only `kernel_events.jsonl`, folded read model |
| `metaphysical_kernel_runtime.py` | `kernel.metaphysical.runtime` | 003 | Capture → claim → state → bounded view → provenance |
| `metaphysical_kernel_profile_registry.py` | `kernel.metaphysical.profile_registry` | 004 | Profile registration, bindings, conformance, upgrades |
| `metaphysical_kernel_application_sdk.py` | `kernel.metaphysical.application_sdk` | 005 | Profile-bound SDK, two consumer proofs |
| `metaphysical_kernel_cli.py` | `kernel.metaphysical.cli` | tools | CLI handlers for `conversation_os.py foundation` |

### 2.3 Persistence

| Artifact | Path | Semantics |
|----------|------|-----------|
| Kernel event log | `memory/foundation/kernel_events.jsonl` | Append-only; operations `append_record`, `retract_record` |
| Session events (bridge input) | `memory/events/{session_id}.jsonl` | Existing Conversation OS capture; SDK reads, does not replace |

There is **no separate application database**. Applications use the shared kernel store via SDK.

---

## 3. Task-by-task deliverables

### TASK-001 — Lock kernel contracts and lifecycles (Gate F0)

**Framework sections:** §4.1, §5.1–5.7, §5.10–5.11, §5.15–5.16, §4.3, §6.12, §22.1

**Records implemented:**

- `KernelRecordEnvelope`
- `SourceFragment`, `Referent`, `Scope`, `State`, `Claim`, `RelationInstance`, `Provenance`, `ModelBranch`
- `BranchMembership`, `StateCommitment`
- `ProfileDefinition`, `ProfileConformanceResult` (minimal, for profile/kernel separation)

**Invariants enforced in code:**

| Invariant | Enforcement |
|-----------|-------------|
| State ≠ Claim | `validate_state` requires `StateCommitment` |
| Branch-bound records need membership | `validate_claim`, `validate_state` |
| Lifecycle axes orthogonal | `validate_lifecycle_independence` |
| Profiles cannot redefine kernel | `FORBIDDEN_KERNEL_REDEFINITIONS` in `validate_profile_definition` |
| Provenance terminates in sources | `validate_provenance_closure` |

**Tests:** `tests/test_metaphysical_kernel_contracts.py` (12)  
**Fixtures:** `tests/fixtures/metaphysical_kernel/*.json`

---

### TASK-002 — Migration fixtures (Gate F1)

**Authority:** Appendix F

**Source families:**

| Family | Fixture | Maps to |
|--------|---------|---------|
| MTSF | `migration/mtsf_minimal_assertion.json` | Referent, Claim, SourceFragment; CandidateShape deferred |
| ThoughtShape | `migration/thoughtshape_stateclaim_hold.json` | Hold → held fragment; StateClaim → Claim only |
| SDS | `migration/sds_signal_dilution.json` | Entities, states→Claim, relations; loops/shapes/anti-match deferred |
| Conversation OS | `migration/conversation_os_minimal_session.json` | Events→SourceFragment, concept, formation, knowledge→Claim |

**Gate F1 rules in code:**

- Source IDs preserved in `MappingRule.source_id`
- Analogy → Claim, never Referent (`_analogy_identity_violations`)
- No State without `StateCommitment` in migrated bundles
- `semantic_loss_warnings` + `loss_report` for profile-deferred concepts

**Tests:** `tests/test_metaphysical_kernel_migration.py` (14)

---

### TASK-003 — Vertical slice runtime (Gate F2)

**Path implemented:**

```text
capture SourceFragment (incl. session_append bridge)
→ ensure Scope + ModelBranch
→ resolve Referent
→ assert Claim + BranchMembership
→ optional commit_state (StateCommitment + State)
→ retract / revise
→ query BoundedView (branch + scope + max_depth)
→ trace_provenance → SourceFragment
```

**Gate F2 tests verify:**

- Append-only durability
- Competing branches isolated in bounded views
- Retraction excludes records from default view
- Depth limit fails closed
- Provenance trace completes at source fragment

**Tests:** `tests/test_metaphysical_kernel_runtime.py` (11)

---

### TASK-004 — Profile registry (Gate F3)

**Built-in profile:** `profile:field_formation` v1.0.0 (§8A)

**Registry capabilities:**

- `register()` with semver + duplicate rejection
- `_parallel_kernel_type_errors` — profile record types must not duplicate kernel kinds
- `_dependency_cycle_errors` — acyclic dependency graph
- `bind_application()` — invariant preservation
- `evaluate_conformance()` — kernel bundle vs profile invariants
- `plan_upgrade()` — stale records when profile record types removed

**Tests:** `tests/test_metaphysical_kernel_profile_registry.py` (9)

---

### TASK-005 — Application SDK (Gate F4)

**SDK:** `FoundationApplicationSdk` + `ApplicationContext` + `SdkMutationResult`

Every mutation returns: record IDs, branch, scope, provenance, validation errors, compensating operation metadata.

**Consumer proofs:**

| Consumer | App ID | Demonstrates |
|----------|--------|--------------|
| World Studio | `app:world_studio` | Fictional scene capture, claim, formation projection |
| Workspace Curator | `app:workspace_curator` | Workspace insight, optional state commit, hold |

**Gate F4:**

- Same store + profile for both consumers
- Unauthorized / budget-exceeded → abstain without new mutation records
- `derive_shape` abstains in Phase 1 without corrupting bundle

**Tests:** `tests/test_metaphysical_kernel_application_sdk.py` (7)

---

## 4. Locked decisions (review must not regress)

From workspace v1.1 cutover and implementation:

1. **One kernel** → governed profiles → application projections (not three stacked frameworks).
2. **State ≠ Claim** — adoption requires `StateCommitment`.
3. **Branch-bound interpretation** requires `BranchMembership`.
4. **Maturity, epistemic, governance** are orthogonal lifecycle axes.
5. **Raw capture** must work with all inference services unavailable.
6. **Historical frameworks** are migration evidence, not runtime owners.
7. **Profile record types** must not duplicate kernel record kinds.

---

## 5. Verification checklist for reviewers

Run in order:

```bash
# 0. One-shot automated review (preferred — includes adversarial state fixtures)
python3 tools/conversation_os.py foundation review

# 1. CLI handler tests (not in foundation test)
PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_cli -v

# 2. Full kernel test suite (verbose)
python3 tools/conversation_os.py foundation test --verbose

# 2. Empty store status
python3 tools/conversation_os.py foundation status

# 3. Bootstrap + slice + validate
python3 tools/conversation_os.py foundation bootstrap
python3 tools/conversation_os.py foundation slice \
  --content "Review slice." \
  --referent-label "Review subject"
python3 tools/conversation_os.py foundation validate

# 4. Both consumers on same store (use same repo root / tmp dir)
python3 tools/conversation_os.py foundation consumer world-studio \
  --content "Scene text." --referent-label "Element"
python3 tools/conversation_os.py foundation consumer workspace-curator \
  --content "Insight text."
python3 tools/conversation_os.py foundation conformance

# 5. Migration fixture
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/sds_signal_dilution.json

# 6. Live workspace state (read-only confirmation)
python3 tools/workspace_coordination.py tasks --workspace-id unified-framework-synthesis
```

**Expected:** `foundation review` → `"passed": true` (all 10 steps); adversarial state fixtures rejected; live tasks remain `review` with blocker `blocker-7f7662afad54` resolved.

---

## 6. Known limitations (intentional Phase 1 scope)

| Item | Status |
|------|--------|
| Shape / Conversation / Pattern profiles | Not registered; `derive_shape` abstains |
| `field`, `hold`, `formation` profile record instances | Projections only in SDK; not persisted as kernel records |
| CLI `session_append --foundation-capture` | Not wired; use `foundation capture` or SDK |
| Kernel module manifests | Tracked in `manifests/`; copy to `context/substrate/modules/` locally |
| Repo-wide module manifests | Not recovered; engineering guard may report `needs_index` |
| Live workspace ledger | Reconciled; all five tasks are `review` and no blocker is open |
| Round-trip inverse migration loaders | Not implemented |
| Production auth | SDK uses `ApplicationContext.authorized` flag only |

---

## 7. Review questions (suggested)

1. Does `validate_state_adoption_links` fully enforce §5.16 / §6.11 (re-run adversarial fixtures)?
2. Do contract field names and lifecycle literals match v1.1 §4–6, §22 exactly enough for Phase 2?
3. Are migration loss reports complete for deferred profile concepts?
4. Does bounded view isolation correctly prevent cross-branch leakage in realistic bundles?
5. Is live workspace ledger reconciled (`blocker-7f7662afad54` resolved)?
6. Is `profile:field_formation` v1.0.0 sufficient as first normative profile, or should Field and Formation split?

---

## 8. File index (all new/changed implementation files)

```
src/conversation_os/
  metaphysical_kernel.py
  metaphysical_kernel_contracts.py
  metaphysical_kernel_migration.py
  metaphysical_kernel_store.py
  metaphysical_kernel_runtime.py
  metaphysical_kernel_profile_registry.py
  metaphysical_kernel_application_sdk.py
  metaphysical_kernel_cli.py
  cli.py                          # `foundation` subcommand wiring

tests/
  test_metaphysical_kernel_cli.py
  test_metaphysical_kernel_contracts.py
  test_metaphysical_kernel_migration.py
  test_metaphysical_kernel_runtime.py
  test_metaphysical_kernel_profile_registry.py
  test_metaphysical_kernel_application_sdk.py
  fixtures/metaphysical_kernel/   # valid + invalid + Gap 1 adversarial
  fixtures/migration/

docs/workboards/unified-metaphysical-foundation/
  REVIEWER-START.md              # start here
  GAP-REPORT-2026-07-12.md
  GAP-2-RECONCILIATION.md
  manifests/                     # tracked kernel module manifests
  tasks/TASK-001 … TASK-005
  TASKS.md
  TOOLS.md
  PHASE-1-IMPLEMENTATION-REVIEW.md   # this file
  HANDOFFS.md
```

---

## 9. Suggested next work after merge

1. Complete branch review, then merge PR #11 into `codex/unified-framework-sync` when the reviewer accepts the recorded evidence.
2. Opt-in `session_append` → foundation capture flag.
3. Register Shape profile; implement `derive_shape` beyond abstain.
4. Wire World Studio / workspace services to `FoundationApplicationSdk` at application boundaries.
5. Continue repo-wide module manifest recovery.

---

## 10. Contact surfaces

| Need | Location |
|------|----------|
| Reviewer fast path | [`REVIEWER-START.md`](./REVIEWER-START.md) |
| Audit / gaps | [`GAP-REPORT-2026-07-12.md`](./GAP-REPORT-2026-07-12.md) |
| Live ledger reconciliation | [`GAP-2-RECONCILIATION.md`](./GAP-2-RECONCILIATION.md) |
| CLI tools | [`TOOLS.md`](./TOOLS.md) |
| Per-task acceptance | [`tasks/`](./tasks/) |
| Build sequencing | [`../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md) |
| Normative semantics | [`../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) |
