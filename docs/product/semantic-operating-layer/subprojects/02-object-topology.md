# Object Topology

Status: `seeded`  
Owner: `unassigned`  
First contract: `ObjectTopology`

## Responsibility

Track the shape of work: main spine, sidecars, sub-objects, branches, imported material, and reintegration.

## Scope In

- active spine object
- sub-object and parent links
- sidecar isolation
- reintegration status
- rollback path

## Scope Out

- content retrieval scoring
- task execution
- lens-specific schemas

## Integration

Feeds `ContextFrame`, `SessionEnvelope`, correction/reversibility, and work coordination.

## First Tasks

- Define topology states: `spine`, `sub_object`, `sidecar`, `parallel`, `imported`, `promoted`.
- Define reintegration event shape.
- Test imported sidecar isolation before promotion.

## Acceptance Criteria

- Sidecars do not pollute the main spine by default.
- Reintegration preserves provenance.
- Object shifts create inspectable events.
