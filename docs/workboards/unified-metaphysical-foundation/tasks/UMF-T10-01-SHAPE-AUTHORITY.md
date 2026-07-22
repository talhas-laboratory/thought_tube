# UMF-T10-01-SHAPE-AUTHORITY: T10-01: Repair canonical Shape authority and identity

Status: backlog
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

- Not recorded in this projection yet.

## Handoff Notes

- Today only `profile:field_formation` is bootstrapped locally; SDK still abstains on legacy Shape profile id.
