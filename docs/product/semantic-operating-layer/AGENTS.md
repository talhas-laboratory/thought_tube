# Agents

Rules for agents working in this product folder.

## Start Protocol

1. Read `README.md`, `SYSTEMS.md`, `CONNECTIONS.md`, `GATES.md`, `DECISIONS.md`, and latest `UPDATES.jsonl`.
2. Select one subproject packet.
3. Define or claim one task inside that packet.
4. Record meaningful changes in `UPDATES.jsonl`.
5. Record durable decisions in `DECISIONS.md`.

## Work Rules

- Keep packets sparse and current.
- Do not duplicate state across files unless one file is an index and the other is the source of truth.
- Preserve raw source boundaries for imported conversations, docs, or sidecars.
- Do not silently promote session-local material into durable memory.
- If a change crosses systems, update `CONNECTIONS.md`.
- If a task touches Holodeck or task-pack flow, update `SHARED_WORKSPACES.md` when ownership rules change.
- If a task cannot pass gates, leave it open with residual risks.

## Quality Bar

The product folder should remain elegant enough that another agent can orient in under five minutes.
