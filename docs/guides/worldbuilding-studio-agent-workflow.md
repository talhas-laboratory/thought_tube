# Worldbuilding Studio Agent Workflow

Use the Worldbuilding Studio when the goal is to create, deepen, or operationalize a fictional world for later scene generation.

## What It Is

The system treats world knowledge as an explicit world OS instead of a one-shot questionnaire or a hidden prompt memory. Inputs land in:

- source evidence
- evidence-backed world records
- inferred cross-layer connections
- canon assets
- the refreshed world snapshot used by scene compilation

That means later scenes can reuse the same primitives, places, objects, rules, visual tone, canon references, and relationships without re-asking for everything.

## Fastest Entry Points

Browser:

- `/world-studio.html`
- The browser client is a conversation-first spatial canvas. The center graph is the live world surface, the lower dock is the current prompt, and the right inspector shows what any selected node means.

CLI:

- `python3 tools/conversation_os.py world-studio guide`
- `python3 tools/conversation_os.py world-studio ingest-evidence --world-id <world_id> --source-text "..."`
- `python3 tools/conversation_os.py world-studio next-question --world-id <world_id>`
- `python3 tools/conversation_os.py world-studio inspect-evidence --world-id <world_id>`
- `python3 tools/conversation_os.py world-studio generate-canon --world-id <world_id>`
- `python3 tools/conversation_os.py world-studio compile-scene-from-canon --world-id <world_id> --scene-text "..."`
- `python3 tools/conversation_os.py world-studio execute-packet --packet-id <packet_id> --mode auto`
- `python3 tools/conversation_os.py world-studio executions --packet-id <packet_id>`
- `python3 tools/conversation_os.py world-studio populate-start --name "Your World" --summary "Optional summary"`
- `python3 tools/conversation_os.py world-studio populate-answer --session-id <session_id> --answer "..."`
- `python3 tools/conversation_os.py world-studio population-session --session-id <session_id>`
- `python3 tools/conversation_os.py world-studio inspect-knowledge --world-id <world_id>`
- `python3 tools/conversation_os.py world-studio inspect-graph --world-id <world_id>`
- `python3 tools/conversation_os.py world-studio compile-scene --world-id <world_id> --scene-text "..."`

API:

- `GET /api/world-studio/guide`
- `POST /api/world-studio/ingest-evidence`
- `GET /api/world-studio/world/<world_id>/next-question`
- `GET /api/world-studio/world/<world_id>/evidence`
- `POST /api/world-studio/generate-canon`
- `POST /api/world-studio/compile-scene-from-canon`
- `POST /api/world-studio/execute-packet`
- `GET /api/world-studio/executions`
- `POST /api/world-studio/population/start`
- `POST /api/world-studio/population/answer`
- `GET /api/world-studio/population/session/<session_id>`
- `GET /api/world-studio/world/<world_id>/knowledge`
- `GET /api/world-studio/world/<world_id>/graph`
- `POST /api/world-studio/compile-scene`

## Recommended Agent Loop

1. Ingest freeform notes and still-image references as evidence.
2. Ask only the next question returned by the system.
3. After each answer or ingest, trust the refreshed world state rather than rebuilding your own separate summary.
4. Use `inspect-evidence` when you need provenance. Use `inspect-knowledge` for exact records, and `inspect-graph` for the projected node/edge state.
5. Keep going until the world is coherent enough for canon generation.
6. Generate canon before compiling scenes.
7. Compile scenes from canon, not from isolated ad hoc prompts.
8. Execute the prepared packet only after canon-backed scene compilation.

## What Good Looks Like

Before generating canon, the world should usually have:

- at least one active primitive or emotional core
- one anchor character
- one anchor place
- one meaningful object
- one binding world rule
- one visual tone
- one active conflict
- at least one explicit or inferred relationship between layers

Before full scene generation, the world should also have:

- at least one canon asset
- visible provenance on the core records driving the scene
- no unresolved ambiguity about who, where, and what the scene depends on

## Operator Manuscript

Primary reference:

- `docs/guides/worldbuilding-studio-operator-manuscript.md`

## New Chat Prompt

Use this if a fresh agent needs to continue the workflow:

`Use the World Studio operator manuscript. Ingest user notes and still-image references as evidence, commit explicit world records with provenance, ask only the next high-value question, inspect evidence before making assumptions, generate canon references before full scenes, compile every scene from canon-backed world state, and execute only prepared canon-backed packets.`
