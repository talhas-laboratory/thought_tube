# Dependency Contract: Kernel Ontology → Vocabulary Governance

**Provider:** `metaphysical-kernel-ontology`
**Consumer:** `metaphysical-vocabulary-governance`
**Status:** Draft — becomes consumable after Kernel G3 and versioned at Kernel G5.

The provider supplies the universal record envelope, `TypeDefinition`, provenance, lifecycle axes, and profile-conformance boundaries. The consumer may govern extensions but may not redefine kernel meaning or erase source provenance.

Consumer runtime work requires a provider contract version, invariants, migration behavior, failure/absence behavior, and conformance evidence. Breaking semantic changes require a parent change record and consumer gate regression.
