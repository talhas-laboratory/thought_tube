# Shape certification — chat_converter_seed_v2_shape_certification

- fixture_revision: cae-shape-cert-v2-2026-07-20
- corpus_revision: db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad
- service_certified: False
- probe_count: 6
- known_failure_count: 1

## Metrics
- lexical_recall_at_1: 0.75
- shape_recall_at_1: 0.5
- shape_beats_lexical_rate: 0.0
- anti_match_precision: 1.0
- candidate_upgrade_rate: 0.0
- abstention_correctness_rate: 0.0
- latency_ms_p95: 1.901
- catalog_lookup_ms_p95: 0.172
- max_bytes_resolved: 338

## Probes
- positive-shape-assisted-recall: pass
- near-neighbour-distractor-harm: known_failure
- negative-unrelated-query: no_hits
- cross-branch-scope-mismatch: fail
- anti-match-false-analogy: pass
- resource-latency-and-catalog: pass

## Threshold check

- lexical_recall_at_1: True
- shape_recall_at_1: True
- shape_beats_lexical_rate: False
- anti_match_precision: True
- candidate_upgrade_rate: True
- abstention_correctness_rate: False
- latency_ms_p95: True
- max_catalog_lookup_ms: True
- max_bytes_resolved: True

- Harness: `src/conversation_os/shape_certification_harness.py`
- Fixture: `tests/fixtures/aperture_baselines/v2/shape_certification_probes.json`
