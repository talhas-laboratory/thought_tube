# UMF-SHAPE-004 ShapeCore/ShapeView/composite lifecycle evidence

## Scope

First slice for ShapeCore, ShapeView, ShapeRecord, DimensionalShape, and CompositeShape contract validation in `src/conversation_os/metaphysical_kernel_profile_registry.py`.

## What landed

- `composite_shape` now requires `boundary_ref`, `scale`, `temporal_scope`, and `branch_id`.
- Optional `coupling_specs` must be non-empty mappings with valid coupling kinds.
- Added `dimensional_shape` validation.
- Added `validate_shape_lifecycle_bundle` to check ShapeCore, ShapeView, ShapeRecord, DimensionalShape, and CompositeShape references.

## Verification command

`. /workspace/.venv/bin/activate && cd /workspace && pytest tests/test_metaphysical_kernel_profile_registry.py tests/test_disclosure_contracts.py -q`

Result: `51 passed in 0.18s`.

## Residuals

- This slice validates portable profile contracts only; persistence and query behavior remain later work.
