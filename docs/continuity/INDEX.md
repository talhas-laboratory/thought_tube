# Continuity index

Agent-facing continuity artifacts for long Cursor threads that may be context-compressed.

**Foreign agents:** start at [`docs/cross-agent/README.md`](../cross-agent/README.md).

| Session ID | Task pack ID | Transcript | Branch / PR |
|------------|--------------|------------|-------------|
| `cursor-mtsf-activation-thread-4f48` | `mtsf-activation-continuity-4f48` | [cursor-mtsf-activation-thread-2026-07-07.md](./cursor-mtsf-activation-thread-2026-07-07.md) | `cursor/mtsf-v1.1-amendment-4f48` PR [#3](https://github.com/talhas-laboratory/thought_tube/pull/3), `cursor/activation-graph-binding-4f48` PR [#4](https://github.com/talhas-laboratory/thought_tube/pull/4) |
| `cursor-unified-framework-synthesis-4f48` | `unified-framework-continuity-4f48` | [cursor-unified-framework-synthesis-2026-07-10.md](./cursor-unified-framework-synthesis-2026-07-10.md) | `cursor/mtsf-semantic-substrate-g01-g05-4f48` PR [#7](https://github.com/talhas-laboratory/thought_tube/pull/7) |

## Resume commands

```bash
# Foreign agent boot
cat docs/cross-agent/README.md

# Unified framework thread (this conversation)
cat docs/continuity/cursor-unified-framework-synthesis-2026-07-10.md
cat docs/task_packs/unified-framework-continuity-4f48.md
cat docs/plans/2026-07-10-unified-framework-synthesis.md

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

- Cross-agent workspace established: `docs/cross-agent/README.md`
- Full transcript captured for unified framework synthesis thread
- Task pack: `unified-framework-continuity-4f48`
- **Next:** rearrange decomposed primitives → lock schemas → capture kernel

## Current state (2026-07-07)

- MTSF promotion pipeline + graph event log shipped (PR #3)
- Activation ↔ content graph binding shipped (PR #4)
- **Next agreed increments:** traversal router (`follow(intent=...)`), cross-session dedup (merge/alias/retract)
