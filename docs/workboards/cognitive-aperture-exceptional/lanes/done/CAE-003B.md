Status: done
Owner: cursor-stage-b-review
# CAE-003B — Deterministic budget allocator

**Stage:** B
**Priority:** critical
**Depends on:** CAE-015, CAE-003A
**Owner paths:** disclosure budget owner, bridge projection, focused tests

## Outcome

Orientation and evidence are selected by a deterministic token/block ledger before execution composition.

## Acceptance

- tokenizer/estimator and reservation rules are versioned;
- evidence is included as whole provenance-preserving blocks;
- no execution bundle exceeds the effective budget;
- identical inputs at one corpus/policy revision are deterministic;
- insufficient required capacity returns explicit status;
- drop ledger appears in audit only.

## Verification

- **Commits:** `05ea6e9` (allocator), `3808659` (unset-budget fix) on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_disclosure_budget_allocator.py tests/test_reasoning_bridge_policy.py`
- **Result:** whole-block selection, drop ledger in audit only, `abstained_insufficient_budget` when required blocks cannot fit; unset `token_budget` defaults from depth mode after fix.
- **Changed paths:** `disclosure_budget_allocator.py`, `reasoning_bridge.py` (`apply_frame_budget_to_assembly`), `tests/test_disclosure_budget_allocator.py`.
- **Feature flag:** `bridge.deterministic_budget_enforcement_v1` (default `true`).
- **Decision:** D-015.
- **Reviewer:** blocked on zero-budget wipe (`60a77a4`); fix approved (`c7d7b10`).

## Rollback / risk

- Set `bridge.deterministic_budget_enforcement_v1: false` to skip whole-block budget enforcement.
- Residual risk: explicit `token_budget: 0` and incognito must continue to skip enforcement (regression-tested in `3808659`).
