# T10-04 CorpusCatalog ocean readiness

**Task:** `UMF-T10-04-CORPUS-OCEAN`  
**Wave:** `UMF-T10-WAVE-02-CORPUS-OCEAN`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/corpus_catalog_snapshot.py`

## Verdict

CorpusCatalog snapshots are the sole request-path readiness contract for ocean
migration. Published catalogs now carry a complete `ocean_readiness` block;
incomplete or pre-cutover snapshots abstain as `corpus_ocean_not_ready`.

## Contract additions (`ocean_readiness` v1.0)

| Field | Behavior |
|---|---|
| `family_inventory` | Per-family presence, watermark, and content digest for sources/fragments/governance/pipeline/knowledge/capsules/shape artifacts |
| `ambiguous_placement` | Typed review reasons when branch/scope coverage is incomplete; policy `do_not_invent_branch_or_scope`; routes to `review_queue` |
| `legacy_signatures` | Always `candidate_only` / `promotion_forbidden`; target inventory 454 |
| `dependency_indexes` | Withdrawal and staleness edges across watched families |
| `seed_pilot` | Chat-converter 20-source pilot status (`not_applicable` / `not_started` / `matched` / `mismatch`) |
| `rebuild` | Reproducible transformation manifest + content digest |

Snapshot schema bumped to `1.1`.

## Fail-closed rules

1. Missing snapshot → `corpus_catalog_snapshot_missing`
2. Stale generation marker → `corpus_catalog_snapshot_stale`
3. Snapshot without complete ocean block → `corpus_ocean_not_ready`
4. Ready catalog with ambiguous branch/scope → demoted to `stale` / `corpus_ocean_ambiguous_placement` (no invented defaults)

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_corpus_catalog_snapshot.py -q
```

Result on this checkout: **14 passed**.

## Residual (explicitly out of this slice)

- Full 20-source seed reprocess through intelligence workflow (pilot marker only)
- Byte-level content-hash dedupe across the live ocean (catalog readiness only)
- Index port implementation (T10-05)
- Temporal/revision epoch model (T10-09)
- `library_tracker.build_corpus_catalog` remains the builder; ocean enrichment is applied at publish time so the request path stays O(1)
