# UMF-T10-03-LIVE-SHAPE-POPULATION: T10-03: Integrate and operate live Shape Population

Status: review
Owner: population
Current gate: not_required

## Scope

Operate hardened Shape Population as the deployed post-ingest path: async worker, least-privilege identities, budgets, human approval, operator controls.

## Claimed paths

- `src/conversation_os/shape_population/` (all modules)
- `src/conversation_os/vault_ingest.py`
- `tools/run_shape_population_worker.py` (to create/import)
- `product/inner_world_v1/config/runtime.json`
- `tests/test_shape_population*.py`

## Implementation steps

1. Integrate storage, normalizer, packet assembler, gateway, identities, SQLite store, worker, orchestrator, promotion port, ingest hook.
2. Hook vault ingest: immediate source receipt + async enqueue; ingest survives Population failure.
3. Provision proposer/critic/synthesizer/evaluator from versioned manifests; source text untrusted.
4. Worker: leasing, retry, dead letter, idempotency, cancel, replay, backpressure, budgets.
5. Pin model/prompt/tool/policy versions in receipts.
6. Deterministic mock suite + OpenClaw canary.

## Acceptance Criteria

- Full module set integrated and reachable from release checkout.
- Large uploads receipt immediately and enqueue; ingest available if Population fails.
- Crash-safe worker semantics; no duplicate candidates.
- Model JSON cannot choose identity/authority/approval/canonical/runtime metadata; injection cannot gain tools or cite outside packet.
- Human approval before canonical apply; rejection terminal; operator pause/drain/resume/retry/cancel/inspect.
- Mock tests and live canary pass.

## Constraints

- Depends on `UMF-T10-00-INTEGRATION-BASELINE` and `UMF-T10-02-POPULATION-CANONICAL-MAP`
- Parent: `UMF-PROGRAM-SHAPE`

## Verification Evidence

- `pytest tests/test_shape_population_canonical_map.py tests/test_shape_population_promotion.py tests/test_shape_population_remediation_lifecycle.py` → **20 passed**
- Live verify pass recorded for the same focused suite
- OpenClaw canary: not run in this environment (deterministic mock path verified)

## Handoff Notes

- `build_post_ingest_hook(root)` enqueues after vault ingest without blocking; failures recorded via `record_enqueue_failure`
- `apply_approved_promotion_live(...)` applies through `FoundationCanonicalPort` after human approval
- `promotion.py` default remains `FailClosedCanonicalPort` (guard ownership); live callers pass the foundation port explicitly
- Operator controls: pause / resume / drain / cancel / retry / list / status on store + worker CLI
- Next Wave 1 exit: `UMF-T10-WAVE-01-GOLDEN-TRACE`
