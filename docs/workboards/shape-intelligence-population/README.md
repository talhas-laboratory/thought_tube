# Shape Intelligence Population Workboard

This board is the execution mirror for the remediation described in `docs/workspaces/shape-intelligence-population/derived/REMEDIATION_IMPLEMENTATION_PLAN.md`.

Use the live workspace API as task truth. `TASKS.md`, `tasks/`, `lanes/`, `CONTINUITY.md`, and `UPDATES.jsonl` are generated projections and must not be hand-edited. Human-authored execution rules live in `GATES.md` and `LOCAL-AGENT-BOOT.md`.

The critical path is:

1. `SIP-R00` reconstructs a safe current baseline.
2. Child workspaces execute their remediation packets in the ordering declared by the central plan.
3. `SIP-R01` proves the asynchronous production lifecycle and recovery behavior.
4. `SIP-R02` proves semantic quality, performance, rollout, and rollback readiness.

The old `SIP-001` through `SIP-004` tasks retain the original architecture history. The `SIP-R*` tasks and child `*A`/`*B` subtasks contain the remediation execution authority.
