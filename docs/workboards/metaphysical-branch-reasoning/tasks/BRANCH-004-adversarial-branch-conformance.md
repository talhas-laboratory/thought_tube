# BRANCH-004-adversarial-branch-conformance: Verify branch conformance

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: prove branch semantics resist leakage, contradiction explosion, hidden winner selection, and false conflict classification.

Out: a happy-path-only test suite or unexplained acceptance-test exclusions.

## Work plan

1. Execute every required scenario in [BRANCH_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-branch-reasoning/derived/BRANCH_TEST_AND_RELEASE_GUIDE.md).
2. Add minimized regressions for every defect.
3. Validate continuity from Kernel records to branch result and consumer view.
4. List remaining semantic/open research limits.

## Acceptance criteria

- Contradictory branches remain valid and non-explosive.
- Branch-neutral source reuse and bounded traversal work.
- Every claimed rule has a positive and negative test.

## Verification plan

- Run focused branch/Kernal suites and record exact commands/results in live verification.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Do not close without fixture paths, command output, residual risk, and release-readiness recommendation.
