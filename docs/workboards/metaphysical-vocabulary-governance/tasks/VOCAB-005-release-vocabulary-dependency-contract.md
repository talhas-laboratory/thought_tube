# VOCAB-005-release-vocabulary-dependency-contract: Release vocabulary dependency contract

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: release a versioned vocabulary contract that profiles and applications can consume without erasing local language.

Out: an unversioned label list, a hidden normalization rule, or consumer integration without a compatibility/migration statement.

## Work plan

1. Freeze mapping, promotion, and evolution contract versions.
2. Publish allowed mapping kinds, lifecycle/governance behavior, migration/deprecation policy, and known limits.
3. State exact Kernel and Branch dependencies.
4. Demonstrate a profile or application consumer rendering the mapping without mutation.
5. Record merge SHA and consumer evidence.

## Acceptance criteria

- Consumers receive a versioned contract, examples, compatibility policy, tests, and merge evidence.
- Documentation makes clear that canonicalization is not forced normalization.

## Verification plan

- Complete the release checklist in [VOCABULARY_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-vocabulary-governance/derived/VOCABULARY_TEST_AND_RELEASE_GUIDE.md).

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Do not close until live verification names the consumer proof, exact SHA, and residual limitations.
