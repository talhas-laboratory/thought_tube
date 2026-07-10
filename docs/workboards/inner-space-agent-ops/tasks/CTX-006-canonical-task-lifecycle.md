# CTX-006: Canonical Task Lifecycle

- status: done
- owner: codex
- gate: done
- depends_on: CTX-001, CTX-002, CTX-004

## Problem

The canonical service can inspect, claim, and complete existing tasks, but agents cannot yet create or revise canonical tasks or resolve blockers through that service.

## Acceptance

- Agents can create tasks with acceptance criteria, constraints, dependencies, owner, priority, and source references.
- Controlled updates preserve the existing append-only work-item event schema and reject invalid status transitions.
- Agents can resolve a blocker with reasoning and provenance.
- Context is available through the shared CLI/client contract.
- Telegram-created tasks are immediately visible in Codex context from the same SQLite store.

## Verification

- Direct lifecycle, HTTP client/service, Codex CLI, and Telegram task/context/update/resolve flows are automated.
- Live server task `DEPLOY-VERIFY-001` passed create, update, claim, decision, verification, completion, and release-gate checks.
- Final live gate: `ready`, zero reasons, zero active claims/blockers, one verified task, observed source revision.

## Residual Risks

- Status transition policy is intentionally compact; richer workflow customization should be versioned rather than added ad hoc.
