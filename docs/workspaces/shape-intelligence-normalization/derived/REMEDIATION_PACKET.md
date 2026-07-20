# Normalization Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 1, 3, 7, and 8. This packet narrows that authority; it does not replace it.

## Required outcome

Build a lossless, deterministic, streaming normalization boundary that accepts large heterogeneous inputs without interpreting them, stores source bytes once, and emits stable source/segment references for later intelligence.

## Owned edit surface

- `src/conversation_os/source_content_store.py` — generic content-addressed byte ownership.
- `src/conversation_os/shape_population/normalization.py` — streaming decode, structure extraction, offsets, fingerprints.
- `src/conversation_os/vault_ingest.py` — invoke a generic post-ingest adapter only.
- `src/conversation_os/shape_population/orchestrator.py` — enqueue after successful source commit; never run intelligence inline.
- `tests/test_source_content_store.py`, `tests/test_shape_normalization.py`, and ingestion integration tests.

Do not put Shape semantics in `vault_ingest.py`, choose evidence, call a model, compare candidates, or write canonical Shapes.

## Ordered implementation

1. Write failing tests for byte-for-byte round trips, stable IDs, multibyte offsets, repeated substrings, malformed encodings, empty input, restart, and 10 MB/100 MB sources.
2. Add a content-addressed store keyed by SHA-256 of original bytes. Commit with a temporary file, `fsync`, atomic rename, and directory `fsync`; an existing digest must be verified and reused.
3. Store immutable metadata separately: digest, byte length, media type, declared encoding, detected encoding, source URI, received time, and ingestion receipt. Never store the full text in the Shape database.
4. Implement incremental decoding with explicit replacement/error policy. Maintain byte and Unicode offsets while scanning once; never compute offsets by repeatedly encoding prefixes.
5. Emit deterministic segment IDs from source digest, normalizer version, byte range, and structural path. Preserve ordered headings, paragraphs, list/table/code markers, and source-relative ranges.
6. Make normalization policy explicit and versioned. No silent 500,000-character truncation. If an operator limit is configured, reject or quarantine with a receipt containing the observed and permitted size.
7. Add a generic post-ingest hook. It receives committed source identity only, creates an idempotent job, and returns promptly. Ingestion succeeds even if the worker is unavailable.
8. Record normalizer version and content fingerprint on every segment so downstream packets are reproducible.

## Tests and exact gates

Run:

```bash
pytest -q tests/test_source_content_store.py tests/test_shape_normalization.py
pytest -q tests/test_vault_ingest.py -k 'shape or hook or source'
```

Add performance assertions on the project’s reference machine:

- peak RSS for 100 MB input is no more than 2.5 times configured stream/chunk buffers plus interpreter baseline;
- runtime growth from 10 MB to 100 MB is no worse than 15 times, guarding against quadratic behavior;
- persisted source bytes are within 1.05 times original bytes plus fixed metadata;
- a rerun creates no second content blob, segment set, or job.

## Evidence required in the live task

Changed paths; schema/version decisions; commands and timings; 10 MB and 100 MB byte/RSS results; an idempotent rerun receipt; full-suite impact; residual encoding/media limitations.

## Exit gate

No source-text duplication, truncation, semantic classification, or synchronous model work remains in normalization. Evidence workspace can reconstruct exact cited spans from stable references after restart.
