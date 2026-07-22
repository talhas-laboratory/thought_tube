# T10-05 Index / retrieval contracts

**Task:** `UMF-T10-05-INDEX-CONTRACTS`  
**Wave:** `UMF-T10-WAVE-02-CORPUS-OCEAN`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/corpus_catalog_snapshot.py`

## Verdict

CorpusCatalog snapshots now expose replaceable hybrid index port contracts under
`ocean_readiness.index_contracts`. Stale/absent required ports demote readiness
and never claim to widen retrieval.

## Ports (`index_contracts` v1.0)

| Port | Role |
|---|---|
| `exact` | Content-hash / source-ref exact lookup |
| `lexical` | Chunk lexical index |
| `semantic_address` | Bounded semantic-address candidate pool |
| `vector` | Embedding candidate pool (side-by-side re-embed supported) |
| `graph` | Governed graph / knowledge nodes |
| `structural_fingerprint` | Legacy structural signatures (candidate-only) |

Each port records: replaceability, status, abstention reason, incremental
add/update/tombstone (+ rebuild/rollback), auth/branch/scope/lifecycle/time
filters, revision id, footprint, reserved latency fields, and
content-addressed source-byte policy (`copied_into_index: false`).

## Fail-closed rules

1. Required ports for non-empty corpora: `exact`, `lexical`
2. If required ports are not ready while base readiness is `ready` → demote to
   `stale` with `corpus_index_not_ready:<ports>`
3. Policy flags: `no_full_ocean_scan`, `stale_or_corrupt_abstain`,
   `similarity_alone_cannot_merge_or_promote`,
   `approximate_indexes_candidate_pool_only`
4. Snapshots missing `index_contracts` abstain as `corpus_ocean_not_ready`

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_corpus_catalog_snapshot.py -q
```

Result on this checkout: **16 passed**.

## Residual (explicitly out of this slice)

- Concrete vector/semantic-address builders and measured latency publication
- Side-by-side re-embedding migration runners
- Temporal/revision epoch model (T10-09)
