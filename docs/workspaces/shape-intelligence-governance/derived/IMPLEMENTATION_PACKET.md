# Build Packet — Automatic Candidate Governance

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Owner and interfaces

Create `src/conversation_os/shape_population/governance.py` and `storage.py`. Internal operations are `validate_candidate`, `persist_candidate`, and `record_population_receipt`; they are never agent tools. `submit_candidate` and `submit_evaluation` call one atomic transaction.

Validation checks schema, source/segment evidence existence and digest, allowed transitions, agent authorization, idempotency key, budget, and policy version. Receipt stores request/candidate/evaluation IDs, packet fingerprint, agent/model/prompt/tool versions, timing, retry/cost facts, validation outcome, and redaction-safe provenance.

## State and failure rules

Allowed lifecycle: `proposed → under_review → recommended | rejected | needs_evidence`; no automatic `canonical`. Replayed idempotency key returns the original receipt. Any validation, persistence, or receipt failure rolls back all writes. Candidate operations cannot touch retrieval indexes or canonical projections.

## Fixtures and tests

`tests/test_shape_population_governance.py` must prove: invalid schema/evidence fails closed; exact idempotent replay; concurrent duplicate submission; transaction rollback at each failure point; retry/cost caps; receipt privacy; forbidden transition; no retrieval/canon side effect; retained audit reconstruction.

Run: `pytest tests/test_shape_population_governance.py -q`.
