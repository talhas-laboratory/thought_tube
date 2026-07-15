# Branch Runtime Operations — BRANCH-004

**Task:** `BRANCH-004-adversarial-branch-conformance` (conformance evidence)  
**Owner module:** `src/conversation_os/metaphysical_branch_reasoning.py`  
**Contract:** [`BRANCH_PUBLIC_CONTRACT_LOCK.md`](./BRANCH_PUBLIC_CONTRACT_LOCK.md) v1.0.0  
**Kernel consumed:** `1.1.0`  
**Conformance:** [`BRANCH_CONFORMANCE_COVERAGE.md`](./BRANCH_CONFORMANCE_COVERAGE.md)

## Implemented operations (Phase 1)

| Operation | Section | Module function |
|---|---|---|
| InheritanceQuery | §7.2 | `resolve_inheritance` |
| SupportAssessment | §7.3 | `assess_support` |
| ConflictRecord | §7.4 | `classify_conflict` |
| MergeAssessment | §7.5 | `assess_merge` |
| InferenceContext / InferenceResult | §7.6 | `run_inference` |

BranchEnsemble (§7.7) remains contract-locked for BRANCH-005+.

## Verification

```bash
pytest -q tests/test_metaphysical_branch_reasoning.py
pytest -q tests/test_metaphysical_branch_conformance.py
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py
```

Table fixtures:

- `tests/fixtures/metaphysical_branch/inheritance_outcome_table.json`
- `tests/fixtures/metaphysical_branch/support_outcome_table.json`
- `tests/fixtures/metaphysical_branch/conflict_outcome_table.json`
- `tests/fixtures/metaphysical_branch/merge_outcome_table.json`
- `tests/fixtures/metaphysical_branch/inference_outcome_table.json`

## Phase 1 limits

- Merge assessment reports conflicts; it does not resolve them or select winners.
- Inference always emits `candidate` epistemic status; non-candidate `output_status` raises `InvalidInferenceOutputStatusError`.
- `both` handling is explicit via `contradiction_policy` (`preserve`, `branch`, `clarify`, `abstain`).
