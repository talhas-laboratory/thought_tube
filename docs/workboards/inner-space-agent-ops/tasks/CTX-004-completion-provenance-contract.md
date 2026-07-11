# CTX-004: Completion Provenance Contract

- status: done
- owner: codex
- gate: done
- depends_on: CTX-002

## Acceptance

- Done/release promotion requires reasoning, changed files, commands, passing tests, evidence, and residual risks.
- Missing evidence returns actionable gate failures across direct, HTTP, and Telegram paths.
- Intermediate discussion and handoff remain possible without false completion.

## Test Strategy

- Reject completion independently for each missing field and for non-passing verification.
- Accept a complete packet, transition the task to done, release its claim, and preserve one structured completion event.
- Exercise direct coordination, HTTP client/service, and Telegram command paths.

## Verification

- `pytest tests/test_workspace_store.py tests/test_workspace_coordination.py tests/test_workspace_atlas.py tests/test_workspace_service.py tests/test_workspace_client.py tests/test_workspace_context_packet.py tests/test_workspace_observer.py tests/test_observe_workspace.py tests/test_workspace_completion_gates.py tests/test_workspace_coordination_cli.py tests/test_run_telegram_meta_agent.py tests/test_meta_telegram_agent.py -q`
- result: 75 passed
- completion is idempotent and releases the completing agent's claims
- HTTP failures include structured missing fields; Telegram reports those fields to the agent

## Residual Risks

- Append-only completion writes are validation-before-mutation but are not wrapped in one cross-record SQLite transaction. Retry idempotency repairs ordinary client retries; stronger crash-atomic grouping remains a future store-level enhancement.
