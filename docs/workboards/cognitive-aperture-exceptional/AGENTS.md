# Agent Rules — Cognitive Aperture Exceptional

1. Boot from [`AGENT_BOOT.md`](../../workspaces/cognitive-aperture-exceptional/AGENT_BOOT.md).
2. Query live coordination state before trusting Git status.
3. Read [`GATES.md`](./GATES.md), [`DECISIONS.md`](./DECISIONS.md), and the active task packet.
4. Stay within the disclosure boundary in ADR-002. Do not repair ingestion or invent a Shape store here.
5. Prefer the Stage A → B → C → D order in the canonical gap map.
6. Claim leaf tasks only; parent tasks are coordination containers.
7. Before runtime edits, refresh the repo overview and pass the engineering guard with the smallest path set.
8. Never pass suppressed/omitted material to execution.
9. Never admit a retrieval candidate on confidence alone.
10. Never enforce metadata-dependent fail-closed behavior before readiness/backfill evidence exists.
11. Record exact verification, artifacts, rollback, and residual risks before review.
12. After live mutations: publish projections, check freshness, commit, and push.
