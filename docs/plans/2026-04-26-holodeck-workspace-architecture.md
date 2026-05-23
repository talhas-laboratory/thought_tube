# Holodeck Workspace Architecture

## Purpose

This document defines the `Holodeck` as a first-class organizational and incubation environment inside the Conversation OS.

The product effect is:

- turn a raw idea or goal into a bounded execution environment
- provide the bounded space in which that objective is fully developed
- let multiple agents and mediums contribute work without losing continuity
- keep local work sharply scoped and inspectable
- preserve a clean boundary between local incubation knowledge and repo-global knowledge
- produce implementation-ready handoff surfaces instead of archive dumps

This is not a naming exercise anymore. This document treats `Holodeck` as an implementation-grade system design.

## Naming and Object Model

`Holodeck` should be the user-facing metaphor.

Internal code should stay generic:

- user-facing term: `Holodeck`
- internal object: `workspace`
- internal owner module: `workspaces.py`

That split matters.

The current codebase already uses multiple thread concepts:

- `conversation_threads`
- `thread_abstractions`
- `ThoughtThread`

So Holodeck must **not** become another `thread` type.

It is a goal-scoped organizational workspace that **links** sessions, task packs, plans, tests, and derived views.

More strongly:

It is the bounded development environment in which a project objective is shaped, revised, decomposed, validated, coordinated, and matured until it is ready for integration, launch, closure, or deliberate abandonment.

## Core Design Decision

The Holodeck is a typed, append-oriented workspace layer that sits above sessions and below task-pack handoff.

It is:

- not a semantic thread
- not a domain overlay
- not a project lens
- not a direct Jira mirror
- not a free-form notes folder

It is the control plane for incubating one bounded goal until it becomes production-ready work.

It is also the primary space in which that goal becomes fully developed.

Holodeck is therefore not just for tracking work around an objective.
It is the environment where the objective itself becomes clearer, changes shape, gains new constraints, absorbs new ideas, and turns into a fully worked feature, system, initiative, or decision.

The central rule is:

`all reasoning and state inside a Holodeck must be typed, evidence-linked, and rebuildable from source records`

That rule should be enforced by the operator surface, not left as a cultural suggestion.

## Dynamic Objective Rule

The objective inside a Holodeck must be treated as dynamically developing, not frozen at creation time.

At creation time the user or agent may only know:

- a partial goal
- an initial direction
- one promising wedge
- a first framing of the problem

That is acceptable.

Holodeck should assume that during operation the user may:

- sharpen the objective
- add new ideas
- redefine success
- split or merge workstreams
- change priority
- add or remove constraints
- discover better tests
- replace a weak framing with a stronger one

So the project-management layer inside a Holodeck must also be dynamic.

Work items, tests, risks, founder context, and handoff state should be easy to revise as understanding improves.

The rule is:

`Holodeck preserves continuity while allowing the objective and its management structure to evolve`

The system should not punish refinement.
It should make refinement explicit, typed, and inspectable.

## Maturation Framework

The deeper pattern behind Holodeck is not just "workspace around a goal."

The deeper pattern is:

`raw idea -> context -> constraints -> development -> verification -> integration`

Every Holodeck should help an objective move through that maturation path.

That means Holodeck needs explicit support for:

- capturing the raw idea without pretending it is already mature
- placing the idea in the right project and domain context
- attaching constraints and non-goals before execution expands
- developing the idea through typed work, decisions, tests, and artifacts
- verifying the developed output with evidence
- embedding the result into the larger system through code, docs, cards, task packs, product surfaces, or archived learnings

### Maturation stages

The workspace manifest should eventually track a `maturation_stage`.

Allowed stages:

- `raw`
- `contextualizing`
- `scoping`
- `developing`
- `verifying`
- `integrating`
- `complete`
- `abandoned`

Stage movement should be explicit.

The system should not infer that a Holodeck is `verifying` just because tests exist, or `complete` just because all work items are done.

Each stage should have readiness checks.

Examples:

- `raw` can exist with only title, goal, and purpose
- `contextualizing` requires at least one context record or linked artifact
- `scoping` requires scope boundaries and at least one constraint record
- `developing` requires work items and open verification shape
- `verifying` requires declared tests or acceptance criteria with evidence paths
- `integrating` requires at least one integration target or promotion candidate
- `complete` requires no active blockers, no unresolved conflicts, and explicit integration or closure reason

### Context records

Context records should be separate from knowledge records.

Knowledge records capture claims, decisions, risks, assumptions, requirements, and questions.

Context records explain where the objective sits.

Minimum context record fields:

- `context_id`
- `workspace_id`
- `context_kind`
- `title`
- `summary`
- `domain`
- `source_refs`
- `linked_artifact_ids`
- `confidence`
- `status`
- `created_at`
- `updated_at`

Suggested `context_kind` values:

- `domain_context`
- `existing_system`
- `owner_surface`
- `precedent`
- `user_context`
- `market_context`
- `technical_context`
- `historical_note`

### Constraint records

Constraint records should also be first-class.

They prevent agent drift by making boundaries inspectable instead of burying them in prose.

Minimum constraint record fields:

- `constraint_id`
- `workspace_id`
- `constraint_kind`
- `statement`
- `applies_to`
- `severity`
- `source_refs`
- `status`
- `created_at`
- `updated_at`

Suggested `constraint_kind` values:

- `scope_in`
- `scope_out`
- `non_goal`
- `invariant`
- `owner_boundary`
- `allowed_path`
- `blocked_path`
- `verification_requirement`
- `budget`
- `stop_condition`

### Integration targets

Integration should be modeled before the work is done.

Minimum integration target fields:

- `target_id`
- `workspace_id`
- `target_kind`
- `title`
- `destination_ref`
- `required_evidence_refs`
- `status`
- `source_refs`
- `created_at`
- `updated_at`

Suggested `target_kind` values:

- `code`
- `docs`
- `memory_card`
- `task_pack`
- `product_surface`
- `test_suite`
- `external_artifact`
- `successor_holodeck`

This makes the final embedding step explicit instead of relying on an agent to remember where the work should land.

## Fit With Existing Repo Architecture

This repo already has the right lower-level primitives:

- source capture through sessions in `memory/events/`
- derived session artifacts in `memory/sessions/<session_id>/`
- durable repo memory cards in `memory/cards/`
- scoped handoff through `context/task_packs/`
- product-level runtime state in `product/inner_world_v1/`

The Holodeck should reuse those primitives rather than replace them.

The resulting stack becomes:

`conversation substrate`
-> `session artifacts`
-> `Holodeck workspace`
-> `task pack handoff`
-> `implementation work`
-> `promotion back into repo-global memory`

This preserves the repo's core laws from `AGENTS.md`:

- raw source stays append-only
- derived never overwrites source
- task packs remain the canonical handoff surface
- uncertainty remains explicit

## Holodeck Operating Law

Every Holodeck should enforce these rigor rules.

### 1. Typed records only

No important state should exist only as prose.

Every meaningful contribution must land as one of:

- workspace event
- artifact link
- work-item transition
- test case
- test run
- knowledge record
- promotion record

### 2. Claim posture is explicit

Every knowledge-bearing record must declare one of:

- `observed`
- `inferred`
- `proposed`
- `decided`

This is not optional.

The system must not flatten direct evidence, working hypothesis, and finalized decision into the same surface text.

### 3. Evidence is required

Any requirement, risk, or decision in the Holodeck must carry at least one of:

- direct source ref
- linked session ref
- linked artifact ref
- explicit note that evidence is still missing

### 4. Derived views are non-authoritative

Agents may not directly edit:

- `board.md`
- `diary.md`
- `tests.md`
- `knowledge.md`
- `handoff.md`
- `mobile.md`

Those are projections.

### 5. Purpose and boundaries come first

No work item becomes active without:

- concrete purpose
- explicit scope
- acceptance criteria
- declared non-goals

These are initial grounding fields, not a claim that the objective is already fully understood.

The Holodeck must support later revision of all of these when the user or agent learns something better.

### 6. Verification shape is declared early

Implementation work cannot be considered well-formed unless the Holodeck already knows:

- how the change should be tested
- what evidence will count as success
- what remains risky even if tests pass

### 7. Promotion is explicit

Holodeck-local knowledge does not silently become global truth.

Promotion into repo-global cards, plans, or task packs must happen through explicit promotion records.

## Non-Goals

The Holodeck core should not do these things in v1:

- no direct Jira API coupling in the core operator
- no founder-specific branching in the core workspace model
- no hidden mutable board state outside source records
- no implicit promotion of local notes into repo-global truth
- no new graph or semantic reasoning stack separate from existing Inner World layers
- no direct editing of raw session logs

## Holodeck Lifecycle

### Create

An agent creates a Holodeck around one concrete goal.

That goal may still be early, provisional, or incomplete.

Inputs:

- title
- purpose
- success condition
- scope boundaries
- optional template key
- optional domain overlays

### Ground

The agent links the initial materials:

- live session ids
- imported transcript ids
- plans
- task packs
- docs
- screenshots
- run outputs

Grounding establishes the first bounded version of the objective.
It does not lock the objective permanently.

### Decompose

The agent turns the goal into typed work items, open questions, risks, and tests.

This decomposition must be revisable.
As the user develops new ideas, discovers new constraints, or changes the intended outcome, the decomposition should be updated rather than forcing work into stale structure.

### Operate

Agents append work transitions, test runs, and knowledge records while the reducer keeps the derived surfaces current.

Operate also includes active reframing of the objective itself.

Examples:

- update the goal statement
- revise the success condition
- change priorities
- replace one wedge with another
- add a newly discovered workstream
- retire work that no longer serves the objective
- rewrite tests to match a stronger understanding of done

### Handoff

When another agent or medium should continue, the Holodeck emits a task pack and handoff view instead of dumping the archive.

That handoff should reflect the latest developed state of the objective, not just the original framing.

### Promote

Only accepted local knowledge is promoted outward into repo-global cards, design docs, or task packs.

### Archive

When the goal is complete or abandoned, the Holodeck is closed but remains inspectable.

Closure should mean the objective reached a real outcome:

- integrated
- shipped
- intentionally paused
- intentionally abandoned
- or spun into a successor Holodeck

## On-Disk Layout

### Source layer

Canonical workspace state should live under:

- `memory/workspaces/<workspace_id>/manifest.json`
- `memory/workspaces/<workspace_id>/events.jsonl`
- `memory/workspaces/<workspace_id>/artifact_links.jsonl`
- `memory/workspaces/<workspace_id>/work_item_events.jsonl`
- `memory/workspaces/<workspace_id>/test_cases.jsonl`
- `memory/workspaces/<workspace_id>/test_runs.jsonl`
- `memory/workspaces/<workspace_id>/knowledge_records.jsonl`
- `memory/workspaces/<workspace_id>/promotion_records.jsonl`

These are the authoritative inputs.

`manifest.json` is the only mutable control object.

The JSONL files are append-oriented logs.

### Derived layer

Materialized workspace views should live under:

- `context/workspaces/<workspace_id>/summary.json`
- `context/workspaces/<workspace_id>/brief.md`
- `context/workspaces/<workspace_id>/board.json`
- `context/workspaces/<workspace_id>/board.md`
- `context/workspaces/<workspace_id>/diary.md`
- `context/workspaces/<workspace_id>/tests.json`
- `context/workspaces/<workspace_id>/tests.md`
- `context/workspaces/<workspace_id>/knowledge.json`
- `context/workspaces/<workspace_id>/knowledge.md`
- `context/workspaces/<workspace_id>/handoff.md`
- `context/workspaces/<workspace_id>/mobile.md`

These views are disposable and rebuildable.

## Source Schemas

### Workspace manifest

The manifest defines the current workspace envelope.

Suggested fields:

- `workspace_id`
- `label`
- `status`
- `goal`
- `purpose`
- `success_condition`
- `scope_in`
- `scope_out`
- `template_key`
- `template_fields`
- `domain_overlays`
- `linked_session_ids`
- `linked_task_pack_ids`
- `created_at`
- `updated_at`
- `closed_at`

Status vocabulary:

- `active`
- `paused`
- `blocked`
- `closed`
- `archived`

### Workspace event

Workspace events are chronological narrative anchors, not free-form state stores.

Suggested fields:

- `event_id`
- `workspace_id`
- `timestamp`
- `actor`
- `kind`
- `summary`
- `content`
- `source_refs`
- `related_work_item_ids`
- `related_test_ids`
- `tags`

Event kinds:

- `workspace_created`
- `scope_refined`
- `artifact_linked`
- `work_started`
- `work_blocked`
- `work_completed`
- `test_recorded`
- `decision_noted`
- `handoff_prepared`
- `promotion_requested`
- `promotion_applied`

### Artifact link

Artifact links are the canonical way to attach external and repo artifacts into a Holodeck.

Suggested fields:

- `artifact_id`
- `workspace_id`
- `artifact_kind`
- `title`
- `source_ref`
- `source_type`
- `provenance`
- `summary`
- `status`
- `linked_at`
- `attributes`

Artifact kinds:

- `session`
- `task_pack`
- `plan_doc`
- `design_doc`
- `spec_doc`
- `code_ref`
- `test_output`
- `image`
- `mobile_artifact`
- `external_note`
- `runbook`

Default rule:

`ingest by reference unless durability or transport requires capture`

### Work-item event

Work items should be event-sourced enough to preserve transitions.

Suggested fields:

- `event_id`
- `workspace_id`
- `work_item_id`
- `operation`
- `timestamp`
- `actor`
- `payload`
- `source_refs`

Operations:

- `create`
- `rename`
- `set_status`
- `set_parent`
- `set_dependencies`
- `set_owner`
- `set_acceptance`
- `set_constraints`
- `link_artifact`
- `link_test`
- `archive`

The reducer builds the current work-item state from these events.

### Reduced work-item state

The board projection should compute this shape:

- `work_item_id`
- `title`
- `kind`
- `status`
- `goal_ref`
- `parent_id`
- `depends_on`
- `owner`
- `priority`
- `acceptance_criteria`
- `constraints`
- `linked_artifacts`
- `linked_tests`
- `guard_status`
- `updated_at`

Work-item kinds:

- `epic`
- `feature`
- `task`
- `bug`
- `research`
- `decision`

Work-item statuses:

- `proposed`
- `scoped`
- `ready`
- `in_progress`
- `blocked`
- `done`
- `archived`

Required board rules:

- no `in_progress` without acceptance criteria
- no `ready` without scope and constraints
- no `done` without linked verification evidence
- parent items cannot close while open children remain

### Test case

Test planning must be explicit before code starts.

Suggested fields:

- `test_id`
- `workspace_id`
- `target_ref`
- `work_item_id`
- `test_kind`
- `intent`
- `command_or_protocol`
- `expected_signal`
- `risk_level`
- `status`
- `created_at`

Test kinds:

- `unit`
- `integration`
- `workflow`
- `manual`
- `regression`
- `acceptance`

Test status vocabulary:

- `planned`
- `ready`
- `blocked`
- `retired`

### Test run

Test execution must be separate from test definition.

Suggested fields:

- `run_id`
- `workspace_id`
- `test_id`
- `timestamp`
- `actor`
- `result`
- `evidence_ref`
- `notes`
- `command_or_protocol`

Run result vocabulary:

- `passing`
- `failing`
- `blocked`
- `not_run`

### Knowledge record

Knowledge inside the Holodeck must be structured and uncertainty-aware.

Suggested fields:

- `record_id`
- `workspace_id`
- `record_kind`
- `claim_posture`
- `title`
- `statement`
- `confidence`
- `status`
- `source_refs`
- `related_work_item_ids`
- `supersedes_record_id`
- `created_at`
- `attributes`

Record kinds:

- `requirement`
- `decision`
- `assumption`
- `risk`
- `open_question`
- `constraint`
- `insight`
- `promotion_candidate`

Claim posture vocabulary:

- `observed`
- `inferred`
- `proposed`
- `decided`

Knowledge status vocabulary:

- `active`
- `resolved`
- `superseded`
- `rejected`

### Promotion record

Promotion is the explicit bridge from local incubation knowledge into repo-global artifacts.

Suggested fields:

- `promotion_id`
- `workspace_id`
- `record_id`
- `target_kind`
- `target_ref`
- `decision`
- `timestamp`
- `actor`
- `notes`

Promotion targets:

- `memory_card`
- `plan_doc`
- `task_pack`
- `product_doc`
- `none`

Promotion decision vocabulary:

- `proposed`
- `accepted`
- `rejected`
- `applied`

## Derived Surfaces

### Brief

`brief.md` is the single fastest operator summary.

It should answer:

- what this Holodeck is for
- what is active now
- what is blocked
- what must not change
- what verification matters next

### Board

`board.md` and `board.json` are the reduced current-state view over work-item events.

This is the Jira-like surface, but it is internal and deterministic.

Do not couple the core model to Jira naming or APIs.

### Diary

`diary.md` is generated from workspace events plus key work and test transitions.

It is a narrative continuity surface, not the source of truth.

### Tests

`tests.md` and `tests.json` show:

- defined test cases
- most recent run per test
- still-unverified acceptance criteria
- hotspots with repeated failures or blocked verification

### Knowledge

`knowledge.md` and `knowledge.json` show:

- active requirements
- active decisions
- open questions
- risks
- promotable local insights

The view must keep claim posture visible.

### Handoff

`handoff.md` is the continuity surface for another agent or another medium.

It should include:

- current goal
- current work item
- exact next actions
- constraints
- tests to run
- linked task pack refs
- raw sessions that matter most

### Mobile

`mobile.md` is a compressed form of the handoff surface for constrained clients like mobile ChatGPT.

It should be short enough to paste or inspect quickly without losing the goal and next verification target.

## Operator Surface

The Holodeck must expose a stable operator layer that agents can call directly.

User-facing CLI namespace should be:

- `python3 tools/conversation_os.py holodeck ...`

Internal implementation can still use `workspaces.py`.

### Required commands

- `holodeck create`
- `holodeck event`
- `holodeck ingest-artifact`
- `holodeck link-session`
- `holodeck add-work-item`
- `holodeck update-work-item`
- `holodeck add-test`
- `holodeck record-test-run`
- `holodeck add-knowledge`
- `holodeck promote`
- `holodeck materialize`
- `holodeck status`
- `holodeck task-pack`

### Command invariants

All commands must obey these rules:

- mutate only source records
- never write rendered views directly except through `materialize`
- attach source refs where possible
- reject invalid status transitions
- reject missing-purpose work activation

## Artifact Ingestion Model

The Holodeck must be able to ingest or link artifacts from:

- repo docs
- live sessions
- imported transcripts
- task packs
- screenshots
- test output
- mobile artifacts
- external text artifacts

The ingestion contract must answer:

- is this copied or referenced
- what kind of artifact is it
- why does it matter to this workspace
- what provenance path does it have

The reducer should deduplicate artifacts by:

- normalized source ref
- artifact kind
- optional content hash when captured locally

## Task-Pack Integration

Holodeck should improve task-pack quality, not replace task packs.

`holodeck task-pack` should emit a standard task pack augmented with workspace context:

- workspace goal
- active work item
- acceptance criteria
- current blockers
- linked tests
- relevant sessions
- relevant local knowledge records

This preserves the repo rule that handoff goes through a task pack.

## Lens and Template Model

The Holodeck core should be lens-neutral.

That means:

- no founder-specific branching in the core schema
- no separate core type for product versus research versus platform work

Instead, Holodeck should support templates.

Suggested template keys:

- `founder`
- `research`
- `product`
- `platform`
- `creative`

The founder template should be a follow-on on top of the core model.

Example founder-specific additions:

- user wedge
- buyer/user split
- success metric
- moat hypothesis
- GTM risk
- launch blocker

These belong in template-driven fields or derived sections, not in the universal core schema.

Template overlays must also be dynamically revisable.

For example, a founder Holodeck may begin with a weak wedge and no clear moat, then later revise:

- wedge
- target user
- launch metric
- GTM risk
- moat hypothesis

Those revisions should be treated as expected development, not plan drift.

## Multi-Agent and Cross-Medium Rules

Holodeck exists specifically because work will happen across:

- local Codex
- mobile ChatGPT
- other IDE agents
- imported notes and artifacts

So concurrency rules must be explicit.

### Source discipline

- append new source rows instead of silently overwriting local state where practical
- treat manifest as control envelope, not as the only history
- use reducer logic to build current board and knowledge state

### Conflict discipline

If two agents create conflicting decisions or requirements:

- keep both records
- mark conflict in a derived view or conflict attribute
- require explicit resolution rather than silent overwrite

### Ownership discipline

Owner fields are advisory coordination, not truth.

The source of truth remains the record graph, not an assumption that only one agent acted.

### Dynamic management discipline

Holodeck project management should be plastic but explicit.

That means:

- plans may be restructured
- work items may be split, merged, blocked, or retired
- success metrics may be revised
- priorities may move
- new idea branches may enter the workspace

But every meaningful change should still leave a typed trail.

The management surface should feel dynamic to the user while remaining legible to future agents.

## Guard and Verification Discipline

Holodeck should make the engineering guard operational, not optional.

For implementation-oriented work items, the board state should track:

- `guard_status`
- `guard_request`
- `guard_purpose`
- `guard_paths`

Recommended board rule:

`a work item cannot transition from scoped to ready until its implementation request has a guard result of ready`

This keeps the repo's minimality discipline embedded in the workspace itself.

## Agent Run Contract

Agents should not work "inside a Holodeck" in a general way.

They should work under a bounded run contract.

The run contract is the anti-drift layer for agent execution.

It should answer:

- what objective is being advanced
- which work item or maturation stage is active
- which files, records, or artifact surfaces are allowed
- which commands are expected
- what verification must happen
- what should make the agent stop instead of continuing
- what must be summarized before handoff

### Run contract source record

Minimum source fields:

- `run_id`
- `workspace_id`
- `active_work_item_id`
- `active_maturation_stage`
- `purpose`
- `allowed_paths`
- `blocked_paths`
- `allowed_commands`
- `expected_outputs`
- `verification_plan`
- `context_budget`
- `stop_conditions`
- `started_at`
- `ended_at`
- `status`

Suggested `status` values:

- `planned`
- `active`
- `completed`
- `stopped`
- `blocked`
- `abandoned`

### Run contract rules

The operator layer should eventually enforce these rules:

- no implementation edit without an active run contract
- no active run contract without purpose and stop conditions
- no file edit outside `allowed_paths` without recording scope expansion
- no transition to `completed` without verification result or explicit reason verification was impossible
- no follow-on bug fixing outside the active work item unless a new work item or run contract is created
- no broad context loading unless the run contract records why that context is needed

### Drift detection

`holodeck check` should eventually report drift signals.

Examples:

- changed files outside allowed paths
- commands outside allowed commands
- context budget exceeded
- active run has no verification record
- active run has no checkpoint after a completed slice
- agent touched a blocked path
- agent opened new work without linking it to the current objective

Drift detection should not punish discovery.

It should require discovery to be converted into typed work, typed context, a new constraint, or a successor Holodeck instead of silently expanding the current run.

## Initial Implementation Slice

The first implementation slice should be narrow and useful.

### Phase 1

Build:

- workspace source layer
- Holodeck CLI
- reducers/materializers for brief, board, tests, knowledge, and handoff
- objective revision and management revision support
- workspace-scoped task-pack generation
- acceptance tests for creation, event logging, board transitions, test recording, and materialization

Do not build yet:

- Jira sync
- UI or miniapp
- advanced concurrency resolution
- external connectors

## Remaining Implementation Backlog

This backlog reflects the conversation slice that clarified Holodeck as a general maturation system and raised the risk of agent drift.

Each slice should be implemented with the engineering guard, a failing regression test first, and the smallest owner surface the guard clears.

### Slice A: maturation stage field

Goal:

- add `maturation_stage` to the workspace manifest and snapshot
- add `holodeck advance-stage`
- add stage history through workspace events

Implementation steps:

- add manifest default `maturation_stage=raw`
- add parser command `holodeck advance-stage --workspace-id ... --stage ... --reason ...`
- validate stage values against the allowed stage list
- write a workspace event `maturation_stage_changed`
- materialize stage into `brief.md`, `handoff.md`, `mobile.md`, and summary JSON
- add tests for create default, valid stage advance, invalid stage rejection, and stage visibility in `holodeck check`

### Slice B: stage readiness checks

Goal:

- make `holodeck check` report whether the current maturation stage is satisfied

Implementation steps:

- add `stage_ok`
- add `stage_gaps`
- add `counts.stage_gaps`
- check `raw`, `contextualizing`, `scoping`, `developing`, `verifying`, `integrating`, and `complete` against concrete evidence
- include stage gaps in task-pack constraints
- add tests for one passing and one failing readiness case per stage

### Slice C: context records

Goal:

- add first-class context records so agents know what environment the idea belongs in

Implementation steps:

- add source file `context_records.jsonl`
- add `holodeck add-context`
- add `holodeck update-context`
- add reducer for current context records
- materialize `context.md` and `context.json`
- include top context records in handoff and task packs
- add tests for add, update, materialize, and stage-readiness interaction

### Slice D: constraint records

Goal:

- make scope, non-goals, allowed paths, and stop conditions explicit records

Implementation steps:

- add source file `constraint_records.jsonl`
- add `holodeck add-constraint`
- add `holodeck update-constraint`
- add reducer for current constraint records
- materialize `constraints.md` and `constraints.json`
- feed `allowed_path`, `blocked_path`, `non_goal`, and `stop_condition` records into `holodeck check`
- add tests for constraint materialization and check output

### Slice E: integration targets

Goal:

- make final embedding into the larger system explicit before completion

Implementation steps:

- add source file `integration_targets.jsonl`
- add `holodeck add-integration-target`
- add `holodeck update-integration-target`
- materialize `integration_targets.md` and `integration_targets.json`
- require at least one active or completed integration target before `complete`
- link promotion records and generated artifacts to integration targets where possible
- add tests for target lifecycle and complete-stage readiness

### Slice F: agent run contracts

Goal:

- prevent agents from working in an unbounded, drifting way

Implementation steps:

- add source file `run_contracts.jsonl`
- add `holodeck start-run`
- add `holodeck finish-run`
- allow run contracts to bind to `active_work_item_id` or `active_maturation_stage`
- record `allowed_paths`, `blocked_paths`, `allowed_commands`, `verification_plan`, `context_budget`, and `stop_conditions`
- add active run state to `holodeck status`
- include active run context in task packs
- add tests for start, finish, missing stop conditions, and active run visibility

### Slice G: drift checks

Goal:

- make agent drift visible before it compounds

Implementation steps:

- add `drift_warnings` to `holodeck check`
- compare active run contract against known changed paths where available
- compare completed run against verification evidence
- flag active runs with no checkpoint or no finish record
- flag work-item expansion without a linked work item, context record, constraint, or successor Holodeck
- add tests for at least path drift, missing verification, and stale active run

### Slice H: implementation extraction

Goal:

- move Holodeck logic out of the growing CLI owner once the behavior is stable

Implementation steps:

- run guard for `src/conversation_os/workspaces.py` and `tests/test_workspaces.py`
- move pure reducers and validators first
- keep CLI as command wiring
- keep routing as task-pack enrichment owner
- preserve all existing CLI regression tests while adding focused workspace unit tests
- add a task pack for any follow-on extraction work before handing off to another agent

### Phase 1 success criteria

- an agent can create a Holodeck with a concrete goal
- that goal can later be revised without losing continuity
- sessions and docs can be linked into it
- work items can be created and moved through valid statuses
- test cases and runs can be recorded with evidence refs
- a materialized brief, board, tests view, knowledge view, and handoff can be regenerated from source records
- a Holodeck-scoped task pack can be built for another agent

## Proposed Owner Modules

The smallest plausible initial edit surface is:

- `src/conversation_os/models.py`
- `src/conversation_os/storage.py`
- `src/conversation_os/workspaces.py`
- `src/conversation_os/cli.py`
- `src/conversation_os/routing.py`
- `tests/test_workspaces.py`

This is intentionally narrow.

It avoids:

- polluting semantic runtime modules
- adding founder branching to core lens logic
- spreading Holodeck logic across multiple product subsystems too early

### Guard note

The current engineering guard heuristic is tuned for existing owner modules and lexical lookup, so it may under-rank a new `workspaces.py` owner even when that split is correct.

If the guard still returns `review_targets` because of the new owner path, the implementation run should do one of two things explicitly:

- justify the new owner module as the smallest coherent responsibility boundary and proceed only after that decision is recorded, or
- start with the narrower existing-owner surface in `models.py`, `storage.py`, `cli.py`, and `routing.py`, then extract to `workspaces.py` only after the first usable workflow exists

The important rule is not “never create a new owner file.”

The important rule is “do not create a new owner file casually.”

## Next-Run Guard Request

When implementation starts, the engineering guard should be run with this request:

Request:

`Add a Holodeck workspace operator and deterministic derived workspace views for goal-scoped feature incubation and cross-agent handoff.`

Purpose:

`Let agents create a bounded, typed, evidence-linked incubation environment that turns an idea into implementation-ready work without dumping the whole archive or mixing local incubation knowledge into repo-global truth by default.`

Proposed paths:

`src/conversation_os/models.py,src/conversation_os/storage.py,src/conversation_os/workspaces.py,src/conversation_os/cli.py,src/conversation_os/routing.py,tests/test_workspaces.py`

## Final Design Rule

Holodeck should feel strict in the right places.

It should be easy to add work.

It should be hard to:

- blur evidence and decision
- hide uncertainty
- mutate rendered views directly
- mark work complete without verification
- globalize local knowledge accidentally

If it does not enforce those boundaries, it is just a prettier scratchpad.

If it does enforce them, it becomes a reusable incubation environment that the product can use to build itself.
