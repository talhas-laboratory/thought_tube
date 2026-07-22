# T10-07 Shape-aware retrieval repair

**Task:** `UMF-T10-07-SHAPE-RETRIEVAL`  
**Wave:** `UMF-T10-WAVE-03-STRUCTURAL-INTEL`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_candidate_retrieval.py`

## Verdict

Shape-aware retrieval now has an owner-side wrapper that always returns a typed
`shape_retrieval` envelope. Catalog abstention no longer drops Shape status.
Focused audit failures are green.

## API

| Symbol | Role |
|---|---|
| `typed_shape_retrieval_result` | Normalize Shape context (+ catalog) into typed envelope with locked order |
| `build_shape_aware_retrieval_bundle` | Compose catalog + Shape context + underlying bundle; never omit `shape_retrieval` |

Locked order recorded on every envelope:

`authorization → catalog_readiness → shape_dependency → positive_admission → ranking → anti_match → evidence_resolution → budget`

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_shape_candidate_retrieval.py -q
```

Result: **8 passed** (includes structural-over-lexical, profile abstention without widen, AntiMatch hard-reject, and Pattern/AntiMatch unit cases).

## Residual

- `knowledge_layer.build_retrieval_bundle` early catalog returns still omit
  `shape_retrieval` when called directly (guard blocks that owner). Callers that
  need typed Shape status should use `build_shape_aware_retrieval_bundle`.
- T10-14 first comparative benchmark still backlog.
