# KERNEL-001-atomic-obligation-and-contract-lock: Refine kernel obligations and lock contracts

Status: done
Owner: cursor:cloud-umf
Current gate: not_required

## Scope

In: convert assigned v1.1 kernel sections into atomic obligations; compare them to Phase 1 owners, fixtures, and tests; lock the next contract boundary.

Out: runtime expansion, product fields, silently changing kernel meaning, or treating an existing dataclass as proof of full coverage.

## Work plan

1. Read the [build guide](../../../workspaces/metaphysical-kernel-ontology/derived/AGENT_BUILD_GUIDE.md) and [obligation register](../../../workspaces/metaphysical-kernel-ontology/derived/KERNEL_OBLIGATION_REGISTER.md).
2. Map every requirement to existing owner, test/fixture, gap, downstream consumer, and uncertainty.
3. Draft the public contract with branch, lifecycle, provenance, and compatibility behavior.
4. Record unresolved semantic choices in the parent workspace before implementation depends on them.

## Acceptance criteria

- Every assigned obligation has one owner, contract target, and explicit unknowns.
- Fields have type, cardinality, nullability, branch behavior, lifecycle applicability, and migration impact.
- Profiles cannot redefine kernel semantics.
- No product-specific field enters the universal kernel.

## Verification plan

- Review the register against framework §§4–6 and the Phase 1 implementation review.
- Run `python3 tools/conversation_os.py foundation review` after any contract/fixture change.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Use the [task execution map](../../../workspaces/metaphysical-kernel-ontology/derived/TASK_EXECUTION_MAP.md). Record task status and evidence through the live API.
