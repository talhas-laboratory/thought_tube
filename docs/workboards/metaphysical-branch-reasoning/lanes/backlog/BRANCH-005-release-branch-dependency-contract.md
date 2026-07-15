# BRANCH-005-release-branch-dependency-contract: Release branch dependency contract

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: publish the verified Branch contract for Vocabulary and future profile/execution consumers.

Out: unversioned assumptions, a claim of global truth semantics, or downstream integration without a consumer proof.

## Work plan

1. Freeze contract and Kernel dependency versions.
2. Publish supported branch, merge, support, and inference operations with limitations.
3. State compatibility and migration behavior.
4. Run a Vocabulary or profile-consumer smoke proof and record SHA.

## Acceptance criteria

- Consumers receive versioned semantics, examples, known limits, and merge evidence.
- Documentation states that weights are task-relative and merges do not choose winners.

## Verification plan

- Complete the release evidence checklist in [BRANCH_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-branch-reasoning/derived/BRANCH_TEST_AND_RELEASE_GUIDE.md).

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Close only after live verification cites consumer evidence, exact SHA, and residual limits.
