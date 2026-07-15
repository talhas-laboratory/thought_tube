# KERNEL-002-migration-and-persistence-fixtures: Build kernel migration and persistence fixtures

Status: done
Owner: unassigned
Current gate: not_required

## Scope

In: prove that historical and current source families reach the kernel without identity, provenance, branch, lifecycle, or raw-expression loss.

Out: silently coercing a source concept into a kernel type, inventing identity from analogy, or mutating raw event logs.

## Work plan

1. Start only from a KERNEL-001-approved mapping contract.
2. Add a minimized migration fixture for the source family or edge case.
3. Preserve source IDs and raw expressions; map only justified records.
4. Emit semantic-loss/defer warnings for profile concepts.
5. Verify commitment links and branch membership in the resulting bundle.

## Acceptance criteria

- MTSF, SDS, ThoughtShape, and Conversation OS mappings remain traceable.
- No migrated State lacks an explicit `StateCommitment`.
- Mapping reports retain loss warnings and provenance.

## Verification plan

- Run `python3 tools/conversation_os.py foundation migrate-fixture --fixture-path <fixture>`.
- Run `pytest -q tests/test_metaphysical_kernel_migration.py` and the full foundation review before release.

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- See [task execution map](../../../workspaces/metaphysical-kernel-ontology/derived/TASK_EXECUTION_MAP.md); attach fixture paths and results to live verification.
