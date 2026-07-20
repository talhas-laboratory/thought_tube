# Chat converter seed baseline v1

Pre-enforcement retrieval baseline for corpus `cognitive_aperture_chat_converter_v1`.

## Contract

| Field | Value |
| --- | --- |
| Baseline suite | `chat_converter_seed_v1` |
| Harness version | `1.0` |
| Corpus revision | `db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad` |
| Sources / chunks | 20 / 6,611 |
| Retrieval certified | **no** |

## Approved thresholds (Stage A)

| Metric | Threshold |
| --- | ---: |
| Positive recall@1 | 0.80 |
| Negative false-open rate | 0.00 |
| Latency p50 (ms) | 250 |
| Latency p95 (ms) | 750 |
| Max bytes resolved | 65536 |

These thresholds are recorded before enforcement. They are not release gates until Stage B/C evidence is published.

## Observed probe results (2026-07-19)

| Probe | Verdict | Result status | Top source |
| --- | --- | --- | --- |
| exact-hybrid-rag-file | pass | disclosed | agentic-hybrid-rag-for-information-extraction |
| retrieval-information-extraction-query | pass | disclosed | agentic-hybrid-rag-for-information-extraction |
| semantic-context-embedding-query | pass | disclosed | context-in-embedding-spaces |
| out-of-domain-quantum-gardening | no_hits | empty_no_positive_match | — |
| structural-agent-memory-lexical | pass | disclosed | mapping-the-mind-for-agentic-systems |
| near-neighbour-agent-memory | **known_failure** | disclosed | understanding-the-nature-of-thought (expected mapping-the-mind…) |

## Known regression

Query `biological cognition agent memory` returns `understanding-the-nature-of-thought` instead of `mapping-the-mind-for-agentic-systems`. Preserve this near-neighbour failure in the harness; CAE-006B adds Shape/AntiMatch evaluation.

## Machine-readable artifact

See [`chat_converter_seed_v1.json`](./chat_converter_seed_v1.json) and probe fixtures under `tests/fixtures/aperture_baselines/v1/probes.json`.

## Limits

Lexical and legacy-Shape baseline only. No materialized embedding index or canonical Shape profile is claimed for this corpus revision.
