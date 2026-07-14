# TASK-002-build-historical-and-current-migration-fixtures: Build historical and current migration fixtures

Status: review
Owner: cursor-cloud-agent
Current gate: implementation

## Problem

Historical MTSF, ThoughtShape, and SDS concepts plus current Conversation OS records exist in the repo, but there is no deterministic, testable mapping into the v1.1 kernel. Without migration fixtures and Gate F1 checks, Phase 1 implementation risks silently rewriting source vocabulary or collapsing Claim into State.

## Scope

In:

- deterministic migration fixtures for MTSF, ThoughtShape, SDS, and Conversation OS source families;
- `metaphysical_kernel_migration.py` mappers with mapping rules, loss reports, and reversibility metadata;
- Gate F1 invariant checks (no analogy-as-identity, no State without StateCommitment);
- adversarial invalid fixture for uncommitted State;
- tests covering all four source families.

Out:

- live persistence or database migration;
- profile runtime materialization (ShapeCore, AntiMatch, TransformationProcess deferred to loss reports);
- full round-trip inverse loaders;
- TASK-003 vertical slice wiring.

## Acceptance Criteria

- Every supported source family has at least one valid migration fixture citing Appendix F authority.
- Mappings preserve source identifiers in `MappingRule.source_id`.
- SDS States migrate as Claims until explicit StateCommitment exists.
- ThoughtShape Holds migrate as held SourceFragments, not States.
- MTSF Assertions migrate as Claims, never as States.
- Analogy evaluation maps to branch-scoped Claim, never Referent identity.
- Valid fixtures pass `validate_migration_fixture`; migrated bundles pass `validate_fixture_bundle`.
- Invalid uncommitted State fixture fails kernel validation.

## Plan

1. Reuse `SystemDynamicSignature` golden structure from existing tests for SDS fixture.
2. Add synthetic MTSF and ThoughtShape historical fixtures from synthesis docs.
3. Add Conversation OS session/events/concept/formation/workspace knowledge fixture.
4. Implement family-specific migrators returning `MigrationResult`.
5. Add Gate F1 validators and tests.

## Verification Evidence

- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_migration -v` — 14 tests, OK
- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_contracts -v` — 12 tests, OK (TASK-001 regression)
- Fixtures: `tests/fixtures/migration/*.json` (4 valid families + 1 invalid)
- Implementation: `src/conversation_os/metaphysical_kernel_migration.py`

## Updates

- Created: `2026-07-12T14:18:38.451592+00:00`
- Implementation completed (2026-07-12): migration mappers, four source-family fixtures, Gate F1 tests.

## Handoff Notes

- Profile-level targets (CandidateShape, AntiMatch, feedback loops) are recorded in `loss_report` and `MappingRule.semantic_loss_warnings`, not materialized as kernel records yet.
- TASK-003 should wire `session_append` → `SourceFragment` using the Conversation OS migrator patterns established here.
- Blocked pending Gap 1 repair per .
- Audit alignment: candidate migration work exists on the unmerged branch, but TASK-002 is blocked by TASK-001 contract repair and missing live verification evidence.

## Handoff Notes

- See `GAP-REPORT-2026-07-12.md`; unblock only after TASK-001 repair and live-ledger reconciliation.
