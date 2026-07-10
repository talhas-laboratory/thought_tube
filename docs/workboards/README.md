# Workboards

This directory is the project-local coordination surface for multi-agent work.

The canonical creator is the installed Codex skill:

- `~/.codex/skills/agent-work-board`

Use the repo-local wrapper to create a new board from this project root:

```bash
python3 tools/create_agent_work_board.py \
  --name "Inner Space Agent Ops" \
  --owner talha \
  --task "Define scope and acceptance criteria" \
  --task "Implement scoped changes" \
  --task "Verify and hand off"
```

Design intent:

- sparse but durable task state
- explicit gates before completion
- append-only update history
- clean handoff between agents
- modular task packets with verification evidence

Each board should keep its own:

- `README.md`
- `TASKS.md`
- `GATES.md`
- `DECISIONS.md`
- `HANDOFFS.md`
- `AGENTS.md`
- `UPDATES.jsonl`
- `tasks/`
- `artifacts/`
- `inbox/`
