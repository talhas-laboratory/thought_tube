# Kernel Provider Acknowledgment — Branch Reasoning

**Consumer workspace:** `metaphysical-branch-reasoning`  
**Provider workspace:** `metaphysical-kernel-ontology`  
**Acknowledged contract version:** `1.1.0`  
**Release task:** `KERNEL-005-release-kernel-dependency-contract`  
**Release git revision:** `512236d4b089d0a4d04821cca3d068a2d0a539f4`

## Confirmed for BRANCH program use

Branch specification and runtime work (from BRANCH-002 onward) may depend on the provider release packet:

- [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-kernel-ontology/derived/KERNEL_RELEASE_DEPENDENCY_CONTRACT.json)
- [`dependency-contract-branch-reasoning.md`](../../metaphysical-kernel-ontology/derived/dependency-contract-branch-reasoning.md)

## Consumer constraints

- Branch semantics (§7) remain owned by this workspace; kernel invariants are not redefined
- BRANCH-005 must cite this acknowledgment SHA when publishing the Branch→Vocabulary contract

## Smoke alignment

Branch contract design is validated against kernel consumer proofs:

- `app:world_studio` shared-store capture path
- `app:workspace_curator` state commitment path
