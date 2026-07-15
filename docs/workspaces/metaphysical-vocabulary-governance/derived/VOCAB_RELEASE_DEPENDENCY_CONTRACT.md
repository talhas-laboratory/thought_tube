# Vocabulary Release Dependency Contract — G5

**Task:** `VOCAB-005-release-vocabulary-dependency-contract`  
**Provider:** `metaphysical-vocabulary-governance`  
**Contract version:** `1.0.0`  
**Machine packet:** [`VOCAB_RELEASE_DEPENDENCY_CONTRACT.json`](./VOCAB_RELEASE_DEPENDENCY_CONTRACT.json)

This document is the **consumable G5 release** for Phase 1 vocabulary governance. Profile and application programs may pass integration gates against the version and SHA named here.

## Release identity

| Field | Value |
|---|---|
| `provider_contract_version` | `1.0.0` |
| `kernel_contract_version_consumed` | `1.1.0` |
| `branch_contract_version_consumed` | `1.0.0` |
| `compatibility_class` | Additive within `1.0.x` |
| `release_git_revision` | `22fa9ebe69ec0115bf6b0d0247b704638bba2add` |
| Conformance evidence | [`VOCAB_CONFORMANCE_COVERAGE.json`](./VOCAB_CONFORMANCE_COVERAGE.json) |

## What consumers may depend on

- Public contract lock ([`VOCAB_PUBLIC_CONTRACT_LOCK.md`](./VOCAB_PUBLIC_CONTRACT_LOCK.md)) v1.0.0
- Runtime module `src/conversation_os/metaphysical_vocabulary_governance.py`
- Operations documented in [`VOCAB_RUNTIME_OPERATIONS.md`](./VOCAB_RUNTIME_OPERATIONS.md)
- Table and adversarial fixtures under `tests/fixtures/metaphysical_vocabulary/`

**Canonicalization is not forced normalization.** Mappings are records; raw expressions remain addressable.

## Supported operations

| Operation | Function | Section |
|---|---|---|
| Vocabulary level | `classify_vocabulary_level` | §8.1 |
| Raw expression capture | `capture_raw_expression` | §6.10, §27.15 |
| Entry registration | `register_vocabulary_entry` | §8.1 |
| Term mapping | `create_term_mapping` | §8.3 |
| Mapping assessment | `assess_mapping` | §8.3 |
| Branch mapping separation | `assess_branch_mapping_separation` | §8.4 |
| Type extension validation | `validate_type_extension` | §8.5 |
| Non-destructive lookup | `lookup_with_mapping` | §8.3 |
| Promotion workflow | `propose_promotion`, `review_promotion`, `assess_promotion_policy` | §8.2 |
| Evolution workflow | `record_deprecation`, `publish_evolution_report`, `record_evolution_reversal` | §8.6 |

## Mapping kinds

`equivalent`, `narrower`, `broader`, `overlaps`, `analogous` — only `equivalent` with `identity_confirmation` may imply identity.

## Core invariants (non-negotiable)

1. Mappings are records, not rewrites
2. `analogous` / `overlaps` never imply identity or equivalence
3. Promotion is optional; declined promotion leaves local terms usable
4. Extensions cannot redefine kernel `Claim`, `State`, or `SourceFragment`
5. Branch-local mappings are not global by default
6. Governance approval does not promote epistemic status (§22)
7. Evolution keeps prior definitions addressable; destructive in-place edits forbidden
8. Raw expressions preserved verbatim

## Forbidden interpretations

- Treating analogy or overlap as equivalence
- Forced normalization or silent canonical substitution
- Coercing branch-local terms to global scope
- Redefining kernel record semantics via vocabulary extension
- Treating steward approval as epistemic promotion

## Upstream dependencies

| Provider | Version | Release SHA | Acknowledgment |
|---|---|---|---|
| Kernel | `1.1.0` | `4830b81…` | [`VOCABULARY_ATOMIC_OBLIGATIONS.json`](./VOCABULARY_ATOMIC_OBLIGATIONS.json) |
| Branch | `1.0.0` | `e3784b7…` | [`branch-provider-acknowledgment.md`](./branch-provider-acknowledgment.md) |

## Known Phase 1 limits

| Risk | Limit |
|---|---|
| VOCAB-R-001 | Namespace prefix conventions may need parent harmonization |
| VOCAB-R-002 | Abstention threshold caller-configurable (default 0.5) |
| VOCAB-R-003 | Stale dependent refresh reported, not auto-executed |
| VOCAB-R-006 | Profile rendering proof via vocabulary consumer smoke only |

## Verification ladder

```bash
pytest -q tests/test_metaphysical_vocabulary_governance.py \
  tests/test_metaphysical_vocabulary_conformance.py \
  tests/test_vocab_contract_fixtures.py \
  tests/test_vocab_release_contract.py \
  tests/test_vocab_consumer_smoke.py \
  tests/test_metaphysical_kernel_contracts.py \
  tests/test_metaphysical_kernel_profile_registry.py \
  tests/test_metaphysical_branch_consumer_smoke.py
```

## Consumer smoke proof

| Consumer | Test |
|---|---|
| `metaphysical-kernel-application-sdk` | `test_application_consumer_renders_mapping_without_mutation` |

## Future consumers

Conversation/Formation, Shape/Pattern, and Agent programs should pin this release packet before implementing vocabulary-dependent rendering.
