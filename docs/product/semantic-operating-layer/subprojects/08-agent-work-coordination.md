# Agent Work Coordination

Status: `seeded`  
Owner: `unassigned`  
First contract: `WorkPacket`

## Responsibility

Turn approved context into scoped multi-agent work with task state, gates, handoffs, and verification.

## Scope In

- work packet creation
- task gates
- agent handoffs
- update logs
- verification evidence
- decision linkage

## Scope Out

- broad project management UI
- unscoped autonomous agent spawning

## Integration

Consumes purpose, frame, gates, topology, and `WorkspaceBinding`. Feeds workboards, Holodeck workspaces, task packs, and implementation tasks.

## First Tasks

- Define when work begins as a product-folder task versus a Holodeck workspace.
- Map `WorkPacket` to the existing agent work board structure.
- Map `WorkPacket` to Holodeck `work_item`, `test`, `constraint`, and `promotion` records.
- Define required frame/provenance fields for task handoff.
- Add task gates for multi-agent updates staying current.

## Acceptance Criteria

- Another agent can resume from the packet alone.
- Work carries source frame and verification gates.
- Updates never depend on hidden chat context.
- Shared workspace state has one explicit source of truth.
