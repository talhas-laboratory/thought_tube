# Correction and Reversibility

Status: `seeded`  
Owner: `unassigned`  
First contract: `CorrectionEvent`

## Responsibility

Make correction and rollback first-class product mechanics.

## Scope In

- correct
- discard
- split
- merge
- pin/unpin
- promote/demote
- forget or keep session-local

## Scope Out

- permanent deletion policy beyond product-level intent
- surface UI implementation

## Integration

Feeds topology, promotion policy, user learning, and evaluator updates.

## First Tasks

- Define correction event schema.
- Define reversible updates for frames, captures, and promoted memory.
- Test correction changes future retrieval or steering without rewriting raw evidence.

## Acceptance Criteria

- No correction destroys raw provenance.
- Demotion and rollback are inspectable.
- Corrected interpretations are not silently reintroduced.
