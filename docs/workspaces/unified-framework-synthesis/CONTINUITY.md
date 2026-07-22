<!-- generated: workspace continuity export; canonical store remains authoritative -->
<!-- workspace_id: unified-framework-synthesis -->
<!-- canonical_revision: baf29cb8b9755094f07224efcfcaa13eedba8d700faccba69545dfcb9e3386ce -->
<!-- repository_source_revision: 162184b8b04fce8cf6dbd46ef78969ebf8b2410d -->
<!-- generated_at: 2026-07-22T14:09:11+00:00 -->

# Workspace continuity: unified-framework-synthesis

## Resume

Select a task to receive a recommended next action.

## Focus task

- id: ``
- status: ``
- title: _none_

## Recent runs

- T10-05 index contracts implemented and verified.
- T10-04 implementation and verification complete.
- Hermetic golden pytest passed; evidence pack published.
- Focused suites passed; task in review. Golden trace is next.
- Focused suites passed; task in review.
- Focused verification passed; task moved to review.
- Repair canonical Shape authority to profile:shape
- T10-19 in review; Wave 0 complete enough to unlock T10-01.
- T10-00 baseline in review with suite evidence; handoff to T10-19 and reviewers.
- Wave 0-1 task set created; handing off for projection publish and T10-00 start.
- Task created in live backlog; projections published for handoff.

## Reasoning

- T10-05 index contracts on CorpusCatalog
- T10-04 implementation decision
- Wave 1 golden ingest-to-retrieve (+rollback) trace archived and hermetic test passes.
- Live path uses build_post_ingest_hook + apply_approved_promotion_live; promotion.py default remains FailClosed.
- Versioned CanonicalShapeProposal + FoundationCanonicalPort apply closed refs only; label-only stays unresolved.
- Canonical Shape authority is profile:shape on FoundationRuntime; legacy id is candidate-only until 2026-08-22.

## Verification

- tests/test_corpus_catalog_snapshot.py
- tests/test_corpus_catalog_snapshot.py
- pytest tests/test_shape_population_golden_trace.py
- pytest tests/test_shape_population_canonical_map.py tests/test_shape_population_promotion.py tests/test_shape_population_remediation_lifecycle.py
- pytest tests/test_shape_population_canonical_map.py tests/test_shape_population_canonical_port.py tests/test_shape_population_promotion.py
- pytest tests/test_shape_projection_reader.py tests/test_shape_authority.py tests/test_shape_population_canonical_port.py tests/test_metaphysical_kernel_application_sdk.py
- t10-19-release-discipline
- t10-00-same-checkout-suites
- role_assignment_contracts
- composition_profile_contracts_after_merge
- composition_profile_contracts
- quality_instance_profile_contracts_after_merge
