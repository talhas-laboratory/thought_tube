# Vocabulary Conformance Coverage — VOCAB-004

**Task:** `VOCAB-004-vocabulary-conformance-suite`  
**Owner module:** `src/conversation_os/metaphysical_vocabulary_governance.py`  
**Machine manifest:** [`VOCAB_CONFORMANCE_COVERAGE.json`](./VOCAB_CONFORMANCE_COVERAGE.json)

## Verification command

```bash
pytest -q tests/test_metaphysical_vocabulary_governance.py \
  tests/test_metaphysical_vocabulary_conformance.py \
  tests/test_vocab_contract_fixtures.py \
  tests/test_metaphysical_kernel_contracts.py \
  tests/test_metaphysical_kernel_profile_registry.py \
  tests/test_metaphysical_branch_consumer_smoke.py
```

## Layers exercised

| Layer | Evidence |
|---|---|
| Table-driven semantics | Six VOCAB-001/002/003 outcome tables |
| Adversarial regressions | `adversarial_suite.json` (10 cases) |
| Required G4 scenarios | `VOCABULARY_TEST_AND_RELEASE_GUIDE.md` scenarios 1–6 |
| Acceptance | VOCAB-ACC-001 through VOCAB-ACC-005 |
| Cross-program | Kernel contracts, branch vocabulary consumer smoke |

## Adversarial guarantees

- `analogous` and `overlaps` never imply identity or equivalence.
- Branch-local mappings for the same phrase stay separated.
- Declined promotion does not invalidate local terms.
- Kernel redefinition and destructive in-place edits are rejected.
- Evolution reports list stale dependents and semantic-loss warnings.
- Raw expressions with punctuation are preserved verbatim.
- Governance approval does not promote epistemic status.

## Last verified

**2026-07-15** — `45 passed, 50 subtests passed`

## Residual Phase 1 limits

See `residual_limits` in the JSON manifest. Profile rendering proof remains indirect until product-surface consumer tests land.
