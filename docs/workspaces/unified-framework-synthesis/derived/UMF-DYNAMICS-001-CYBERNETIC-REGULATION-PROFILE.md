# UMF-DYNAMICS-001 cybernetic regulation profile evidence

## Scope

First qualifier-check slice for `validate_cybernetic_bundle_contract` in `src/conversation_os/metaphysical_kernel_profile_registry.py`.

## What landed

- `validate_cybernetic_bundle_contract` now accepts optional `shape_records` and `claim_records`.
- When Shape records are supplied, `dynamic_model_extension.shape_ref` must resolve.
- Shape branch/scope alignment is checked from the extension when present, otherwise from referenced variable context.
- When Claim records are supplied, `state_variable.claim_ref` must resolve and Claim epistemic status is bounded.
- Existing behavior is unchanged when Shape and Claim records are omitted.

## Verification command

`. /workspace/.venv/bin/activate && cd /workspace && pytest tests/test_metaphysical_kernel_profile_registry.py tests/test_disclosure_contracts.py -q`

Result: `51 passed in 0.18s`.

## Residuals

- This slice validates contract references only; executable dynamics semantics remain governed by later compiler/runtime gates.
