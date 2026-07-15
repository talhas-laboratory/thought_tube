# Dependency Contract: Kernel Ontology → Branch Reasoning

**Provider:** `metaphysical-kernel-ontology`  
**Consumer:** `metaphysical-branch-reasoning`  
**Status:** **Released** — Kernel G5 (`KERNEL-005`)  
**Provider contract version:** `1.1.0`  
**Release packet:** [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-kernel-ontology/derived/KERNEL_RELEASE_DEPENDENCY_CONTRACT.json)

## Provider supplies

Universal record identity, provenance closure, `ModelBranch`, `BranchMembership`, `StateCommitment`, and branch-bound `Claim`/`State` semantics per framework v1.1 §§4–6 and §21.

## Consumer obligations

- Do not duplicate kernel record kinds or infer `State` from `Claim`
- Consume `BranchMembership` and scope facts from kernel validators; own §7 inheritance/support/conflict/merge/inference semantics only
- Pin `provider_contract_version` and `release_git_revision` in consumer releases (BRANCH-005)

## Compatibility

| Change type | Policy |
|---|---|
| Additive optional fields within `1.1.x` | Consumer may adopt when ready |
| Breaking semantic change | Requires new provider version + parent decision + consumer gate regression |

## Failure / absence

- If kernel validation rejects a bundle, Branch runtime must not bypass with private stores
- Deferred kernel concepts (Occurrence, Perspective, Evidence, TypeDefinition) must not be assumed

## Verification consumed from provider

- [`KERNEL_CONFORMANCE_COVERAGE.json`](../../metaphysical-kernel-ontology/derived/KERNEL_CONFORMANCE_COVERAGE.json)
- Foundation review consumer steps for `app:world_studio` and `app:workspace_curator`

## Known provider limits (Phase 1)

- Lifecycle transition policy not published (`KERNEL-22-LIFECYCLE-TRANSITIONS`)
- Staleness propagation contract not published (`KERNEL-5.16-STALENESS-PROPAGATION`)

Consumer acknowledgment: [`kernel-provider-acknowledgment.md`](../../metaphysical-branch-reasoning/derived/kernel-provider-acknowledgment.md)
