# Vocabulary Runtime Operations — VOCAB-002

**Task:** `VOCAB-002-type-registry-and-nondestructive-mapping`  
**Owner module:** `src/conversation_os/metaphysical_vocabulary_governance.py`  
**Contract:** [`VOCAB_PUBLIC_CONTRACT_LOCK.md`](./VOCAB_PUBLIC_CONTRACT_LOCK.md) v1.0.0  
**Kernel consumed:** `1.1.0`  
**Branch consumed:** `1.0.0`

## Implemented operations (Phase 1)

| Operation | Section | Module function |
|---|---|---|
| Vocabulary level classification | §8.1 | `classify_vocabulary_level` |
| Raw expression capture | §6.10, §27.15 | `capture_raw_expression` |
| Vocabulary entry registration | §8.1 | `register_vocabulary_entry` |
| Term mapping record | §8.3 | `create_term_mapping` |
| Mapping consequence assessment | §8.3 | `assess_mapping` |
| Branch mapping separation | §8.4 | `assess_branch_mapping_separation` |
| Type extension validation | §8.5 | `validate_type_extension` |
| Non-destructive lookup | §8.3 | `lookup_with_mapping` |

Promotion workflow (§8.2) and evolution reports (§8.6) remain contract-locked for VOCAB-003+.

## Verification

```bash
pytest -q tests/test_metaphysical_vocabulary_governance.py
pytest -q tests/test_vocab_contract_fixtures.py
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_profile_registry.py
```

Table fixtures: `tests/fixtures/metaphysical_vocabulary/*.json`.

## Phase 1 limits

- Mapping abstention uses default confidence threshold `0.5`; consumers may override per call.
- Registry is in-memory record construction; persistent store integration deferred.
- Promotion and deprecation workflows not yet implemented.
