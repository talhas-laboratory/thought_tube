<!-- generated: workspace continuity export; canonical store remains authoritative -->
<!-- workspace_id: unified-framework-synthesis -->
<!-- canonical_revision: 14d945bfc4fe30ba3e89faae3654fc02061e433021a84d87e6d1202b56529426 -->
<!-- repository_source_revision: 162184b8b04fce8cf6dbd46ef78969ebf8b2410d -->
<!-- generated_at: 2026-07-22T15:27:32+00:00 -->

# Workspace continuity: unified-framework-synthesis

## Resume

Select a task to receive a recommended next action.

## Focus task

- id: ``
- status: ``
- title: _none_

## Recent runs

- Implemented, verified, evidenced, and moved to review.
- T10-10 moved to review with verification evidence and residuals documented.
- Wave 4 parent moved to review after T10-17 and T10-18 reached review.
- T10-18 first slice committed-ready: focused tests passed and task moved to review.
- T10-17 first slice committed-ready: focused test passed and task moved to review.
- Implementation committed and pushed at be212c332a1cc476ce0ed322174c93e7a0bc946f; residuals remain for broader partition/worker-crash/rollback/retraction slices.
- Focused retrieval/evidence authorization suites passed; task is in review with evidence under derived/T10-12-AUTH-PRIVACY.md.
- T10-08 Bridge shadow slice complete.
- T10-14 first benchmark complete.
- T10-07 retrieval repair complete.
- T10-06 Pattern/AntiMatch typing complete; residual retrieval bundle failures handed to T10-07.
- T10-09 temporal/revision complete.

## Reasoning

- T10-10 first executable cybernetic compile slice
- Wave 4 parent review run closed
- Wave 4 parent ready for review
- T10-18 first Shape inspector slice
- T10-17 first agent harness slice
- T10-13 first concurrency slice
- T10-12 first slice on retrieval/evidence ports
- T10-06 Pattern records on retrieval owner
- T10-05 index contracts on CorpusCatalog
- T10-04 implementation decision
- Wave 1 golden ingest-to-retrieve (+rollback) trace archived and hermetic test passes.
- Live path uses build_post_ingest_hook + apply_approved_promotion_live; promotion.py default remains FailClosed.

## Verification

- pytest tests/test_shape_candidate_retrieval.py -q
- python3 -m compileall -q src/conversation_os/metaphysical_kernel_profile_registry.py
- pytest tests/test_metaphysical_kernel_profile_registry.py
- pytest tests/test_metaphysical_kernel_application_sdk.py tests/test_shape_projection_reader.py
- pytest tests/test_shape_projection_reader.py
- pytest tests/test_metaphysical_kernel_application_sdk.py
- pytest tests/test_shape_population*.py
- pytest tests/test_disclosure_service_bridge_parity.py tests/test_disclosure_contracts.py tests/test_disclosure_receipts.py
- pytest tests/test_shape_candidate_retrieval.py tests/test_evidence_resolver.py
- tests/test_disclosure_rollout.py+receipt_rollout
- tests/test_shape_candidate_retrieval.py
- tests/test_shape_candidate_retrieval.py
