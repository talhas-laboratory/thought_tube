# AGENTS

This repo is a Conversation OS. Treat conversations as substrate, not as disposable chat.

## Default workflow

1. Start or identify a session.
2. Append every meaningful user or agent turn as an event.
3. Checkpoint when you need a stable artifact boundary.
4. Close the session to trigger transcript generation, analysis, materialization, and index refresh.
5. Build a task pack before handing work to another agent or starting a new focused thread.

## Required discipline

- Always write clean, efficient code that serves a clear purpose.
- Before generating code, explicitly question whether the code is necessary, whether an existing owner module already fits, and what the smallest useful change is.
- Do not edit raw event logs.
- Do not collapse source and derived layers into one file.
- Do not add domain-specific branching into core capture or routing modules.
- Always prefer task packs over archive dumps when handing work off.
- Surface uncertainty explicitly in cards and insights.

## Engineering guard

Before implementation work, run the guard and do not proceed until it is ready:

- `python tools/conversation_os.py repo-overview refresh`
- `python tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "path/a.py,path/b.py"`

Guard expectations:

- The purpose must describe the concrete user or system effect, not a generic improvement.
- The proposed paths must name the smallest plausible edit surface.
- If the guard returns anything other than `ready`, narrow the scope or clarify the purpose before writing code.

## Codebase overview

Always keep the generated overview current before substantial changes:

- `python tools/conversation_os.py repo-overview refresh`
- `python tools/conversation_os.py repo-overview lookup --query "..."`

Primary overview artifacts:

- `context/substrate/CODEBASE_OVERVIEW.md`
- `context/substrate/codebase_map.json`

## Core commands

- `python tools/conversation_os.py init`
- `python tools/conversation_os.py repo-overview refresh`
- `python tools/conversation_os.py repo-overview lookup --query "..."`
- `python tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "..."`
- `python tools/conversation_os.py session start --title "..."`
- `python tools/conversation_os.py session append --session-id ... --actor user --kind request --content "..."`
- `python tools/conversation_os.py session checkpoint --session-id ...`
- `python tools/conversation_os.py session close --session-id ...`
- `python tools/conversation_os.py session import --source-path ... --title "..."`
- `python tools/conversation_os.py task-pack build --task-id ... --request "..."`
- `python tools/conversation_os.py inner-world batch --limit 5`

## World Studio

If the user wants to build or populate a fictional world, use the Worldbuilding Studio instead of inventing a one-off interview.

Primary references:

- `docs/guides/worldbuilding-studio-agent-workflow.md`
- `docs/guides/worldbuilding-studio-operator-manuscript.md`
- `src/conversation_os/worldbuilding_studio.py`

Primary commands:

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

Browser entry:

- `product/inner_world_v1/miniapp/world-studio.html`
- The browser client is a conversation-first spatial canvas. Use it when you want the human-facing worldbuilding flow instead of raw JSON.

Remote UI sync:

- Full server deploy: `python3 tools/deploy_inner_world_to_openclaw.py`
- UI-only push: `python3 tools/sync_inner_world_ui_to_openclaw.py`
- UI watch loop: `python3 tools/sync_inner_world_ui_to_openclaw.py --watch`
- Local tunnel for this machine: `python3 tools/tunnel_inner_world_openclaw.py`
- Use through the tunnel: `http://127.0.0.1:9310/apps/inner-world/`

Portable handoff pack:

- Build the disconnected UI pack with `python3 tools/build_world_studio_portable_pack.py`
- Generated folder: `product/inner_world_v1/portable/world-studio-portable`
- Generated zip: `product/inner_world_v1/portable/world-studio-portable.zip`
- Reimport only the real UI files unless the mock bridge changes are intentionally needed

Portable master library:

- Build the full system + experiment knowledge pack with `python3 tools/build_world_studio_master_library.py`
- Generated folder: `product/inner_world_v1/portable/world-studio-master-library`
- Generated zip: `product/inner_world_v1/portable/world-studio-master-library.zip`

Rule:

- Keep the agent inside the world OS loop. Ingest evidence first, ask the next returned question, preserve provenance on core records, generate canon before compiling scenes, and execute only canon-backed packets.

## Deployment Guide

Canonical deployment reference:

- `docs/guides/deployment-guide.md`

Use that guide for the full OpenClaw, backend, UI sync, portable pack, Personal Interface MCP, and GitHub publish/release procedures.

## Artifact lookup rule

- When a user asks to read, inspect, verify, or list mobile artifacts, treat the server-hosted `mobile_artifacts` directory as canonical before concluding the artifact is missing.
- Check the server path `/home/talha/.openclaw/workspace/containers/inner-world/mobile_artifacts` on `talha@192.168.0.102` first, then compare against the local repo copy only as a sync/status check.
- If server and local contents differ, say so explicitly and treat the server copy as the source of truth for the answer.

## Shared substrate library

- Agent-facing abstraction library:
  - `context/substrate/AGENT_INDEX.md`
- Machine registry:
  - `context/substrate/registry.json`
  - `context/substrate/browse_map.json`
- Source manifests and specs:
  - `context/substrate/families/*`
- Refresh or watch the generated browse indexes:
  - `python tools/substrate_index.py refresh`
  - `python tools/substrate_index.py watch`
- MTSF runtime system map (structure family): `context/substrate/generated/purpose/structure.mtsf.system-map.md`
- Per-module purpose artifacts: `context/substrate/generated/purpose/` and `context/substrate/generated/purpose-modules/`

## Handoff rule

If another agent should continue the work, build a task pack first and hand them:

- the task pack JSON
- the task pack markdown
- any directly relevant raw session refs

**Foreign agents (Codex, etc.):** start at `docs/cross-agent/README.md`, then read the full workspace at `docs/workspaces/unified-framework-synthesis/` (sources, analyses, continuity). See `docs/workspaces/INDEX.md` for all agent workspaces.

That handoff is the canonical continuity surface for this repo.

## Workspace coordination

When using the live workspace feature (any `workspace_id`):

**Read [`docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md`](docs/workspaces/WORKSPACE-AGENT-PROTOCOL.md) first.**

Summary:

1. **Live API** is coordination truth (task status, blockers, verification). **Git** is code truth. Workboard markdown is a **published mirror**.
2. **Boot:** `git pull` → query live API → `workspace_projection_sync.py check`
3. **After every live mutation:** `workspace_projection_sync.py publish` → commit → push
4. **Never** hand-edit `Status:` in `tasks/*.md` — sync from live instead
5. **Never** `git add -A` without checking staged file count (avoid mass-staging `runtime/`, `node_modules`)

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context --workspace-id <workspace-id> \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py publish --workspace-id <workspace-id>
python3 tools/workspace_projection_sync.py check --workspace-id <workspace-id>
```

## Cursor Cloud specific instructions

Pure-Python project (`requires-python >=3.11`, single runtime dependency `mcp`). There is no lint tooling configured and no JS/build step. The startup update script provisions a `.venv` with `mcp` and `pytest`; activate it before doing anything: `. .venv/bin/activate`.

- Do NOT `pip install -e .` (or otherwise put `src/` on `sys.path`). The CLI entrypoint `tools/conversation_os.py` shares the name of the `conversation_os` package, so having `src/` on the path makes the script shadow the package and fail with `'conversation_os' is not a package`. The scripts and `tests/conftest.py` already self-inject `src/` on the path, so only the dependencies need installing.
- `context/` substrate is git-ignored and NOT shipped; regenerate it before running tests or the app: `python3 tools/conversation_os.py init` (or `repo-overview refresh`). Without it, tests error out copying `context/substrate`.
- Tests: run `pytest` from the repo root. In this stripped-down public release ~302 tests pass; ~36 fail by design because they depend on hand-authored module manifests (`context/substrate/modules/*.json`) that are part of the excluded private substrate. Those failures are expected here, not an environment problem. Anything that builds a task pack is likewise blocked (`task_pack_index_not_ready`) because the codebase atlas has manifest warnings — e.g. `session close` only triggers a task pack when `--task-id` is passed, so omit it for a clean full session lifecycle.
- Run the app (Inner World miniapp backend): `python3 tools/run_inner_world_backend.py --host 127.0.0.1 --port 8421`. It serves both the static feed UI (`/`) and the API (`/api/*`, `/apps/api/inner-world/*`). On start it runs a pipeline refresh (can take ~15s); pass `--skip-refresh-on-start` to skip. With no ingested source corpus the feed returns `runtime_not_ready` and the UI shows zeroed counters — that is the empty-state, not a failure.

### Canonical workspace tailnet

The canonical workspace API (`INNER_WORLD_WORKSPACE_API_BASE`) lives on a private tailnet and is required by the always-applied canonical-workspace protocol. The startup update script bootstraps this automatically (needs the `TAILSCALE_AUTHKEY` and `INNER_WORLD_WORKSPACE_API_BASE` secrets), so on a fresh pod it should already be joined and `~/.config/inner-space-workspace.env` written.

- In this Firecracker VM, `tailscaled` must run in **userspace networking** mode; the default `sudo tailscale up` (tun mode) path in `tools/setup_cursor_tailnet.sh` fails on its own. The update script first starts `tailscaled --tun=userspace-networking --outbound-http-proxy-listen=localhost:1054 --socks5-server=localhost:1055` on the default socket, then runs the script.
- Userspace mode has no kernel route to tailnet nodes, so any command that must reach the workspace API needs the outbound proxy. Set it **only for those commands** (do NOT export globally, or normal internet egress like git/pip/apt breaks): `ALL_PROXY=socks5h://localhost:1055/ HTTPS_PROXY=http://localhost:1054/ HTTP_PROXY=http://localhost:1054/ curl "$INNER_WORLD_WORKSPACE_API_BASE/health"`.
- To re-bootstrap manually: `ALL_PROXY=socks5h://localhost:1055/ HTTPS_PROXY=http://localhost:1054/ HTTP_PROXY=http://localhost:1054/ bash tools/setup_cursor_tailnet.sh` (start the userspace `tailscaled` first if `pgrep -x tailscaled` is empty). Verify with `/health` (`{"status": "ok"}`) and `/api/workspaces`.
