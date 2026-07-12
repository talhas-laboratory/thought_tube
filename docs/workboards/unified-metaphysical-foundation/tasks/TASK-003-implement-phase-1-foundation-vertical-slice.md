# TASK-003-implement-phase-1-foundation-vertical-slice: Implement Phase 1 foundation vertical slice

Status: review
Owner: cursor-cloud-agent
Current gate: verification

## Problem

Kernel contracts (TASK-001) and migration fixtures (TASK-002) exist, but there is no executable path that captures raw input, branches interpretation, asserts claims, optionally commits state, and supports bounded query and provenance traversal without LLM or inference services.

## Scope

In:

- append-only `FoundationStore` at `memory/foundation/kernel_events.jsonl`;
- `FoundationRuntime` vertical slice operations;
- `capture_from_conversation_event` bridge from `session_append` events;
- scope, branch, referent, claim, StateCommitment, retract, and revise operations;
- `BoundedView` query with branch, scope, and depth limits;
- provenance trace from claim to `SourceFragment`;
- `run_vertical_slice` end-to-end helper;
- Gate F2 tests.

Out:

- CLI subcommands (programmatic API only for now);
- profile registry (TASK-004);
- LLM, embedding, or graph projection services;
- durable ReasoningSignatures or resurfacing.

## Acceptance Criteria

- Raw capture succeeds with inference unavailable (`capture_from_conversation_event`).
- Full path: capture → referent → scope/branch → claim → optional state commitment.
- Contradictory branches remain isolated in bounded views.
- Retraction excludes records from default bounded view.
- Bounded view fails closed on `max_depth`.
- Provenance trace terminates at `SourceFragment`.
- Migrated bundle validates with zero errors after vertical slice run.

## Plan

1. Add append-only kernel event store with folded read model.
2. Implement runtime operations citing framework §20.3, §20.5, §21.
3. Bridge `memory/events/*.jsonl` session events to `SourceFragment`.
4. Add Gate F2 tests including branch isolation, retraction, depth, and provenance.

## Verification Evidence

- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_runtime -v` — 11 tests, OK
- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_contracts tests.test_metaphysical_kernel_migration tests.test_metaphysical_kernel_runtime -v` — 37 tests, OK
- Implementation: `src/conversation_os/metaphysical_kernel_store.py`, `src/conversation_os/metaphysical_kernel_runtime.py`
- Store path: `memory/foundation/kernel_events.jsonl`

## Updates

- Created: `2026-07-12T14:18:38.453018+00:00`
- Implementation completed (2026-07-12): Phase 1 vertical slice runtime and Gate F2 tests.

## Handoff Notes

- TASK-004 should register Field/Formation profiles against this store without redefining kernel semantics.
- Optional follow-up: wire `foundation_capture_from_session` into `session_append` CLI as an opt-in flag.
