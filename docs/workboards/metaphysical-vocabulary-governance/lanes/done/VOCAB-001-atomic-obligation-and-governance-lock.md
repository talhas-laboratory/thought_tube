# VOCAB-001-atomic-obligation-and-governance-lock: Refine vocabulary obligations and governance lock

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: turn §8, §22, and §27.15 into an atomic governance contract for vocabulary levels, mappings, promotion, constraints, and evolution.

Out: automatic normalization, changing Kernel semantics, forced promotion, or treating a mapping as identity without explicit confirmation.

## Work plan

1. Read the [build guide](../../../workspaces/metaphysical-vocabulary-governance/derived/AGENT_BUILD_GUIDE.md), both dependency contracts, and [obligation register](../../../workspaces/metaphysical-vocabulary-governance/derived/VOCABULARY_OBLIGATION_REGISTER.md).
2. Define public records and required fields for raw expressions, entries, mappings, promotion, deprecation, and evolution.
3. Specify mapping kinds, branch/scope behavior, lifecycle axes, stewardship, and abstention.
4. Write promotion and migration decision tables; record ambiguity through the parent workspace.

## Acceptance criteria

- Levels, promotion authority, mappings, and unresolved questions are explicit.
- Source terms and provenance cannot be erased by any contract path.
- Kernel redefinition and branch-local-to-global coercion are forbidden.

## Verification plan

- Review against §8 and §22; add table/JSON fixtures for representative raw, workspace, model-local, and governed terms.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Use [TASK_EXECUTION_MAP.md](../../../workspaces/metaphysical-vocabulary-governance/derived/TASK_EXECUTION_MAP.md); live API owns task status and evidence.
