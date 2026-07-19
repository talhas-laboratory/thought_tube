<!-- generated: workspace continuity export; canonical store remains authoritative -->
<!-- workspace_id: cognitive-aperture-exceptional -->
<!-- canonical_revision: b330ea34a9de47f0ecce3d19e6c7b46e9085c02bfe4a639b06bd49348016f5be -->
<!-- repository_source_revision: 162184b8b04fce8cf6dbd46ef78969ebf8b2410d -->
<!-- generated_at: 2026-07-19T21:47:10+00:00 -->

# Workspace continuity: cognitive-aperture-exceptional

## Resume

Select a task to receive a recommended next action.

## Focus task

- id: ``
- status: ``
- title: _none_

## Recent runs

- CAE-012 approved: read-only cross-surface operator metrics from receipts/baselines; flag default-off.
- CAE-011 approved: wire kernel bounded view as optional epistemic backend (ADR-003/D-027).
- CAE-010 approved: optional task-pack bounded_evidence via CandidateSearchPort; flag default-off.
- CAE-008 approved: multi-turn rollback restores prior ActiveState snapshot (D-025).
- CAE-006 parent closed
- CAE-005 parent closed
- CAE-008 blocked on rollback semantics; other Stage C/D leaves approved.
- CAE-009 approved: feed adapter routes evidence pairs through CandidateSearchPort with grant/provenance; flag default-off.
- CAE-006B approved: shape-aware service baselines published; structural/parity/perf probes pass; near-neighbour known_failure preserved.
- CAE-007 approved: persistent AuditReceipts with reconstruction; incognito hashes-only; flag default-off.
- CAE-005B approved: Holodeck adapter uses CandidateSearchPort; legacy meta scorer isolated; flag default-off.
- Independent review approve CAE-005A

## Reasoning

- Stage B review: CAE-003B APPROVE after unset-budget fix
- Stage B review: CAE-004 APPROVE pending CAE-003B fix
- Stage B review: CAE-003B CHANGES REQUESTED
- Stage B review: CAE-001 APPROVE pending Stage B gate
- Stage B review: CAE-003A APPROVE pending Stage B gate
- Stage B review: CAE-002 APPROVE pending Stage B gate
- Stage A independent review APPROVE CAE-000
- Stage A independent review APPROVE CAE-006A
- Stage A independent review APPROVE CAE-015
- Stage A independent review APPROVE CAE-014
- Stage A independent review APPROVE CAE-013
- ShapeProjectionReader contract v1.0 implemented

## Verification

- tests/test_aperture_operator_metrics.py
- tests/test_bounded_view_disclosure_adapter.py
- tests/test_task_pack_disclosure_parity.py
- tests/test_active_state_continuity.py::test_multi_turn_rollback_restores_prior_snapshot
- parent-children-complete
- parent-children-complete
- adversarial_multi_turn_active_state_rollback
- tests/test_feed_disclosure_parity.py
- tests/test_aperture_service_baseline_harness.py
- tests/test_disclosure_receipts.py
- tests/test_holodeck_disclosure_parity.py
- tests/test_disclosure_service_bridge_parity.py
