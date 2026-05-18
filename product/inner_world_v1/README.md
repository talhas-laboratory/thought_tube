# Inner World v1

Inner World v1 is built on top of the Conversation OS.

## Core product objects

- source item
- concept node
- connection
- reasoning primitive
- insight candidate
- surfaced insight
- feedback event

## Runtime surfaces

- thought feed: compact, tweet-like posts generated from surfaced insights
- archive: revisit every surfaced thought with lightweight filtering
- article expansion: longform explanation for a selected thought
- source drill-down: open any source fragment and trace related thoughts from it
- scoped thought chat: a thread grounded in the thought, source refs, and reasoning primitive
- saved thread embedding: saved thought chats are written back into the source library
- pluggable chat backend: heuristic fallback, `openclaw agent --local`, or gateway-backed `openclaw agent`

## Default output

Morning Batch of 3-5 ranked, evidence-backed insights, materialized as feed thoughts.

## Run the miniapp

From the repo root:

```bash
python3 tools/run_inner_world_miniapp.py
```

Or through the CLI:

```bash
python3 tools/conversation_os.py inner-world serve --domains research,art,entrepreneurship
```

For a backend service that also accepts the OpenClaw-hosted API prefix:

```bash
python3 tools/run_inner_world_backend.py
```

## Chat backend configuration

Copy `product/inner_world_v1/config/runtime.sample.json` to `product/inner_world_v1/config/runtime.json` and set:

- `chat_backend`: `heuristic`, `openclaw_local`, or `openclaw_gateway`
- `openclaw.agent`: agent id to target
- `openclaw.thinking`: OpenClaw thinking level
- `openclaw.timeout_seconds`: command timeout

Environment variables override the file:

- `INNER_WORLD_CHAT_BACKEND`
- `INNER_WORLD_OPENCLAW_AGENT`
- `INNER_WORLD_OPENCLAW_THINKING`
- `INNER_WORLD_OPENCLAW_TIMEOUT`

## World Studio visual embeddings

World Studio can embed image references plus notes into a shared visual retrieval layer.

Configure either:

- `~/.config/inner_space/world_studio_runtime.json`
- or `product/inner_world_v1/config/runtime.json`

with:

```json
{
  "world_studio": {
    "visual_embeddings": {
      "model": "google/gemini-embedding-2-preview",
      "api_key": "your-openrouter-key"
    }
  }
}
```

Environment overrides:

- `WORLD_STUDIO_OPENROUTER_API_KEY`
- `OPENROUTER_API_KEY`
- `WORLD_STUDIO_VISUAL_EMBEDDING_MODEL`

Core commands:

```bash
python3 tools/conversation_os.py world-studio ingest-visual-reference --world-id <world_id> --source-path ./ref.png --note "..."
python3 tools/conversation_os.py world-studio inspect-visual-world --world-id <world_id>
python3 tools/conversation_os.py world-studio compile-visual-context --world-id <world_id> --query-text "..."
```

Portable packs:

```bash
python3 tools/build_world_studio_portable_pack.py
python3 tools/build_world_studio_master_library.py
```

Outputs:

- `product/inner_world_v1/portable/world-studio-portable`
- `product/inner_world_v1/portable/world-studio-portable.zip`
- `product/inner_world_v1/portable/world-studio-master-library`
- `product/inner_world_v1/portable/world-studio-master-library.zip`

Current provider behavior:

- text embeddings work directly
- image+note embeddings depend on the provider being able to fetch the image
- if a local file or remote URL cannot be fetched by the provider, World Studio falls back to embedding the note text and records that fallback in the visual reference metadata

## OpenClaw miniapp packaging

Build the static OpenClaw bundle:

```bash
python3 tools/build_inner_world_openclaw_miniapp.py
```

Or install it directly into an OpenClaw apps root:

```bash
python3 tools/build_inner_world_openclaw_miniapp.py \
  --install-to ~/.openclaw/workspace/apps/miniapps
```

The build writes a static miniapp with:

- `app.json`
- `index.html`
- `styles.css`
- `app.js`
- `runtime-config.js`

The OpenClaw-hosted UI expects an API base like `/apps/api/inner-world`. The backend script already serves both:

- `/api/*`
- `/apps/api/inner-world/*`

So the deployment shape is:

1. run `python3 tools/run_inner_world_backend.py` on the server
2. copy/install the bundle into the OpenClaw miniapps root
3. expose the static UI under `/apps/inner-world/`
4. proxy `/apps/api/inner-world/*` to the backend service if the host is fronting requests
