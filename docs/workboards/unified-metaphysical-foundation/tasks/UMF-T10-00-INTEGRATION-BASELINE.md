# UMF-T10-00-INTEGRATION-BASELINE: T10-00: Establish one integration and release baseline

Status: review
Owner: foundation/release
Current gate: not_required

## Scope

Make “implemented” mean one checkout. Import aperture modules from remediation-pass and hardened Population from the Population branch into a declared release authority.

## Claimed paths

- `src/conversation_os/release_management.py`
- `docs/workspaces/unified-framework-synthesis/derived/T10-00-RECONCILIATION-MATRIX.md`
- Imported on this branch:
  - `src/conversation_os/candidate_admission.py`
  - `src/conversation_os/disclosure_budget_allocator.py`
  - `src/conversation_os/orient_first_compose.py`
  - `src/conversation_os/shape_projection_reader.py`
  - `src/conversation_os/shape_population/`
- Source remotes:
  - `origin/cursor/shape-intelligence-remediation-pass` @ `0c8f367`
  - `origin/codex/shape-population-production-hardening` @ `82a1c35`

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

- Live verify `t10-00-same-checkout-suites` = pass @ commit `00931c94cabd7afb22a1c9ac8ab3510cd6922dca`
- Population suite: 59 passed
- Foundation/release smoke: 22 passed
- Aperture focused gate: `green=True`
- Decision `decision-d2a3fbf3438c`: baseline established on `cursor/t10-wave-01-tasks-a790`
- `runtime.json` union: disclosure rollout remains `legacy`/off; `agents.shape_population` present

## Residual risks

- `shape_projection_reader` still uses legacy `profile:shape_and_semantic_addressing` → T10-01
- Module manifests / hermetic debt for imported modules → T10-19
- Disclosure flags intentionally off → T10-08

## Handoff Notes

- Next Wave 0 sibling: claim `UMF-T10-19-RELEASE-DISCIPLINE`
- Then unlock T10-01 Shape authority cutover
