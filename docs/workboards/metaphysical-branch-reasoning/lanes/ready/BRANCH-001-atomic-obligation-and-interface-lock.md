# BRANCH-001-atomic-obligation-and-interface-lock: Refine branch obligations and lock interfaces

Status: ready
Owner: unassigned
Current gate: not_required

## Scope

In: turn §7 into atomic, public, Kernel-compatible contracts for inheritance, support, conflict, merge, inference, and abstention.

Out: a private runtime, global truth selection, implicit negation, or a change to Kernel identity/provenance/state rules.

## Work plan

1. Read the [build guide](../../../workspaces/metaphysical-branch-reasoning/derived/AGENT_BUILD_GUIDE.md), Kernel dependency contract, and [obligation register](../../../workspaces/metaphysical-branch-reasoning/derived/BRANCH_OBLIGATION_REGISTER.md).
2. Create outcome tables for inheritance and all four support values.
3. Define record/operation inputs, outputs, scope compatibility, provenance, lifecycle filters, errors, and abstention.
4. Identify the smallest owner module only after engineering guard.

## Acceptance criteria

- §7 obligations, Kernel assumptions, and safe `both` behavior are explicit and reviewable.
- Every interface says how it behaves when evidence, membership, or compatible scope is absent.
- No contract allows an implicit winner selection.

## Verification plan

- Review contract tables against §§7.2–7.7 and Kernel fixtures.
- Add table fixtures before implementation; record unresolved choices as parent decisions.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- The authoritative sequence is in [TASK_EXECUTION_MAP.md](../../../workspaces/metaphysical-branch-reasoning/derived/TASK_EXECUTION_MAP.md); live API owns status/evidence.
