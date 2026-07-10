# Purpose and Motion

Status: `seeded`  
Owner: `unassigned`  
First contract: `PurposeState`

## Responsibility

Track why the user is moving and what transformation the system should support.

## Scope In

- current purpose
- purpose history
- motion direction
- answer shape pressure
- task mode: explore, compress, evaluate, build, decide, recover, handoff

## Scope Out

- retrieval mechanics
- durable promotion
- surface-specific UI

## Integration

Feeds bridge routing, lens selection, evaluator choice, and work packet generation.

## First Tasks

- Define minimal `PurposeState` schema.
- Add examples from product thesis and bridge conversations.
- Define tests for ambiguous same-topic/different-purpose turns.

## Acceptance Criteria

- Purpose is distinguishable from topic.
- Purpose changes are inspectable.
- Low-confidence purpose does not over-route execution.
