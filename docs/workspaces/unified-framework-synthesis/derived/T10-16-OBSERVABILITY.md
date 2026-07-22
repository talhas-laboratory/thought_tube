# T10-16 Observability first slice

**Task:** `UMF-T10-16-OBSERVABILITY`  
**Wave:** `UMF-T10-WAVE-05-DYNAMICS-PROOF`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/aperture_operator_metrics.py`

## Verdict

First slice complete: aperture operator metrics now expose a privacy-safe
lifecycle observability view. The view aggregates lifecycle families, statuses,
expected abstentions, infrastructure failures, stale indexes, stuck jobs, drift
signals, repair paths, and authorized control categories without serializing
source refs, evidence text, grants, block ids, or principals.

## Boundaries

- Read-only, with no mutation paths.
- Counts and repair/drift codes only; hidden corpus content and privileged state
  are excluded.
- Expected abstentions are info-level, while infrastructure failures, stale
  indexes, and stuck jobs receive distinct alert classes.

## Verification

```bash
. .venv/bin/activate
pytest tests/test_aperture_operator_metrics.py -q
```

Result: **13 passed**.

## Residual

- No dashboard UI wiring yet.
- No live alert sink or SLO paging policy yet.
- Receipt-to-source reconstruction remains covered by earlier receipt paths, not
  a complete end-to-end operator console.
