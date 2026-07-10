# Capture and Promotion

Status: `seeded`  
Owner: `unassigned`  
First contract: `PromotionPolicy`

## Responsibility

Move material from raw evidence to provisional interpretation to durable memory without silent drift.

## Scope In

- provisional capture cards
- promotion thresholds
- confidence and recurrence signals
- reviewable durable memory updates

## Scope Out

- raw retrieval
- UI design
- execution answer composition

## Integration

Consumes evaluator results, correction events, and source evidence. Feeds knowledge ocean and user/project memory.

## First Tasks

- Define capture ladder.
- Define promotion metadata.
- Add tests that one-off material stays session-local unless confirmed.

## Acceptance Criteria

- Raw text remains preserved.
- Interpretation is separable from source.
- Promotion has a reason, confidence, and rollback path.
