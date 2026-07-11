# CTX-005: Production Recovery

- status: done
- owner: codex
- gate: done
- depends_on: CTX-001, CTX-002, CTX-003, CTX-004

## Acceptance

- Health and readiness are observable.
- Restart preserves state.
- Backup/restore reproduces canonical task, decision, test, and context state.
- Systemd service and observer units use safe defaults and documented rollback.

## Test Strategy

- Exercise `/health` and `/ready` against a real ephemeral service and SQLite store.
- Backup live state, restore to a fresh database, and compare context packets after removing assembly timestamps.
- Restart the service over the same database and verify task, decision, test, and snapshot continuity.
- Validate systemd samples for non-root identity, localhost binding, restart policy, environment loading, and dependency ordering.

## Verification

- `pytest tests/test_workspace_store.py tests/test_workspace_coordination.py tests/test_workspace_atlas.py tests/test_workspace_service.py tests/test_workspace_client.py tests/test_workspace_context_packet.py tests/test_workspace_observer.py tests/test_observe_workspace.py tests/test_workspace_completion_gates.py tests/test_workspace_backup_restore.py tests/test_workspace_recovery_cli.py tests/test_workspace_coordination_cli.py tests/test_run_workspace_service.py tests/test_run_telegram_meta_agent.py tests/test_meta_telegram_agent.py -q`
- result: 83 passed
- backup/restore packet equivalence, restart continuity, liveness, readiness, and systemd safety properties are exercised

## Residual Risks

- The sample units are not yet installed on the production server; server cutover remains part of final operational verification.
- Service authentication is delegated to localhost isolation and the authenticated reverse-proxy boundary.
