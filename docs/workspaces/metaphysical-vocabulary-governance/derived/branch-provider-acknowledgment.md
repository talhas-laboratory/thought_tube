# Branch Provider Acknowledgment — Vocabulary Governance

**Consumer workspace:** `metaphysical-vocabulary-governance`  
**Provider workspace:** `metaphysical-branch-reasoning`  
**Acknowledged contract version:** `1.0.0`  
**Release task:** `BRANCH-005-release-branch-dependency-contract`  
**Release git revision:** `e3784b72f7f51bea8f62a6637419634d6e096fe8`

## Confirmed for VOCAB program use

Vocabulary specification and runtime work (from VOCAB-002 onward) may depend on the provider release packet:

- [`BRANCH_RELEASE_DEPENDENCY_CONTRACT.json`](../../metaphysical-branch-reasoning/derived/BRANCH_RELEASE_DEPENDENCY_CONTRACT.json)
- [`dependency-contract-vocabulary-governance.md`](../../metaphysical-branch-reasoning/derived/dependency-contract-vocabulary-governance.md)

## Consumer constraints

- Vocabulary owns mapping, promotion, and evolution semantics; branch §7 invariants are not redefined
- Canonicalization is not forced normalization; branch-local readings remain valid
- VOCAB-005 must cite this acknowledgment SHA when publishing the Vocabulary dependency contract

## Smoke alignment

Validated by `test_vocabulary_governance_consumer_preserves_branch_local_support`: opposing branch-local support readings for the same proposition remain isolated without collapse.
