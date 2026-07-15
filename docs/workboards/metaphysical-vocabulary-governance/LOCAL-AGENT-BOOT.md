# Vocabulary Governance — Local Agent Boot

```bash
git fetch origin && git checkout main && git pull --ff-only origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context --workspace-id metaphysical-vocabulary-governance --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check --workspace-id metaphysical-vocabulary-governance
```

Then read workspace `README.md`, `derived/AGENT_BUILD_GUIDE.md`, `derived/VOCABULARY_OBLIGATION_REGISTER.md`, `derived/TASK_EXECUTION_MAP.md`, both dependency contracts, `GATES.md`, and live task context. VOCAB-001 must preserve raw language and branch context; do not add normalization behavior before the contract is locked.
