# CTX-001: Canonical Service Client

- status: done
- owner: codex
- gate: done
- plan: `docs/superpowers/plans/2026-06-30-agent-context-repository-gap-plan.md`

## Problem

Local coordination tooling can bypass the server store, so agents may believe they share state while mutating different sources.

## Scope

- Create one reusable workspace HTTP client.
- Cut the local CLI over when `INNER_WORLD_WORKSPACE_API_BASE` or `--workspace-api-base` is present.
- Keep file mode as an explicit offline fallback.

## Acceptance

- Every coordination verb has a tested client operation.
- HTTP failures are visible and do not silently fall back to local mutation.
- Existing file-backed CLI behavior remains compatible when no service is configured.

## Verification

- `pytest tests/test_workspace_client.py tests/test_workspace_coordination_cli.py -q`
- result: 10 passed
- changed files: `src/conversation_os/workspace_client.py`, `tools/workspace_coordination.py`, client and CLI tests, coordination docs

## Residual Risks

- Service authentication and TLS termination remain deployment concerns in CTX-005.
