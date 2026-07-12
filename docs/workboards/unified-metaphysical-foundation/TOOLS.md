# Metaphysical Foundation — Tools Reference

**Branch:** `cursor/metaphysical-kernel-contracts-423a`  
**PR:** [#11](https://github.com/talhas-laboratory/thought_tube/pull/11)  
**Authority:** `docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`

All commands assume repo root and `python3`.

## Quick start for reviewers

```bash
# Run the Phase 1 kernel test suite (53 tests via CLI; 56 with CLI handler tests)
python3 tools/conversation_os.py foundation test --verbose
PYTHONPATH=src python3 -m unittest tests.test_metaphysical_kernel_cli -v

# Inspect empty or existing foundation store
python3 tools/conversation_os.py foundation status

# Bootstrap Field/Formation profile into the store
python3 tools/conversation_os.py foundation bootstrap

# Run end-to-end vertical slice demo
python3 tools/conversation_os.py foundation slice \
  --content "Control loops may inhibit initiative." \
  --referent-label "Company initiative" \
  --claim-predicate inhibits \
  --claim-arguments control_loop

# Prove two application consumers on the same store
python3 tools/conversation_os.py foundation consumer world-studio \
  --content "A harbor city under violet fog." \
  --referent-label "Harbor district" \
  --world-id world-aurora

python3 tools/conversation_os.py foundation consumer workspace-curator \
  --content "Kernel contracts precede profile implementation." \
  --workspace-id unified-framework-synthesis

# Validate migration fixture (no writes)
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/sds_signal_dilution.json

# Execute migration and show kernel bundle counts
python3 tools/conversation_os.py foundation migrate-fixture \
  --fixture-path tests/fixtures/migration/mtsf_minimal_assertion.json \
  --execute
```

## CLI: `foundation` command group

| Command | Purpose |
|---------|---------|
| `foundation status` | Event log path, record counts, validation errors |
| `foundation validate` | Validate folded kernel bundle in store |
| `foundation bootstrap` | Register `profile:field_formation` v1.0.0 |
| `foundation test [--module M] [--verbose]` | Run unittest modules (default: all 5 kernel test files) |
| `foundation capture` | Capture `SourceFragment` via SDK (manual pointer or session event) |
| `foundation slice` | Run Phase 1 vertical slice demo |
| `foundation migrate-fixture` | Validate or execute a migration fixture |
| `foundation consumer` | Run World Studio or Workspace Curator consumer proof |
| `foundation conformance` | Evaluate profile conformance on current bundle |

### Store location

Append-only kernel events: `memory/foundation/kernel_events.jsonl`

### Direct unittest (without CLI)

```bash
PYTHONPATH=src python3 -m unittest \
  tests.test_metaphysical_kernel_contracts \
  tests.test_metaphysical_kernel_migration \
  tests.test_metaphysical_kernel_runtime \
  tests.test_metaphysical_kernel_profile_registry \
  tests.test_metaphysical_kernel_application_sdk \
  -v
```

## Python API entry points

| Module | Import | Use |
|--------|--------|-----|
| Contracts | `from conversation_os.metaphysical_kernel import ...` | Dataclasses, lifecycle literals |
| Validation | `from conversation_os.metaphysical_kernel_contracts import validate_fixture_bundle` | Invariant checks |
| Migration | `from conversation_os.metaphysical_kernel_migration import migrate_source_fixture` | Historical → kernel |
| Store | `from conversation_os.metaphysical_kernel_store import FoundationStore` | Append-only log |
| Runtime | `from conversation_os.metaphysical_kernel_runtime import FoundationRuntime` | Vertical slice ops |
| Profiles | `from conversation_os.metaphysical_kernel_profile_registry import ProfileRegistry` | Registry + conformance |
| SDK | `from conversation_os.metaphysical_kernel_application_sdk import FoundationApplicationSdk` | Application boundary |
| CLI handlers | `from conversation_os.metaphysical_kernel_cli import foundation_status` | Tooling |

## Fixture locations

| Path | Purpose |
|------|---------|
| `tests/fixtures/metaphysical_kernel/` | Kernel contract fixtures (valid + invalid) |
| `tests/fixtures/metaphysical_kernel/profile_field_formation_v1_0_0.json` | Profile metadata reference |
| `tests/fixtures/migration/` | Migration source-family fixtures |

## Engineering guard (before further code)

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "..." \
  --purpose "..." \
  --proposed-paths "src/conversation_os/metaphysical_kernel_....py"
```

Note: guard may report `needs_index` due to repo-wide missing module manifests on this branch; kernel tests are the authoritative verification for Phase 1.

## Review reading order

1. `PHASE-1-IMPLEMENTATION-REVIEW.md` (this workboard) — architecture + task map
2. `tasks/TASK-001` … `tasks/TASK-005` — per-task acceptance + verification
3. `docs/workspaces/unified-framework-synthesis/derived/foundation-build-plan.md` — normative sequencing
4. Framework v1.1 sections 4–6, 8A, 20, 22, Appendix F
