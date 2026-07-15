# Branch Reasoning — Test and Release Guide

## Test layers

1. **Contract tests:** malformed inheritance, support, conflict, merge, and inference inputs fail with actionable errors.
2. **Table-driven semantics:** inheritance × retraction × replacement × scope × evidence polarity covers the expected outcome matrix.
3. **Adversarial isolation:** no record in one branch becomes usable in another without explicit compatible membership and scope.
4. **Continuity:** Kernel fixture bundle → branch result → consumer view preserves IDs, provenance, and status.
5. **Regression:** every defect becomes a minimal fixture under `tests/fixtures/metaphysical_branch/`.

## Required scenarios before G4

| Scenario | Expected result |
|---|---|
| Child inherits parent Claim | Read-visible with inherited membership semantics |
| Child retracts parent Claim | Omitted from its default view; parent remains unchanged |
| Affirmative and negative evidence in same scope | `both`, no explosion |
| Same claim, incompatible scopes | Not a logical contradiction by default |
| Two perspectives disagree | Preserved as divergence, not overwrite |
| Merge conflicting branches | `MergeAssessment` lists unresolved conflict |
| Inference encounters `both` | Preserve/branch/clarify/abstain with explicit reason |
| Source reused in two branches | One source identity; distinct branch-local interpretations |

## Release evidence

BRANCH-005 ships a versioned API/contract, examples, compatibility notes, Kernel version consumed, test command/results, fixtures, merge SHA, and known limits. It must explicitly say that weighting is task-relative and that it does not implement a global truth selector.

## Suggested commands once implementation begins

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "src/conversation_os/<owner>.py,tests/test_<owner>.py"
pytest -q tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py
pytest -q tests/test_metaphysical_branch_reasoning.py
```

The final command is intentionally future-facing. Do not create that module or test file until BRANCH-001 has locked the contract and the guard approves the smallest owner surface.
