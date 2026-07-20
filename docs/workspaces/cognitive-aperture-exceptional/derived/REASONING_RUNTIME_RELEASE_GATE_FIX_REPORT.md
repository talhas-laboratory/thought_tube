# Reasoning-runtime release-gate fix report

**Branch reviewed:** `cursor/shape-intelligence-remediation-pass`
**Merge under review:** `31f4be68006683cbd917bd5ed5d4189b8edd0193`
**Status:** blocked — test isolation diagnosis required before Cognitive Aperture rollout

## Decision

Keep every Cognitive Aperture rollout flag at `false` / `legacy`. Do not merge the
Shape-population tools branch as part of this repair. The release gate is the
authoritative blocker until the five unapproved reasoning-runtime failures are
explained and eliminated.

## Evidence

| Check | Result |
|---|---|
| CAE focused suite | 132 passed |
| First full suite | 994 passed, 70 failed, 4 skipped |
| Gate full suite | 993 passed, 71 failed, 4 skipped |
| Gate decision | `blocked` — `unapproved_full_suite_regressions` |
| Isolated reproduction | `test_classify_turn_applies_creative_expansion_bridge_behavior_for_metathought` passed alone |

The full-suite failure set contains these five failures that are not listed in
`derived/baselines/approved_repository_debt.json`:

1. `ReasoningRuntimeBridgeAndFieldTestCase::test_build_active_field_handles_ambiguous_request_without_retrieval`
2. `ReasoningRuntimeBridgeAndFieldTestCase::test_build_active_field_prefers_intuition_expansion_pipeline_when_bridge_behavior_matches`
3. `ReasoningRuntimeBridgeAndFieldTestCase::test_classify_turn_applies_creative_expansion_bridge_behavior_for_metathought`
4. `ReasoningRuntimeExecutionTestCase::test_run_reasoning_persists_confirmed_bridge_behavior_patterns`
5. `ReasoningRuntimeExecutionTestCase::test_run_reasoning_uses_intuition_expansion_for_metathought_queries`

## Root-cause hypothesis — not yet proven

The failures are order-dependent: the creative-expansion test passes in an
isolated process, yet fails in the release-gate full suite. All five tests pass
through `classify_turn()` and the behaviour-spec loader in
`src/conversation_os/reasoning_bridge.py`. They use temporary roots, so an
earlier test is likely leaking process-global state such as the working
directory, an environment variable, mutable module state, or a behaviour-spec
cache/configuration reference.

This is not enough evidence to call the implementation correct. The contaminating
predecessor and the shared mutable boundary must be identified before changing
the production code or debt baseline.

## Required repair

1. Reproduce each failure with an ordered subset: run the five target tests after
   progressively larger prefixes of the suite, then binary-search the preceding
   tests to identify the first contaminator.
2. Capture the differing state immediately before `classify_turn()` in passing
   and failing runs: current working directory, relevant environment variables,
   `BRIDGE_BEHAVIOR_RULES`, behaviour-spec source path, and module cache state.
3. Repair the owner of the leak. Tests that patch global process state must restore
   it with scoped fixtures/context managers; production loading must not retain a
   mutable reference supplied by a test.
4. Add an order-independence regression: run the contaminating test followed by
   the five reasoning-runtime tests in one process, then assert all five pass.
5. Run the five-target test command, the complete reasoning-runtime file, the
   CAE focused suite, and `evaluate_release_gate(Path('.'), run_full_suite=True)`.

## Acceptance criteria

- The five node IDs pass both alone and after the identified predecessor.
- No approved-debt entry is added for these node IDs.
- The release gate returns `status: ready` with no `new_regressions`.
- Runtime rollout configuration remains unchanged during this repair.

## Exact verification commands

```bash
python3 -m pytest -q tests/test_reasoning_pipeline_runtime.py
PYTHONPATH=src python3 -c "from pathlib import Path; from conversation_os.aperture_release_gate import evaluate_release_gate; print(evaluate_release_gate(Path('.'), run_full_suite=True)['status'])"
```

## Residual risk

The first and gate full-suite runs differ by one historical failure (70 versus
71). Treat the approved-debt baseline as a comparison aid, not a claim of a
stable suite, until order-independent verification is established.
