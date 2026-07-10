# CTX-003: Automatic Repository Observation

- status: done
- owner: codex
- gate: done
- depends_on: CTX-002

## Acceptance

- Added, modified, deleted, and renamed files inside workspace roots are captured automatically.
- Unrelated files are excluded.
- Unchanged snapshots are idempotent and GitNexus remains optional enrichment.

## Test Strategy

- Build temporary git repositories and verify added, modified, deleted, renamed, clean, and out-of-scope paths.
- Verify stable snapshot fingerprints and context-packet propagation.

## Verification

- `pytest tests/test_workspace_observer.py tests/test_observe_workspace.py tests/test_workspace_atlas.py tests/test_workspace_context_packet.py tests/test_workspace_store.py -q`
- result: 10 passed
- generated projections are explicitly excluded from snapshots to prevent observer feedback loops

## Residual Risks

- Polling interval and service supervision require production configuration in CTX-005.
- GitNexus enrichment remains optional and does not affect canonical snapshot correctness.
