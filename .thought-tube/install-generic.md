# Install: generic MCP host

## Requirements

- Python 3.11+
- Repository checkout with `src/conversation_os`
- Optional vendored MCP SDK at `.vendor/mcp_py`

## MCP stdio server

```bash
python3 tools/run_bridge_mcp.py
```

Configure your host to launch that command with `cwd` set to the repository root.

## Primary tool

Call **`bridge_prepare_turn`** before substantive reasoning.

Inputs:

- `raw_text` (required)
- `session_id` (recommended)
- `workspace_id` (optional)
- `surface` (host name)

Outputs:

- `steering_markdown` — binding guidance
- `control_packet` — structured summary
- `context_policy` — budgets
- `steering_file` — `.thought-tube/latest-steering.md`

## CLI equivalent

```bash
python3 tools/bridge_prepare_turn.py --text "..." --session-id "..." --surface mcp --json
```

## Host rules

Install `.thought-tube/STEERING.md` into whatever rules file your host reads.

## Other tools

- `bridge_inspect_request`
- `bridge_list_control_packets`
- `bridge_list_behaviors`
- `bridge_get_config`
- `bridge_classify_preview`
- `bridge_run`

## Environment overrides

- `INNER_WORLD_BRIDGE_ENABLED=1`
- `INNER_WORLD_BRIDGE_AGENT=thought_tube_router`
- `INNER_WORLD_BRIDGE_EXECUTION_MODE=operators`
