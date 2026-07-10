# Continuity index

Agent-facing continuity artifacts for long Cursor threads that may be context-compressed.

| Session ID | Task pack ID | Transcript | Branch / PR |
|------------|--------------|------------|-------------|
| `cursor-mtsf-activation-thread-4f48` | `mtsf-activation-continuity-4f48` | [cursor-mtsf-activation-thread-2026-07-07.md](./cursor-mtsf-activation-thread-2026-07-07.md) | `cursor/mtsf-v1.1-amendment-4f48` PR [#3](https://github.com/talhas-laboratory/thought_tube/pull/3), `cursor/activation-graph-binding-4f48` PR [#4](https://github.com/talhas-laboratory/thought_tube/pull/4) |
| `cursor-unified-framework-synthesis-4f48` | — | [2026-07-10-unified-framework-synthesis.md](../plans/2026-07-10-unified-framework-synthesis.md) | `cursor/mtsf-semantic-substrate-g01-g05-4f48` PR [#7](https://github.com/talhas-laboratory/thought_tube/pull/7) |

## Resume commands

```bash
# Read the human transcript
cat docs/continuity/cursor-mtsf-activation-thread-2026-07-07.md

# Unified framework synthesis (pre-build canonical)
cat docs/plans/2026-07-10-unified-framework-synthesis.md

# Inspect captured session (local workspace; memory/ is gitignored)
cat memory/sessions/cursor-mtsf-activation-thread-4f48/manifest.json
cat memory/events/cursor-mtsf-activation-thread-4f48.jsonl

# Load handoff pack
cat docs/task_packs/mtsf-activation-continuity-4f48.md
```

## Current state (2026-07-10)

- Unified framework synthesis locked as pre-build canonical doc
- Covers: three-framework unification, Thought Trace, Inner Space Curator, community pipeline
- **Next:** lock schemas (ThoughtObject, ReasoningStep, ReasoningSignature) then build capture kernel

## Current state (2026-07-07)

- MTSF promotion pipeline + graph event log shipped (PR #3)
- Activation ↔ content graph binding shipped (PR #4)
- **Next agreed increments:** traversal router (`follow(intent=...)`), cross-session dedup (merge/alias/retract)
