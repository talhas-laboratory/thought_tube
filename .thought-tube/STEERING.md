# Thought Tube bridge steering contract

Apply this contract in Cursor rules, `AGENTS.md`, `CLAUDE.md`, Codex instructions, or any host-specific system prompt.

## Required workflow

Before any substantive reply:

1. Call `bridge_prepare_turn` (MCP) **or** run:

```bash
python3 tools/bridge_prepare_turn.py --text "<user message>" --session-id "<session>" --surface "<host>" --json
```

2. Read `.thought-tube/latest-steering.md` when working in this repository and a fresh steering file exists.

3. Treat `steering_markdown` as **binding control-plane guidance** for the current turn.

## Honor

- `context_policy` budgets (depth, layers, retrieval limits)
- `reasoning_posture` and `user_goal`
- `bridge_behavior_ids`
- `steering_constraints`

## Do not

- Request full corpus / ocean dumps
- Bypass policy to load unbounded context
- Make silent durable memory changes from a single turn
- Ignore steering without noting an explicit user override

## Surfaces

Use a stable `session_id` per conversation. Set `surface` to the host name:

- `cursor`
- `codex`
- `claude_code`
- `mcp`
- `cli`

## Optional tools

- `bridge_inspect_request` — debug a persisted turn
- `bridge_run` — full product spine when you need an executed answer, not just steering
- `bridge_list_control_packets` — recent control-plane history

## Failure behavior

If `bridge_prepare_turn` fails, continue with explicit caution, stay within narrow context, and say that steering was unavailable.
