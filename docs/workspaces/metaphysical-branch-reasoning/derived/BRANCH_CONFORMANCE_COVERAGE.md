# Branch Conformance Coverage — BRANCH-004

**Task:** `BRANCH-004-adversarial-branch-conformance`  
**Owner module:** `src/conversation_os/metaphysical_branch_reasoning.py`  
**Machine manifest:** [`BRANCH_CONFORMANCE_COVERAGE.json`](./BRANCH_CONFORMANCE_COVERAGE.json)

## Verification command

```bash
pytest -q tests/test_metaphysical_branch_reasoning.py tests/test_metaphysical_branch_conformance.py tests/test_metaphysical_kernel_contracts.py tests/test_metaphysical_kernel_runtime.py
```

**Last run:** 43 passed, 55 subtests passed (2026-07-15).

## Layers exercised

| Layer | Artifact |
|---|---|
| Table-driven semantics | Five outcome tables under `tests/fixtures/metaphysical_branch/` |
| Adversarial regressions | `adversarial_suite.json` (12 minimized cases) |
| Required G4 scenarios | `test_required_acceptance_scenarios` maps BRANCH-ACC-001–008 |
| Continuity | `test_continuity_preserves_input_claim_ids` |
| Contract errors | `SelfConflictError`, `InvalidInferenceOutputStatusError` |

## Adversarial guarantees

- Cross-branch claims do not affect support without inheritance.
- `both` support does not explode claim ID lists beyond matched evidence.
- Scope and perspective disagreements are not classified as logical contradictions.
- Merge reports incompatible verdicts without selecting winners.
- Inference `preserve` and `abstain` policies keep outputs inspectable.
- `causal_hypothesis` and `executable_state` kinds never exceed `candidate`.
- `max_depth < 1` halts traversal with `contradiction_policy_halt` abstention.

## Residual Phase 1 limits

See `residual_limits` in the JSON manifest. Notable: multi-proposition depth traversal beyond the primary proposition group is not implemented; depth bound applies at request entry.
