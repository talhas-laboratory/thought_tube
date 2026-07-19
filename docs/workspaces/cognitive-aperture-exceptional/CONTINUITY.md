<!-- generated: workspace continuity export; canonical store remains authoritative -->
<!-- workspace_id: cognitive-aperture-exceptional -->
<!-- canonical_revision: bfc8eb7ee0b6e018f6476f7b6000d9e850c2d892819879620de7d2cae5a2a374 -->
<!-- repository_source_revision: 162184b8b04fce8cf6dbd46ef78969ebf8b2410d -->
<!-- generated_at: 2026-07-19T17:50:01+00:00 -->

# Workspace continuity: cognitive-aperture-exceptional

## Resume

Select a task to receive a recommended next action.

## Focus task

- id: ``
- status: ``
- title: _none_

## Recent runs

- CAE-006 parent closed
- CAE-005 parent closed
- CAE-008 blocked on rollback semantics; other Stage C/D leaves approved.
- CAE-009 approved: feed adapter routes evidence pairs through CandidateSearchPort with grant/provenance; flag default-off.
- CAE-006B approved: shape-aware service baselines published; structural/parity/perf probes pass; near-neighbour known_failure preserved.
- CAE-007 approved: persistent AuditReceipts with reconstruction; incognito hashes-only; flag default-off.
- CAE-005B approved: Holodeck adapter uses CandidateSearchPort; legacy meta scorer isolated; flag default-off.
- Rotate to sequential leaf approvals
- CAE-003B approved and done; Stage B leaf tasks completed after unset-budget fix verification.
- Stage B review complete: CAE-003B blocked on token_budget=0 wipe; other Stage B leaves review-approved pending gate.
- Stage A independent review approved CAE-000; task marked done.
- Stage A independent review approved CAE-015; task marked done.

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

- parent-children-complete
- parent-children-complete
- adversarial_multi_turn_active_state_rollback
- tests/test_feed_disclosure_parity.py
- tests/test_aperture_service_baseline_harness.py
- tests/test_disclosure_receipts.py
- tests/test_holodeck_disclosure_parity.py
- tests/test_disclosure_service_bridge_parity.py
- stage-b-parent-children-complete
- stage-b-gate-reverify-CAE-004
- stage-b-gate-reverify-CAE-001
- stage-b-gate-reverify-CAE-003A
