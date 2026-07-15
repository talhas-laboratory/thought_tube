# Dependency Contract: Kernel Ontology → Branch Reasoning

**Provider:** `metaphysical-kernel-ontology`
**Consumer:** `metaphysical-branch-reasoning`
**Status:** Draft — becomes consumable after Kernel G3 and versioned at Kernel G5.

The provider supplies universal record identity, provenance closure, `ModelBranch`, `BranchMembership`, and `StateCommitment` semantics. The consumer must not duplicate these concepts or infer a State from a Claim.

Consumer runtime work requires a provider contract version, invariants, migration behavior, failure/absence behavior, and conformance evidence. Breaking semantic changes require a parent change record and consumer gate regression.
