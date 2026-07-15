# Kernel Migration Fixture Catalog

**Task:** KERNEL-002
**Authority:** framework v1.1 Appendix F via `metaphysical_kernel_migration.py`

| Fixture | Source family | Proves |
|---|---|---|
| `mtsf_minimal_assertion.json` | MTSF | Assertion → Claim (never State); CandidateShape deferred |
| `mtsf_uncertain_identity.json` | MTSF | Two Referents + `possibly_same_as` relation; no forced merge (§5.13) |
| `thoughtshape_stateclaim_hold.json` | ThoughtShape | Hold preserved as held SourceFragment |
| `sds_signal_dilution.json` | SDS | Source IDs in mapping rules; analogy → Claim not Referent |
| `conversation_os_minimal_session.json` | Conversation OS | Events → SourceFragment; workspace knowledge → Claim |
| `invalid_claim_as_state.json` | inject | Uncommitted State fails kernel validation |

Run a single fixture:

```bash
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/mtsf_uncertain_identity.json
```

Run the migration test suite:

```bash
pytest -q tests/test_metaphysical_kernel_migration.py
```
