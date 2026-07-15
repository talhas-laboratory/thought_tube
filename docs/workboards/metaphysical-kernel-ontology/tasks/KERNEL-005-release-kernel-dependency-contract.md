# KERNEL-005-release-kernel-dependency-contract: Release kernel dependency contract

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: turn verified kernel behavior into a versioned dependency contract that Branch and Vocabulary can consume safely.

Out: declaring the entire framework released, changing downstream semantics without coordination, or hiding Phase 1 limits.

## Work plan

1. Freeze the contract version and compatibility classification.
2. Publish supported records/operations, invariants, migrations, failure behavior, and known limits.
3. Update provider/consumer dependency contracts.
4. Obtain a consumer smoke proof and record exact SHA.

## Acceptance criteria

- Consumers receive a versioned contract, compatibility statement, migration notes, tests, and merge evidence.
- Downstream programs can identify the exact kernel version they depend on.

## Verification plan

- Run the complete kernel release ladder in [KERNEL_TEST_AND_RELEASE_GUIDE.md](../../../workspaces/metaphysical-kernel-ontology/derived/KERNEL_TEST_AND_RELEASE_GUIDE.md).
- Verify dependency links with Branch and Vocabulary owners.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Do not close until live verification names the release SHA, consumer evidence, and remaining limitations.
