# Dependency Contract: Branch Reasoning → Vocabulary Governance

**Provider:** `metaphysical-branch-reasoning`
**Consumer:** `metaphysical-vocabulary-governance`
**Status:** Draft — becomes consumable after Branch G3 and versioned at Branch G5.

The provider supplies branch-scoped assertion, inheritance, contradiction-preserving support, and merge/inference policy. The consumer must preserve branch-local vocabulary interpretations and may not promote a branch-local mapping as universal truth by implication.

Consumer runtime work requires a provider contract version, invariants, migration behavior, failure/absence behavior, and conformance evidence. Breaking semantic changes require a parent change record and consumer gate regression.
