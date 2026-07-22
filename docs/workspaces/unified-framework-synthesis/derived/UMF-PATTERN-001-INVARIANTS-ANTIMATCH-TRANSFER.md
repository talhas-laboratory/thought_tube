# UMF-PATTERN-001 invariants, AntiMatch, and transfer evidence

## Scope

First Pattern profile slice in `src/conversation_os/metaphysical_kernel_profile_registry.py` and `tests/fixtures/metaphysical_kernel/profile_pattern_v1_0_0.json`.

## What landed

- Added `profile:pattern@1.0.0` constants, invariant descriptions, profile builder, and registry bootstrap.
- Added validators for `pattern`, `anti_match`, and `transfer_assessment`.
- Pattern records require declared ShapeCore refs and reject explicit `merge_shapes_forbidden=false`.
- AntiMatch records require explicit rejection reasons.
- Transfer assessments require explicit transferability and mechanism notes.

## Verification command

`. /workspace/.venv/bin/activate && cd /workspace && pytest tests/test_metaphysical_kernel_profile_registry.py tests/test_disclosure_contracts.py -q`

Result: `51 passed in 0.18s`.

## Residuals

- This slice locks contract shape and registry metadata; automated Pattern discovery remains out of scope.
