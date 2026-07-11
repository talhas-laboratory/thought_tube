# Decisions

Record durable decisions here.

## ADR-001: Server State Is Canonical

- status: accepted
- date: 2026-06-30
- decision: SQLite workspace state behind the workspace HTTP service is canonical in deployed operation. Markdown, JSON atlas files, and workboards are inspectable projections.
- reasoning: Multiple agents cannot coordinate reliably when each process can mutate a different local copy. A single service contract gives claims, decisions, tests, and gates one concurrency boundary while preserving readable projections.
- consequence: Clients must use explicit service configuration. Offline file mode remains supported but must never masquerade as synchronized server operation.

## ADR-002: Context Is Assembled, Bounded, and Provenanced

- status: accepted
- date: 2026-06-30
- decision: Every agent entry packet is assembled from canonical workspace state plus workspace-scoped repository observations, prioritizes the selected task, and includes source revision and source references.
- reasoning: A raw atlas dump is too broad and a hand-written summary goes stale. Deterministic assembly provides useful orientation without erasing source boundaries.

## ADR-003: Completion Is a Separate Governed Action

- status: accepted
- date: 2026-06-30
- decision: Discussion and handoff remain lightweight, but promotion to done or release-ready requires a structured completion packet with reasoning, changed files, commands, passing evidence, and residual risks.
- reasoning: Requiring full evidence on every conversational update creates friction; omitting it at completion makes the board untrustworthy.

## ADR-004: Dynamic Context Packets Are Not Persisted Per Agent

- status: accepted
- date: 2026-06-30
- decision: The atlas is the durable human-readable workspace projection. Agent- and task-specific `/context` packets are assembled on demand and are not written as mutable per-session files.
- reasoning: Persisting every context response would leak session identifiers, create projection churn, and invite stale packet reuse. Canonical records plus deterministic assembly are sufficient to reproduce a packet.

## ADR-005: Private Service With SSH Connectivity

- status: accepted
- date: 2026-06-30
- decision: Keep the workspace service bound to server localhost. Server agents connect directly; local Codex connects through a persistent SSH local-forward and config discovery.
- reasoning: This creates one canonical state without adding another public authentication surface. Tunnel failure remains explicit and cannot silently select local state.
