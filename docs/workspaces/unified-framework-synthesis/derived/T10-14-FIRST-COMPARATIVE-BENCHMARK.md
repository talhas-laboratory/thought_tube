# T10-14 First comparative quality benchmark (Wave 3 slice)

**Task:** `UMF-T10-14-FIRST-BENCHMARK`  
**Wave:** `UMF-T10-WAVE-03-STRUCTURAL-INTEL`  
**Date:** 2026-07-22  
**Owner module:** `src/conversation_os/shape_candidate_retrieval.py`

## Verdict

Wave 3 first comparative benchmark is locked and green: structural
Pattern/Shape classification recovers held-out cross-domain positives and
rejects lexical/vector distractors under thresholds frozen before evaluation.

## Suite

| Field | Value |
|---|---|
| `benchmark_id` | `wave3_first_comparative_v1` |
| `benchmark_revision` | `2026-07-22.wave3.first` |
| Cases | 3 positive cross-domain + 1 AntiMatch negative |
| Baselines | lexical token overlap, bag-of-tokens vector proxy, structural `classify_shape_pair` |

## Locked thresholds (before evaluation)

- `structural_beats_lexical_rate` ≥ 0.80
- `structural_beats_vector_rate` ≥ 0.80
- `anti_match_distractor_reject_rate` = 1.0
- `positive_pair_recovery_rate` ≥ 0.80
- `min_pair_count` ≥ 4

## Observed metrics

```text
structural_beats_lexical_rate: 1.0
structural_beats_vector_rate: 1.0
anti_match_distractor_reject_rate: 1.0
positive_pair_recovery_rate: 1.0
pair_count: 4
passed: true
```

Each case publishes `holds_where` / `breaks_where` / transfer limits and keeps
`merge_shapes_forbidden`.

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_shape_candidate_retrieval.py -q
```

Result: **9 passed**.

## Residual (full T10-14 later)

- Multi-corpus factual/temporal/privacy/poisoning suites
- Learned embedding / GraphRAG / agent-memory baselines
- Blinded expert adjudication + confidence intervals
- Fresh-clone reproduction against a frozen release manifest
- Final Wave 5 benchmark replication
