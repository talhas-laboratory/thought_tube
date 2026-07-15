# VOCAB-003-promotion-and-evolution-workflow: Implement promotion and ontology evolution workflow

Status: backlog
Owner: unassigned
Current gate: not_required

## Scope

In: implement explicit proposal/review/promotion/deprecation/evolution operations with reversible migration and impact visibility.

Out: destructive type edits, promotion by model fluency, hidden stale dependents, or conversion of governance approval into epistemic truth.

## Work plan

1. Require VOCAB-002 and applicable Branch behavior.
2. Model promotion as a governed record with steward, rationale, scope, and outcome.
3. Version each definition change; retain the prior definition.
4. Identify affected records, migration plan, semantic-loss warnings, and stale Shape/compiled dependents.
5. Test rejection and reversal as first-class outcomes.

## Acceptance criteria

- Promotion records and compatibility rules enforce layered governance.
- Version changes are addressable, reversible, and impact-aware.
- A governed term may remain epistemically unresolved.

## Verification plan

- Run promotion/evolution fixtures and the adversarial cases in [VOCABULARY_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-vocabulary-governance/derived/VOCABULARY_TEST_AND_RELEASE_GUIDE.md).

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Record migrations, stale dependents, and residual semantic loss through live verification.
