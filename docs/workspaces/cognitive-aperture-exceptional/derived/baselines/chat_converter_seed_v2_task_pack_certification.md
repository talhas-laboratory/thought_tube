# Task-pack certification — chat_converter_seed_v2_task_pack_certification

- fixture_revision: cae-task-pack-cert-v2-2026-07-20
- corpus_revision: db340a77323741710f5f2a9512123271505c13880a3f72ac4c3e11c19fc4ccad
- service_certified: True
- probe_count: 7
- known_failure_count: 0

## Metrics
- positive_overlap_rate: 1.0
- bridge_parity_rate: 1.0
- negative_zero_block_rate: 1.0
- narrative_preservation_rate: 1.0
- abstention_correctness_rate: 1.0
- latency_ms_p95: 3.326
- catalog_lookup_ms_p95: 0.177
- max_bytes_resolved: 93

## Probes
- positive-bounded-evidence-overlap: pass
- bridge-parity-research-query: pass
- negative-unrelated-no-filler: no_hits
- narrative-preservation-with-evidence: pass
- narrative-preservation-empty-evidence: pass
- abstention-missing-catalog-snapshot: pass
- resource-latency-and-catalog: pass

## Threshold check

- positive_overlap_rate: True
- bridge_parity_rate: True
- negative_zero_block_rate: True
- narrative_preservation_rate: True
- abstention_correctness_rate: True
- latency_ms_p95: True
- max_catalog_lookup_ms: True
- max_bytes_resolved: True

- Harness: `src/conversation_os/task_pack_certification_harness.py`
- Fixture: `tests/fixtures/aperture_baselines/v2/task_pack_certification_probes.json`
