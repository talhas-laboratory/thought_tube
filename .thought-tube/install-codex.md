# Install: Codex

## 1. MCP server

Add the server from `.thought-tube/mcp.codex.json` to your Codex MCP configuration, replacing `{{REPO_ROOT}}` with this repository path.

## 2. Steering contract

Copy `.thought-tube/STEERING.md` into the project agent instructions (`AGENTS.md` or Codex-specific rules).

## 3. CLI fallback

When MCP is unavailable, run before each substantive turn:

```bash
python3 tools/bridge_prepare_turn.py --text "<user message>" --session-id "<session>" --surface codex --json
```

## 4. File-based steering

Read `.thought-tube/latest-steering.md` after prepare_turn runs.

## 5. Verify

```bash
python3 tools/bridge_prepare_turn.py --text "smoke test" --surface codex --json
```
