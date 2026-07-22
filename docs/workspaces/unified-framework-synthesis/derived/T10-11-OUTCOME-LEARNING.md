# T10-11 Outcome Learning first slice

**Task:** `UMF-T10-11-OUTCOME-LEARNING`  
**Wave:** `UMF-T10-WAVE-05-DYNAMICS-PROOF`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_candidate_retrieval.py`

## Verdict

First slice complete: Shape retrieval can now convert held-out outcome events
into offline, review-only policy proposals. The helper separates outcome,
preference, reviewer, task-success, and factual-validation signals; attributes
them to evidence, matches, disclosure choices, prompt/tool/model revisions; and
blocks review promotion on safety or minority-view regression.

## Boundaries

- Does not mutate sources, Shape identity, approval history, or runtime policy.
- Requires offline replay, human review, canary, and rollback plan before any
  proposal can influence policy.
- Rollback scope is policy-only and independent of canonical knowledge.

## Verification

```bash
. .venv/bin/activate
pytest tests/test_shape_candidate_retrieval.py -q
```

Result: **12 passed**.

## Residual

- No online learning or self-modifying policy.
- No long-horizon causal credit assignment across agent tasks yet.
- No production canary or statistical improvement claim yet.
