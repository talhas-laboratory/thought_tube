# Reasoning-runtime release-gate fix report

**Branch reviewed:** `cursor/shape-intelligence-remediation-pass`
**Merge under review:** `31f4be68006683cbd917bd5ed5d4189b8edd0193`
**Status:** repaired — deep-copy isolation fix landed; five target tests pass in full suite

## Decision

Keep every Cognitive Aperture rollout flag at `false` / `legacy`. Do not merge the
Shape-population tools branch as part of this repair. The release gate is now
ready; any rollout still requires an explicit, surface-specific operator decision.

## Repair outcome (2026-07-20)

| Check | Result |
|---|---|
| Five target tests (isolated) | 5 passed |
| Five target tests (after 803-test prefix) | 5 passed — no order-dependent contaminator found |
| `load_bridge_behavior_specs` isolation | `copy.deepcopy` prevents embedded-rule mutation leak |
| CAE focused suite | unchanged |
| Release gate (`run_full_suite=True`) | `ready`, `new_regressions: []` |

Root cause confirmed: `load_bridge_behavior_specs()` returned `dict(BRIDGE_BEHAVIOR_RULES)`, a
shallow copy whose nested dicts were shared with module state. Any caller that mutated a
returned spec could corrupt global bridge behavior routing for later tests in the same process.

Fix: return `copy.deepcopy(BRIDGE_BEHAVIOR_RULES)` on the embedded-rules fallback path.
Regression coverage: `tests/test_reasoning_bridge_isolation.py`.

The two retrieval-dependent reasoning-runtime tests
(`test_build_active_field_produces_parent_ideas_from_retrieval_bundle`,
`test_get_context_bundle_uses_session_user_and_global_layers`) remain in approved repository
debt — they require private substrate ingest fixtures, not bridge-behavior isolation.

## Exact verification commands

```bash
python3 -m pytest -q tests/test_reasoning_pipeline_runtime.py
PYTHONPATH=src python3 -c "from pathlib import Path; from conversation_os.aperture_release_gate import evaluate_release_gate; print(evaluate_release_gate(Path('.'), run_full_suite=True)['status'])"
```

## Residual risk

The approved-debt baseline still contains retrieval-dependent tests that require
private-substrate fixtures. Rollout remains disabled until a separate operator
sign-off and surface-specific activation plan are recorded.
