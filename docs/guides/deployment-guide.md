# Deployment Guide

This is the canonical deployment runbook for Inner Space.

Use it when you need to:

- deploy the live OpenClaw runtime
- refresh only the miniapp UI
- run the backend locally
- expose the GPT bridge
- run the Personal Interface MCP service
- run the Bridge MCP service
- build portable Worldbuilding Studio handoff packs
- publish the repo to GitHub

If you are unsure which path to use, start with the deployment matrix below.

## Repository

- GitHub remote: `https://github.com/talhas-laboratory/thought_tube.git`
- Main repo root: `/Users/talhauddin/software/inner_space`
- Live OpenClaw workspace root: `/home/talha/.openclaw/workspace`
- Live repo path: `/home/talha/.openclaw/workspace/containers/inner-world`
- Live miniapp path: `/home/talha/.openclaw/workspace/apps/miniapps/inner-world`

## Deployment Matrix

| Target | Command | Use When |
| --- | --- | --- |
| Full OpenClaw deploy | `python3 tools/deploy_inner_world_to_openclaw.py` | The runtime, bundle, repo mirror, and host patches all need to stay in sync. |
| Thought Capture deploy | `python3 tools/deploy_thought_capture_pwa_to_openclaw.py` | Deploy the authenticated notes surface with bridge-governed OpenClaw replies. |
| OpenClaw deploy with GPT bridge | `python3 tools/deploy_inner_world_to_openclaw.py --with-gpt-bridge` | You need the live GPT bridge service, cloudflared config, and bridge validation. |
| UI-only sync | `python3 tools/sync_inner_world_ui_to_openclaw.py` | The backend is already correct and you only changed miniapp assets. |
| UI watch loop | `python3 tools/sync_inner_world_ui_to_openclaw.py --watch` | You want continuous UI updates during local iteration. |
| Backend runtime | `python3 tools/run_inner_world_backend.py` | You are running the backend locally or as a service target. |
| Backend GPT bridge mode | `python3 tools/run_inner_world_backend.py --mode gpt_bridge` | You need the GPT bridge HTTP surface instead of the app surface. |
| Local miniapp | `python3 tools/run_inner_world_miniapp.py` | You want to run the OpenClaw miniapp locally without the deploy wrapper. |
| Personal Interface MCP | `python3 tools/run_personal_interface_mcp.py` | You need the Personal Interface MCP server over stdio. |
| Bridge MCP | `python3 tools/run_bridge_mcp.py` | You need the bridge inspect/control-plane MCP server over stdio. |
| Portable Worldbuilding pack | `python3 tools/build_world_studio_portable_pack.py` | You need a disconnected miniapp handoff bundle. |
| Worldbuilding master library | `python3 tools/build_world_studio_master_library.py` | You need the full worldbuilding knowledge pack and supporting docs. |
| GitHub publish/release | `git push origin <branch>` and `gh pr create` / `gh release create` | You want to publish source, open review, or tag a release. |

## Preflight

Run these before any deployment or publish step:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
```

Then run the tests relevant to your change. For large changes, run the full surface suite for the area you touched.

Check the tree before you deploy:

```bash
git status --short
git diff --stat
```

If the atlas is stale or invalid, stop and fix that first. The repo now treats atlas freshness as part of deployment readiness.

## Versioned Releases And Rollback

Production deploys should be attached to a release manifest.

Create a candidate:

```bash
python3 tools/inner_world_release.py candidate --release-id inner-world-YYYYMMDDTHHMMSSZ
```

Deploy scripts now accept a release gate report and should use it for normal production promotion:

```bash
python3 tools/deploy_inner_world_to_openclaw.py \
  --release-gate-report product/inner_world_v1/releases/<release_id>/gate_report.json
```

```bash
python3 tools/deploy_thought_capture_pwa_to_openclaw.py \
  --release-gate-report product/inner_world_v1/releases/<release_id>/gate_report.json
```

You can bypass this only for explicit recovery work:

```bash
python3 tools/deploy_inner_world_to_openclaw.py --allow-ungated-deploy
```

Rollback planning:

```bash
python3 tools/inner_world_release.py rollback-plan \
  --current-release-id <current> \
  --previous-release-id <previous>
```

## Full OpenClaw Deploy

`tools/deploy_inner_world_to_openclaw.py` is the canonical runtime deployment entrypoint.

What it does:

- refreshes the codebase overview before syncing
- mirrors the repo into the live OpenClaw workspace
- builds the OpenClaw miniapp bundle
- installs the bundle into the live apps directory
- installs or refreshes the user-level systemd service
- patches the OpenClaw miniapps host for `/apps/api/inner-world/*`
- restarts the runtime services
- verifies the live feed and miniapp path

The script defaults to:

- remote host: `talha@192.168.0.102`
- live repo path: `/home/talha/.openclaw/workspace/containers/inner-world`
- live app path: `/home/talha/.openclaw/workspace/apps/miniapps/inner-world`
- backend port: `8422`

Typical execution:

```bash
python3 tools/deploy_inner_world_to_openclaw.py
```

Optional GPT bridge deployment:

```bash
python3 tools/deploy_inner_world_to_openclaw.py --with-gpt-bridge
```

Useful GPT bridge flags:

- `--gpt-bridge-port 8093`
- `--gpt-bridge-hostname inner-world-gpt.talhaslaboratory.xyz`
- `--gpt-bridge-action-key <key>`
- `--gpt-bridge-legacy-action-keys <comma-separated-keys>`
- `--gpt-bridge-artifact-root <path>`
- `--cloudflared-config /home/talha/.cloudflared/config.yml`
- `--cloudflared-tunnel-name klarorder-gpt`

If you use the GPT bridge path, the deploy script also:

- writes `~/.config/inner-world-gpt-bridge.env`
- installs `~/.config/systemd/user/inner-world-gpt-bridge.service`
- patches the cloudflared config for the GPT bridge hostname
- ensures DNS routing for the tunnel
- verifies the bridge health endpoints

Verification on the remote host:

```bash
systemctl --user is-active inner-world.service
systemctl --user is-active openclaw-miniapps.service
curl -fsS http://127.0.0.1:8422/api/feed
curl -fsS http://127.0.0.1:3010/apps/api/inner-world/feed
curl -fsS http://127.0.0.1:3010/apps/inner-world/
```

If the GPT bridge is enabled, also verify:

```bash
systemctl --user is-active inner-world-gpt-bridge.service
curl -fsS http://127.0.0.1:8093/health
curl -fsS -H "X-Inner-World-Action-Key: $INNER_WORLD_GPT_ACTION_KEY" http://127.0.0.1:8093/context/status-bundle
curl -fsS -H "X-Inner-World-Action-Key: $INNER_WORLD_GPT_ACTION_KEY" http://127.0.0.1:8093/sync/local-status
```

## UI-Only Sync

Use the UI-only path when the backend and runtime state are already correct and you only changed the miniapp assets.

```bash
python3 tools/sync_inner_world_ui_to_openclaw.py
```

Common options:

- `--watch` to keep syncing on file changes
- `--restart-miniapps` if you want the remote miniapps service restarted after each sync
- `--interval 0.8` to tune the watch cadence

This path updates the bundle under the live OpenClaw apps root without touching the backend service or the repo mirror.

Verification:

```bash
curl -fsS http://127.0.0.1:3010/apps/inner-world/
curl -fsS http://127.0.0.1:3010/apps/api/inner-world/feed
```

## Backend Runtime

`tools/run_inner_world_backend.py` is the backend entrypoint for both local use and service deployment.

Modes:

- `app` mode serves the backend and miniapp API surface
- `gpt_bridge` mode serves the GPT bridge HTTP surface

Typical app-mode run:

```bash
python3 tools/run_inner_world_backend.py --host 127.0.0.1 --port 8421
```

If you want a fast boot without refreshing the runtime on startup:

```bash
python3 tools/run_inner_world_backend.py --host 127.0.0.1 --port 8421 --skip-refresh-on-start
```

Useful flags:

- `--domains research,art,entrepreneurship`
- `--api-prefixes /api,/apps/api/inner-world`
- `--limit 12`

GPT bridge mode:

```bash
python3 tools/run_inner_world_backend.py --mode gpt_bridge --host 127.0.0.1 --port 8093
```

In bridge mode, the service uses:

- `INNER_WORLD_GPT_ACTION_KEY`
- `INNER_WORLD_GPT_LEGACY_ACTION_KEYS`
- `INNER_WORLD_GPT_PUBLIC_BASE_URL`
- `INNER_WORLD_GPT_ARTIFACT_ROOT`

## Personal Interface MCP

Run the Personal Interface MCP server when a toolchain needs the Personal Interface over stdio instead of via the main runtime.

```bash
python3 tools/run_personal_interface_mcp.py
```

This is a local service surface, not an OpenClaw deploy target. Use it when you want the MCP boundary to stay separate from the browser/runtime deployment path.

## Bridge MCP

Run the Bridge MCP server when a toolchain needs inspect-only access to the Thought Tube bridge control plane over stdio.

```bash
python3 tools/run_bridge_mcp.py
```

MCP tools:

- `bridge_prepare_turn` (primary steering entrypoint)
- `bridge_inspect_request`
- `bridge_list_control_packets`
- `bridge_list_behaviors`
- `bridge_get_config`
- `bridge_classify_preview`
- `bridge_run`

This is a local service surface, not an OpenClaw deploy target. Use it for debugging routing, control packets, and bridge configuration from Cursor or other MCP clients.

Portable install pack: `.thought-tube/README.md`

Per-turn steering CLI:

```bash
python3 tools/bridge_prepare_turn.py --text "user message" --surface cursor --json
```

## Local Miniapp

Use the local miniapp runner when you want to test the OpenClaw miniapp without the full remote deploy wrapper.

```bash
python3 tools/run_inner_world_miniapp.py
```

This runs the miniapp with:

- `domain_overlays=["research", "art", "entrepreneurship"]`
- `refresh_on_start=False`

Use the UI sync script instead if you want to deploy the bundle to the live OpenClaw workspace.

## Worldbuilding Studio Deployment

Worldbuilding has two deployment-style artifacts: a portable handoff pack and a master library pack.

### Portable Pack

Use this when you need a disconnected bundle that another agent can open without the full backend.

```bash
python3 tools/build_world_studio_portable_pack.py
```

Outputs:

- `artifacts/exports/inner_world_v1/portable/world-studio-portable`
- `artifacts/exports/inner_world_v1/portable/world-studio-portable.zip`

Use this when you want the miniapp slice plus handoff documents, not the full production backend.

### Master Library Pack

Use this when you need the full worldbuilding knowledge library for review, analysis, or handoff.

```bash
python3 tools/build_world_studio_master_library.py
```

Outputs:

- `artifacts/exports/inner_world_v1/portable/world-studio-master-library`
- `artifacts/exports/inner_world_v1/portable/world-studio-master-library.zip`

This pack includes the worldbuilding workflow, model behavior notes, and representative packet/execution artifacts.

## GitHub Publish And Release

GitHub is the source-control and release surface, not the runtime surface.

Use it when you want to publish a branch, request review, or pin a release:

```bash
git add -A
git commit -m "Describe the deployment or feature clearly"
git push origin <branch-name>
```

If you have the `gh` CLI:

```bash
gh pr create
gh release create v0.1.0
```

Release checklist:

- atlas refresh and validation are clean
- tests for the changed area pass
- the branch history is readable
- release notes describe what changed
- generated artifacts are attached or linked if they matter to the release

If you later automate publish flows, keep the workflow narrow and explicit under `.github/workflows/`, and never use GitHub Actions as a substitute for local validation.

## Handoff Checklist

Before you hand deployment work to another agent or close the session:

1. Refresh the atlas.
2. Validate the atlas.
3. Run the relevant tests.
4. Verify the target service or artifact.
5. Build a task pack if another agent must continue.
6. Link the exact artifact or deployment command used.

## Recovery And Rollback

### Canonical Workspace Service

The deployed multi-agent context layer uses one SQLite database and a localhost-only HTTP service. Install the samples after replacing the repository path or service user if the server differs:

```bash
install -m 0600 ops/systemd/inner-space-workspace.env.sample ~/.config/inner-space-workspace.env
install -m 0644 ops/systemd/inner-space-workspace.service.sample ~/.config/systemd/user/inner-space-workspace.service
install -m 0644 ops/systemd/inner-space-workspace-observer.service.sample ~/.config/systemd/user/inner-space-workspace-observer.service
systemctl --user daemon-reload
systemctl --user enable --now inner-space-workspace.service inner-space-workspace-observer.service
```

The service binds to `127.0.0.1:8765`. Keep it private; remote agent surfaces should reach it through the existing authenticated server boundary or a restricted reverse proxy.

Verify liveness, store integrity, and agent context:

```bash
curl --fail http://127.0.0.1:8765/health
curl --fail http://127.0.0.1:8765/ready
curl --fail 'http://127.0.0.1:8765/api/workspaces/inner-world/context?agent_id=operator&surface=server'
```

Set the same API base for Codex automation and the Telegram meta agent:

```bash
INNER_WORLD_WORKSPACE_API_BASE=http://127.0.0.1:8765/api
```

Create a consistent live backup before deployment or schema-affecting work:

```bash
python3 tools/backup_workspace_store.py \
  --source state/workspace.db \
  --output backups/workspace-pre-deploy.db
```

Restore only after stopping both writers. Restore automatically preserves the current target as a uniquely named pre-restore backup:

```bash
systemctl --user stop inner-space-workspace-observer.service inner-space-workspace.service
python3 tools/restore_workspace_store.py \
  --backup backups/workspace-pre-deploy.db \
  --target state/workspace.db
systemctl --user start inner-space-workspace.service inner-space-workspace-observer.service
curl --fail http://127.0.0.1:8765/ready
```

After restore, request `/context` and verify the expected task, decision, test, and repository revision before allowing agent mutations.

If a deployment fails:

1. Check the remote service state.
2. Inspect the last successful artifact or bundle.
3. Re-run the smallest safe step instead of the whole pipeline.
4. Only force a recompute if you know the derived artifacts are stale.

If the runtime was interrupted, resume from the last safe stage using the runtime rebuild flow in [docs/plans/2026-04-21-runtime-rebuild-runbook.md](../plans/2026-04-21-runtime-rebuild-runbook.md).

## Related References

- [AGENTS.md](/Users/talhauddin/software/inner_space/AGENTS.md)
- [GitHub Deployment Guide](github-deployment-guide.md)
- [Inner World Server Deployment Plan](../plans/2026-04-14-inner-world-server-deployment-plan.md)
- [Runtime Rebuild Runbook](../plans/2026-04-21-runtime-rebuild-runbook.md)

## Bottom Line

Use OpenClaw for runtime deployment, GitHub for source control and release pinning, and the portable packs for agent handoff. If a path changes live behavior, validate locally first, refresh the atlas, and then deploy the smallest safe artifact set that matches the target surface.
