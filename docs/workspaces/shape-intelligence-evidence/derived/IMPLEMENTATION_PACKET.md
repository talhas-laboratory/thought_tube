# Build Packet — Evidence Assembly

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interface

Create `src/conversation_os/shape_population/evidence.py` with `build_evidence_packet(request) -> EvidencePacket`. It runs automatically after normalization and before every agent invocation.

An intelligence identity or authorized caller first forms an `evidence_inquiry` naming the question, candidate/evidence anchors, and desired scope. The request then names normalized segment IDs, that inquiry, deterministic assembly policy/version, token/segment budgets, and optional anchor ranges. Output contains `packet_id`, ordered immutable evidence blocks, exact source/segment spans, omitted-block ledger, budget ledger, and injection-safe data envelope.

## Rules

- Source text is always quoted data inside a typed evidence block; it cannot alter system instructions, tools, or policy.
- Intelligence selects the inquiry and what needs examination. The tool deterministically resolves that declared inquiry from request, corpus revision, and policy version; it makes no semantic relevance, Shape, or ranking claim.
- Whole blocks are included or omitted with a reason; truncation must retain exact original span mapping.
- Empty/missing/denied evidence returns a safe packet with an explicit reason, not invented context.

## Fixtures and tests

Create `tests/fixtures/shape_population/evidence/` with anchor-neighbor, budget-overflow, empty, missing segment, denied segment, prompt-injection, and repeated-run fixtures.

`tests/test_shape_population_evidence.py` must prove: identical packet for the same inquiry/request; provenance resolution; budget ledger correctness; whole-block omission/truncation mapping; injection delimiters; missing/denied safe behavior; no hidden retrieval side effect; and that different authorized inquiries may yield different bounded views without the assembler asserting semantic preference.

Run: `pytest tests/test_shape_population_evidence.py -q`.
