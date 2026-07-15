# Kernel Ontology — Local Agent Boot

```bash
git fetch origin && git checkout main && git pull --ff-only origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context --workspace-id metaphysical-kernel-ontology --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check --workspace-id metaphysical-kernel-ontology
```

Then read, in order: workspace `README.md`, `derived/AGENT_BUILD_GUIDE.md`, `derived/KERNEL_OBLIGATION_REGISTER.md`, `derived/TASK_EXECUTION_MAP.md`, `GATES.md`, and the live task context. Claim only the current ready task. Before code, run the engineering guard against the smallest existing kernel owner module.

**Coordination outage (2026-07-15):** if `/health` or `context` fails, read [`derived/BLOCK-REPORT-2026-07-15.md`](../../workspaces/metaphysical-kernel-ontology/derived/BLOCK-REPORT-2026-07-15.md) and [`UMF-COORDINATION-RECONCILIATION-2026-07-15.md`](../unified-metaphysical-foundation/UMF-COORDINATION-RECONCILIATION-2026-07-15.md) before trusting `TASKS.md` status.
