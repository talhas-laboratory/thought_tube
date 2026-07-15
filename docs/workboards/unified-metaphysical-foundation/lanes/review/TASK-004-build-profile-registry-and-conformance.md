# TASK-004-build-profile-registry-and-conformance: Build profile registry and conformance

Status: review
Owner: cursor-cloud-agent
Current gate: implementation

## Problem

The Phase 1 kernel runtime can capture and branch records, but applications cannot yet declare which governed profile they use, validate profile invariants, or upgrade profile versions without silent semantic drift.

## Scope

In:

- `ProfileRegistry` with semantic versioning and acyclic dependency validation;
- built-in Field and Formation profile (`profile:field_formation` v1.0.0);
- application-to-profile bindings with invariant preservation;
- profile conformance evaluation against active kernel bundles;
- profile upgrade staleness reports;
- Gate F3 tests.

Out:

- Shape, Conversation, Pattern, Agent, and Execution profiles beyond the initial Field/Formation bootstrap;
- full profile record persistence for `field`, `hold`, and `formation` instances;
- application SDK surface (TASK-005).

## Acceptance Criteria

- Profiles register with semantic versions and reject duplicate versions.
- Profile record types cannot duplicate kernel record kinds.
- Profiles cannot redefine forbidden kernel semantics.
- Dependency cycles are rejected.
- Application bindings cannot weaken required invariants.
- Conformance evaluation passes on a valid vertical slice bundle.
- Profile upgrades identify stale records when profile record types are removed.

## Plan

1. Implement registry on top of `FoundationRuntime` append-only store.
2. Bootstrap Field and Formation normative profile (§8A).
3. Add binding, conformance, and upgrade planning APIs.
4. Add Gate F3 tests and profile metadata fixture.

## Verification Evidence

- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_profile_registry -v` — 9 tests, OK
- `PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_contracts tests.test_metaphysical_kernel_migration tests.test_metaphysical_kernel_runtime tests.test_metaphysical_kernel_profile_registry -v` — 46 tests, OK
- Implementation: `src/conversation_os/metaphysical_kernel_profile_registry.py`
- Fixture: `tests/fixtures/metaphysical_kernel/profile_field_formation_v1_0_0.json`

## Updates

- Created: `2026-07-12T14:18:38.453409+00:00`
- Implementation completed (2026-07-12): profile registry, Field/Formation bootstrap, Gate F3 tests.

## Handoff Notes

- TASK-005 should expose bounded SDK methods (`capture_source`, `create_branch`, etc.) bound to registered profiles.
- Profile record instances (`field`, `hold`, `formation`) remain profile-layer projections; kernel store stays canonical.
- Blocked pending Gap 1 repair per .
- Audit alignment: candidate profile work exists on the unmerged branch and the Phase 1 review evidence is recorded; TASK-004 is in `review` pending branch review.

## Handoff Notes

- See `GAP-REPORT-2026-07-12.md`; unblock only after TASK-003 revalidation and live-ledger reconciliation.
