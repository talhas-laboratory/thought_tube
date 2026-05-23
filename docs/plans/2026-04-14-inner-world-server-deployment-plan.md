# Inner World Server Deployment Plan

## Goal

Deploy Inner World into the live OpenClaw workspace so it is available as:

- a static OpenClaw miniapp
- a local backend service behind the miniapps host
- a live repo inside the workspace that OpenClaw GPT can read through the existing GPT context service

## Canonical Live Paths

- OpenClaw workspace root:
  - `/home/talha/.openclaw/workspace`
- Inner World live repo:
  - `/home/talha/.openclaw/workspace/containers/inner-world`
- Inner World miniapp:
  - `/home/talha/.openclaw/workspace/apps/miniapps/inner-world`
- OpenClaw miniapps host:
  - `127.0.0.1:3010`
- Inner World backend:
  - `127.0.0.1:8422`
- OpenClaw GPT context service:
  - `127.0.0.1:8092`
- GPT public base URL:
  - `https://openclaw-gpt.talhaslaboratory.xyz`

## Required Outcomes

1. The repo is mirrored into the live workspace under `containers/inner-world`.
2. The static bundle is installed into `apps/miniapps/inner-world`.
3. The backend runs as a user-level systemd service.
4. The miniapps host proxies `/apps/api/inner-world/*` to the backend.
5. The miniapp loads from `/apps/inner-world/`.
6. The existing OpenClaw GPT can read the live repo because it already has workspace-bounded repo access.

## Step-by-Step Execution

### 1. Prepare the local bundle

- rebuild the static OpenClaw miniapp bundle
- confirm the bundle targets `/apps/api/inner-world`

Verification:

- bundle contains `index.html`, `styles.css`, `app.js`, `runtime-config.js`, and `app.json`

### 2. Mirror the repo into the workspace

- sync this repo into:
  - `/home/talha/.openclaw/workspace/containers/inner-world`
- exclude transient caches and oversized local-only artifacts

Verification:

- remote path exists
- `README.md`, `src/`, `product/`, `tools/`, and `docs/` are present

### 3. Install the miniapp

- copy the built static bundle into:
  - `/home/talha/.openclaw/workspace/apps/miniapps/inner-world`

Verification:

- `app.json` exists in the installed miniapp
- `runtime-config.js` points at `/apps/api/inner-world`

### 4. Install the backend service

- create a user-level unit:
  - `~/.config/systemd/user/inner-world.service`
- run:
  - `python3 tools/run_inner_world_backend.py --host 127.0.0.1 --port 8422 --skip-refresh-on-start`

Reason:

- the deployed repo already includes synced product state
- the service should bind quickly and serve that state immediately
- full graph refresh should be a deliberate maintenance action, not a boot-time requirement

Verification:

- `systemctl --user status inner-world.service`
- `curl http://127.0.0.1:8422/api/feed`

### 5. Patch the miniapps host

- add a reverse proxy route inside:
  - `/home/talha/.openclaw/workspace/apps/miniapps/_host/server.js`
- route:
  - `/apps/api/inner-world/*`
  - to `127.0.0.1:8422`

Verification:

- `curl http://127.0.0.1:3010/apps/api/inner-world/feed`

### 6. Restart the miniapps host

- restart:
  - `openclaw-miniapps.service`

Verification:

- `systemctl --user status openclaw-miniapps.service`
- `curl http://127.0.0.1:3010/apps/inner-world/`

### 7. Confirm GPT visibility

- verify the repo lives under the workspace root already used by the GPT context service
- no service change is required if the repo is deployed into that workspace

Verification:

- `GET /repo/file` can read:
  - `containers/inner-world/README.md`
  - `containers/inner-world/docs/plans/2026-04-14-inner-world-openclaw-server-architecture.md`

## Post-Deploy Verification Checklist

- the miniapp opens at `/apps/inner-world/`
- the feed loads
- a thought can expand into detail
- thread chat works
- the GPT context service can read the deployed docs

## Deployment Notes

- the miniapp host is the stable web surface
- the Inner World backend stays private on localhost
- the GPT context service remains the live repo access surface for GPT
- no direct filesystem exposure is added
