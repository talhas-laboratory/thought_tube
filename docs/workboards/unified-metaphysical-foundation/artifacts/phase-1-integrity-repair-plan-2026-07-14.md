# Phase 1 integrity repair plan

**Status:** Proposed — do not move TASK-001 through TASK-005 to `done` until the P1 gates below pass.
**Scope:** Repair the merged Phase 1 kernel without changing framework v1.1 semantics or adding new primitives.
**Authority:** Framework v1.1 §§4.1, 5.1–5.16, 6.1, 6.2, 6.11, 6.12, 20.5, 21.1; review evidence from 2026-07-14.

## Outcome

The foundation must reject malformed records and incoherent State adoption *before* they enter the append-only store. A complete bundle validator must cover every implemented kernel record kind, preserve State–Claim disjointness, and remain safe to execute in tests on machines connected to the live workspace API.

## Chosen approach

1. **Rejected: isolated patches.** Fixing only the four observed examples would leave the validator fragmented and make the next missing cross-record invariant likely.
2. **Rejected: a new schema subsystem.** A parallel validation layer would violate the one-kernel principle and duplicate existing dataclasses, parsers, and store folds.
3. **Chosen: extend the existing contracts module into the single conformance gate.** Add missing record validators and a bundle-level identity/reference index; have runtime writes preflight through that gate before append. This is the smallest path that fixes the observed failures and provides a reusable boundary for future profiles and applications.

## Work package A — complete the contract gate

**Owner modules:** `metaphysical_kernel_contracts.py`, `metaphysical_kernel.py`, `tests/test_metaphysical_kernel_contracts.py`, `tests/fixtures/metaphysical_kernel/`.

1. Add semantic validators for `SourceFragment`, `Referent`, `Scope`, `RelationInstance`, and `ModelBranch`.
2. Make `validate_fixture_bundle()` parse and validate every implemented record collection, rather than silently skipping them.
3. Build one bundle identity index before individual validation. Reject duplicate IDs across and within collections; specifically enforce `State(id) → not Claim(id)` (§6.1).
4. Validate reference closure:
   - every envelope `provenance_id` resolves to a `Provenance` record;
   - every `BranchMembership.record_id` resolves to an implemented record;
   - Claim membership matches both the Claim branch and scope (§5.15, §6.2);
   - State, StateCommitment, and every source Claim membership agree on branch and effective scope (§5.16, §6.11).
5. Remove the unreachable `validate_state_claim_disjoint(record_kind)` helper or replace it with the bundle-level ID check.

**Required regression fixtures:**

- source Claim membership with a mismatched effective scope;
- duplicate State/Claim ID;
- malformed SourceFragment, Referent, Scope, RelationInstance, and ModelBranch;
- dangling envelope provenance, branch membership, StateCommitment, and source Claim references.

**Acceptance:** every fixture fails with an error that identifies the governing framework section; existing valid fixtures remain valid.

## Work package B — make adoption writes fail closed

**Owner modules:** `metaphysical_kernel_runtime.py`, `metaphysical_kernel_store.py`, `tests/test_metaphysical_kernel_runtime.py`.

1. In `commit_state_from_claims()`, resolve and validate source Claims, their memberships, the requested branch/scope, provenance, and generated State/StateCommitment records before appending anything.
2. Preflight the proposed records against the current folded bundle through the complete contract gate from work package A.
3. Add a minimal atomic append mechanism to `FoundationStore` for the commitment, State, and both memberships. The fold must expose all records only after a complete batch is present.
4. On validation failure, return or raise a structured `ContractValidationError`; append zero events and leave the folded bundle unchanged.
5. Preserve reversibility: valid retraction/revision behavior must continue to work and must not silently adopt a replacement State.

**Acceptance:** attempting adoption with a missing Claim, wrong branch, wrong scope, missing provenance, or duplicate ID adds zero events. A valid adoption creates the expected four records and validates cleanly.

## Work package C — make verification safe and representative

**Owner modules:** `metaphysical_kernel_cli.py`, `tests/test_metaphysical_kernel_cli.py`, kernel test modules.

1. Split reconciliation-command construction from reconciliation execution. Unit tests test command construction only.
2. Require an explicit execution intent for a connected `foundation reconcile-ledger` run; default test and inspection paths are dry-run/offline and never read the home API configuration implicitly.
3. Replace the current offline-mode test with mocked transport/subprocess boundaries. Assert that no workspace command or projection publish can execute in a unit test.
4. Extend `foundation review` with:
   - one successful runtime State adoption (`states: 1`, `state_commitments: 1`);
   - one rejected runtime adoption that proves event count and bundle contents are unchanged;
   - the new malformed-record and duplicate-ID fixture suite.
5. Keep `foundation review` ephemeral. Live ledger reconciliation remains an explicitly authorized operational command, not a test command.

**Acceptance:** all tests can run with a configured live API without mutating the workspace; review output proves both valid and invalid adoption paths.

## Work package D — separate repository hygiene from integrity repair

**Owner:** repository maintainer; no kernel semantic change.

The Phase 1 merge brought 2,854 files, 1,043,241 added lines, and 2,433 tracked `node_modules` paths. Create a separate maintenance change that inventories tracked vendor artifacts, confirms which are intentional releases, removes generated dependency trees from source control where appropriate, and adds ignore/reproducible-install rules. Do not combine this cleanup with the integrity repair PR.

**Acceptance:** the repair diff is limited to the kernel, its tests/fixtures, CLI isolation, and reviewer evidence; vendor cleanup has its own reviewable change and rollback path.

## Execution order and gates

```text
A. Complete bundle conformance gate
        ↓
B. Preflight + atomic State adoption
        ↓
C. Safe, representative test and review harness
        ↓
D. Independent vendor/repository hygiene change
        ↓
Independent reviewer reruns the foundation gate
        ↓
Live task evidence records merge SHA; tasks may move to done
```

Before implementation, refresh the repository overview and obtain an engineering-guard result for the smallest declared edit surface. Create one live child task per work package; keep TASK-001 through TASK-005 in `review` until A–C pass. After each live coordination mutation, publish projections, commit them, and push.

## Verification matrix

| Gate | Evidence |
|---|---|
| Contract completeness | Targeted contract tests plus all valid/invalid fixtures |
| Branch/scope integrity | New Claim-membership-scope and StateCommitment-path adversarial fixtures |
| State–Claim separation | Duplicate-ID fixture rejected |
| Write safety | Runtime test: invalid adoption adds zero events; valid adoption adds one atomic batch |
| Coordination safety | CLI tests with reachable API configuration show zero requests and zero projection writes |
| End-to-end | `python3 tools/conversation_os.py foundation review` passes with one adopted State and one negative path |
| Merge hygiene | Repair diff excludes vendor cleanup; a reviewer verifies `git diff --check` and changed-file scope |

## Residual risks

- Atomic append requires a small store-format extension; the migration of existing append events must be tested.
- Profile and application surfaces rely on this gate, so they should not be expanded while A–C are incomplete.
- The existing live evidence references pre-merge history; after repair, record the repair merge SHA rather than treating old evidence as final acceptance.
