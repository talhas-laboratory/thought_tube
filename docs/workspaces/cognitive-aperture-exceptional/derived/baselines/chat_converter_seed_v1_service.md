# Chat converter seed service baseline v1

Shape-aware and service performance baseline for corpus `cognitive_aperture_chat_converter_v1` (CAE-006B).

## Contract

| Field | Value |
| --- | --- |
| Baseline suite | `chat_converter_seed_v1_service` |
| Parent suite | `chat_converter_seed_v1` |
| Harness version | `1.0` |
| Corpus revision | `db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad` |
| Service certified | **no** |

## Approved thresholds (Stage C service)

| Metric | Threshold |
| --- | ---: |
| Structural beats distractor rate | 1.00 |
| AntiMatch block rate | 1.00 |
| Candidate upgrade rate | 0.00 |
| Adapter parity rate | 1.00 |
| Latency p50 (ms) | 250 |
| Latency p95 (ms) | 750 |
| Max bytes resolved | 65536 |
| Max expansion count | 12 |

These thresholds are recorded before enforcement. They are not release gates until Stage C gate evidence is published.

## Observed probe results (2026-07-19)

| Probe | Category | Verdict | Notes |
| --- | --- | --- | --- |
| structural-agent-memory-ranking | ranking | pass | mapping-the-mind ranks above understanding-the-nature-of-thought |
| near-neighbour-distractor-harm | distractor | **known_failure** | understanding-the-nature-of-thought wins over mapping-the-mind |
| shape-anti-match-no-promotion | shape | pass | promotion blocked; no candidate upgrade in retrieval |
| bridge-holodeck-retrieval-parity | parity | pass | admitted capsule IDs and source refs match |
| disclosure-path-performance | performance | pass | p50/p95 within limits; cache stable |

## Known regression

Query `biological cognition agent memory` returns `understanding-the-nature-of-thought` instead of `mapping-the-mind-for-agentic-systems`. This near-neighbour distractor harm is preserved from Stage A baseline CAE-006A.

## Shape / AntiMatch behavior

Legacy Shape signatures enter retrieval only as explicit candidates. `migration_decision()` keeps `promotion_allowed: false`. AntiMatch records block false analogy promotion; retrieval must not upgrade candidate status to promoted.

## Machine-readable artifacts

- [`chat_converter_seed_v1_service.json`](./chat_converter_seed_v1_service.json)
- Probe fixtures: `tests/fixtures/aperture_baselines/v1/service_probes.json`
- Harness: `src/conversation_os/aperture_service_baseline_harness.py`

## Limits

Synthetic semantic capsule fixtures on the shared disclosure service path. Lexical ranking and legacy-Shape adapter behavior only; no materialized embedding index or canonical Shape profile is claimed for this corpus revision.
