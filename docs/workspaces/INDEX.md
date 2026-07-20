# Agent Workspaces Index

Git-tracked working spaces for long design threads. These are continuity projections backed by a live workspace service for coordination state.

**Mandatory protocol:** [`WORKSPACE-AGENT-PROTOCOL.md`](./WORKSPACE-AGENT-PROTOCOL.md)  
**Foreign agents:** [`docs/cross-agent/README.md`](../cross-agent/README.md)

| Workspace ID | Status | Entry | Manifest |
|--------------|--------|-------|----------|
| `shape-intelligence-normalization` | Active — deterministic information normalization | [`shape-intelligence-normalization/README.md`](./shape-intelligence-normalization/README.md) | [`manifest.json`](./shape-intelligence-normalization/manifest.json) |
| `shape-intelligence-evidence` | Active — bounded evidence assembly | [`shape-intelligence-evidence/README.md`](./shape-intelligence-evidence/README.md) | [`manifest.json`](./shape-intelligence-evidence/manifest.json) |
| `shape-intelligence-interpretation` | Active — provisional Shape proposal intelligence | [`shape-intelligence-interpretation/README.md`](./shape-intelligence-interpretation/README.md) | [`manifest.json`](./shape-intelligence-interpretation/manifest.json) |
| `shape-intelligence-critique` | Active — independent critique and synthesis | [`shape-intelligence-critique/README.md`](./shape-intelligence-critique/README.md) | [`manifest.json`](./shape-intelligence-critique/manifest.json) |
| `shape-intelligence-governance` | Active — deterministic candidate validation and operations | [`shape-intelligence-governance/README.md`](./shape-intelligence-governance/README.md) | [`manifest.json`](./shape-intelligence-governance/manifest.json) |
| `shape-intelligence-evaluation-promotion` | Active — evaluation and governed promotion | [`shape-intelligence-evaluation-promotion/README.md`](./shape-intelligence-evaluation-promotion/README.md) | [`manifest.json`](./shape-intelligence-evaluation-promotion/manifest.json) |
| `shape-intelligence-population` | Active — governed interpretative Shape-candidate population | [`shape-intelligence-population/README.md`](./shape-intelligence-population/README.md) | [`manifest.json`](./shape-intelligence-population/manifest.json) |
| `cognitive-aperture-exceptional` | Active — good→exceptional disclosure/aperture hardening | [`cognitive-aperture-exceptional/README.md`](./cognitive-aperture-exceptional/README.md) | [`manifest.json`](./cognitive-aperture-exceptional/manifest.json) |
| `holodeck-productization` | Active — local-first product discovery | [`holodeck-productization/README.md`](./holodeck-productization/README.md) | [`manifest.json`](./holodeck-productization/manifest.json) |
| `unified-framework-synthesis` | Active — canonical foundation and schema lock | [`unified-framework-synthesis/README.md`](./unified-framework-synthesis/README.md) | [`manifest.json`](./unified-framework-synthesis/manifest.json) |
| `metaphysical-kernel-ontology` | Active — kernel contract lock | [`metaphysical-kernel-ontology/README.md`](./metaphysical-kernel-ontology/README.md) | [`manifest.json`](./metaphysical-kernel-ontology/manifest.json) |
| `metaphysical-branch-reasoning` | Active — branch semantic authority | [`metaphysical-branch-reasoning/README.md`](./metaphysical-branch-reasoning/README.md) | [`manifest.json`](./metaphysical-branch-reasoning/manifest.json) |
| `metaphysical-vocabulary-governance` | Active — vocabulary semantic authority | [`metaphysical-vocabulary-governance/README.md`](./metaphysical-vocabulary-governance/README.md) | [`manifest.json`](./metaphysical-vocabulary-governance/manifest.json) |

## Boot sequence

```bash
git fetch origin && git checkout main && git pull origin main
source ~/.config/inner-space-workspace.env 2>/dev/null || true

python3 tools/workspace_coordination.py context \
  --workspace-id unified-framework-synthesis \
  --agent-id <agent> --surface <surface> --session-id <session>

python3 tools/workspace_projection_sync.py check --workspace-id unified-framework-synthesis
# if not fresh:
python3 tools/workspace_projection_sync.py publish --workspace-id unified-framework-synthesis

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
