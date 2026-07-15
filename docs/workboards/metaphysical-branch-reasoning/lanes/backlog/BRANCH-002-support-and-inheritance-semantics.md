# BRANCH-002-support-and-inheritance-semantics: Implement support and inheritance semantics

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: implement the locked inheritance resolver and branch/scope-specific four-valued support semantics.

Out: physical record duplication as inheritance, cross-branch leakage, global evidence aggregation, or treating support as truth.

## Work plan

1. Require BRANCH-001 and the relevant Kernel contract version.
2. Implement parent read/inherit, local assertion, retraction, replacement, and scope-change behavior.
3. Compute support only from explicit polarity and usable evidence in a declared branch/scope.
4. Add the full outcome matrix and source-reuse fixtures.

## Acceptance criteria

- `supported_only`, `opposed_only`, `both`, and `unresolved` are all testable.
- Retraction changes only the child view; source/referent identity remains reusable.
- Scope or perspective difference is not automatically logical contradiction.

## Verification plan

- Run the future branch suite described in [BRANCH_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-branch-reasoning/derived/BRANCH_TEST_AND_RELEASE_GUIDE.md) plus required Kernel tests.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Include the exact Kernel version, behavior table, fixture paths, and unimplemented cases.
