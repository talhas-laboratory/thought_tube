# Kernel Release Dependency Contract — G5

**Task:** `KERNEL-005-release-kernel-dependency-contract`  
**Provider:** `metaphysical-kernel-ontology`  
**Contract version:** `1.1.0`  
**Machine packet:** [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](./KERNEL_RELEASE_DEPENDENCY_CONTRACT.json)

This document is the **consumable G5 release** for the Phase 1 metaphysical kernel. Branch, Vocabulary, and profile programs may pass integration gates against the version and SHA named here.

## Release identity

| Field | Value |
|---|---|
| `provider_contract_version` | `1.1.0` |
| `compatibility_class` | Additive within `1.1.x` |
| `release_git_revision` | `512236d4` (`512236d4b089d0a4d04821cca3d068a2d0a539f4`) |
| Conformance evidence | [`KERNEL_CONFORMANCE_COVERAGE.json`](./KERNEL_CONFORMANCE_COVERAGE.json) |

## What consumers may depend on

- Universal record envelope and Phase 1 record kinds (see [`KERNEL_PUBLIC_CONTRACT_LOCK.md`](./KERNEL_PUBLIC_CONTRACT_LOCK.md))
- Append-only kernel store (`metaphysical_kernel_store.py`) as the single logical persistence surface
- Validators in `metaphysical_kernel_contracts.py`
- Runtime operations in `metaphysical_kernel_runtime.py` (see [`KERNEL_RUNTIME_OPERATIONS.md`](./KERNEL_RUNTIME_OPERATIONS.md))
- Application SDK (`metaphysical_kernel_application_sdk.py`) for bounded consumer mutations
- Historical migration families (see [`KERNEL_MIGRATION_FIXTURE_CATALOG.md`](./KERNEL_MIGRATION_FIXTURE_CATALOG.md))

## Core invariants (non-negotiable)

1. Claim ≠ State — adoption only via `StateCommitment`
2. No universal `branch_id` on envelope — use `BranchMembership`
3. Provenance closure for non-raw records
4. Profiles cannot redefine kernel semantics
5. No product-specific fields in universal kernel records
6. No parallel canonical store per application

## Failure and absence behavior

| Condition | Kernel behavior |
|---|---|
| Invalid bundle / adoption | Fail closed; no misleading append |
| `same_as` identity merge | Rejected until explicit confirmation workflow |
| Missing provenance / membership | Validator errors |
| Deferred concepts (Occurrence, Perspective, Evidence, TypeDefinition) | Must not be assumed |

## Known Phase 1 limits (explicit)

| Obligation | Limit |
|---|---|
| `KERNEL-22-LIFECYCLE-TRANSITIONS` | Literal-set validation only; no public transition policy API |
| `KERNEL-5.16-STALENESS-PROPAGATION` | Commitment links exist; staleness signals for dependents not published |

## Verification ladder

```bash
python3 tools/conversation_os.py foundation review
pytest -q tests/test_kernel_release_contract.py tests/test_kernel_conformance_suite.py \
  tests/test_kernel_atomic_obligations.py tests/test_metaphysical_kernel_contracts.py \
  tests/test_metaphysical_kernel_migration.py tests/test_metaphysical_kernel_runtime.py \
  tests/test_metaphysical_kernel_profile_registry.py tests/test_metaphysical_kernel_application_sdk.py
```

## Consumer smoke proofs

| Application | Test |
|---|---|
| `app:world_studio` | `test_world_studio_consumer_uses_shared_kernel_without_private_ontology` |
| `app:workspace_curator` | `test_workspace_curator_consumer_can_commit_state` |

## Downstream contracts

| Consumer | Provider contract | Consumer acknowledgment |
|---|---|---|
| Branch reasoning | [`dependency-contract-branch-reasoning.md`](./dependency-contract-branch-reasoning.md) | [`kernel-provider-acknowledgment.md`](../../metaphysical-branch-reasoning/derived/kernel-provider-acknowledgment.md) |
| Vocabulary governance | [`dependency-contract-vocabulary-governance.md`](./dependency-contract-vocabulary-governance.md) | [`kernel-provider-acknowledgment.md`](../../metaphysical-vocabulary-governance/derived/kernel-provider-acknowledgment.md) |
