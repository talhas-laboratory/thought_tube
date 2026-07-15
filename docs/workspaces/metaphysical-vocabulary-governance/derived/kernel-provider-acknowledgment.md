# Kernel Provider Acknowledgment — Vocabulary Governance

**Consumer workspace:** `metaphysical-vocabulary-governance`  
**Provider workspace:** `metaphysical-kernel-ontology`  
**Acknowledged contract version:** `1.1.0`  
**Release task:** `KERNEL-005-release-kernel-dependency-contract`  
**Release git revision:** `512236d4b089d0a4d04821cca3d068a2d0a539f4`

## Confirmed for VOCAB program use

Vocabulary governance work (from VOCAB-002 onward) may depend on the provider release packet:

- [`KERNEL_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-kernel-ontology/derived/KERNEL_RELEASE_DEPENDENCY_CONTRACT.json)
- [`dependency-contract-vocabulary-governance.md`](../../metaphysical-kernel-ontology/derived/dependency-contract-vocabulary-governance.md)

## Consumer constraints

- Type promotion and mapping must not redefine kernel record kinds
- VOCAB-005 must cite this acknowledgment SHA when publishing the Vocabulary dependency contract

## Smoke alignment

Vocabulary validators align with kernel profile conformance adversarial fixtures (`invalid_profile_redefines_kernel.json`).
