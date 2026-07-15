# VOCAB-004-vocabulary-conformance-suite: Verify vocabulary conformance

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: prove vocabulary behavior preserves meaning, avoids forbidden redefinition, and exposes uncertainty/evolution honestly.

Out: only happy-path registry tests, silent migration loss, or a claim that canonical labels are universal interpretation.

## Work plan

1. Run every adversarial scenario in [VOCABULARY_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-vocabulary-governance/derived/VOCABULARY_TEST_AND_RELEASE_GUIDE.md).
2. Add positive/negative tests for mapping kinds, level/scope behavior, promotion, redefinition, deprecation, and stale dependents.
3. Preserve minimized fixtures for all repaired defects.
4. Identify any unresolved requirements as owned follow-up work.

## Acceptance criteria

- Vocabulary-preservation and extension-safety tests pass.
- Raw expression, scope, confidence, and provenance survive mapping/evolution.
- Every claimed contract rule has executable evidence.

## Verification plan

- Run focused vocabulary tests, required Kernel/Branch tests, and consumer rendering proof.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Attach commands/results, fixtures, residual risks, and release recommendation in the live workspace.
