# Canonical Workspace Access

The canonical workspace service is the single source of truth for tasks, claims, decisions, blockers, verification, and agent runs. Git-tracked files such as `memory/workspaces/*`, workboards, and continuity exports are projections only.

Use one of these access paths depending on where the agent runs:

| Surface | API base | Setup |
|---|---|---|
| OpenClaw server (local) | `http://127.0.0.1:8765/api` | systemd user services below |
| Local Mac / Codex | `http://127.0.0.1:18765/api` | SSH tunnel via `ops/launchd/com.inner-space.workspace-tunnel.plist.sample` |
| Cursor Cloud / remote agent | `https://talhas-laboratory.tailefe062.ts.net/workspace` | `tools/setup_cursor_tailnet.sh` |

All clients read `INNER_WORLD_WORKSPACE_API_BASE` from the environment or `~/.config/inner-space-workspace.env`. The `/api` suffix is optional; clients normalize it automatically.

## Local Mac SSH tunnel

Install the launchd sample so local agents reach the same canonical SQLite service as the server:

```bash
cp ops/launchd/com.inner-space.workspace-tunnel.plist.sample \
  ~/Library/LaunchAgents/com.inner-space.workspace-tunnel.plist
launchctl bootstrap "gui/$(id -u)" ~/Library/LaunchAgents/com.inner-space.workspace-tunnel.plist
```

Write the client config:

```bash
install -m 0600 /dev/stdin ~/.config/inner-space-workspace.env <<'EOF'
INNER_WORLD_WORKSPACE_API_BASE=http://127.0.0.1:18765/api
EOF
```

Verify:

```bash
curl --fail http://127.0.0.1:18765/health
curl --fail http://127.0.0.1:18765/api/workspaces
```

## Cursor Cloud over Tailscale

Cursor Cloud agents are not on your LAN. Give them a tagged ephemeral Tailscale auth key and restrict it in your tailnet ACL to `talhas-laboratory:443` for `tag:cursor-agent`.

Required Cursor Cloud secrets / environment:

```text
TAILSCALE_AUTHKEY=tskey-auth-...
INNER_WORLD_WORKSPACE_API_BASE=https://talhas-laboratory.tailefe062.ts.net/workspace
```

Bootstrap on the agent host:

```bash
tools/setup_cursor_tailnet.sh
```

The script joins the tailnet, writes `~/.config/inner-space-workspace.env`, and verifies `/health` plus `/api/workspaces`. It tries passwordless `sudo tailscale up` first, then reuses an existing tailnet session, then falls back to userspace networking when TUN access is unavailable.

Quick verification from any connected surface:

```bash
python3 tools/workspace_coordination.py status --workspace-id inner-world
```

If the API is unreachable, stop before workspace mutations and report the outage instead of editing `memory/workspaces/*` directly.

## Server install and recovery

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

## Related references

- [Workspace coordination implementation spec](../implementation/workspace-coordination/README.md)
- [Canonical workspace Cursor rule](../../.cursor/rules/canonical-workspace.mdc)
