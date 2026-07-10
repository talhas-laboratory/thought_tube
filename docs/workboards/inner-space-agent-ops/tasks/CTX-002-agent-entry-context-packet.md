# CTX-002: Agent Entry Context Packet

- status: done
- owner: codex
- gate: done
- depends_on: CTX-001

## Acceptance

- One endpoint returns bounded task-first context, active coordination state, source revision, open threads, and provenance.
- Packet limits and isolation are deterministic and tested.
- Packet can be reconstructed from canonical state.

## Verification

- `pytest tests/test_workspace_context_packet.py tests/test_workspace_service.py tests/test_workspace_client.py tests/test_workspace_coordination_cli.py -q`
- result: 14 passed
- changed files: `src/conversation_os/workspace_context_packet.py`, `src/conversation_os/workspace_service.py`, `src/conversation_os/workspace_client.py`, tests and coordination docs

## Residual Risks

- Repository revision and changed-file values remain empty until CTX-003 supplies automatic observations.
