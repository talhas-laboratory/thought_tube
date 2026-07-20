# Build Packet — Evidence Assembly

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interface

Create `src/conversation_os/shape_population/evidence.py` with `build_evidence_packet(request) -> EvidencePacket`. It runs automatically after normalization and before every agent invocation.

Request names normalized segment IDs, deterministic selection policy/version, token/segment budgets, and optional anchor ranges. Output contains `packet_id`, ordered immutable evidence blocks, exact source/segment spans, omitted-block ledger, budget ledger, and injection-safe data envelope.

## Rules

- Source text is always quoted data inside a typed evidence block; it cannot alter system instructions, tools, or policy.
- Selection is deterministic from request, corpus revision, and policy version. No semantic Shape judgment or ranking claim is emitted.
- Whole blocks are included or omitted with a reason; truncation must retain exact original span mapping.
- Empty/missing/denied evidence returns a safe packet with an explicit reason, not invented context.

## Fixtures and tests

Create `tests/fixtures/shape_population/evidence/` with anchor-neighbor, budget-overflow, empty, missing segment, denied segment, prompt-injection, and repeated-run fixtures.

`tests/test_shape_population_evidence.py` must prove: deterministic block order; provenance resolution; budget ledger correctness; whole-block omission/truncation mapping; injection delimiters; missing/denied safe behavior; no hidden retrieval side effect; identical repeated packet fingerprint.

Run: `pytest tests/test_shape_population_evidence.py -q`.
