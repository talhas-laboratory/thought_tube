# Cognitive Aperture integration status

**Branch:** `cursor/shape-intelligence-remediation-pass`  
**Updated:** 2026-07-20  
**Source implementation:** merged from `cursor/cloud-agent-1784542105487-zjzbu`

## What changed in this integration

1. Merged cloud-agent remediation implementation (code + tests + baselines) into the remediation planning branch.
2. **Kept all rollout flags disabled** in `product/inner_world_v1/config/runtime.json` (legacy paths remain default).
3. Added rollout scaffold keys (`disclosure.rollout`, `receipts.rollout`, `active_state.rollout`) set to `legacy` for staged cutover later.
4. Preserved remediation-pass workspace planning docs in merge conflicts.

## Implementation inventory (post-merge)

| Packet | In tree | Rollout enabled |
|--------|---------|-----------------|
| R-001 / R-002 Shape retrieval + AntiMatch | yes | n/a |
| R-003 Shape certification harness | yes | n/a |
| R-004 Disclosure rollout modes | yes | **no** (`legacy`) |
| R-005 Grant-first retrieval | yes | n/a |
| R-006 Corpus catalog snapshot | yes | n/a |
| R-007 Evidence resolver | yes | n/a |
| R-008 Execution audit isolation | yes | n/a |
| R-009 Holodeck source ref portability | yes | n/a |
| R-010 Holodeck dependency abstention | yes | n/a |
| R-011 Receipt persistence | yes | **no** |
| R-012 ActiveState continuity | yes | **no** |
| R-013 Feed/task-pack certification | yes | **no** |
| R-014 Bounded-view integration | yes | **no** |
| R-015 Operator metrics | yes | **no** |
| R-016 Release gate | yes | n/a |

## Verification

```bash
. .venv/bin/activate
PYTHONPATH=src python -c "from pathlib import Path; from conversation_os.aperture_release_gate import run_focused_suite; r=run_focused_suite(Path('.')); print(r['green'], r.get('failed_node_ids',[]))"
```

Focused CAE suite: **green** (132 tests across 18 files, Linux).

## Not integrated yet

- `origin/cursor/shape-intelligence-tools-61ce` — Shape population tools (separate branch)
- Shape Intelligence workspace tasks — remain `backlog` until population track starts
- Production rollout cutover — blocked until explicit release decision after certification review

## Next steps (recommended)

1. Review merged diff on this branch (not the cloud-agent branch in isolation).
2. Run full repository suite + `evaluate_release_gate(..., run_full_suite=True)`.
3. Integrate shape-intelligence-tools when population contracts are ready.
4. Enable rollout flags surface-by-surface only after certification + operator sign-off.
