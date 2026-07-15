# Vocabulary Governance — Test and Release Guide

## Test layers

| Layer | What it proves |
|---|---|
| Contract | Required mapping/promotion/evolution fields and allowed values are validated |
| Preservation | Raw term, source reference, scope, branch context, and confidence survive all mappings |
| Type safety | Extensions cannot redefine kernel semantics or violate declared constraints |
| Governance | Promotion is explicit, stewarded, reviewable, and optional |
| Evolution | Versions remain addressable; migration is reversible; semantic loss and stale dependents are visible |
| Consumer | A profile/application renders mapped language without silently mutating canonical or raw records |

## Required adversarial fixtures before G4

1. A user term maps only by analogy; a consumer must not treat it as equivalence.
2. Two branches use the same phrase differently; the mappings remain separated.
3. A local term fails promotion; it remains usable in its valid local scope.
4. A proposed extension tries to redefine a kernel record; validation rejects it.
5. A term version is deprecated; prior records resolve, migration is explicit, and a dependent artifact is marked stale.
6. A source expression has punctuation, ambiguity, or a legacy label; mapping preserves it exactly.

## Suggested implementation commands

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "src/conversation_os/<owner>.py,tests/test_<owner>.py"
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_profile_registry.py
pytest -q tests/test_metaphysical_vocabulary_governance.py
```

The last command is introduced only after VOCAB-001 locks the contract. Until then, use tables and JSON fixtures in the task packet to test the specification itself.

## Release evidence

VOCAB-005 publishes the versioned mapping and evolution contract, allowed mapping kinds, promotion decision model, consumer examples, migration/deprecation policy, test results, exact SHA, known limits, and the Kernel/Branch versions it consumes. It must state clearly that canonicalization is not forced normalization.
