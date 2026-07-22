# UMF-AGENT-001 EnvironmentSpec packet evidence

## Scope

First EnvironmentSpecPacket contract slice in `src/conversation_os/disclosure_contracts.py`.

## What landed

- Added `EnvironmentSpecPacket` with typed fields, `from_dict`, and `to_dict`.
- Added `validate_environment_spec_packet` and `build_environment_spec_packet`.
- Registered the packet in `PUBLIC_API`, `__all__`, `_MODEL_BY_NAME`, and `contract_field_catalog`.
- Added fixture coverage for a valid environment packet and rejection tests for empty tools, non-positive timeout, and missing `auth_boundaries.forbidden_intents`.

## Verification command

`. /workspace/.venv/bin/activate && cd /workspace && pytest tests/test_metaphysical_kernel_profile_registry.py tests/test_disclosure_contracts.py -q`

Result: `51 passed in 0.18s`.

## Residuals

- This slice defines disclosure contract structure only; no agent runtime or tool execution path was added.
