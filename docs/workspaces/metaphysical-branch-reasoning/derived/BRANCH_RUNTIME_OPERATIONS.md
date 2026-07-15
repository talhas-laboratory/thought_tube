# Branch Runtime Operations — BRANCH-002

**Task:** `BRANCH-002-support-and-inheritance-semantics`  
**Owner module:** `src/conversation_os/metaphysical_branch_reasoning.py`  
**Contract:** [`BRANCH_PUBLIC_CONTRACT_LOCK.md`](./BRANCH_PUBLIC_CONTRACT_LOCK.md) v1.0.0  
**Kernel consumed:** `1.1.0`

## Implemented operations (Phase 1)

| Operation | Section | Module function |
|---|---|---|
| InheritanceQuery | §7.2 | `resolve_inheritance` |
| SupportAssessment | §7.3 | `assess_support` |

Conflict, merge, and inference operations remain contract-locked for BRANCH-003+.

## Verification

```bash
pytest -q tests/test_metaphysical_branch_reasoning.py
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py
```

Table fixtures: `tests/fixtures/metaphysical_branch/inheritance_outcome_table.json`, `support_outcome_table.json`.
