# T10-10 Cybernetic Compile

## Scope

First minimal executable cybernetic compilation slice for Wave 5.

- Owner: `src/conversation_os/metaphysical_kernel_profile_registry.py`
- Public entrypoint: `compile_cybernetic_bundle_to_ir`
- Profile: `profile:cybernetics@1.0.0`
- Compiler: `compiler:cybernetic-profile-v1`

## What landed

- Validated selected cybernetics profile bundles compile into deterministic `ExecutableModelIR` dictionaries.
- Compilation is selection-bounded: it only uses records passed by the caller and never scans the full record universe.
- The compiler returns principled abstention when the selected bundle is invalid, empty, lacks a compiled/approved `dynamic_model_extension`, or requests an unsupported runtime adapter.
- IR records variables, state spaces, mechanisms, transition rules, constraints, observations, policies, time model, assumptions, validation results, provenance, and execution authorization.
- Runtime side effects are explicitly disabled; a compiled-but-unapproved extension can produce IR but cannot authorize execution.

## Verification

- `pytest tests/test_metaphysical_kernel_profile_registry.py` — 29 passed.

## Residuals

- No runtime adapter executes the IR in this slice.
- No outcome learning, scale recovery, observability, or final benchmark work was started.
- Later slices still need richer semantic validation against source Shape/Claim qualifiers and backend-specific unsupported construct reporting.
