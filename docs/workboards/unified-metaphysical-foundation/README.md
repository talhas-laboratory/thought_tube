# Unified Metaphysical Foundation

Purpose: coordinate multi-agent work with sparse, reliable task state, decision history, and mandatory completion gates.

Board id: `unified-metaphysical-foundation`
Owner: `talha`
Created: `2026-07-12T14:18:38.440398+00:00`

Canonical workspace: [`docs/workspaces/unified-framework-synthesis/README.md`](../../workspaces/unified-framework-synthesis/README.md)  
Normative framework: [`Thought Tube Unified Metaphysical Modeling Framework v1.1`](../../workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)  
Foundation build plan: [`derived/foundation-build-plan.md`](../../workspaces/unified-framework-synthesis/derived/foundation-build-plan.md)
Live workspace id: `unified-framework-synthesis`  
**Universal workspace rules:** [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../workspaces/WORKSPACE-AGENT-PROTOCOL.md)

## Agent Start Protocol

0. **Fresh local agent:** read [`LOCAL-AGENT-BOOT.md`](./LOCAL-AGENT-BOOT.md) first. Run `git fetch origin && git pull origin main` before searching for any board doc.
1. Query live workspace (`workspace_coordination.py context`) and run `workspace_projection_sync.py check`.
2. Read `README.md`, `REVIEWER-START.md`, `GAP-REPORT-2026-07-12.md`, `TASKS.md`, `GATES.md`, `DECISIONS.md`, and latest `UPDATES.jsonl`.
3. Claim one task via the **live workspace API**; do not hand-edit `Status:` in task files.
4. Work only inside the task scope unless the board owner expands it.
5. Record decisions and verification in the live workspace service.
6. After live mutations, run `workspace_projection_sync.py publish` before handoff or commit.
7. Cite governing framework sections and invariants in every implementation task.

## Board Shape

- `LOCAL-AGENT-BOOT.md`: **start here for a fresh local agent** (find workspace, gaps, close-out checklist)
- `TASKS.md`: board index and task status
- `GAP-REPORT-2026-07-12.md`: blocking audit findings and worker repair sequence
- `GAP-2-RECONCILIATION.md`: live workspace ledger reconciliation commands
- `PHASE-1-IMPLEMENTATION-REVIEW.md`: architecture, invariants, checklist
- `REVIEWER-START.md`: fast path for reviewers (`foundation review` + reading order)
- `TOOLS.md`: CLI and verification commands (`conversation_os.py foundation …`)
- `lanes/`: Asana/Jira-style task lanes
- `tasks/`: one durable task packet per work item
- `GATES.md`: mandatory requirements and verification gates
- `DECISIONS.md`: Confluence-style decision log
- `UPDATES.jsonl`: append-only activity feed
- `HANDOFFS.md`: transfer notes between agents
- `AGENTS.md`: agent operating rules for this board
- `artifacts/`: plans, outputs, screenshots, logs, generated files
- `inbox/`: untriaged notes, imported context, pending requests
