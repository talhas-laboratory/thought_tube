<!-- generated: workspace continuity export; canonical store remains authoritative -->
<!-- workspace_id: unified-framework-synthesis -->
<!-- canonical_revision: b4d4d802ec0d48f0eca37223c1c706497b698d05c296b1cf4a4cc71982132ef8 -->
<!-- repository_source_revision: 162184b8b04fce8cf6dbd46ef78969ebf8b2410d -->
<!-- generated_at: 2026-07-22T15:13:18+00:00 -->

# Workspace continuity: unified-framework-synthesis

## Resume

Select a task to receive a recommended next action.

## Focus task

- id: ``
- status: ``
- title: _none_

## Recent runs

- T10-18 first slice committed-ready: focused tests passed and task moved to review.
- T10-17 first slice committed-ready: focused test passed and task moved to review.
- Implementation committed and pushed at be212c332a1cc476ce0ed322174c93e7a0bc946f; residuals remain for broader partition/worker-crash/rollback/retraction slices.
- Focused retrieval/evidence authorization suites passed; task is in review with evidence under derived/T10-12-AUTH-PRIVACY.md.
- T10-08 Bridge shadow slice complete.
- T10-14 first benchmark complete.
- T10-07 retrieval repair complete.
- T10-06 Pattern/AntiMatch typing complete; residual retrieval bundle failures handed to T10-07.
- T10-09 temporal/revision complete.
- T10-05 index contracts implemented and verified.
- T10-04 implementation and verification complete.
- Hermetic golden pytest passed; evidence pack published.

## Reasoning

- T10-18 first Shape inspector slice
- T10-17 first agent harness slice
- T10-13 first concurrency slice
- T10-12 first slice on retrieval/evidence ports
- T10-06 Pattern records on retrieval owner
- T10-05 index contracts on CorpusCatalog
- T10-04 implementation decision
- Wave 1 golden ingest-to-retrieve (+rollback) trace archived and hermetic test passes.
- Live path uses build_post_ingest_hook + apply_approved_promotion_live; promotion.py default remains FailClosed.
- Versioned CanonicalShapeProposal + FoundationCanonicalPort apply closed refs only; label-only stays unresolved.
- Canonical Shape authority is profile:shape on FoundationRuntime; legacy id is candidate-only until 2026-08-22.

## Verification

- pytest tests/test_shape_projection_reader.py
- pytest tests/test_metaphysical_kernel_application_sdk.py
- pytest tests/test_shape_population*.py
- pytest tests/test_disclosure_service_bridge_parity.py tests/test_disclosure_contracts.py tests/test_disclosure_receipts.py
- pytest tests/test_shape_candidate_retrieval.py tests/test_evidence_resolver.py
- tests/test_disclosure_rollout.py+receipt_rollout
- tests/test_shape_candidate_retrieval.py
- tests/test_shape_candidate_retrieval.py
- tests/test_shape_candidate_retrieval.py -k pattern
- tests/test_corpus_catalog_snapshot.py
- tests/test_corpus_catalog_snapshot.py
- tests/test_corpus_catalog_snapshot.py
