# Personal Cognitive Exoskeleton

Purpose: coordinate multi-agent work with sparse, reliable task state, decision history, and mandatory completion gates.

Board id: `personal-cognitive-exoskeleton`
Owner: `talha`
Created: `2026-07-21T21:45:10.883142+00:00`

## Agent Start Protocol

1. Read [`../../workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../workspaces/WORKSPACE-AGENT-PROTOCOL.md), then query the live workspace before trusting task status.
2. Read `README.md`, `TASKS.md`, `GATES.md`, `DECISIONS.md`, and the latest entries in `UPDATES.jsonl`.
2. Claim one task by editing its task file and adding an update row.
3. Work only inside the task scope unless the board owner expands it.
4. Record decisions before relying on them.
5. Attach verification evidence before moving a task to `review` or `done`.

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
