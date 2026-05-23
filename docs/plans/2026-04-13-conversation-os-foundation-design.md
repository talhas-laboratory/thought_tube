# Conversation OS Foundation Design

Date: 2026-04-13
Status: accepted for implementation

## Purpose

This repo is the control plane for building Inner World v1 through conversation.
Every project conversation and every explicit import is treated as canonical substrate.
Raw artifacts stay append-only.
Derived artifacts stay inspectable, reproducible, and disposable.

## Accepted architecture

- Canonical source of truth: Markdown and JSONL
- Capture layer: `memory/events/<session_id>.jsonl`
- Session layer: `memory/sessions/<session_id>/`
- Memory layer: `memory/cards/` and `memory/indexes/`
- Routing layer: `context/task_packs/`
- Product layer: `product/inner_world_v1/`
- Domain specialization: `plugins/<plugin_id>/`

## Required operating rules

- No rewriting raw event logs.
- No hidden state that cannot be rebuilt from repo truth.
- No domain-specific branching in core capture, analysis, or routing modules.
- Every handoff must go through a task pack.
- Every surfaced product insight must satisfy the insight contract.

## Canonical pipeline

1. Start or import a session.
2. Append conversation events.
3. Checkpoint when a stable transcript is useful.
4. Close the session to materialize transcript, analysis artifacts, cards, and indexes.
5. Build a task pack for the next focused unit of work.
6. Seed or update Inner World v1 using explicit source artifacts.
7. Generate a Morning Batch and record explicit feedback.

## Current implementation notes

- Routing always includes core reference docs so a new agent has immediate continuity.
- Routing falls back to recent sessions and durable decision/state cards when keyword overlap is weak.
- Inner World v1 stores source items, concept nodes, connections, reasoning primitives, insight candidates, surfaced insights, and feedback events as transparent files.
- Feedback affects later Morning Batch ranking without mutating raw source items.

## Core commands

- `python tools/conversation_os.py init`
- `python tools/conversation_os.py session start --title "..."`
- `python tools/conversation_os.py session append --session-id ... --actor user --kind request --content "..."`
- `python tools/conversation_os.py session close --session-id ... --task-id ... --request "..."`
- `python tools/conversation_os.py session import --source-path ... --title "..."`
- `python tools/conversation_os.py task-pack build --task-id ... --request "..."`
- `python tools/conversation_os.py inner-world seed --source-path ...`
- `python tools/conversation_os.py inner-world derive --domains research,art,entrepreneurship`
- `python tools/conversation_os.py inner-world batch --limit 5 --domains research,art,entrepreneurship`
- `python tools/conversation_os.py inner-world feedback --insight-id ... --feedback-state relevant`
- `python tools/conversation_os.py inner-world export`

## Immediate next milestones

- Capture this active build thread as a live session artifact.
- Keep adding imported conversations and design reviews through the same session pipeline.
- Replace the heuristic graph and ranking logic with stricter evidence scoring only after the current inspectable baseline is stable.
