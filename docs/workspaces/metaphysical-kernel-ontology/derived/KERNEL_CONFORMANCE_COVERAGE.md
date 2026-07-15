# Kernel Conformance Coverage — KERNEL-004

**Task:** `KERNEL-004-kernel-conformance-suite`
**Machine index:** [`KERNEL_CONFORMANCE_COVERAGE.json`](./KERNEL_CONFORMANCE_COVERAGE.json)
**Obligation matrix:** [`KERNEL_ATOMIC_OBLIGATIONS.json`](./KERNEL_ATOMIC_OBLIGATIONS.json)

## Suite modules

| Module | Category |
|---|---|
| `tests.test_kernel_atomic_obligations` | Obligation matrix integrity |
| `tests.test_kernel_conformance_suite` | Coverage inventory + adversarial/gap fixtures |
| `tests.test_metaphysical_kernel_contracts` | Contract validators |
| `tests.test_metaphysical_kernel_migration` | Historical migration |
| `tests.test_metaphysical_kernel_runtime` | Runtime vertical slice |
| `tests.test_metaphysical_kernel_profile_registry` | Profile registry |
| `tests.test_metaphysical_kernel_application_sdk` | Consumer SDK |

## Adversarial fixtures (must reject)

| Fixture | Invariant |
|---|---|
| `invalid_claim_without_membership.json` | Branch membership alignment |
| `invalid_state_*` (4 fixtures) | State commitment linkage |
| `invalid_state_without_commitment.json` | Claim ≠ State |
| `invalid_profile_redefines_kernel.json` | Profile cannot redefine kernel |
| `invalid_provenance_no_source.json` | Provenance closure |
| `invalid_lifecycle_axis_collapse.json` | Lifecycle axis orthogonality |
| `migration/invalid_claim_as_state.json` | Uncommitted State injection |

## Gap fixtures (documented limits)

| Fixture | Obligation | Phase 1 behavior |
|---|---|---|
| `invalid_maturity_transition.json` | `KERNEL-22-LIFECYCLE-TRANSITIONS` | Literal validation only; no transition policy |
| `commitment_revocation_staleness.json` | `KERNEL-5.16-STALENESS-PROPAGATION` | Links validate; staleness propagation not published |

## Residual risks (explicit)

1. **Lifecycle transitions** — owned by KERNEL-005 dependency contract
2. **Staleness propagation** — owned by KERNEL-005 dependency contract

## Verification ladder

```bash
python3 tools/conversation_os.py foundation review
pytest -q tests/test_kernel_conformance_suite.py tests/test_kernel_atomic_obligations.py \
  tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_migration.py \
  tests/test_metaphysical_kernel_runtime.py tests/test_metaphysical_kernel_profile_registry.py \
  tests/test_metaphysical_kernel_application_sdk.py
```
