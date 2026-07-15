# Kernel Ontology — Test and Release Guide

## Local verification ladder

Run from repository root after activating the project environment when one is configured.

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py foundation review
python3 tools/conversation_os.py foundation test --verbose
PYTHONPATH=src python3 -m unittest \
  tests.test_metaphysical_kernel_contracts \
  tests.test_metaphysical_kernel_migration \
  tests.test_metaphysical_kernel_runtime \
  tests.test_metaphysical_kernel_profile_registry \
  tests.test_metaphysical_kernel_application_sdk -v
```

Use focused commands while iterating, then run the full ladder before review. Do not use `foundation review --in-place` unless the task explicitly permits modifying the local foundation store.

## Test categories

| Category | Minimum proof |
|---|---|
| Contract | Valid bundle passes; malformed envelope and invalid record fail with the intended error |
| Invariants | State/Claim separation, commitment linkage, branch membership, provenance closure, lifecycle independence |
| Migration | Source IDs, raw expressions, mapping confidence, semantic-loss warnings, and deferrals survive |
| Runtime | Capture-to-view path is append-only; bounded views fail closed; provenance traces terminate |
| Profile | Kernel redefinition and dependency cycles fail; conformance reports are traceable |
| Consumer | Two applications use the shared SDK/store without parallel canonical records |
| Regression | A bug receives a minimized fixture or test before its repair is considered complete |

## Release packet for consumers

KERNEL-005 must publish: contract version; supported record operations; invariant list; breaking-change policy; migration instructions; known Phase 1 limits; test command/results; exact Git SHA; and consumer integration examples. Branch and Vocabulary must confirm the version they consume in their own dependency contracts.

## Completion rule

Record verification through the live workspace service, then publish/check the projection. The task packet must name commands, results, changed paths, merge SHA, and residual risks. “No known risks” is acceptable only after an explicit search for them.
