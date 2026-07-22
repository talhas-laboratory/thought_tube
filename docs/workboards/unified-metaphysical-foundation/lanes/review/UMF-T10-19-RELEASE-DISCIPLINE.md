# UMF-T10-19-RELEASE-DISCIPLINE: T10-19: Close repo and release-discipline debt for Wave 0 modules

Status: review
Owner: engineering
Current gate: not_required

## Scope

For every module touched by T10-00 imports, restore release honesty: manifests, hermetic green, live/unit split, stale-artifact gates, deprecation windows.

## Claimed paths

- `context/substrate/modules/kernel.disclosure.*.json` (27 new manifests)
- `src/conversation_os/codebase_overview.py` (used via freshness gate)
- `src/conversation_os/engineering_guard.py` (existing stale/missing enforcement)
- `src/conversation_os/release_management.py` (`evaluate_codebase_freshness_gate`)
- `src/conversation_os/aperture_release_gate.py` (truthful focused-suite summary parsing)
- `pytest.ini` (live/hermetic markers)
- `tests/test_agent_bridge_live.py` (`pytest.mark.live`)
- `docs/workspaces/unified-framework-synthesis/derived/ADR-SHAPE-PROFILE-ID-DEPRECATION.md`

## Acceptance Criteria

- Overview refresh/validate: zero errors/warnings/missing production manifests for touched modules.
- Hermetic unit suite green from fresh clone; live tests reported separately.
- Release gate fails on stale artifacts / drift / unregistered modules.
- Deprecation window documented for legacy Shape profile id.

## Verification Evidence

- `repo-overview validate`: fresh=true, missing_manifest_count=0, errors=0, warnings=0, manifests=189
- `evaluate_codebase_freshness_gate`: passed (includes ADR presence check)
- Population focused: 59 passed
- Aperture focused gate: green, 132 passed
- Release/aperture unit tests: 11 passed
- Live marker: `tests/test_agent_bridge_live.py` marked `live`; hermetic guidance `pytest -m "not live"`

## Residual risks

- Some non-focused admission tests (`test_fail_empty_admission.py`) can fail without a materialised corpus catalog snapshot; Wave 2 T10-04/T10-07 own corpus readiness. Focused aperture suite remains the Wave 0 release bar.
- Generated overview artifacts are gitignored in some environments; operators must run `repo-overview refresh` before release claims.

## Handoff Notes

- Next: claim `UMF-T10-01-SHAPE-AUTHORITY` to cut `shape_projection_reader` from legacy id to `profile:shape`.
