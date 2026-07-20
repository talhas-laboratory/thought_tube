# Remediation manager status — R-014 / R-015 / R-016

**Branch:** `cursor/cloud-agent-1784542105487-zjzbu`  
**Manager run:** 2026-07-20  
**Outcome:** All three gaps implemented and integrated.

## Gap summary

| Gap | Status | Key deliverables |
| --- | --- | --- |
| R-014 | **done** | `merge_bounded_view_evidence_into_bundle`, bridge + holodeck wiring, certification harness |
| R-015 | **done** | Operator metrics v2 baselines, certification labeling, k-anonymity, rollout modes |
| R-016 | **done** | `aperture_release_gate.py`, approved debt baseline, focused suite (18 files) |

## Release gate (R-016)

```bash
. .venv/bin/activate
PYTHONPATH=src python -c "from pathlib import Path; from conversation_os.aperture_release_gate import evaluate_release_gate; print(evaluate_release_gate(Path('.'), run_full_suite=True)['status'])"
```

**Linux 2026-07-20:** `status: ready`

- Focused suite: green (18 test files)
- Full repository suite: 987 passed, 77 failed — all failures in approved debt baseline; **0 new regressions**

## R-014 highlights

- `bounded_view_disclosure_adapter.merge_bounded_view_evidence_into_bundle` — reference-only evidence, no lexical ranking mix
- Wired in `reasoning_bridge._assemble_bridge_context_bundle_impl` and `holodeck_disclosure_adapter.collect_disclosure_knowledge_candidates`
- `disclosure.bounded_view.epistemic_backend_v1: true` in release runtime
- Published baseline: `chat_converter_seed_v2_bounded_view_certification` (`service_certified: true`)

## R-015 highlights

- `operator_metrics_v1: true` in release runtime
- v2 certification baselines loaded with `certify_baseline_snapshot` (uncertified excluded from release claims)
- Cross-surface aggregates suppress counts below k=3
- Feed/task_pack receipt rollout `enforced` (aligned with R-013)

## Orchestration model

1. Manager subagent implemented R-016 + debt baseline
2. Worker subagents implemented R-014 and R-015 in parallel
3. Integrator fixed catalog snapshot gaps, receipt rollout expectations, focused suite membership
4. Release gate verified end-to-end
