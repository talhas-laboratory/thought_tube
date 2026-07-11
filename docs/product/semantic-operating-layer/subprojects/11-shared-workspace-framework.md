# Shared Workspace Framework

Status: `active`  
Owner: `codex`  
First contract: `WorkspaceBinding`

## Responsibility

Bind the product spine, Holodeck workspaces, workboards, task packs, sessions, and artifacts into one explicit shared workspace framework.

## Scope In

- source-of-truth rules
- Holodeck binding rules
- workspace creation thresholds
- workboard and task-pack linkage
- session and artifact linkage
- materialized workspace views

## Scope Out

- replacing Holodeck internals
- replacing product-level architecture docs
- free-form coordination outside declared ownership

## Integration

Consumes product subproject ownership, work coordination rules, capture/promotion policy, and surface adapter constraints. Feeds Holodeck-backed execution and cross-agent continuity.

## Live Binding

- active workspace: `sol-context-frames`
- linked workboard: `semantic-operating-layer-context-frames`
- linked evidence session: `session-gpt-bridge-2026-04-24`
- materialized workspace root: [context/workspaces/sol-context-frames](/Users/talhauddin/software/inner_space/context/workspaces/sol-context-frames/brief.md:1)

## First Tasks

- Define `WorkspaceBinding` schema.
- Define when a subproject becomes an active Holodeck objective.
- Define how workboards mirror, rather than duplicate, active workspace state.
- Create the first linked Holodeck for `Context Frames and Envelopes`.

## Acceptance Criteria

- Every active objective has one explicit shared workspace owner.
- Product spine, Holodeck, workboard, and task packs do not conflict on source of truth.
- Another agent can tell where to update state without guessing.
- Blocked handoff paths are explicit when atlas or guard state prevents task-pack generation.
