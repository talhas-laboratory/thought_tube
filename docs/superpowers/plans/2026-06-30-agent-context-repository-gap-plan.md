# Agent Context Repository Gap Closure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the workspace coordination layer into the canonical, server-native meta/context repository through which Codex, Telegram/OpenClaw, and future agents enter, coordinate, explain, verify, and hand off work.

**Architecture:** SQLite-backed workspace state is canonical on the server and is exposed through one HTTP contract. Human-readable atlas and workboard files are deterministic projections. Every agent receives a bounded context packet, claims work before editing, and leaves structured provenance and verification evidence; repository observation keeps the packet fresh without requiring agents to narrate routine facts manually.

**Tech Stack:** Python 3, SQLite, `ThreadingHTTPServer`, JSON/JSONL contracts, git CLI, pytest, systemd deployment.

---

## Completion Status

Completed and deployed on 2026-06-30. The task checklists below preserve the original execution recipe; authoritative completion evidence is in `docs/workboards/inner-space-agent-ops/`.

- local verification: 100 focused tests passed; all new runtime entrypoints compiled
- server services: workspace, observer, and Telegram meta agent active as non-root user units
- live lifecycle: `DEPLOY-VERIFY-001` reached governed completion and release gate `ready`
- canonical state: zero active claims/blockers, one verified task, observed revision `50b896758744ace898571473980993e67f263d08`
- recovery: integrity-checked 20-record pre-deploy backup
- local connectivity: persistent SSH tunnel active; implicit Codex context reads server state
- Telegram cutover: old local poller disabled, offset migrated, no post-cutover 409 conflicts

## Gap Assessment

The current implementation has the right structural core: store abstraction, SQLite adapter, coordination semantics, atlas projection, HTTP service, and Telegram service cutover. It does not yet fulfill the complete meta/context-repository role because local tooling can still bypass the canonical service, context packets omit repository state and explicit orientation, provenance is permissive, refresh depends on explicit mutations, and production recovery is not yet proven.

The closure order is deliberate. Canonical access comes first because automation built over split state would make divergence worse. Context assembly comes second so every later worker enters through the same contract. Observation and provenance then make that context trustworthy. Deployment hardening comes last because it must test the completed semantics, not an intermediate shape.

## System-Wide Requirement Gates

- **Canonicality:** With service mode enabled, Codex CLI and Telegram read and mutate the same SQLite workspace. A local mutation path must be an explicit offline fallback, never an accidental default.
- **Freshness:** A repository change is visible in the next context packet without manual atlas editing. Every packet reports its assembly time and source revision.
- **Provenance:** A task cannot be handed off as complete without changed files, reasoning, commands, verification evidence, and residual risks.
- **Bounded context:** Packets prioritize the selected task and workspace, preserve source references, expose unresolved tensions, and stay within deterministic limits.
- **Concurrency:** Overlapping active claims are rejected consistently across all clients.
- **Release safety:** Deployment requires passing task verification, no active blockers or claims, a known source revision, health checks, and a tested rollback target.
- **Recoverability:** Service restart preserves state; file projections can be regenerated from canonical state; backup restoration is exercised in an automated test or scripted drill.

## Task 1: Canonical Service Client and CLI Cutover

**Files:**
- Create: `src/conversation_os/workspace_client.py`
- Modify: `tools/workspace_coordination.py`
- Modify: `docs/implementation/workspace-coordination/README.md`
- Test: `tests/test_workspace_client.py`
- Test: `tests/test_workspace_coordination_cli.py`

- [ ] Write a failing client contract test using a real ephemeral workspace service. Assert that `prepare`, `claim`, `handoff`, `decision`, `verify`, `blocker`, `gate`, `status`, and `tasks` preserve HTTP errors as typed client errors.
- [ ] Run `pytest tests/test_workspace_client.py -q` and confirm failure because `workspace_client` does not exist.
- [ ] Implement a small standard-library HTTP client with explicit timeout and no silent local fallback.
- [ ] Add `--workspace-api-base` and `INNER_WORLD_WORKSPACE_API_BASE` to the CLI. Route every command except projection-only maintenance through the client when configured.
- [ ] Run `pytest tests/test_workspace_client.py tests/test_workspace_coordination_cli.py -q` and record the passing result.

## Task 2: Agent Entry Context Packet

**Files:**
- Create: `src/conversation_os/workspace_context_packet.py`
- Modify: `src/conversation_os/workspace_service.py`
- Modify: `src/conversation_os/workspace_atlas.py`
- Test: `tests/test_workspace_context_packet.py`
- Test: `tests/test_workspace_service.py`

- [ ] Write a failing test for a packet containing workspace purpose, selected task, acceptance criteria, active claims, blockers, relevant decisions, latest tests, recent substantive activity, changed files, open threads, source revision, assembly timestamp, and agent identity.
- [ ] Assert deterministic limits and task-first filtering so unrelated workspace history cannot crowd out selected-task context.
- [ ] Run the focused tests and confirm failure because the assembler and `/context` endpoint do not exist.
- [ ] Implement the pure packet assembler and expose `GET /api/workspaces/<id>/context` with task and agent query parameters.
- [ ] Materialize the latest packet as a projection only; keep SQLite records authoritative.
- [ ] Run the focused tests and record packet size, provenance, and isolation evidence.

## Task 3: Automatic Repository Observation

**Files:**
- Create: `src/conversation_os/workspace_observer.py`
- Create: `tools/observe_workspace.py`
- Modify: `src/conversation_os/workspace_store.py`
- Modify: `src/conversation_os/workspace_atlas.py`
- Test: `tests/test_workspace_observer.py`

- [ ] Write failing tests against temporary git repositories for modified, added, deleted, renamed, and clean states.
- [ ] Require path filtering by workspace `artifact_roots`, source revision capture, stable fingerprints, and idempotency when no change occurred.
- [ ] Implement a one-shot observer that records a structured change snapshot and refreshes the atlas. Keep GitNexus enrichment optional and non-authoritative.
- [ ] Add a polling CLI suitable for systemd with bounded interval, graceful shutdown, and an explicit one-shot mode.
- [ ] Verify that a file edit appears in the next context packet and that unrelated paths remain excluded.

## Task 4: Mandatory Completion and Provenance Contract

**Files:**
- Modify: `src/conversation_os/workspace_coordination.py`
- Modify: `src/conversation_os/workspace_service.py`
- Modify: `tools/run_telegram_meta_agent.py`
- Test: `tests/test_workspace_completion_gates.py`
- Test: `tests/test_run_telegram_meta_agent.py`

- [ ] Write failing tests showing that completion is rejected when reasoning, changed files, commands, passing verification, or residual-risk declaration is absent.
- [ ] Define one structured completion packet rather than inferring completion from free-form handoff text.
- [ ] Add task-scoped gate evaluation and a completion endpoint/Telegram command that returns actionable missing fields.
- [ ] Preserve discussion and intermediate handoffs without forcing completion fields; enforce the contract only when the task is promoted to done/release-ready.
- [ ] Verify rejection and success paths through direct coordination, HTTP, and Telegram adapters.

## Task 5: Production Operation, Backup, and Recovery

**Files:**
- Create: `ops/systemd/inner-space-workspace.service.sample`
- Create: `ops/systemd/inner-space-workspace-observer.service.sample`
- Create: `tools/backup_workspace_store.py`
- Create: `tools/restore_workspace_store.py`
- Modify: `docs/guides/deployment-guide.md`
- Test: `tests/test_workspace_backup_restore.py`
- Test: `tests/test_workspace_service.py`

- [ ] Write a failing round-trip test that backs up SQLite state, restores it to a fresh path, and reproduces the same context packet except for assembly timestamps.
- [ ] Add `/health` and `/ready` endpoints; readiness must prove the store is readable and writable without mutating workspace history.
- [ ] Implement atomic SQLite backup and guarded restore with schema validation and pre-restore backup.
- [ ] Define systemd units with non-root execution, restart policy, environment file loading, localhost binding, and dependency ordering.
- [ ] Run unit, integration, restart, and restore drills. Record exact commands and evidence in the workboard before declaring the migration complete.

## Final Verification

- [ ] Run `pytest tests/test_workspace_store.py tests/test_workspace_coordination.py tests/test_workspace_atlas.py tests/test_workspace_service.py tests/test_workspace_client.py tests/test_workspace_context_packet.py tests/test_workspace_observer.py tests/test_workspace_completion_gates.py tests/test_workspace_backup_restore.py tests/test_workspace_coordination_cli.py tests/test_run_telegram_meta_agent.py tests/test_meta_telegram_agent.py -q`.
- [ ] Start the service against a temporary SQLite database and exercise context, claim, decision, verify, completion, and gate through HTTP.
- [ ] Restart the service and confirm state continuity.
- [ ] Regenerate all projections from SQLite and compare semantic contents.
- [ ] Perform a backup/restore drill and confirm the restored service emits the same task and decision state.
- [ ] Update the workboard task packets, decision log, handoff, and append-only update feed with evidence and residual risks.

## Completion-Audit Extension: Canonical Task Lifecycle

The first completion audit found that server state could be read, claimed, and completed but not used to create or revise tasks or resolve blockers. That would preserve a split between the readable workboard and canonical runtime state. This extension closes that operational gap before final verification.

**Files:**
- Modify: `src/conversation_os/workspace_coordination.py`
- Modify: `src/conversation_os/workspace_service.py`
- Modify: `src/conversation_os/workspace_client.py`
- Modify: `tools/workspace_coordination.py`
- Modify: `tools/run_telegram_meta_agent.py`
- Test: `tests/test_workspace_task_lifecycle.py`
- Test: `tests/test_workspace_service.py`
- Test: `tests/test_run_telegram_meta_agent.py`

- [ ] Write failing tests for task creation, allowed task updates, invalid transitions, blocker resolution, duplicate request idempotency, and assembled context access.
- [ ] Add canonical create/update task events and blocker resolution without introducing a second task schema.
- [ ] Expose lifecycle operations through HTTP and the shared client, with CLI and Telegram adapters using the same contracts.
- [ ] Ensure every mutation refreshes projections and appends actor/reasoning provenance.
- [ ] Verify that a task created through Telegram is immediately visible to Codex context and can proceed through claim, verification, completion, and release gate evaluation.
