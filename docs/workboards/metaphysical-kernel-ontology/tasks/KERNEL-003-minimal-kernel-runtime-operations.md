# KERNEL-003-minimal-kernel-runtime-operations: Implement minimal kernel runtime operations

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: add only the smallest public kernel operation required by a locked obligation and a real consumer.

Out: new product stores, profile-specific semantics, implicit State adoption, or unproven generic abstractions.

## Work plan

1. Name the existing owner module and run the engineering guard.
2. Add the smallest operation with input validation, provenance, and bounded failure behavior.
3. Exercise it through the shared store/runtime or SDK, not a private test-only pathway.
4. Add focused regression and end-to-end tests.

## Acceptance criteria

- The operation preserves kernel invariants and append-only behavior.
- A bounded vertical slice demonstrates it without product-specific fields.
- Failure or abstention does not create misleading records.

## Verification plan

- Run focused module tests, then `python3 tools/conversation_os.py foundation slice ...`.
- Run `python3 tools/conversation_os.py foundation review` before review.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Follow [task execution map](../../../workspaces/metaphysical-kernel-ontology/derived/TASK_EXECUTION_MAP.md); include owner-module rationale and residual risk.
