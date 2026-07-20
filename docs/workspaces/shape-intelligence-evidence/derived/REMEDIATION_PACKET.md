# Evidence Assembly Remediation Packet

Authority: [central remediation plan](../../shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md), especially Phases 1, 3, and 8.

## Required outcome

Materialize bounded, injection-safe evidence from an intelligence-authored inquiry. Deterministic code enforces access, provenance, and budgets; it must not decide what is semantically important.

## Owned edit surface

- `src/conversation_os/shape_population/evidence.py`
- evidence-related contracts and repository queries in `storage.py`
- `tests/test_shape_evidence.py`
- evidence golden fixtures under `tests/fixtures/shape_population/`

## Ordered implementation

1. First reproduce the confirmed exploit: a candidate cites a segment that exists globally but was never included in its packet. Keep the test red until packet membership is enforced.
2. Define an immutable inquiry containing source scope, requested structural paths/ranges, per-block and total budgets, and purpose. Intelligence chooses these fields; the assembler only validates them.
3. Persist packet blocks as references: `packet_id`, `block_id`, `source_id`, `segment_id`, byte/character ranges, content digest, ordering, and truncation marker. Do not persist copied source text.
4. Materialize text only at the model boundary by reading the content store and verifying digest/ranges. Any mismatch fails closed and produces an auditable error.
5. Require every candidate EvidenceRef to match one packet block exactly: packet, block, source, segment, ranges, and digest. Global segment existence is insufficient.
6. Enforce positive integer budgets for packets, blocks, sources, and bytes/tokens. Reject negative, zero, overflow, duplicate, reversed, or out-of-source ranges.
7. Wrap untrusted source text in a data-only envelope and place instructions outside it. Preserve source ordering and make truncation explicit.
8. Fingerprint packet identity from inquiry, normalization version, ordered block references, and policy version so retries return the same packet.

## Required tests

- valid exact citation;
- out-of-packet segment, wrong packet, wrong block, wrong digest, widened range, and stale normalization version all reject;
- prompt-injection text remains quoted data and cannot alter system instructions;
- boundary budgets, Unicode ranges, empty selection, duplicate blocks, and deterministic rerun;
- packet persistence grows with reference count, not source-text size;
- restart reconstructs the identical materialized packet.

Run:

```bash
pytest -q tests/test_shape_evidence.py
pytest -q tests/test_shape_normalization.py tests/test_shape_evidence.py
```

## Evidence required in the live task

The red/green exploit test, packet schema, storage-size comparison, materialization digest check, exact command output, full-suite impact, and unresolved tokenizer/source-type limits.

## Exit gate

No accepted candidate can cite material outside its exact packet; packets carry complete provenance without duplicating the source corpus; and no evidence code makes a semantic relevance decision.
