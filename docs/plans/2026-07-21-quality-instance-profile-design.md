# QualityInstance profile design

## Decision

Add a contract-first governed profile, `profile:quality_instance@1.0.0`, as
the first Shape-program implementation. It is a profile extension, not a new
universal kernel primitive and not a persistence or SDK feature.

## Contract

A `quality_instance` identifies one bearer referent, vocabulary-owned quality
definition identifier, scope, branch, provenance record, and one basis record.
The basis is either a Claim or an adopted State; existing branch-membership and
StateCommitment rules still govern those kernel records. `TypeDefinition` is a
normative kernel concept but is not implemented in the current Phase 1 record
set, so this version deliberately does not claim it as a kernel dependency.
The Vocabulary program must replace the identifier with a validated
`TypeDefinition` reference when that kernel contract is delivered.

`quality_refinement` is optional. When present, it names the source quality
instance, an existing explicit relation instance, a permitted relation type
(`refines_to` or `reified_as`), and the reified referent. This keeps the
transition from attribute-level modeling to independently addressable entity
modeling queryable and provenance-preserving.

## Boundaries

This increment provides profile metadata, portable contract validators, and
fixtures. It does not add profile-record persistence, composition semantics,
role/influence semantics, ShapeCore/View, automated reification, or a public
application API. Those are later dependency-ordered workspace tasks.

## Verification

Focused registry and kernel-contract tests must pass. The existing foundation
review must remain green. The profile fixture is checked against the built-in
profile definition and both portable record contracts.
