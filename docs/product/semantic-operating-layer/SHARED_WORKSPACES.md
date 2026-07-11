# Shared Workspaces

This file defines the workspace stack for this product spine.

## Goal

Keep strategic architecture, active incubation, agent coordination, session evidence, and handoff packets tightly connected without creating duplicate state or hidden drift.

## Workspace Stack

```text
product spine folder
  -> active Holodeck workspace
  -> linked workboard
  -> linked task packs
  -> linked sessions and artifacts
```

## Layers

### Product spine folder

Location: `docs/product/semantic-operating-layer/`

Use for:

- product architecture
- system boundaries
- shared contracts
- cross-system decisions
- roadmap
- subproject packets

Source of truth for:

- what the product is
- how the systems connect
- which subprojects exist
- product-level decisions and gates

### Holodeck workspace

Owner module: [holodeck.py](/Users/talhauddin/software/inner_space/src/conversation_os/holodeck.py:1)

Use for:

- one bounded active objective
- typed context records
- constraints and non-goals
- work items and tests
- linked artifacts and sessions
- promotions and integration targets
- materialized workspace views

Source of truth for:

- active workspace state
- execution-stage constraints
- verification readiness
- workspace-local promotions and blockers

### Workboard

Location: `docs/workboards/...`

Use for:

- sparse coordination surface for agents
- readable task status
- decisions and handoffs
- explicit completion gates

Source of truth for:

- human-readable coordination state for a board
- durable agent handoff notes

Not the source of truth for:

- workspace context records
- workspace tests
- workspace constraints

### Task pack

Use for:

- bounded handoff packet to another agent or surface
- transfer of verified, relevant workspace context

Source of truth for:

- one handoff event

Not the source of truth for:

- the ongoing objective

### Sessions and artifacts

Use for:

- raw evidence
- transcripts
- imports
- repo artifacts
- attached references

Source of truth for:

- raw source material

## Ownership Rules

- The product spine owns architecture and system contracts.
- Holodeck owns active objective state for build work once an objective is accepted as active.
- Workboards own sparse coordination, not deep workspace truth.
- Task packs own handoff payloads, not durable project state.
- Sessions and artifacts own raw evidence, not normalized interpretation.

## When To Create A Holodeck

Create a Holodeck when all are true:

- the objective is bounded enough to name
- the work will span multiple steps, agents, or artifacts
- constraints or tests need to be tracked explicitly
- handoff quality matters

Do not create a Holodeck for:

- one-off architectural notes
- tiny self-contained edits
- speculative ideas that are not yet accepted as active work

## Binding Contract

Every active Holodeck linked to this product spine should declare:

- `workspace_id`
- owning subproject
- linked workboard id, if any
- linked source sessions
- linked task-pack ids
- primary artifact paths
- current maturation stage

## Sync Rules

- Product-level design changes update the spine first.
- Workspace execution changes update Holodeck first.
- Workboard summaries should be derived from workspace state, not invented independently.
- Task packs should be emitted from current workspace state whenever possible.
- Promotions from workspace-local knowledge to global memory must pass product gates.

## First Infrastructure Slice

The first active slice should be:

- one Holodeck for `Context Frames and Envelopes`
- one linked workboard or task packet for implementation coordination
- one linked session for bridge design evidence
- one materialized workspace view to prove the stack works end to end

## Active Bindings

| Subproject | Workspace ID | Workboard | Linked Session | Stage | Status |
|---|---|---|---|---|---|
| `Context Frames and Envelopes` | `sol-context-frames` | `semantic-operating-layer-context-frames` | `session-gpt-bridge-2026-04-24` | `developing` | active |
| `Frontend` (product element) | `sol-frontend` | `sol-frontend` | `26ef2474-c2bd-4dda-a4b1-7815b6df28cf` | `developing` | active |
| `Mobile Thought Capture` (subproject) | `sol-frontend` | `sol-frontend-mobile-capture` | `26ef2474-c2bd-4dda-a4b1-7815b6df28cf` | `developing` | active |

## Current Notes

- Materialized workspace views exist under [context/workspaces/sol-context-frames/brief.md](/Users/talhauddin/software/inner_space/context/workspaces/sol-context-frames/brief.md:1) and adjacent files.
- Frontend element workspace: [PILLARS.md](/Users/talhauddin/software/inner_space/docs/workboards/sol-frontend/PILLARS.md) is the binding decision spine; brief at [context/workspaces/sol-frontend/brief.md](/Users/talhauddin/software/inner_space/context/workspaces/sol-frontend/brief.md).
- Mobile Thought Capture subproject: [sol-frontend-mobile-capture](/Users/talhauddin/software/inner_space/docs/workboards/sol-frontend-mobile-capture/README.md) from conversation bundle `conv_20260627_125956_smooth-microgestures-on-mobile`.
- `holodeck task-pack` is currently blocked by codebase-atlas readiness, not by workspace structure.
