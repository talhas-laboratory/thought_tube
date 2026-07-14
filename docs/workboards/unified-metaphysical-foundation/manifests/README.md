# Kernel module manifests (migrated)

The canonical, Git-tracked module-manifest registry now lives in
[`context/substrate/modules/`](../../../context/substrate/modules/). It is
deliberately versioned even though the rest of `context/` remains generated
local state: a fresh local or cloud clone needs these ownership records before
the codebase overview and engineering guard can operate.

This directory is retained as a migration marker for the Phase 1 kernel
tranche. The JSON manifests have moved to the canonical registry; do not add a
second copy here.

## Modules

| module_id | canonical registry path |
|-----------|------|
| `kernel.metaphysical.records` | `kernel.metaphysical.records.json` |
| `kernel.metaphysical.contracts` | `kernel.metaphysical.contracts.json` |
| `kernel.metaphysical.migration` | `kernel.metaphysical.migration.json` |
| `kernel.metaphysical.store` | `kernel.metaphysical.store.json` |
| `kernel.metaphysical.runtime` | `kernel.metaphysical.runtime.json` |
| `kernel.metaphysical.profile_registry` | `kernel.metaphysical.profile_registry.json` |
| `kernel.metaphysical.application_sdk` | `kernel.metaphysical.application_sdk.json` |
| `kernel.metaphysical.cli` | `kernel.metaphysical.cli.json` |
