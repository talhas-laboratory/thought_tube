# Install: Cursor

## 1. MCP server

Merge `.thought-tube/mcp.cursor.json` into your Cursor MCP config, replacing `{{REPO_ROOT}}` with the absolute path to this repository.

Example Cursor MCP entry (use an **absolute** path — Cursor may ignore `cwd`):

```json
{
  "mcpServers": {
    "thought-tube-bridge": {
      "command": "python3",
      "args": ["/absolute/path/to/inner_space/tools/run_bridge_mcp.py"]
    }
  }
}
```

Start command manually to verify:

```bash
python3 tools/run_bridge_mcp.py
```

## 2. Project hooks (recommended)

This repo ships:

- `.cursor/hooks.json`
- `.cursor/hooks/bridge_session_start.py`
- `.cursor/hooks/bridge_prepare_turn.py`

Make hooks executable:

```bash
chmod +x .cursor/hooks/bridge_session_start.py .cursor/hooks/bridge_prepare_turn.py
```

Behavior:

- `sessionStart` — sets `THOUGHT_TUBE_SESSION_ID` and injects the steering contract
- `beforeSubmitPrompt` — runs `prepare_turn`, writes `.thought-tube/latest-steering.md`, appends turn ledger

## 3. Always-apply rule

The repo includes `.cursor/rules/thought-tube-bridge-steering.mdc`. Keep it enabled.

## 4. OpenClaw model (Moonshot / Kimi)

Register the API key in OpenClaw (never commit keys to the repo):

```bash
openclaw onboard --non-interactive --accept-risk \
  --auth-choice moonshot-api-key \
  --moonshot-api-key "$MOONSHOT_API_KEY" \
  --skip-channels --skip-skills --skip-ui --skip-daemon --no-install-daemon --skip-health
```

Provision the bridge agent model:

```bash
python3 tools/provision_bridge_openclaw_agent.py --model moonshot/kimi-k2.5 --json
```

Bridge defaults in `product/inner_world_v1/config/runtime.json`:

- `bridge.model`: `moonshot/kimi-k2.5`
- `bridge.openclaw_mode`: `auto` (uses `--local` when gateway is down)

## 5. Optional agent classify

```bash
export INNER_WORLD_BRIDGE_ENABLED=1
```

Or set `bridge.enabled: true` in `product/inner_world_v1/config/runtime.json`.

## 5. Verify

```bash
python3 tools/bridge_prepare_turn.py --text "smoke test" --surface cursor --json
```

Then submit a prompt in Cursor and confirm `.thought-tube/latest-steering.md` updates.
