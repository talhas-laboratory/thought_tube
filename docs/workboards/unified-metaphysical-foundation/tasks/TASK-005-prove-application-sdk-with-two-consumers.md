# TASK-005-prove-application-sdk-with-two-consumers: Prove application SDK with two consumers

Status: blocked
Owner: cursor-cloud-agent
Current gate: implementation

## Problem

Kernel runtime and profile registry exist, but no bounded application-facing API proves that materially different products can share the same canonical store and profile contracts without inventing private persistence ontologies.

## Scope

In:

- `FoundationApplicationSdk` with profile-bound mutations and `SdkMutationResult` envelopes;
- authorization and context-budget gates before projection construction;
- abstention paths that preserve canonical records;
- World Studio and Workspace Curator consumer proofs;
- Gate F4 tests.

Out:

- CLI wiring for SDK methods;
- Shape profile implementation;
- production auth integration beyond SDK context flags.

## Acceptance Criteria

- SDK exposes capture, branch, membership, claim, state commit, hold, formation projection, bounded view, provenance, and profile operations.
- Every mutation returns identifiers, branch, scope, provenance, validation results, and compensating-operation metadata.
- Two consumers (World Studio + Workspace Curator) operate on the same canonical store and `profile:field_formation`.
- Unauthorized and over-budget calls abstain without adding mutation records.
- `derive_shape` abstains in Phase 1 without corrupting the kernel bundle.

## Plan

1. Wrap `FoundationRuntime` + `ProfileRegistry` in SDK with `ApplicationContext`.
2. Implement consumer flows for fictional-world capture and workspace insight curation.
3. Add Gate F4 tests for shared store, abstention, and compensating operations.

## Verification Evidence

- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_application_sdk -v` — 7 tests, OK
- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_contracts tests.test_metaphysical_kernel_migration tests.test_metaphysical_kernel_runtime tests.test_metaphysical_kernel_profile_registry tests.test_metaphysical_kernel_application_sdk -v` — 53 tests, OK
- Implementation: `src/conversation_os/metaphysical_kernel_application_sdk.py`

## Updates

- Created: `2026-07-12T14:18:38.454643+00:00`
- Implementation completed (2026-07-12): application SDK and two consumer proofs.

## Handoff Notes

- Foundation workboard Phase 1 stack (TASK-001–005) is code-complete pending human review/merge.
- Optional: opt-in `session_append --foundation-capture` CLI flag using `capture_source_from_event`.
- Blocked pending Gap 1 repair per .
- Audit alignment: candidate SDK work exists on the unmerged branch, but TASK-005 is blocked until TASK-004 profile conformance is revalidated.

## Handoff Notes

- See `GAP-REPORT-2026-07-12.md`; unblock only after TASK-004 revalidation and live-ledger reconciliation.
