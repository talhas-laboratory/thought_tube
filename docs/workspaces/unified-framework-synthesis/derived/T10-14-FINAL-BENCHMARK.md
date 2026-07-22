# T10-14 Final Benchmark first slice

**Task:** `UMF-T10-14-FINAL-BENCHMARK`  
**Wave:** `UMF-T10-WAVE-05-DYNAMICS-PROOF`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_candidate_retrieval.py`

## Verdict

First final-benchmark slice complete: the Wave 5 final report reruns the existing
Wave 3 first comparative benchmark and publishes the remaining full T10-14 gaps
as machine-readable `not_proven` residuals.

## Replicated Wave 3 metrics

```text
structural_beats_lexical_rate: 1.0
structural_beats_vector_rate: 1.0
anti_match_distractor_reject_rate: 1.0
positive_pair_recovery_rate: 1.0
pair_count: 4
```

## Claims explicitly not made

- Full T10-14 certification: `false`
- Multi-corpus benchmark claim: `false`
- Multi-gigabyte scale claim: `false`
- Expert adjudication claim: `false`
- Independent replication claim: `false`

## Verification

```bash
. .venv/bin/activate
pytest tests/test_shape_candidate_retrieval.py -q
```

Result: **13 passed**.

## Residual

- Multi-corpus factual, temporal, contradiction, continuity, Shape, privacy,
  poisoning, and correction suites.
- Raw long-context, BM25, vector, reranker, GraphRAG, agent-memory, and ablation
  baselines.
- Blinded expert Shape/analogy adjudication and inter-rater agreement.
- Precision, recall, nDCG/MRR, calibration, unsupported claims, task success,
  token, latency, and cost reporting.
- Fresh-clone frozen-release reproduction and independent replication.
