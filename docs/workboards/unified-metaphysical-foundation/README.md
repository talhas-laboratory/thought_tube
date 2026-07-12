# Unified Metaphysical Foundation

Purpose: coordinate multi-agent work with sparse, reliable task state, decision history, and mandatory completion gates.

Board id: `unified-metaphysical-foundation`
Owner: `talha`
Created: `2026-07-12T14:18:38.440398+00:00`

Canonical workspace: [`docs/workspaces/unified-framework-synthesis/README.md`](../../workspaces/unified-framework-synthesis/README.md)  
Normative framework: [`Thought Tube Unified Metaphysical Modeling Framework v1.1`](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)  
Foundation build plan: [`derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md)
Live workspace id: `unified-framework-synthesis`

## Agent Start Protocol

1. Read `README.md`, `TASKS.md`, `GATES.md`, `DECISIONS.md`, and the latest entries in `UPDATES.jsonl`.
2. Claim one task by editing its task file and adding an update row.
3. Work only inside the task scope unless the board owner expands it.
4. Record decisions before relying on them.
5. Attach verification evidence before moving a task to `review` or `done`.
6. Cite the governing framework sections and invariants in every implementation task.
7. Record coordination changes in the live workspace service before treating the board as current.

## Board Shape

- `TASKS.md`: board index and task status
- `lanes/`: Asana/Jira-style task lanes
- `tasks/`: one durable task packet per work item
- `GATES.md`: mandatory requirements and verification gates
- `DECISIONS.md`: Confluence-style decision log
- `UPDATES.jsonl`: append-only activity feed
- `HANDOFFS.md`: transfer notes between agents
- `AGENTS.md`: agent operating rules for this board
- `artifacts/`: plans, outputs, screenshots, logs, generated files
- `inbox/`: untriaged notes, imported context, pending requests
