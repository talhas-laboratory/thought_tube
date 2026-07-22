Status: done
Owner: cursor-cloud-reviewer
# CAE-006B — Shape-aware and performance baselines

**Stage:** C
**Priority:** high
**Depends on:** CAE-005B, CAE-007

## Outcome

Prove structural Shape retrieval, AntiMatch behavior, adapter parity, latency, and bounded resource use on the shared service.

## Acceptance

- structural matches beat lexical distractors;
- AntiMatch blocks known false analogy;
- candidate status is never upgraded by retrieval;
- neighborhood precision/recall and distractor harm published;
- p50/p95 latency, bytes resolved, expansion counts, and cache behavior meet approved limits.

## Verification

- **Commit:** `4bbb208` on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_aperture_service_baseline_harness.py`
- **Result:** 7 tests pass; suite `chat_converter_seed_v1_service` reports 4 pass / 1 known_failure (near-neighbour distractor preserved); threshold check passes.
- **Fixture revision:** corpus `db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad`.
- **Changed paths:** `src/conversation_os/aperture_service_baseline_harness.py`, `tests/fixtures/aperture_baselines/v1/service_probes.json`, `tests/test_aperture_service_baseline_harness.py`, `docs/workspaces/cognitive-aperture-exceptional/derived/baselines/chat_converter_seed_v1_service.{json,md}`.
- **Decision:** D-021.
- **Reviewer:** Stage C/D independent review (`5ac2934`) — approved.

## Rollback / risk

- Harness is observational only; no runtime flag. Remove or ignore published baseline JSON if superseded by a new corpus revision.
- Residual risk: synthetic semantic capsules; near-neighbour known failure is intentional and not retrieval-certified.
