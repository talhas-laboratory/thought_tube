# Agent Workspaces Index

Git-tracked working spaces for long design threads. These are continuity projections backed by a live workspace service for coordination state.

**Foreign agents:** start at [`docs/cross-agent/README.md`](../cross-agent/README.md).

| Workspace ID | Status | Entry | Manifest |
|--------------|--------|-------|----------|
| `unified-framework-synthesis` | Active — canonical foundation and schema lock | [`unified-framework-synthesis/README.md`](./unified-framework-synthesis/README.md) | [`manifest.json`](./unified-framework-synthesis/manifest.json) |

## Boot sequence

```bash
python3 tools/workspace_coordination.py status --workspace-id unified-framework-synthesis
python3 tools/workspace_coordination.py context --workspace-id unified-framework-synthesis --agent-id <agent> --surface <surface> --session-id <session>
cat docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md
cat docs/workspaces/unified-framework-synthesis/derived/handoff.md
cat docs/workspaces/unified-framework-synthesis/CONTINUITY.md
```

## Related surfaces

| Surface | Path |
|---------|------|
| Continuity registry | [`docs/continuity/INDEX.md`](../continuity/INDEX.md) |
| Task packs | [`docs/task_packs/`](../task_packs/) |
| Framework sources | [`docs/frameworks/`](../frameworks/) |
| Canonical framework | [`unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](./unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md) |
| Foundation build plan | [`unified-framework-synthesis/derived/foundation-build-plan.md`](./unified-framework-synthesis/derived/foundation-build-plan.md) |
