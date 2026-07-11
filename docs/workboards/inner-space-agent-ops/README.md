# Inner Space Agent Ops

Purpose: coordinate multi-agent work with sparse, reliable task state, decision history, and mandatory completion gates.

Board id: `inner-space-agent-ops`
Owner: `talha`
Created: `2026-06-26T16:26:32.167234+00:00`

## Agent Start Protocol

1. Read `README.md`, `TASKS.md`, `GATES.md`, `DECISIONS.md`, and the latest entries in `UPDATES.jsonl`.
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

## Self-Improvement Packet Intake

Self-improvement packets enter through `inbox/` and must be triaged before they become tasks.

Packet creation:

```bash
python3 tools/self_improvement_packet.py create \
  --text "The bridge should not leak sidecar context." \
  --session-id bridge-session-inner-space-codex-deploy-audit \
  --turn-id bridge-turn-example
```

Triage rules:

- `low` and `medium` risk packets may become normal board tasks.
- `high` risk packets require acceptance criteria, tests, and rollback notes before work starts.
- `critical` risk packets require an explicit decision record before implementation.
