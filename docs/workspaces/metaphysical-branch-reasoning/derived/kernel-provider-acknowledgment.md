# Kernel Provider Acknowledgment — Branch Reasoning

**Consumer workspace:** `metaphysical-branch-reasoning`  
**Provider workspace:** `metaphysical-kernel-ontology`  
**Acknowledged contract version:** `1.1.0`  
**Release task:** `KERNEL-005-release-kernel-dependency-contract`  
**Release git revision:** `4830b81fc6d2d78ea96743adad49bb254e98c7de`

## Confirmed for BRANCH program use

Branch specification and runtime work (BRANCH-002 through BRANCH-005) depend on the provider release packet:

- [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-kernel-ontology/derived/KERNEL_RELEASE_DEPENDENCY_CONTRACT.json) (Kernel G5; merge via kernel program PR stack)
- [`dependency-contract-branch-reasoning.md`](../../metaphysical-kernel-ontology/derived/dependency-contract-branch-reasoning.md)

## Consumer constraints

- Branch semantics (§7) remain owned by this workspace; kernel invariants are not redefined
- BRANCH-005 cites this acknowledgment when publishing the Branch→Vocabulary contract

## Smoke alignment

Branch runtime is validated against kernel record contracts and shared-store consumer proofs documented in the Kernel G5 release packet.
