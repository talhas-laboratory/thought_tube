# Wave 1 golden source-to-Shape production trace

**Task:** `UMF-T10-WAVE-01-GOLDEN-TRACE`  
**Status:** executed on release checkout `cursor/t10-wave-01-tasks-a790`  
**Date:** 2026-07-22  
**Parent:** `UMF-T10-WAVE-01-SHAPE-LIFECYCLE`

## Pipeline

```text
ingest -> normalize -> inquiry -> evidence -> propose -> critique
-> synthesize -> evaluate -> human approve -> canonical apply -> retrieve
(+ rollback / correction demonstration)
```

## Release checkout

| Field | Value |
|---|---|
| Branch | `cursor/t10-wave-01-tasks-a790` |
| Pre-trace HEAD | `4fa5334f5fa6cd1617040376282a7bc3840d1a34` |
| Workspace | `unified-framework-synthesis` |

## Verification command

```bash
. .venv/bin/activate
python -m pytest tests/test_shape_population_golden_trace.py -q
```

Expected: `1 passed`.

Related focused suites already green on this branch:

```bash
python -m pytest \
  tests/test_shape_population_golden_trace.py \
  tests/test_shape_population_canonical_map.py \
  tests/test_shape_population_promotion.py \
  tests/test_shape_population_remediation_lifecycle.py \
  tests/test_shape_authority.py \
  tests/test_shape_projection_reader.py \
  -q
```

## Sample archived IDs (deterministic mock run)

Captured by `run_golden_trace()` and mirrored in
`docs/workspaces/unified-framework-synthesis/derived/golden_trace_archive.json`.

| Stage | ID |
|---|---|
| vault source | `source-7ab3134c8c70` |
| ingest job | `job-baaed9b5bd45` |
| shape source | `f52e4f37c861700d68cdc47cca0e573a` |
| evidence packet | `pkt-85fc69a7cbcac6f09558` |
| candidate | `cand-759279a77d52` |
| critique evaluation | `eval-c4d014f9e905` |
| synthesis evaluation | `eval-84378157b17d` |
| promotion request | `prom-e37f3f9eb0f6` |
| human approval | `appr-4c3a775a88b1` |
| canonical id | `canonical:cand-759279a77d52` |
| shape core | `shape-core:cand-759279a77d52` |
| shape view | `shape-view:cand-759279a77d52:population_candidate` |
| owner version | `1` |

## Versions / receipts

| Field | Value |
|---|---|
| profile | `profile:shape` |
| canonical owner | `FoundationCanonicalPort` |
| prompt/model | `golden-1.0` / `mock` |
| ingest_ok | true |
| canonical_applied | true |
| retrieve_ok | true (`available`) |
| rollback_stale | true |
| post_rollback_status | `stale` |

## Provenance / correction

- Evidence refs terminate in packet/block/segment spans recorded in the archive JSON.
- Correction path demonstrated: owner rollback marks the projection stale; subsequent retrieve reports `stale` without deleting unrelated knowledge.

## Implementation surfaces used

- `build_post_ingest_hook` / `apply_approved_promotion_live` (T10-03)
- `FoundationCanonicalPort` + `CanonicalShapeProposal` (T10-02)
- `profile:shape` authority (T10-01)
- `retrieve_after_canonical_apply` in `shape_candidate_retrieval.py` (retrieve step)

## Residual

- OpenClaw live canary not executed in this Cloud agent environment; hermetic mock golden path is the Wave 1 exit evidence here.
- `promotion.py` default remains FailClosed; live apply helper passes FoundationCanonicalPort explicitly.
