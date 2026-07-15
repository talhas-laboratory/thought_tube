# Vocabulary Runtime Operations — VOCAB-003

**Task:** `VOCAB-003-promotion-and-evolution-workflow`  
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
| Promotion proposal | §8.2 | `propose_promotion` |
| Promotion review | §8.2 | `review_promotion` |
| Promotion policy | §8.2 | `assess_promotion_policy` |
| Deprecation record | §8.6 | `record_deprecation` |
| Evolution report | §8.6 | `publish_evolution_report` |
| Evolution reversal | §8.6 | `record_evolution_reversal` |

## Verification

```bash
pytest -q tests/test_metaphysical_vocabulary_governance.py
pytest -q tests/test_vocab_contract_fixtures.py
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_profile_registry.py
```

Table fixtures include `evolution_outcome_table.json` (VOCAB-003).

## Phase 1 limits

- Promotion and evolution records are in-memory; persistent workflow store deferred.
- Stale dependent refresh is reported but not executed automatically.
- Automated promotion scoring not published; steward review is explicit.
