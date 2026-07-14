# Kernel module manifests (tracked source)

The repo indexes module manifests from `context/substrate/modules/`, which is
**gitignored** (generated Conversation OS state). These JSON files are the
**tracked source** for the Phase 1 kernel tranche.

## Install locally (for repo overview / engineering guard)

```bash
mkdir -p context/substrate/modules
cp docs/workboards/unified-metaphysical-foundation/manifests/*.json context/substrate/modules/
python3 tools/conversation_os.py repo-overview refresh
```

## Modules

| module_id | path |
|-----------|------|
| `kernel.metaphysical.records` | `metaphysical_kernel.py` |
| `kernel.metaphysical.contracts` | `metaphysical_kernel_contracts.py` |
| `kernel.metaphysical.migration` | `metaphysical_kernel_migration.py` |
| `kernel.metaphysical.store` | `metaphysical_kernel_store.py` |
| `kernel.metaphysical.runtime` | `metaphysical_kernel_runtime.py` |
| `kernel.metaphysical.profile_registry` | `metaphysical_kernel_profile_registry.py` |
| `kernel.metaphysical.application_sdk` | `metaphysical_kernel_application_sdk.py` |
| `kernel.metaphysical.cli` | `metaphysical_kernel_cli.py` |
