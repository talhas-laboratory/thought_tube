# CTX-007: Private Agent Connectivity

- status: done
- owner: codex
- gate: done

## Problem

The canonical workspace service is private on the OpenClaw server, but local Codex must reach the same state without public exposure or manual tunnel setup.

## Acceptance

- Server Telegram and local Codex use the same SQLite workspace.
- The service remains bound to server localhost.
- A persistent local tunnel restarts automatically and fails closed if forwarding cannot bind.
- Local CLI discovers the tunnel API from a user config file when no explicit flag is provided.
- The old local Telegram poller is disabled so only the server consumes bot updates.

## Verification

- LaunchAgent `com.inner-space.workspace-tunnel` is loaded and running.
- Local `http://127.0.0.1:18765/ready` returns SQLite integrity `ok`.
- An implicit local CLI context request returns server task `DEPLOY-VERIFY-001` and revision `50b896758744ace898571473980993e67f263d08`.
- Server Telegram offset was migrated from `945417032` and advanced without new HTTP 409 conflicts.
- Direct deployed Telegram adapter `/context DEPLOY-VERIFY-001` returned the canonical completed task.

## Residual Risks

- Tunnel availability depends on LAN reachability and SSH key validity; failure is visible as an explicit workspace client error and never falls back locally.
