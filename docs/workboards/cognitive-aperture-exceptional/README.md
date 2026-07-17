# Workboard — Cognitive Aperture Exceptional

**Workspace:** `cognitive-aperture-exceptional`  
**Gap map:** [`../../workspaces/cognitive-aperture-exceptional/derived/GAP_MAP.md`](../../workspaces/cognitive-aperture-exceptional/derived/GAP_MAP.md)  
**Protocol:** [`../../workspaces/WORKSPACE-AGENT-PROTOCOL.md`](../../workspaces/WORKSPACE-AGENT-PROTOCOL.md)

## Rules

- Live API is coordination truth when available. Do not hand-edit `Status:` as authority.
- Implement against gap IDs (G0–G11) and task seeds (CAE-000…).
- After mutations: publish projections → commit → push.

## Phase board

| Phase | Intent | Exit |
|-------|--------|------|
| 0 Lock | ADR + contracts | Implementers unblocked |
| 1 Stop bleeding | Fail-empty, leak, budgets, orient-first | P0 suites green |
| 2 One kernel + measure | disclose() + evals + receipts | ≥2 surfaces, baselines |
| 3 Sameness | Feed/task-pack/kernel honesty | C1–C12 near exceptional |
| 4 Optional+ | Steering / learned rerank | Category-defining |

## Task index (seeds)

See [`TASKS.md`](./TASKS.md) and [`tasks/`](./tasks/).

## Current blocker

Live workspace API host offline at creation. Local Holodeck workspace exists. Register tasks live before claiming implementation work when API recovers.
