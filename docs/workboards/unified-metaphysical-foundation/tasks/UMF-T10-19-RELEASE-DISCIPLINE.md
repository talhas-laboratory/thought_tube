# UMF-T10-19-RELEASE-DISCIPLINE: T10-19: Close repo and release-discipline debt for Wave 0 modules

Status: ready
Owner: engineering
Current gate: not_required

## Scope

For every module touched by T10-00 imports, restore release honesty: manifests, hermetic green, live/unit split, stale-artifact gates, deprecation windows.

## Claimed paths

- `src/conversation_os/codebase_overview.py`
- `src/conversation_os/engineering_guard.py`
- `src/conversation_os/release_management.py`
- `context/substrate/modules/*.json` for imported disclosure/Shape/Population modules
- pytest markers for live vs hermetic suites
- Deprecation note for `profile:shape_and_semantic_addressing` → `profile:shape`

## Implementation steps

1. Run `repo-overview refresh`; fail release on stale generated artifacts.
2. Add/repair production module manifests for imported aperture + Population modules.
3. Separate live-service tests with markers; keep hermetic suite independently green.
4. Gate release on new debt, contract drift, unregistered modules, checksum/deps.
5. Document deprecation/migration window for legacy Shape profile id.

## Acceptance Criteria

- Overview refresh/validate: zero errors/warnings/missing production manifests for touched modules.
- Hermetic unit suite green from fresh clone; live tests reported separately.
- Release gate fails on stale artifacts / drift / unregistered modules.
- Deprecation window documented for legacy Shape profile id.

## Constraints

- Depends on `UMF-T10-00-INTEGRATION-BASELINE`
- Parent: `UMF-T10-WAVE-01-SHAPE-LIFECYCLE`

## Verification Evidence

- Not recorded in this projection yet.

## Handoff Notes

- Do in parallel with T10-00 for touched paths; do not claim Wave 1 exit without this.
