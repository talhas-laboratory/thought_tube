# Feed certification — chat_converter_seed_v2_feed_certification

- fixture_revision: cae-feed-cert-v2-2026-07-20
- corpus_revision: db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad
- service_certified: True
- probe_count: 6
- known_failure_count: 0

## Metrics
- positive_precision_rate: 1.0
- bridge_parity_rate: 1.0
- negative_abstention_rate: 1.0
- abstention_correctness_rate: 1.0
- receipt_persistence_rate: 1.0
- provenance_preservation_rate: 1.0
- latency_ms_p95: 2.128
- catalog_lookup_ms_p95: 0.179
- max_bytes_resolved: 174

## Probes
- positive-research-evidence-pairs: pass
- bridge-parity-research-domain: pass
- negative-unrelated-domain: no_pairs
- abstention-missing-catalog: pass
- receipt-persistent-feed-rollout: pass
- resource-latency-and-catalog: pass

## Threshold check

- positive_precision_rate: True
- bridge_parity_rate: True
- negative_abstention_rate: True
- abstention_correctness_rate: True
- receipt_persistence_rate: True
- provenance_preservation_rate: True
- latency_ms_p95: True
- max_catalog_lookup_ms: True
- max_bytes_resolved: True

- Harness: `src/conversation_os/feed_certification_harness.py`
- Fixture: `tests/fixtures/aperture_baselines/v2/feed_certification_probes.json`
