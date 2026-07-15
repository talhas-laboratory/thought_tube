# KERNEL-004-kernel-conformance-suite: Verify kernel conformance suite

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: prove each claimed kernel obligation under normal, invalid, adversarial, migration, and consumer conditions.

Out: superficial schema-only checks, test exclusions without a documented reason, or a claim of framework completion beyond tested scope.

## Work plan

1. Map invariant/obligation rows to tests and fixtures.
2. Add adversarial cases for cross-branch leakage, state/claim collapse, missing provenance, lifecycle collapse, and profile redefinition.
3. Run focused suites, full foundation review, and consumer proof.
4. Record gaps as residual risks or new tasks rather than ignoring them.

## Acceptance criteria

- Framework acceptance and adversarial invariants pass with traceable evidence.
- Every repaired defect has a regression test or fixture.
- Coverage gaps are explicit and owned.

## Verification plan

- Run the commands in [kernel test/release guide](../../../workspaces/metaphysical-kernel-ontology/derived/KERNEL_TEST_AND_RELEASE_GUIDE.md).

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Attach command output, fixture inventory, merge SHA, and residual risks through live verification.
