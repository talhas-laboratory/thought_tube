# UMF-T10-01-SHAPE-AUTHORITY: T10-01: Repair canonical Shape authority and identity

Status: review
Owner: shape-profile
Current gate: not_required

## Scope

Register `profile:shape` as canonical on `FoundationRuntime` / `ProfileRegistry`. Replace broad “unavailable” handling with typed abstentions. Keep legacy profile id candidate-only.

## Claimed paths

- `src/conversation_os/metaphysical_kernel_profile_registry.py`
- `src/conversation_os/metaphysical_kernel_runtime.py`
- `src/conversation_os/metaphysical_kernel_application_sdk.py`
- `src/conversation_os/shape_projection_reader.py` (from T10-00 import)
- ADR under `docs/workspaces/unified-framework-synthesis/derived/`
- `tests/test_shape_authority*.py` (to create)

## Implementation steps

1. ADR: `profile:shape` (+semver) canonical; legacy `profile:shape_and_semantic_addressing` candidate-only with dated retirement.
2. Add `build_shape_profile_v1()` + bootstrap beside field-formation bootstrap.
3. Shape reader over FoundationRuntime/ProfileRegistry.
4. Typed states: absent / incompatible / corrupt / unauthorized / empty / unexpected-failure.
5. Projection reads by branch/scope/perspective/time/maturity/epistemic/governance.
6. Tests for all typed states + legacy retirement.

## Acceptance Criteria

- `profile:shape` bootstrapped; ADR locks canonical id.
- Reader uses FoundationRuntime+ProfileRegistry; legacy id candidate-only with retirement date.
- Typed abstentions; programming errors fail release rather than looking unavailable.
- Projection round trips preserve authority, provenance, lifecycle, branch, scope, abstraction contract.

## Constraints

- Depends on `UMF-T10-00-INTEGRATION-BASELINE`
- Depends on `UMF-SHAPE-004-SHAPECORE-SHAPEVIEW-COMPOSITE`
- Parent: `UMF-PROGRAM-SHAPE`

## Verification Evidence

- `pytest tests/test_shape_projection_reader.py tests/test_shape_authority.py tests/test_shape_population_canonical_port.py tests/test_metaphysical_kernel_application_sdk.py` → **24 passed**
- Live verify pass recorded for the same focused suite
- ADR: `docs/workspaces/unified-framework-synthesis/derived/ADR-SHAPE-PROFILE-ID-DEPRECATION.md` (retirement 2026-08-22)

## Handoff Notes

- `CANONICAL_SHAPE_PROFILE_ID` is now `profile:shape` via `FoundationRuntime` + `ProfileRegistry`
- Typed abstentions: absent / incompatible / corrupt / unauthorized / empty / unexpected_failure
- Programming defects (e.g. `AttributeError`) are no longer masked as unavailability
- SDK `derive_shape` bootstraps `profile:shape` and abstains as `empty:` pending T10-02 mapping (no legacy id)
- Legacy `profile:shape_and_semantic_addressing` remains candidate-only adapter identity
- Next Wave 1: `UMF-T10-02-POPULATION-CANONICAL-MAP`
