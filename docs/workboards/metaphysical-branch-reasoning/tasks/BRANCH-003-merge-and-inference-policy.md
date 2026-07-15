# BRANCH-003-merge-and-inference-policy: Implement merge and inference policy

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: implement merge assessment and inference policy as provenance-bearing, candidate-producing operations.

Out: automatic conflict resolution, inference that emits a State or executable rule directly, or hidden lifecycle/scope filters.

## Work plan

1. Implement `MergeAssessment` with shared records, compatible additions, conflicts, assumptions, scope differences, identity mappings, and unresolved items.
2. Define an inference request that names branches, scope, perspective, lifecycle filters, relation families, contradiction policy, and candidate output.
3. Implement explicit `both` paths: preserve, branch, clarify, or abstain.
4. Add provenance and conflict-classification tests.

## Acceptance criteria

- Merge never silently selects a winner.
- Inference output remains a candidate Claim with provenance.
- Every abstention is inspectable and non-destructive.

## Verification plan

- Exercise merge conflicts, scope mismatch, perspective divergence, and `both` inference fixtures.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- See [TASK_EXECUTION_MAP.md](../../../workspaces/metaphysical-branch-reasoning/derived/TASK_EXECUTION_MAP.md); document consumer-facing contract changes.
