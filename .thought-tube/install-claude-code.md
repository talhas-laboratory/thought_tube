# Install: Claude Code

## 1. MCP server

Add the server from `.thought-tube/mcp.claude-code.json` to your Claude Code MCP configuration, replacing `{{REPO_ROOT}}` with this repository path.

## 2. Steering contract

Add the contents of `.thought-tube/STEERING.md` to the project `CLAUDE.md` or your user instructions.

Minimum line to add:

> Before substantive replies, call `bridge_prepare_turn` and honor `steering_markdown`.

## 3. Per-prompt hook (recommended)

If your Claude Code setup supports a `UserPromptSubmit` or equivalent hook, call:

```bash
python3 tools/bridge_prepare_turn.py --text "$PROMPT" --session-id "$SESSION_ID" --surface claude_code --json
```

Then read `.thought-tube/latest-steering.md` before reasoning.

## 4. Session continuity

Pass a stable `session_id` across turns in the same conversation.

## 5. Verify

```bash
python3 tools/bridge_prepare_turn.py --text "smoke test" --surface claude_code --json
```
