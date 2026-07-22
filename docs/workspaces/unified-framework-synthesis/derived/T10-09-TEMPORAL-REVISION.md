# T10-09 Temporal / revision model

**Task:** `UMF-T10-09-TEMPORAL-REVISION`  
**Wave:** `UMF-T10-WAVE-02-CORPUS-OCEAN`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/corpus_catalog_snapshot.py`

## Verdict

CorpusCatalog snapshots now carry a content-addressed `temporal_revision` block:
revision identity, corpus epoch advancement rules, stale projection abstentions,
and explicit contradiction flags (no silent time defaults).

## Contract (`temporal_revision` v1.0)

| Field | Behavior |
|---|---|
| `revision_identity` | `revision_id` from corpus_id + corpus_revision + generation_marker + inventory_digest |
| `corpus_epoch` | `epoch_id` (content-addressed); advances on withdrawal/permission/correction/rebuild |
| `stale_projection_rules` | Typed abstentions for marker mismatch, incomplete ocean, ambiguous placement, required indexes |
| `contradictions` | Open flags surfaced; `surface_explicitly_do_not_auto_reconcile`; blocks quality claims when open |

## Fail-closed rules

1. Snapshots missing complete `temporal_revision` abstain as `corpus_ocean_not_ready`
2. Epoch advances when watched indexes / corpus revision / inventory digests change
3. No invented wall-clock defaults; revision is content-addressed

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_corpus_catalog_snapshot.py -q
```

Result on this checkout: **18 passed**.

## Residual

- Full contradiction resolution workflow beyond catalog surfacing
- Measured index rebuild latency publication (reserved fields from T10-05)
- Concrete withdrawal executor wiring beyond dependency-index metadata (T10-04/05)
