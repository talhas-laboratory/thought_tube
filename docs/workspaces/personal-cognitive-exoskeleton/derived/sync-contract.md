# Workspace Sync Contract

Workspace ID: `personal-cognitive-exoskeleton`

- Semantic authority: [Personal Cognitive Exoskeleton Lens](../sources/PERSONAL_COGNITIVE_EXOSKELETON_LENS.md) and the canonical Unified Framework v1.1 source.
- Coordination authority: live workspace service at `INNER_WORLD_WORKSPACE_API_BASE`.
- Git projection: this workspace and [`docs/workboards/personal-cognitive-exoskeleton/`](../../../workboards/personal-cognitive-exoskeleton/).

## Rules

1. Query the live workspace before task-scoped work.
2. Write task status, decisions, blockers, and verification through the live API only.
3. After every live coordination mutation, publish projections and run the freshness check.
4. Commit and push the semantic artifacts and projections so cloud agents read the same context.

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id personal-cognitive-exoskeleton \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check \
  --workspace-id personal-cognitive-exoskeleton
```

Universal protocol: [Workspace Agent Protocol](../../WORKSPACE-AGENT-PROTOCOL.md).
