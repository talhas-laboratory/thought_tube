# Kernel Public Contract Lock — v1.1.0

**Task:** `KERNEL-001-atomic-obligation-and-contract-lock`
**Workspace:** `metaphysical-kernel-ontology`
**Authority:** [Framework v1.1](../../unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)
**Atomic matrix:** [`KERNEL_ATOMIC_OBLIGATIONS.json`](./KERNEL_ATOMIC_OBLIGATIONS.json)

This document locks the **public kernel contract boundary** after KERNEL-001. Downstream programs (Branch, Vocabulary, Formation, Shape, …) may depend on the version, record kinds, invariants, and explicit deferrals named here. They must not embed private kernel semantics.

## Contract version

| Field | Value |
|---|---|
| `CONTRACT_VERSION` | `1.1.0` |
| Records module | `src/conversation_os/metaphysical_kernel.py` (`MODULE_ID=kernel.metaphysical.records`) |
| Contracts module | `src/conversation_os/metaphysical_kernel_contracts.py` (`MODULE_ID=kernel.metaphysical.contracts`) |
| Compatibility | Additive within 1.1.x; breaking changes require new minor/major version and parent decision |

## Public record kinds (Phase 1)

| `record_kind` | Framework section | Branch-bound | Notes |
|---|---|---|---|
| `source_fragment` | §5.1 | no | Raw capture preserved before interpretation |
| `referent` | §5.2 | no | `identity_policy_id` is opaque reference until IdentityPolicy ships |
| `scope` | §5.3 | no | `modal_scope` literal set enforced |
| `state` | §5.4 | yes | Requires `valid_scope_id`; distinct from `claim` |
| `claim` | §5.7 | yes | Requires `branch_id`, `scope_id`, aligned `BranchMembership` |
| `relation_instance` | §5.6 | no | Typed participants + `scope_id` |
| `provenance` | §5.10 | no | Closure required for non-raw records |
| `model_branch` | §5.11 | no | No global truth selection in kernel |
| `branch_membership` | §5.15 | no | Links record ↔ branch participation |
| `state_commitment` | §5.16 | yes | Explicit Claim→State adoption |
| `profile_definition` | §4.3 | no | Must list `forbidden_kernel_redefinitions` |
| `profile_conformance_result` | §6.12 | no | Traceable validation outcome |

`BRANCH_BOUND_RECORD_KINDS` = `{claim, state, state_commitment}`.

## Deferred first-class kernel concepts (not in 1.1.0 public surface)

| Concept | Section | Owner at deferral | Consumer rule |
|---|---|---|---|
| `Occurrence` | §5.5 | Kernel ontology | Do not assume occurrence records exist |
| `Perspective` | §5.8 | Kernel ontology | Use claimant + branch as proxy until Perspective record ships |
| `Evidence` | §5.9 | Kernel ontology | Use provenance + claim linkage until Evidence record ships |
| `TypeDefinition` | §5.12 | Vocabulary governance | `type_id` is opaque; vocabulary owns promotion/evolution |

## Lifecycle axes (orthogonal)

| Axis | Literal module | Validator |
|---|---|---|
| Maturity | `MaturityStatus` in `metaphysical_kernel.py` | `validate_envelope`, `validate_lifecycle_independence` |
| Epistemic | `EpistemicStatus` | same |
| Governance | `GovernanceStatus` | same |

**Gap (KERNEL-004):** transition policy between maturity/epistemic/governance values is not yet a public operation. Invalid transitions are not rejected beyond literal-set membership.

## Core invariants (locked)

1. **Claim ≠ State** — adoption only through `StateCommitment` (`§6.1`, `§6.11`).
2. **No universal `branch_id` on envelope** — use `BranchMembership` (`§4.1`, `§5.15`).
3. **Provenance closure** — non-raw records trace to source or explicit creation (`§5.10`).
4. **Profiles cannot redefine kernel** — `FORBIDDEN_KERNEL_REDEFINITIONS` enforced (`§4.3`, `§6.12`).
5. **Single logical store** — `metaphysical_kernel_store.py` append-only event log; applications use SDK (`§23`).
6. **No product fields in universal kernel** — product data lives in profiles/applications only (`§29`).

## Field behavior summary (envelope)

| Field | Required | Cardinality | Branch behavior | Lifecycle |
|---|---|---|---|---|
| `id` | yes | 1 | neutral | immutable after create |
| `record_kind` | yes | 1 | neutral | immutable |
| `type_id` | yes | 1 | neutral | vocabulary-owned semantics |
| `created_at` | yes | 1 | neutral | immutable |
| `created_by` | yes | 1 | neutral | immutable |
| `provenance_id` | yes | 1 | neutral | immutable reference |
| `maturity_status` | yes | 1 | neutral | independent axis |
| `epistemic_status` | yes | 1 | neutral | independent axis |
| `governance_status` | yes | 1 | neutral | independent axis |
| `scope_id` | optional on envelope | 0–1 | may scope visibility | neutral |
| `version` | default `"1"` | 1 | neutral | versioned updates |
| `visibility_policy` | default `private` | 1 | neutral | governance-related |

## Migration and compatibility

- **Additive:** new optional fields on existing records require obligation row + guard + fixture.
- **Breaking:** forbidden without contract version bump and parent decision record.
- **Historical frameworks:** migration-only via `metaphysical_kernel_migration.py`; not runtime layers.
- **Identity/provenance:** migrations must preserve source IDs and provenance chains (KERNEL-002 scope).

## Open gaps routed to later tasks

| Obligation ID | Target task |
|---|---|
| `KERNEL-22-LIFECYCLE-TRANSITIONS` | KERNEL-004 |
| `KERNEL-5.16-STALENESS-PROPAGATION` | KERNEL-005 dependency contract |
| `KERNEL-5.2-REFERENT-IDENTITY` | KERNEL-002 |

## Verification commands (KERNEL-001)

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py foundation review
PYTHONPATH=src python3 -m unittest tests.test_kernel_atomic_obligations tests.test_metaphysical_kernel_contracts -v
```

## Downstream dependency statement

Branch and Vocabulary programs may integrate against **KERNEL-005** release packet [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](./KERNEL_RELEASE_DEPENDENCY_CONTRACT.json) at `CONTRACT_VERSION=1.1.0`. Until merge, consume [`KERNEL_ATOMIC_OBLIGATIONS.json`](./KERNEL_ATOMIC_OBLIGATIONS.json) as the semantic boundary.
