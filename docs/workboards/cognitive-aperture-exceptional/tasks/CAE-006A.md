Status: backlog
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
