# Evaluators and Gates

Status: `seeded`  
Owner: `unassigned`  
First contract: `SemanticGate`

## Responsibility

Verify semantic behavior, not only code behavior.

## Scope In

- false-memory checks
- provenance checks
- isolation checks
- smallest sufficient context checks
- purpose-fit checks
- promotion readiness checks

## Scope Out

- replacing unit tests
- subjective scoring without evidence

## Integration

Consumes execution result, frame bundle, control packet, and promotion candidates. Feeds correction, promotion, and work handoff.

## First Tasks

- Define semantic gate taxonomy.
- Create scripted conversation fixtures for bridge behavior.
- Add mandatory gates for strict session and sidecar cases.

## Acceptance Criteria

- Gates can fail a result even when code tests pass.
- Failure explains what should change.
- Gate outputs are usable by agents and users.
