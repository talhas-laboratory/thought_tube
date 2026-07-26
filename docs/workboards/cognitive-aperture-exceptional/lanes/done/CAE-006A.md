Status: done
Owner: cursor-cloud-cae006a
# CAE-006A — Baseline evaluation harness

**Stage:** A
**Priority:** critical
**Depends on:** CAE-013, CAE-014, CAE-015
**Owner paths:** focused test fixtures, `derived/baselines/`

## Outcome

Capture current positive, negative, distractor, privacy, budget, leakage, provenance, and Shape behavior before enforcement.

## Acceptance

- fixtures and corpus revision are immutable/versioned;
- current known failures reproduce;
- approved recall, latency, and resource thresholds are recorded;
- harness distinguishes empty, denial, abstention, and internal failure;
- results are machine-readable and human summarized.

## Verification

- **Commit:** `ba34e32` on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_aperture_baseline_harness.py`
- **Result:** 6 tests pass; published baseline records 5 pass / 1 known_failure (`near-neighbour-agent-memory` → `understanding-the-nature-of-thought`).
- **Fixture revision:** corpus `db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad`.
- **Changed paths:** `aperture_baseline_harness.py`, `tests/fixtures/aperture_baselines/v1/probes.json`, `tests/test_aperture_baseline_harness.py`, `derived/baselines/chat_converter_seed_v1.{json,md}`.
- **Decision:** D-011.
- **Reviewer:** Stage A gate approval (`06bf815`).

## Rollback / risk

- Harness is observational; supersede published JSON when corpus revision changes.
- Residual risk: lexical/legacy-Shape baseline only — not embedding-certified.
