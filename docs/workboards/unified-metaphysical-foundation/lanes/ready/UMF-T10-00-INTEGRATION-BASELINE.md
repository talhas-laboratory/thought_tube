# UMF-T10-00-INTEGRATION-BASELINE: T10-00: Establish one integration and release baseline

Status: ready
Owner: foundation/release
Current gate: not_required

## Scope

Make “implemented” mean one checkout. Import aperture modules from remediation-pass and hardened Population from the Population branch into a declared release authority.

## Claimed paths

- `src/conversation_os/release_management.py`
- `docs/workspaces/unified-framework-synthesis/derived/T10-00-RECONCILIATION-MATRIX.md` (to create)
- Import/merge targets:
  - `src/conversation_os/candidate_admission.py`
  - `src/conversation_os/disclosure_budget_allocator.py`
  - `src/conversation_os/orient_first_compose.py`
  - `src/conversation_os/shape_projection_reader.py`
  - `src/conversation_os/shape_population/`
- Source remotes:
  - `origin/cursor/shape-intelligence-remediation-pass`
  - `origin/codex/shape-population-production-hardening`

## Implementation steps

1. Declare integration branch + release commit as code authority.
2. Write reconciliation matrix for every relevant commit: owned paths, conflicts, tests, disposition.
3. Merge aperture modules; import Population without stale projections/LFS junk.
4. Resolve conflicts by v1.1 semantics / live API coordination / selected Git baseline.
5. Extend `release_management.py` manifest fields (schema/profile/prompt/model/policy/migration/flag/corpus/benchmark).
6. Prove same-checkout suites: foundation, Population, disclosure/retrieval, release.

## Acceptance Criteria

- Declared integration branch and release commit are documented as code authority.
- Reconciliation matrix covers remediation-pass and Population hardening with dispositions.
- Same checkout runs foundation, Population, disclosure/retrieval, and release suites.
- `release_management.py` emits the versioned release manifest.

## Constraints

- Do not use blind `git add -A`; inspect staged paths.
- Parent: `UMF-T10-WAVE-01-SHAPE-LIFECYCLE`

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Current local checkout lacks aperture admission modules and `shape_population/`; they exist only on remotes until this task lands.
