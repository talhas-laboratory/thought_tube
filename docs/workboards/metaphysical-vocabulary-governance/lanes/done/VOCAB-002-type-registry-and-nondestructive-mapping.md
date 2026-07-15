# VOCAB-002-type-registry-and-nondestructive-mapping: Implement type registry and non-destructive mapping

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: implement the smallest governed registry/mapping behavior consistent with the locked contract and existing `TypeDefinition` boundary.

Out: replacing raw strings in place, a second kernel type system, scope-insensitive lookup, or mappings that omit confidence/provenance.

## Work plan

1. Reuse the Kernel owner where sufficient; run engineering guard before a new owner module.
2. Store/read source expression, target, mapping kind, scope, branch context, confidence, provenance, and version.
3. Return mappings as records or views that preserve the original term.
4. Add fixtures for equivalent, narrower, broader, overlaps, and analogous mappings.

## Acceptance criteria

- Mappings retain source terms, provenance, and branch-safe meaning.
- A consumer cannot mistake analogy/overlap for identity.
- Extension constraints protect kernel semantics.

## Verification plan

- Run Kernel contract/profile tests plus focused vocabulary fixtures described in [VOCABULARY_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-vocabulary-governance/derived/VOCABULARY_TEST_AND_RELEASE_GUIDE.md).

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Include owner-module rationale, fixture paths, and any unresolved mapping semantics.
