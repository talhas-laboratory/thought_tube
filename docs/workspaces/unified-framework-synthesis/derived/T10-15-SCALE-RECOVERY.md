# T10-15 Scale Recovery first slice

**Task:** `UMF-T10-15-SCALE-RECOVERY`  
**Wave:** `UMF-T10-WAVE-05-DYNAMICS-PROOF`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_population/orchestrator.py`

## Verdict

First slice complete: Shape Population now has a recovery-readiness report
contract that classifies queue pressure, operator controls, declared recovery
drills, RPO/RTO objective misses, lineage/access safety failures, and residual
scale gaps.

## Boundaries

- The report is declared-drill evidence only.
- It explicitly sets `multi_gigabyte_scale_claimed` to `False`.
- It blocks readiness when required drills are missing, failed, miss RPO/RTO, lose
  accepted evidence, create unreceipted canon, widen access, or fail lineage.

## Verification

```bash
. .venv/bin/activate
pytest tests/test_shape_population_golden_trace.py -q
```

Result: **3 passed**.

## Residual

- Current/10x/100x/max-affordable corpus benchmarks are not run yet.
- Process-kill, machine-restart, corruption, low-disk, network-loss, and timeout
  drills are only represented as required evidence categories, not executed here.
- Cost per source MB, candidate, canonical Shape, query, and agent task remains
  unmeasured.
