# Branch Reasoning — Local Agent Boot

```bash
git fetch origin && git checkout main && git pull --ff-only origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context --workspace-id metaphysical-branch-reasoning --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check --workspace-id metaphysical-branch-reasoning
```

Then read workspace `README.md`, `derived/AGENT_BUILD_GUIDE.md`, `derived/BRANCH_OBLIGATION_REGISTER.md`, `derived/TASK_EXECUTION_MAP.md`, the Kernel dependency contract, `GATES.md`, and live task context. BRANCH-001 is specification work; do not create a runtime owner before the contract and engineering guard are ready.
