# Decisions

## D-001 — Four-layer disclosure law

**Status:** accepted
**Authority:** ADR-001

Execution follows orient → grant → evidence → receipt. Receipts are audit/handoff artifacts, not the primary steering mind.

## D-002 — Modular ownership boundary

**Status:** accepted
**Authority:** ADR-002

This workspace owns disclosure only. Ingestion, canonical records, Shape promotion, embeddings, and surface presentation remain external dependencies behind explicit ports.

## D-003 — One source, derived references

**Status:** accepted

Raw source text is stored once. Fragments, indexes, Shape projections, evidence blocks, and receipts preserve IDs, spans, provenance, and hashes rather than duplicating the source.

## D-004 — Canonical and provisional Shapes

**Status:** accepted

Canonical Shape identity/promotion belongs to the Unified Metaphysical Framework Shape profile. Legacy `meta_layer` signatures may enter retrieval only as explicitly provisional candidates through an adapter. The aperture never promotes them.

## D-005 — Execution and audit separation

**Status:** accepted

ExecutionBundle cannot represent suppressed/omitted material. AuditReceipt owns omission details. This is enforced by contract, not prompt wording.

## D-006 — Admission before ranking

**Status:** accepted

Positive relevance evidence admits candidates. Ranking operates only on admitted candidates. Confidence alone is never positive evidence.

## D-007 — Deterministic whole-block budgets

**Status:** accepted

Evidence is budgeted as provenance-preserving blocks. Required evidence that cannot fit produces an explicit status instead of silent semantic truncation.

## D-008 — Incremental adoption

**Status:** accepted

Bridge adopts first, Holodeck second. Feed and task packs follow only after conformance and performance gates. No big-bang surface migration.

## Open decisions

- Exact tokenizer/estimator and budget reservation constants — CAE-003B.
- Shape projection reader schema/version — CAE-014.
- Approved positive-recall and latency thresholds — CAE-006A.
- Kernel bounded-view integration versus explicit demotion — CAE-011.
