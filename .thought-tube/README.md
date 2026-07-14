# Thought Tube bridge

Portable install pack for cross-platform agent steering.

## What this is

The Thought Tube bridge is a control plane that classifies each turn, writes a turn ledger, and produces binding steering guidance for any agent host (Cursor, Codex, Claude Code, or generic MCP clients).

## Quick start

1. From the repo root, verify the CLI:

```bash
python3 tools/bridge_prepare_turn.py --text "How should we wire bridge steering?" --json
```

2. Add the MCP server using the template for your host:

- [install-cursor.md](./install-cursor.md)
- [install-claude-code.md](./install-claude-code.md)
- [install-codex.md](./install-codex.md)
- [install-generic.md](./install-generic.md)

3. Copy [STEERING.md](./STEERING.md) into your host rules / `AGENTS.md` / `CLAUDE.md` as appropriate.

4. Optional: enable bridge agent classify in `product/inner_world_v1/config/runtime.json` or via `INNER_WORLD_BRIDGE_ENABLED=1`.

## Canonical entrypoints

| Entry | Use |
| --- | --- |
| `bridge_prepare_turn` MCP tool | Primary steering API for agents |
| `python3 tools/bridge_prepare_turn.py` | Hooks, scripts, CI, non-MCP hosts |
| `python3 tools/run_bridge_mcp.py` | stdio MCP server |
| `.thought-tube/latest-steering.md` | File-based steering injected by hooks |

## Reliability model

| Layer | Mechanism |
| --- | --- |
| Contract | [STEERING.md](./STEERING.md) in host rules |
| Tracking | `turn_ledger.jsonl` + `sessions/*.json` |
| Enforcement (Cursor) | `.cursor/hooks.json` + always-apply rule |
| Enforcement (other hosts) | hook or rule equivalent + CLI fallback |

MCP tools alone are advisory. Combine MCP with host hooks or rules for reliable per-turn steering.
