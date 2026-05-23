# Inner World OpenClaw Runtime

## Runtime split

Inner World now runs as two pieces:

1. `Inner World backend`
   - Python service
   - owns feed generation, thought detail, feedback, and scoped thought chat
   - accepts both `/api/*` and `/apps/api/inner-world/*`

2. `OpenClaw miniapp`
   - static frontend bundle
   - served by the OpenClaw miniapps host under `/apps/inner-world/`
   - targets the backend through `runtime-config.js`

## Build commands

Run backend locally or on the server:

```bash
python3 tools/run_inner_world_backend.py
```

Build the OpenClaw bundle:

```bash
python3 tools/build_inner_world_openclaw_miniapp.py
```

Install directly into an apps root:

```bash
python3 tools/build_inner_world_openclaw_miniapp.py \
  --install-to ~/.openclaw/workspace/apps/miniapps
```

## OpenClaw server target

Based on the current server runbook:

- miniapps root: `/home/talha/.openclaw/workspace/apps/miniapps`
- miniapps host: `/home/talha/.openclaw/workspace/apps/miniapps/_host/server.js`
- miniapps URL prefix: `/apps`
- observed host port: `3010`
- gateway port: `18789`

## Recommended first deployment

1. Start the backend on the server:
   - `python3 tools/run_inner_world_backend.py --host 127.0.0.1 --port 8421`
2. Install the bundle into the miniapps root.
3. Ensure the OpenClaw host can reach:
   - `http://127.0.0.1:8421/apps/api/inner-world/feed`
4. Open the UI at:
   - `/apps/inner-world/`

## Proxy contract

If the host server proxies requests before they reach the backend, preserve this frontend contract:

- static app path: `/apps/inner-world/`
- API base: `/apps/api/inner-world`

The frontend bundle bakes the API base into `runtime-config.js`, so the UI does not need code changes between environments.
