# T10-13 Multi-agent concurrency conflicts

## First-slice scope

Task: `UMF-T10-13-CONCURRENCY`

This slice hardens the Shape Population mutation path where multiple agents or retries can touch the same provisional knowledge record:

- `ShapePopulationStore.put_candidate`
- `ShapePopulationStore.put_evaluation`
- `ShapePopulationStore.put_promotion`
- `record_human_decision` / `record_human_approval`

## Behavior

- Candidate, evaluation, and promotion rows now expose a derived `record_version` from persisted row state.
- Writers that submit `record_version`, `expected_record_version`, or `expected_version` receive an explicit `IdempotencyConflictError` when another writer has already advanced the row.
- Exact replay of the same candidate/evaluation/promotion row is a no-op, so at-least-once delivery does not refresh timestamps or duplicate effects.
- Repeated human approval with the same immutable decision returns the original approval event.
- Repeated human approval with a different decision, approver, or reason raises `IdempotencyConflictError`; it never overwrites the prior human decision or invents consensus.

## Verification

- `pytest tests/test_shape_population_governance.py tests/test_shape_population_promotion.py` -> 13 passed.
- `pytest tests/test_shape_population*.py` -> 69 passed.

## Residuals

- This first slice is local to Shape Population storage and human promotion approval. Broader rollback/retraction worker crash and partition coverage remains for later T10-13 slices.
- The docs/test paths are required by the task evidence contract but are not represented in the code overview owner index, so their guard assessment reported an ownership mismatch; implementation owner guards for `storage.py` and `promotion.py` were ready.
