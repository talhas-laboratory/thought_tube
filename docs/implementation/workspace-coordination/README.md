# Workspace Coordination Implementation Spec

## Purpose

Make `notes.talhaslaboratory.xyz` / Inner World usable by multiple agents at the same time without losing task state, decision history, file ownership, verification evidence, or deployment context.

The forward implementation and rollout plan is documented in [Reliable Cross-Agent Holodeck Work System](../../plans/2026-07-11-reliable-cross-agent-holodeck-work-system-design.md).

The target operating model is:

- Codex can implement changes locally.
- The Telegram meta agent can discuss, classify, create tasks, approve work, and request deployment.
- Future OpenClaw agents can take bounded task packets.
- Every agent can see who is working, what they touched, why they made decisions, what is blocked, and what has been verified.

## Current Implementation Snapshot

This specification is implemented and deployed on the OpenClaw server.

Implemented:

- manifest normalization through `src/conversation_os/workspace_coordination.py`
- `scope_in` migration into `artifact_roots` and `objectives`
- append-only workspace activity ledger at `memory/workspaces/<workspace_id>/activity_events.jsonl`
- append-only workspace claims ledger at `memory/workspaces/<workspace_id>/claims.jsonl`
- append-only workspace decision ledger at `memory/workspaces/<workspace_id>/decisions.jsonl`
- workspace test case and test run ledgers at `memory/workspaces/<workspace_id>/test_cases.jsonl` and `memory/workspaces/<workspace_id>/test_runs.jsonl`
- append-only workspace blocker ledger at `memory/workspaces/<workspace_id>/blockers.jsonl`
- storage abstraction boundary via `src/conversation_os/workspace_store.py`
- default `FileWorkspaceStore` adapter so coordination logic is no longer coupled directly to local file helpers
- overlap detection for active claims
- release-gate evaluation over active claims, blockers, and verification state
- task preparation packets with workspace, task, claims, blockers, decisions, tests, and recent activity
- first-class task/subtask hierarchy with independently tracked claims, blockers, verification, and parent completion gates
- atlas materialization from the workspace spine into `context/workspaces/<workspace_id>/atlas.*`
- generated workboard projections for agent state, tasks, decisions, handoffs, releases, and changed surfaces
- automatic atlas refresh after workspace mutations (`claim`, `handoff`, `decision`, `verify`, `blocker`)
- optional `gitnexus` change-report enrichment for changed surfaces / affected process projection
- normalized workspace binding consumption in `src/conversation_os/element_workspace_binding.py`
- Telegram workspace selection and task listing via `/workspace <workspace_id>` and `/tasks`
- Telegram task mutation via `/claim`, `/handoff`, `/decision`, and `/verify`
- CLI entrypoint via `python3 tools/workspace_coordination.py ...`
- canonical SQLite workspace service with task creation/update, claims, decisions, verification, blocker resolution, governed completion, context assembly, and release gates
- idempotent repository observation with revision/fingerprint tracking and projection-loop prevention
- health/readiness, atomic backup, guarded restore, and restart continuity
- server-native Telegram polling with canonical task/context commands
- persistent private SSH connectivity for local Codex with user-config discovery and no silent fallback
- workspace catalog endpoint and safe file-to-SQLite migration tooling with legacy status normalization and conflict refusal

Focused verification currently lives in:

- `tests/test_workspace_atlas.py`
- `tests/test_workspace_coordination.py`
- `tests/test_workspace_coordination_cli.py`
- `tests/test_element_workspace_binding.py`
- `tests/test_run_telegram_meta_agent.py`
- `tests/test_workspace_context_packet.py`
- `tests/test_workspace_observer.py`
- `tests/test_workspace_completion_gates.py`
- `tests/test_workspace_task_lifecycle.py`
- `tests/test_workspace_backup_restore.py`
- `tests/test_workspace_end_to_end.py`

Legacy task-pack note:

- task-specific `/context` packets are now the canonical bounded handoff contract for connected agents
- the older routing-layer task-pack files remain available for disconnected exports but are not required for server-native coordination

## Migration Status

Phase 1 established the storage adapter boundary.

- `src/conversation_os/workspace_coordination.py` reads and writes workspace state through a workspace-store adapter boundary.
- `src/conversation_os/workspace_store.py` defines the current `FileWorkspaceStore`.
- File-backed operation remains available only as explicit offline mode.

Phase 2 now also has a usable server-native slice.

- `src/conversation_os/workspace_store.py` now includes `SQLiteWorkspaceStore`.
- `src/conversation_os/workspace_coordination.py` and `src/conversation_os/workspace_atlas.py` accept an injected workspace store so the same coordination semantics can run against file or SQLite state.
- `src/conversation_os/workspace_service.py` exposes a minimal HTTP service over the existing workspace verbs.
- `tools/run_workspace_service.py` starts that service in `file` or `sqlite` mode.

Current HTTP surface:

- `GET /api/workspaces` lists the canonical catalog with per-workspace revisions
- `POST /api/workspaces` creates a workspace from a manifest
- `POST /api/workspaces/import` imports a normalized workspace snapshot without overwriting divergent state
- `GET /api/workspaces/<workspace_id>/prepare?task_id=&agent_id=&surface=&session_id=`
- `GET /api/workspaces/<workspace_id>/context?task_id=&agent_id=&surface=&session_id=`
- `GET /api/workspaces/<workspace_id>/runs?task_id=` lists durable agent-run state
- `GET /api/workspaces/<workspace_id>/reasoning?task_id=&run_id=` lists bounded task reasoning records
- `GET /api/workspaces/<workspace_id>/progress?task_id=` derives current task progress and the next safe action
- `GET /api/workspaces/<workspace_id>/gate`
- `GET /api/workspaces/<workspace_id>/status`
- `GET /api/workspaces/<workspace_id>/tasks`
- `POST /api/workspaces/<workspace_id>/tasks` creates a canonical task
- `POST /api/workspaces/<workspace_id>/task-update`
- `POST /api/workspaces/<workspace_id>/runs` begins an agent run
- `POST /api/workspaces/<workspace_id>/run-heartbeat`
- `POST /api/workspaces/<workspace_id>/run-end`
- `POST /api/workspaces/<workspace_id>/run-recover-stale` releases expired runs and their linked claims
- `POST /api/workspaces/<workspace_id>/reasoning` records a typed observation, decision, discovery, or next action
- `POST /api/workspaces/<workspace_id>/claim`
- `POST /api/workspaces/<workspace_id>/handoff`
- `POST /api/workspaces/<workspace_id>/decision`
- `POST /api/workspaces/<workspace_id>/verify`
- `POST /api/workspaces/<workspace_id>/blocker`
- `POST /api/workspaces/<workspace_id>/blocker-resolve`
- `POST /api/workspaces/<workspace_id>/complete`
- `POST /api/workspaces/<workspace_id>/archive`

Task hierarchy contract:

- include `parent_task_id` when creating or updating a task to make it a subtask
- hierarchy is intentionally limited to `task -> subtask`; a subtask cannot be a parent
- parent completion is rejected while a child is neither `done` nor `cancelled`
- task, context, atlas, and workboard projections render the hierarchy

Recommended startup for server-native mode:

```bash
python3 tools/run_workspace_service.py \
  --root /path/to/inner_space \
  --store sqlite \
  --sqlite-path /path/to/inner_space/state/workspace.db
```

Operational endpoints:

- `GET /health` proves the process is serving requests
- `GET /ready` runs SQLite integrity plus rollback-only write checks without appending workspace history
- `ops/systemd/inner-space-workspace.service.sample` runs the localhost-only canonical service as a non-root user
- `ops/systemd/inner-space-workspace-observer.service.sample` keeps repository snapshots current after the service starts
- `tools/backup_workspace_store.py` creates an integrity-checked atomic SQLite backup
- `tools/restore_workspace_store.py` validates the source and preserves the existing target before replacement

Current cutover state:

- the OpenClaw server runs the canonical SQLite workspace, repository observer, and Telegram meta agent as user services
- Telegram uses `INNER_WORLD_WORKSPACE_API_BASE=http://127.0.0.1:8765/api`
- local Codex reaches the same private service through `127.0.0.1:18765/api` over a persistent SSH tunnel
- deploy/release readiness reads workspace gates from that service
- direct local file operation remains an explicit offline mode only when neither an argument, environment variable, nor user config supplies a service base

Current Telegram cutover behavior:

- `/workspace`, `/tasks`, `/claim`, `/handoff`, `/decision`, `/verify`, `/blocker`, and `/gate` use the workspace service when `INNER_WORLD_WORKSPACE_API_BASE` is set
- `/deploy` now evaluates workspace gate readiness through the workspace service when that base is set
- when the workspace service base is unset, the Telegram bridge continues to use the local in-repo coordination path

Current Codex/CLI cutover behavior:

- `tools/workspace_coordination.py` uses the canonical workspace service for all coordination verbs when `INNER_WORLD_WORKSPACE_API_BASE` or `--workspace-api-base` is set
- service errors are returned visibly and never trigger a silent local mutation fallback
- file-backed operation remains available as an explicit offline mode when no service base is configured
- CLI authority defaults to `connected`; pass `--mode offline --root /path/to/repo` for local-only operation, or use an explicit service URL to select `connected` mode even when `--root` is supplied for path resolution
- `--idempotency-key <key>` makes one canonical mutation retry-safe; reusing the key with a different workspace operation or payload is rejected
- when the environment variable is absent, the CLI reads `~/.config/inner-space-workspace.env`; the local installation points this at the private SSH tunnel on `127.0.0.1:18765/api`
- `ops/launchd/com.inner-space.workspace-tunnel.plist.sample` keeps that tunnel alive without exposing the server service publicly

Phase 0 catalog and migration commands:

```bash
# Inspect a local file-backed workspace catalog.
python3 tools/workspace_catalog.py catalog --store file

# Compare local workspaces with a SQLite candidate store.
python3 tools/workspace_catalog.py audit --store file --target-store sqlite --target-sqlite-path state/workspace.db

# Preview the pilot migration without writing records.
python3 tools/workspace_catalog.py migrate --store file --target-store sqlite \
  --target-sqlite-path state/workspace.db --workspace-id sol-context-frames --dry-run
```

Migrations normalize legacy `completed` task states to `done` and `passed` test results to `passing`. A target workspace with a different canonical revision is never overwritten. Mutating a nonempty SQLite target requires `--backup-path`.

To import a local pilot directly through a running canonical workspace service:

```bash
python3 tools/workspace_catalog.py migrate --store file --workspace-id sol-context-frames \
  --workspace-api-base http://127.0.0.1:18765/api
```

When the service imports into a nonempty SQLite store, it creates an atomic backup under `state/workspace-import-backups/` and returns that backup path in the import response.

Retry-safe canonical mutation example:

```bash
python3 tools/workspace_coordination.py decision --workspace-id sol-context-frames \
  --workspace-api-base http://127.0.0.1:18765/api \
  --task-id CAW-001 --summary "Use canonical vocabulary" \
  --reasoning "Status aliases must be normalized once." \
  --idempotency-key caw-001-decision-20260711
```

Agent-run example:

```bash
python3 tools/workspace_coordination.py begin-run --workspace-id sol-context-frames \
  --workspace-api-base http://127.0.0.1:18765/api \
  --task-id CAW-201 --agent-id codex --device-id talha-macbook \
  --session-id codex-workspace-201 --intent "Implement durable agent runs" \
  --idempotency-key caw-201-run-start
```

Active runs are included in task context packets. A run becomes derived `stale` if its heartbeat exceeds its recorded TTL; stale state is visible and reclaimable but does not silently mutate the ledger.

When `begin-run` receives `--claimed-path`, it creates a claim bound to that run. Existing compatible claims held by the same agent and task are adopted by the run. Heartbeats renew linked claims; ending a run releases only its linked claims.

Connected surfaces can use [workspace_work_adapter.py](../../../src/conversation_os/workspace_work_adapter.py) to perform the standard begin, heartbeat/update, and handoff lifecycle through one contract. Surface-specific automatic invocation remains the next integration step.

For Codex or another terminal agent, [workspace_work.py](../../../tools/workspace_work.py) exposes that adapter directly:

```bash
python3 tools/workspace_work.py begin --workspace-api-base http://127.0.0.1:18765/api \
  --workspace-id sol-context-frames --task-id CAW-204 --device-id talha-macbook \
  --session-id codex-caw-204 --intent "Wire the connected work wrapper" \
  --claimed-path tools/workspace_work.py --next-action "Run the adapter integration test."
```

Reasoning records are intentionally compact and inspectable, not raw private chain-of-thought. Supported kinds are `observation`, `hypothesis`, `decision`, `tension`, `discovery`, `scope_change`, and `next_action`.

```bash
python3 tools/workspace_coordination.py record-reasoning --workspace-id sol-context-frames \
  --workspace-api-base http://127.0.0.1:18765/api --task-id CAW-301 \
  --reasoning-kind decision --summary "Keep reasoning records bounded" \
  --reasoning "Handoffs need rationale, not hidden deliberation." \
  --source-ref docs/plans/2026-07-11-reliable-cross-agent-holodeck-work-system-design.md
```

Derived progress never accepts a manually authored percentage. It reports task status, child completion, active claims/runs/blockers, passing verification, last activity, and a `recommended_next_action` determined from that evidence. Use `python3 tools/workspace_coordination.py progress --workspace-id <id> --task-id <task>` to read the same view locally or through the canonical service.

Repository observation:

- `src/conversation_os/workspace_observer.py` captures added, modified, deleted, copied, renamed, and conflicted git paths inside workspace `artifact_roots`
- snapshots include the source revision, stable fingerprint, observation time, and rename provenance
- unchanged snapshots are not appended again
- generated atlas/workboard projections are excluded to prevent self-triggered refresh loops
- a new snapshot automatically refreshes the readable atlas and is included in subsequent `/context` packets
- `python3 tools/observe_workspace.py --root /path/to/repo --workspace-id inner-world --store sqlite --once` performs a one-shot observation; omit `--once` for bounded polling

Governed completion:

- completion is separate from handoff; agents may discuss or transfer unfinished work without pretending it is done
- `complete_workspace_task` requires summary, reasoning, changed files, commands, an explicit residual-risk declaration, passing task verification with evidence, and no active task blockers
- completion appends a canonical `set_status: done` event, releases the completing agent's claims, and records one provenance-rich `completed` activity event
- retries are idempotent and return the original completion result without duplicating history
- the contract is available through HTTP, `tools/workspace_coordination.py complete`, and Telegram `/complete`
- Telegram syntax: `/complete <task_id> :: <summary> :: <reasoning> :: <file1,file2> :: <command1 ;; command2> :: <risk1,risk2|none known>`

## Non-Negotiable Principles

- One canonical workspace state, many projections.
- Append-only history for meaningful agent actions.
- Explicit claims before edits.
- No task reaches done without verification evidence.
- No deployment without release evidence, rollback evidence, and linked task evidence.
- Human-readable markdown is a projection; structured JSON/JSONL is the source of truth.
- Agents must leave enough context for another agent to resume without reading the original chat.

## Canonical Layers

### 1. Workspace Spine

Canonical runtime state lives under:

```text
memory/workspaces/<workspace_id>/
```

This is the source of truth for:

- workspace manifest
- activity events
- task state
- claims
- decisions
- blockers
- tests
- releases
- handoffs
- materialized snapshots

### 2. Workboard Projection

Readable project state lives under:

```text
docs/workboards/<board_id>/
```

This is the human-facing projection for:

- `README.md`
- `TASKS.md`
- `GATES.md`
- `DECISIONS.md`
- `HANDOFFS.md`
- `UPDATES.jsonl`
- `tasks/*.md`
- `artifacts/*`

Workboards remain sparse and durable. They should not become unstructured chat transcripts.

### 3. Task Packs

Portable work packets live under:

```text
memory/task_packs/
```

Task packs are the handoff unit for Codex, Telegram meta agent, OpenClaw workers, and any future agents.

## Required Schema Changes

### Workspace Manifest

Existing workspaces currently overload `scope_in`. Replace that ambiguity with explicit fields.

Required manifest shape:

```json
{
  "workspace_id": "inner-world",
  "label": "Inner World",
  "status": "active",
  "maturation_stage": "developing",
  "goal": "Coordinate work on notes.talhaslaboratory.xyz and Inner World.",
  "purpose": "Shared operating layer for multi-agent product work.",
  "success_condition": "Agents can coordinate through claims, task packets, decisions, tests, and release gates.",
  "artifact_roots": [
    "product/thought_capture_pwa/",
    "src/conversation_os/",
    "tools/",
    "docs/workboards/"
  ],
  "objectives": [
    "Harden the notes PWA.",
    "Coordinate Telegram meta agent and Codex work.",
    "Keep release and rollback evidence complete."
  ],
  "scope_out": [
    "Unapproved production deploys.",
    "Untracked direct agent prompt mutation."
  ],
  "domains": [
    "frontend",
    "backend",
    "bridge",
    "knowledge",
    "agent_behavior",
    "deployment"
  ],
  "active_subprojects": [],
  "workboard_ref": "docs/workboards/inner-world/README.md",
  "activity_ref": "memory/workspaces/inner-world/activity_events.jsonl",
  "created_at": "...",
  "updated_at": "..."
}
```

Compatibility rule:

- `scope_in` may be read during migration only.
- If an entry looks like an existing repo path, migrate it to `artifact_roots`.
- Otherwise migrate it to `objectives`.
- New code must not use `scope_in` as an artifact root.

### Agent Activity Event

Every meaningful action must append an event to:

```text
memory/workspaces/<workspace_id>/activity_events.jsonl
```

Required event shape:

```json
{
  "event_id": "evt-...",
  "schema_version": "1.0",
  "created_at": "...",
  "workspace_id": "inner-world",
  "subproject_id": "notes-pwa",
  "task_id": "TASK-001",
  "actor": {
    "agent_id": "codex",
    "surface": "codex",
    "session_id": "..."
  },
  "event_type": "claimed",
  "summary": "Claimed mobile capture UX hardening task.",
  "reasoning": "The task touches PWA layout and should be isolated from bridge runtime changes.",
  "files_touched": [],
  "commands_run": [],
  "verification": [],
  "blockers": [],
  "decision_refs": [],
  "handoff_refs": [],
  "metadata": {}
}
```

Allowed event types:

- `created_task`
- `claimed`
- `released_claim`
- `edited`
- `tested`
- `decided`
- `blocked`
- `unblocked`
- `handoff`
- `reviewed`
- `deployed`
- `rolled_back`
- `status_snapshot`

### Work Claim

Claims prevent silent overlap between agents.

Required claim shape:

```json
{
  "claim_id": "claim-...",
  "schema_version": "1.0",
  "created_at": "...",
  "updated_at": "...",
  "expires_at": "...",
  "workspace_id": "inner-world",
  "task_id": "TASK-001",
  "actor": {
    "agent_id": "codex",
    "surface": "codex",
    "session_id": "..."
  },
  "intent": "Harden mobile notes PWA layout.",
  "claimed_paths": [
    "product/thought_capture_pwa/"
  ],
  "status": "active"
}
```

Claim status values:

- `active`
- `released`
- `expired`
- `superseded`

Overlap rule:

- A new active claim is blocked if it overlaps an active claim path held by another actor.
- The user may explicitly override a claim, but that override must create a `decided` activity event.

## Operator Surfaces

### Telegram Meta Agent

Current workspace coordination commands:

- `/workspace <workspace_id>`: select the active workspace for the Telegram runtime
- `/tasks`: list tracked tasks for the selected workspace
- `/claim <task_id> :: <intent> :: <path[,path]...>`: claim a bounded task/file surface
- `/handoff <task_id> :: <summary> :: <reasoning> :: [next_action]`: release claims and leave a handoff
- `/decision <task_id> :: <summary> :: <reasoning>`: record an accepted task decision
- `/verify <task_id> :: <test_name> :: <result> :: [evidence_ref] :: [notes]`: record verification evidence
- `/blocker <task_id> :: <reason> :: [next_action]`: record an active blocker
- `/gate`: inspect the current workspace release gate

The selected workspace is persisted in:

```text
product/inner_world_v1/meta_agent/state/runtime/state/selected_workspace.json
```

or the custom runtime root passed to `tools/run_telegram_meta_agent.py`.

### CLI

Current command surface:

```bash
python3 tools/workspace_coordination.py status --workspace-id sol-frontend
python3 tools/workspace_coordination.py tasks --workspace-id sol-frontend
python3 tools/workspace_coordination.py prepare --workspace-id sol-frontend --task-id MTC-001
python3 tools/workspace_coordination.py claim --workspace-id sol-frontend --task-id MTC-001 --intent "Harden shell" --claimed-path product/thought_capture_pwa/
python3 tools/workspace_coordination.py decision --workspace-id sol-frontend --task-id MTC-001 --summary "Keep shell language" --reasoning "Preserves continuity"
python3 tools/workspace_coordination.py verify --workspace-id sol-frontend --task-id MTC-001 --test-name mobile-smoke --result passing --evidence-ref artifacts/mobile-smoke.txt
python3 tools/workspace_coordination.py blocker --workspace-id sol-frontend --task-id MTC-001 --reasoning "Safari reload regression" --next-action "Inspect hydration path"
python3 tools/workspace_coordination.py gate --workspace-id sol-frontend
python3 tools/workspace_coordination.py atlas --workspace-id sol-frontend --git-changes-path /tmp/gitnexus-changes.json
python3 tools/workspace_coordination.py handoff --workspace-id sol-frontend --task-id MTC-001 --summary "Implementation complete" --reasoning "Ready for verification" --next-action "Run smoke suite"
```

### Gitnexus Role

`gitnexus` is not a source of truth for coordination state.

It is used only for code-derived enrichment:

- changed files
- changed symbols
- affected processes
- risk summary

That enrichment feeds generated atlas surfaces such as `CHANGED_SURFACES.md`, while tasks, claims, blockers, decisions, tests, and handoffs remain canonical in the workspace spine.

### Release Linkage

Release manifests should declare:

```json
{
  "workspace_id": "sol-frontend"
}
```

Release readiness is blocked when either side is incomplete:

- required release artifacts are missing
- explicit release approval is missing
- linked workspace gate is not `ready`

That means `/deploy <release_id>` is now expected to consume both release artifacts and canonical workspace gate state.

On successful deploy, the system should:

- append a `deployed` activity event into the linked workspace
- attach `release_id`
- attach `post_deploy_smoke_path`
- refresh atlas/workboard projections so release evidence is visible without inspecting release folders directly

The CLI is intentionally thin. It projects the same canonical workspace state used by Codex and the Telegram meta agent.

### Task State

Each task must exist in structured state and markdown projection.

Required task fields:

- `task_id`
- `workspace_id`
- `title`
- `status`
- `owner`
- `current_gate`
- `domain`
- `scope_in_paths`
- `scope_out`
- `acceptance_criteria`
- `required_tests`
- `required_reviews`
- `changed_files`
- `verification_evidence`
- `decision_refs`
- `blockers`
- `handoff_notes`
- `residual_risks`

Task statuses:

- `backlog`
- `ready`
- `claimed`
- `in_progress`
- `blocked`
- `verification`
- `review`
- `done`

## Mandatory Requirement Gates

### Gate 0: Workspace Binding

Required before any agent starts work:

- Workspace exists.
- Workspace has `artifact_roots`.
- Workspace has `objectives`.
- Workspace has `workboard_ref`.
- Workspace has an activity ledger.
- Agent has a `workspace_id`.
- Agent can read recent activity events.

Failure behavior:

- Agent must stop and ask for workspace selection or create an intake task.

Tests:

- Unit test manifest validation accepts `artifact_roots` plus `objectives`.
- Unit test migration splits path-like `scope_in` entries from prose entries.
- Unit test workspace binding never treats prose objectives as artifact roots.

### Gate 1: Task Intake

Required before implementation:

- Task exists.
- Task has domain.
- Task has acceptance criteria.
- Task has scope-in paths.
- Task has scope-out notes.
- Task has required tests.
- Task has current owner or is claimable.

Failure behavior:

- Agent may create or refine task.
- Agent may not edit product files.

Tests:

- Unit test rejects task readiness without acceptance criteria.
- Unit test rejects implementation start without scope-in paths.
- CLI test `workspace_coordination.py prepare` returns blocked state for incomplete task.

### Gate 2: Claim

Required before file edits:

- Agent creates an active claim.
- Claimed paths are inside workspace `artifact_roots`.
- Claimed paths do not overlap another active claim unless override is recorded.
- Claim creates an activity event.

Failure behavior:

- Agent must not edit overlapping paths.
- Telegram status must show the blocker.

Tests:

- Unit test creates claim and appends `claimed` event.
- Unit test blocks overlapping claim from different actor.
- Unit test allows same actor to refresh claim.
- Unit test expires stale claim.
- CLI test `claim` followed by `status` shows active claim.

### Gate 3: Context Readiness

Required before implementation:

- Agent receives a task pack or prepare packet.
- Packet includes recent activity events.
- Packet includes active claims.
- Packet includes relevant decisions.
- Packet includes blockers.
- Packet includes required context docs.
- Packet includes required tests.

Failure behavior:

- Agent must run `prepare` again or mark task blocked.

Tests:

- Unit test task pack includes activity events.
- Unit test task pack includes active claims.
- Unit test task pack includes workboard and decision refs.
- CLI test `prepare --workspace-id inner-world --task-id TASK-001` emits a bounded packet.

### Gate 4: Implementation Logging

Required during work:

- Every meaningful file change is represented by an `edited` event.
- Event includes files touched.
- Event includes reasoning.
- Event links to task id.
- Decision-worthy choices create `decided` events and update `DECISIONS.md`.

Failure behavior:

- Task cannot move to verification.

Tests:

- Unit test edit event requires at least one file path.
- Unit test decision event materializes into workboard `DECISIONS.md`.
- CLI test `log --event-type edited` updates activity ledger and task changed files.

### Gate 5: Verification

Required before review:

- Required tests were run.
- Exact commands are recorded.
- Results are recorded.
- Manual checks are recorded when relevant.
- Failures create blockers or residual risks.
- Verification evidence is attached to task.

Failure behavior:

- Task remains `verification` or `blocked`.

Tests:

- Unit test task cannot enter `review` without verification evidence.
- Unit test failed verification creates blocker.
- CLI test `verify` records command, result, and evidence.
- Integration test verifies targeted suites for PWA, meta agent, and workspace coordination.

### Gate 6: Review

Required before done:

- Acceptance criteria are satisfied.
- Changed files are listed.
- Decisions are linked.
- Verification evidence exists.
- Residual risks are stated, even if `none known`.
- Handoff notes explain what another agent needs to know.

Failure behavior:

- Task remains `review`.

Tests:

- Unit test rejects done transition without residual risks.
- Unit test rejects done transition without changed files.
- Unit test rejects done transition without handoff notes.
- CLI test `complete` enforces all done requirements.

### Gate 7: Deployment

Required before `/deploy <release_id>`:

- Release links to workspace id.
- Release links to task ids.
- All linked tasks are `done`.
- Release manifest exists.
- Gate report exists and passed.
- Rollback plan exists.
- Post-deploy smoke plan exists.
- Explicit approval exists for the release id.

Failure behavior:

- Telegram `/deploy` returns blocked reason.
- No deploy command runs.

Tests:

- Unit test deploy readiness blocks when linked task is not done.
- Unit test deploy readiness blocks missing rollback plan.
- Unit test deploy readiness blocks missing approval.
- Integration test `/deploy` executes only after all gates pass.
- Integration test post-deploy smoke writes activity event and release evidence.

### Gate 8: Handoff

Required whenever an agent stops before completion:

- Current task status is accurate.
- Last files touched are listed.
- Last commands run are listed.
- Current blocker or next action is explicit.
- Handoff event is appended.
- Workboard `HANDOFFS.md` is updated.

Failure behavior:

- Task remains claimed until claim expires.

Tests:

- Unit test handoff event requires next action or blocker.
- CLI test `handoff` releases or renews claim according to flag.
- Projection test materializes handoff into `HANDOFFS.md`.

## Telegram Meta Agent Requirements

### Commands

Required commands:

```text
/workspace <workspace_id>
/status
/tasks
/claim <task_id>
/handoff <task_id>
/blocker <task_id> <reason>
/decision <task_id> <decision>
/files <task_id>
/prepare <task_id>
/deploy <release_id>
```

### Telegram Gates

Telegram agent must:

- Never mutate files directly.
- Create and update structured tasks.
- Append activity events for every command that changes state.
- Refuse claim if another active claim overlaps.
- Refuse deploy unless Gate 7 passes.
- Keep replies compact and include ids.

Tests:

- Unit test command classification for all commands.
- Unit test `/claim` writes claim plus activity event.
- Unit test `/handoff` writes handoff event.
- Unit test `/status` shows active claims, blockers, and recent work.
- Unit test unauthorized Telegram user is ignored.
- Integration test Telegram polling processes command and persists offset.

## Codex Requirements

Before implementation, Codex must run:

```bash
python3 tools/workspace_coordination.py prepare --workspace-id <id> --task-id <id> --agent-id codex
```

Before editing, Codex must claim:

```bash
python3 tools/workspace_coordination.py claim --workspace-id <id> --task-id <id> --agent-id codex --path <path>
```

After edits, Codex must log:

```bash
python3 tools/workspace_coordination.py log --event-type edited ...
python3 tools/workspace_coordination.py verify ...
python3 tools/workspace_coordination.py handoff ...
```

Codex final response should summarize:

- task id
- files changed
- tests run
- blockers
- residual risks
- handoff state

Tests:

- CLI test prepare returns current workspace packet.
- CLI test claim blocks overlap.
- CLI test verify updates task state.
- CLI test complete enforces gates.

## Workboard Projection Requirements

`materialize` must update:

```text
docs/workboards/<board_id>/TASKS.md
docs/workboards/<board_id>/UPDATES.jsonl
docs/workboards/<board_id>/DECISIONS.md
docs/workboards/<board_id>/HANDOFFS.md
docs/workboards/<board_id>/tasks/<task_id>.md
```

Projection rules:

- Structured workspace state wins over markdown drift.
- `UPDATES.jsonl` remains append-only.
- Task markdown reflects current state.
- Decisions are concise and durable.
- Handoffs are enough for another agent to resume.

Tests:

- Unit test materialize writes all required files.
- Unit test materialize preserves append-only updates.
- Unit test manual markdown-only task is reported as drift unless imported.
- Snapshot test for generated task packet markdown.

## Release Requirements

Release manifest must include:

- `release_id`
- `workspace_id`
- `task_ids`
- `packet_ids`
- `activity_event_ids`
- `changed_files`
- `verification_refs`
- `gate_report_path`
- `rollback_plan_path`
- `post_deploy_smoke_path`

Deploy gate must check:

- all task ids are done
- all tasks include verification evidence
- no active blocker exists for linked tasks
- no active overlapping claim exists
- release gate report is passed
- rollback plan exists
- approval matches release id

Tests:

- Unit test release manifest validates workspace/task refs.
- Unit test release gate blocks active blockers.
- Unit test release gate blocks active claims.
- Unit test release gate blocks missing verification.
- Integration test Telegram `/deploy` records `deployed` activity event.

## Implementation Phases

### Phase 1: Schema And Migration

Deliverables:

- Workspace manifest validator.
- Migration from `scope_in` to `artifact_roots` and `objectives`.
- Tests for path/prose split.
- Updated existing workspaces.

Acceptance:

- No workspace binding uses prose objectives as artifact roots.
- Existing `sol-frontend` and `sol-context-frames` validate.

### Phase 2: Activity Ledger

Deliverables:

- `AgentActivityEvent` schema.
- Append/read helpers.
- Activity summary helper.
- Tests for all required event types.

Acceptance:

- Every state-changing CLI command appends an event.
- Activity can be filtered by workspace, task, actor, file path, and event type.

### Phase 3: Claims

Deliverables:

- Claim schema.
- Claim create/release/expire helpers.
- Overlap detector.
- CLI commands.

Acceptance:

- Two agents cannot claim overlapping paths without explicit override.
- Expired claims no longer block work.

### Phase 4: Task State And Gates

Deliverables:

- Structured task schema.
- Gate transition validator.
- `prepare`, `claim`, `verify`, `complete`, `handoff` commands.

Acceptance:

- A task cannot reach `done` unless all mandatory done fields exist.
- Gate failures return precise reasons.

### Phase 5: Workboard Materialization

Deliverables:

- Materializer from workspace state to workboard files.
- Drift detection for markdown-only edits.
- Tests for projection files.

Acceptance:

- Workboard reflects canonical structured state.
- Agents can read the board and resume without hidden context.

### Phase 6: Telegram Integration

Deliverables:

- Telegram commands for workspace coordination.
- Status replies include tasks, claims, blockers, and recent activity.
- Deploy command uses release gate.

Acceptance:

- Telegram meta agent and Codex see the same task/claim/activity state.
- Unauthorized Telegram users cannot mutate workspace state.

### Phase 7: Release Integration

Deliverables:

- Release manifest workspace refs.
- Deploy gate checks workspace/task/activity evidence.
- Post-deploy smoke event.

Acceptance:

- `/deploy` cannot run unless all linked workspace gates pass.
- Deployment writes release evidence and activity evidence.

## Test Suite Map

Add focused tests:

```text
tests/test_workspace_manifest_schema.py
tests/test_workspace_activity_events.py
tests/test_workspace_claims.py
tests/test_workspace_coordination_cli.py
tests/test_workspace_workboard_projection.py
tests/test_workspace_release_gates.py
tests/test_meta_telegram_workspace_commands.py
```

Keep existing tests:

```text
tests/test_element_workspace_binding.py
tests/test_meta_telegram_agent.py
tests/test_deploy_release_gates.py
tests/test_deploy_thought_capture_pwa.py
```

Minimum verification command for this implementation:

```bash
pytest \
  tests/test_workspace_manifest_schema.py \
  tests/test_workspace_activity_events.py \
  tests/test_workspace_claims.py \
  tests/test_workspace_coordination_cli.py \
  tests/test_workspace_workboard_projection.py \
  tests/test_workspace_release_gates.py \
  tests/test_meta_telegram_workspace_commands.py \
  tests/test_element_workspace_binding.py \
  tests/test_meta_telegram_agent.py \
  tests/test_deploy_release_gates.py \
  tests/test_deploy_thought_capture_pwa.py -q
```

## Operational Readiness Checklist

The system is usable when:

- Codex can run `prepare`, claim a task, edit files, verify, and hand off.
- Telegram meta agent can list tasks, claim tasks, record blockers, record decisions, and request deploy.
- Workboard files update from canonical workspace state.
- Active claims prevent accidental overlap.
- Release gates require linked task evidence.
- `/status` tells the user what each agent is doing now.
- A new agent can resume from task packet plus recent activity without reading chat history.

## First Implementation Slice

Build this first:

1. `artifact_roots` / `objectives` migration.
2. Activity event ledger.
3. Claims with overlap detection.
4. `tools/workspace_coordination.py status|prepare|claim|log|handoff`.
5. Telegram `/status`, `/tasks`, `/claim`, `/handoff`.
6. Tests for schema, claims, CLI, Telegram commands, and workboard projection.

This slice gives Codex and the Telegram meta agent shared situational awareness before we add release-deep automation.
