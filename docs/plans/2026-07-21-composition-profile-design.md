# Composition profile design

## Decision

Add `profile:composition@1.0.0` as a contract-first Shape-program profile.
It models bounded whole-constituent claims without adding a universal kernel
primitive, persistence store, traversal API, causal inference, ownership, or
role semantics.

## Contracts

`system_boundary` declares a whole referent, boundary rule, identity rule,
scale, scope, branch, and provenance. A boundary can be material, functional,
organizational, semantic, or unresolved.

`composition_assertion` links a whole and constituent through a declared
composition kind, boundary, scope, branch, provenance, and existing generic
relation instance. Kinds are intentionally distinct: material part, functional
component, membership, and social constitution. It may also cite the
QualityInstance from which a reified constituent originated.

## Recursive systemhood

The same referent may be a constituent under one boundary and a whole under a
different boundary. This is a declared resolution change, not a silent change
of identity. Self-containment in one assertion is rejected; longer cycles are
not inferred from isolated portable contracts and must be surfaced as explicit
unresolved contradictions when graph persistence arrives.

## Verification

The fixture covers each composition kind and a nested mycorrhizal subsystem.
Tests reject missing or invalid boundary/identity/composition fields and a
self-constituent assertion.
