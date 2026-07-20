# Build Packet — Intelligence-led Evaluation and Human-approved Promotion

Read [Implementation Foundations](../../shape-intelligence-population/derived/IMPLEMENTATION_FOUNDATIONS.md) first.

## Roles and interfaces

A designated evaluation agent may call `request_promotion(candidate_id, evaluation_id, rationale, evidence_refs)`. It recommends only. A human canonical approver alone invokes `apply_promotion(request_id, approval_identity, approval_reason)`.

Evaluation is intelligence-led: it assesses evidence grounding, explanatory coherence, boundary clarity, relationship handling, alternatives, and uncertainty. The deterministic system verifies only authorization, required records, lifecycle state, immutable audit fields, and rollbackability.

## Promotion state machine

`recommended → promotion_requested → human approval event | human rejection event`. Only `apply_promotion`, after a valid immutable human approval event, moves the candidate to `canonical`; a rejection event leaves it non-canonical. The evaluator cannot approve its own request; no population agent may apply promotion.

## Fixtures and tests

Create `tests/fixtures/shape_population/promotion/` with grounded recommendation, weak/uncertain recommendation, missing evidence, unauthorized evaluator, unauthorized approver, duplicate request, race, rejection, and rollback cases.

`tests/test_shape_population_promotion.py` must prove: evaluator can recommend but cannot approve; only human role can apply; required evidence/receipt; idempotent request; race safety; rejection leaves candidate non-canonical; rollback removes projection; audit reconstruction. Add a bounded evaluator-rubric test, explicitly marked non-deterministic-quality, using golden cases rather than lexical scoring.

Run: `pytest tests/test_shape_population_promotion.py -q`.
