# Personal Interface v1

Personal Interface v1 is a local-first outgoing-message layer built on top of the Conversation OS.

## Core loop

1. Run the guided calibration interview.
2. Persist an inspectable user profile.
3. Accept a host agent draft reply plus optional caller hints.
4. Infer the current flow mode and select rewrite tactics.
5. Rewrite the outgoing message through a local model backend.
6. Record lightweight explicit feedback to adjust tactic penalties.

## Product objects

- calibration session
- profile snapshot
- rewrite event
- rewrite feedback event
- policy snapshot

## CLI examples

Start calibration:

```bash
python3 tools/conversation_os.py personal-interface calibrate-start
```

Answer a calibration question:

```bash
python3 tools/conversation_os.py personal-interface calibrate-answer \
  --session-id personal-calibration-... \
  --answer "Short, direct, and non-interruptive."
```

Learn from a conversation transcript:

```bash
python3 tools/conversation_os.py personal-interface learn \
  --source-text "User: What does this concept mean?\nAssistant: ...\nUser: Give me a concrete example.\nAssistant: ...\nUser: How does that become code?"
```

Learn from a shared link or uploaded file:

```bash
python3 tools/conversation_os.py personal-interface learn \
  --source-url "https://example.com/shared-conversation"
```

```bash
python3 tools/conversation_os.py personal-interface learn \
  --source-path "/absolute/path/to/conversation.md"
```

Rewrite a draft reply:

```bash
python3 tools/conversation_os.py personal-interface rewrite \
  --draft-text "Long draft reply..." \
  --user-message "I am still exploring this."
```

Rewrite from a conversation payload:

```bash
python3 tools/conversation_os.py personal-interface rewrite-turn \
  --draft-text "Draft reply..." \
  --conversation-json '[{"role":"user","content":"I am thinking out loud about the product."},{"role":"assistant","content":"What part?"},{"role":"user","content":"I want a translation layer from abstract concepts into technical modules.","turn_id":"u-2"}]' \
  --caller-hints-json '{"goal":"translate_concepts_to_technical"}' \
  --client-context-json '{"conversation_id":"demo-conversation"}'
```

Run the MCP server:

```bash
python3 tools/run_personal_interface_mcp.py
```

## Recommended MCP trigger

For real conversations, prefer the `rewrite_conversation_turn` MCP tool over `rewrite_outgoing_message`.

It expects:
- `draft_text`: the host agent's raw reply before adaptation
- `conversation`: recent turns as `{role, content}` items, plus optional `turn_id` and `timestamp`
- `caller_hints`: optional per-turn hints such as `goal`
- `client_context`: optional transport metadata such as `conversation_id`

It derives:
- the latest user message
- a bounded recent conversation window
- base client context such as `latest_user_turn_id` and `conversation_turn_count`

This is the cleanest trigger surface for wiring the personal interface into a host chat loop because the client only needs to send the conversation turns and draft reply.

## Learning mode

The personal interface can also learn how the user asks questions during learning conversations.

Use `ingest_learning_conversation` or `personal-interface learn` to analyze:
- question path
- example requests
- follow-up preferences
- whether the user tends to move from concept -> example -> implementation

The derived signals are saved back into the profile under `learning_preferences.learned_from_conversations`.

When the host sets `caller_hints.goal = "teach_user"`, the rewrite policy will use those saved learning signals to shape the explanation path and the follow-up portion of the answer.

## Runtime configuration

Create `product/personal_interface_v1/data/runtime.json` with a rewrite backend. Example:

```json
{
  "rewrite_backend": {
    "id": "openclaw_local",
    "agent": "main",
    "thinking": "minimal",
    "timeout_seconds": 60
  }
}
```

For local testing, `command_json` backends can read a JSON payload from stdin and return:

```json
{
  "adapted_text": "Rewritten reply",
  "backend_metadata": {
    "model": "local-test"
  }
}
```
