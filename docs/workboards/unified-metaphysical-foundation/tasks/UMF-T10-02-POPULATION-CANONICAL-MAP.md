# UMF-T10-02-POPULATION-CANONICAL-MAP: T10-02: Map Population output into canonical Shape records

Status: backlog
Owner: population+shape
Current gate: not_required

## Scope

Version `PopulationCandidate -> CanonicalShapeProposal` and apply through one transactional owner-receipt boundary into ShapeCore/ShapeView.

## Claimed paths

- `src/conversation_os/shape_population/contracts.py`
- `src/conversation_os/shape_population/canonical_port.py`
- `src/conversation_os/shape_population/promotion.py`
- `src/conversation_os/metaphysical_kernel_runtime.py`
- `src/conversation_os/metaphysical_kernel_store.py`
- `tests/test_shape_population_canonical_map*.py`

## Implementation steps

1. Version the proposal contract.
2. Separate observed vs unresolved referents; qualities/states; relations/roles; boundary/dimension/scale/time/perspective; composition/influence; mechanisms/constraints/feedback; counter-hypotheses/negative evidence.
3. Resolve kernel referents without merge-by-label/embedding.
4. Build ShapeCore only from closed validated refs; ShapeView as perspective/scope projection.
5. One transaction/outbox apply; canonical-local only after versioned owner receipt.
6. Semantic-loss warnings; fixtures for nested/composite/competing-view/AntiMatch cases.

## Acceptance Criteria

- Versioned proposal contract exists.
- Mapping separates the listed ontological facets.
- ShapeCore/ShapeView rules hold; disagreements stay separate.
- Transaction/outbox + receipt; replay idempotent; withdrawal stales dependents only.
- Required fixtures exist and pass.

## Constraints

- No merge solely by label or embedding similarity.
- Depends on `UMF-T10-01-SHAPE-AUTHORITY`
- Parent: `UMF-PROGRAM-SHAPE`

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- `canonical_port.py` exists on Population remote; wire after T10-00 import.
