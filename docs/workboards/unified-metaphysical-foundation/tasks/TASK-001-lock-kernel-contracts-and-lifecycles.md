# TASK-001-lock-kernel-contracts-and-lifecycles: Lock kernel contracts and lifecycles

Status: blocked
Owner: cursor-cloud-agent
Current gate: implementation

## Problem

The canonical paper defines the universal foundation in prose and examples, but implementation cannot begin safely until its first kernel contracts and lifecycle rules are machine-readable and adversarially testable.

## Scope

In:

- universal record envelope;
- `SourceFragment`, `Referent`, `Scope`, `State`, `Claim`, `RelationInstance`, `Provenance`, and `ModelBranch`;
- `BranchMembership` and `StateCommitment`;
- maturity, epistemic, and governance lifecycle axes;
- minimal `ProfileDefinition` and `ProfileConformanceResult` needed to validate kernel/profile separation;
- valid and invalid fixtures;
- schema and invariant tests.

Out:

- persistence services and database migrations;
- semantic extraction, LLM behavior, embeddings, or retrieval;
- Field, Formation, Shape, Conversation, Agent, or Execution profile implementation;
- application SDK or product surfaces;
- historical data migration beyond fixtures.

## Acceptance Criteria

- Every contract cites its governing version 1.1 section.
- Fields have explicit type, cardinality, nullability, branch behavior, and lifecycle applicability.
- Branch-neutral records can be shared without duplication.
- Branch-bound interpretation requires `BranchMembership`.
- No Claim can become an adopted State without `StateCommitment`.
- Maturity, epistemic standing, and governance cannot be collapsed into one status.
- Profile definitions cannot redefine kernel semantics.
- Valid fixtures pass and invalid fixtures fail for the intended reason.
- Repo overview and targeted tests finish with zero errors or warnings.

## Plan

1. Inspect existing owners in `models.py`, `storage.py`, schema helpers, and tests before choosing edit paths.
2. Extract the envelope and first contracts from paper sections 4–6 and 22.
3. Choose one machine-readable schema mechanism already compatible with the repo.
4. Add fixtures before runtime behavior.
5. Add invariant tests for branch isolation, provenance closure, StateCommitment, lifecycle independence, and profile conformance.
6. Refresh and validate the repo overview.

Generated context pack: `context/task_packs/unified-metaphysical-foundation-schema-lock.{json,md}`.

## Verification Evidence

- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_contracts -v` — 12 tests, OK
- `python3 tools/conversation_os.py repo-overview refresh` — 0 errors
- `python3 tools/conversation_os.py repo-overview validate` — 0 errors; 1 repo-wide warning (129 modules without manifests on this branch, pre-existing)
- Implementation: `src/conversation_os/metaphysical_kernel.py`, `src/conversation_os/metaphysical_kernel_contracts.py`
- Fixtures: `tests/fixtures/metaphysical_kernel/*.json` (2 valid, 7 invalid including Gap 1 adversarial cases)

## Updates

- Created: `2026-07-12T14:18:38.450683+00:00`
- Readiness completed: canonical source, scope, failure modes, acceptance criteria, and test strategy recorded.
- Implementation completed (2026-07-12): kernel record dataclasses, contract validators, fixtures, and 12 invariant tests.
- Gap 1 repaired (2026-07-13): `validate_state_adoption_links` + four adversarial fixtures; see `REVIEWER-START.md` §4.
- Blocked by audit: `blocker-7f7662afad54` until live ledger reconciled per `GAP-2-RECONCILIATION.md`.

## Handoff Notes

- Start from the canonical paper, not the historical unified synthesis.
- Run the engineering guard with the smallest owner paths before editing code.
- Main failure mode: designing a second abstract schema beside existing records instead of defining a migration-compatible canonical contract.
- Residual risk before implementation: the local branch diverges from the cloud implementation branch; inspect rather than blindly import owners.
- Do not advance or merge the Phase 1 branch until the audit report's P1 contract repair and live-ledger reconciliation are verified.
