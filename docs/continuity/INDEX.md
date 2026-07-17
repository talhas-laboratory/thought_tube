# Continuity index

Agent-facing continuity artifacts for long Cursor threads that may be context-compressed.

**Foreign agents:** start at [`docs/cross-agent/README.md`](../cross-agent/README.md).

| Session ID | Workspace | Task pack ID | Transcript | Branch / PR |
|------------|-----------|--------------|------------|-------------|
| `cursor-cognitive-aperture-exceptional-24c7` | [**full workspace**](../workspaces/cognitive-aperture-exceptional/README.md) | — (gap map authority) | [thread synthesis](../workspaces/cognitive-aperture-exceptional/analyses/2026-07-17-thread-synthesis.md) | branch `cursor/cognitive-aperture-gap-map-24c7` |
| `cursor-unified-framework-synthesis-4f48` | [**full workspace**](../workspaces/unified-framework-synthesis/README.md) | `unified-framework-continuity-4f48` | [thread + analyses](../workspaces/unified-framework-synthesis/continuity/thread-transcript.md) | PR [#7](https://github.com/talhas-laboratory/thought_tube/pull/7) |
| `cursor-mtsf-activation-thread-4f48` | — | `mtsf-activation-continuity-4f48` | [cursor-mtsf-activation-thread-2026-07-07.md](./cursor-mtsf-activation-thread-2026-07-07.md) | PR [#3](https://github.com/talhas-laboratory/thought_tube/pull/3), [#4](https://github.com/talhas-laboratory/thought_tube/pull/4) |

## Resume commands

```bash
# Foreign agent boot
cat docs/cross-agent/README.md

# Unified framework thread — FULL workspace (sources + analyses)
cat docs/workspaces/unified-framework-synthesis/README.md
cat docs/workspaces/unified-framework-synthesis/derived/handoff.md
cat docs/workspaces/unified-framework-synthesis/analyses/framework-primitive-decomposition.md

# MTSF activation thread (earlier)
cat docs/continuity/cursor-mtsf-activation-thread-2026-07-07.md
cat docs/task_packs/mtsf-activation-continuity-4f48.md

# Machine replay (local; memory/ is gitignored)
python3 tools/conversation_os.py session import \
  --source-path docs/continuity/cursor-unified-framework-synthesis-2026-07-10.md \
  --session-id cursor-unified-framework-synthesis-4f48 \
  --title "Unified framework synthesis thread" \
  --task-id unified-framework-continuity-4f48 \
  --domains research,structure,product \
  --mtsf-mode deep
```

## Current state (2026-07-10)

- **Agent workspace:** `docs/workspaces/unified-framework-synthesis/` (sources, 8 analyses, continuity, manifest)
- Source docs in repo: SDS, ThoughtShape, MTSF tree
- Holodeck workspace: `unified-framework-synthesis-4f48` (local machine)
- Cross-agent boot: `docs/cross-agent/README.md`
- **Next:** rearrange decomposed primitives → lock schemas → capture kernel

## Current state (2026-07-07)

- MTSF promotion pipeline + graph event log shipped (PR #3)
- Activation ↔ content graph binding shipped (PR #4)
- **Next agreed increments:** traversal router (`follow(intent=...)`), cross-session dedup (merge/alias/retract)
