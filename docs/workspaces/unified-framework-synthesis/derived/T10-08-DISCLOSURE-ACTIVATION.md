# T10-08 Safe disclosure/state activation (Bridge shadow slice)

**Task:** `UMF-T10-08-DISCLOSURE-ACTIVATION`  
**Wave:** `UMF-T10-WAVE-04-SAFE-AGENT-USE`  
**Date:** 2026-07-22  
**Owners:** `disclosure_rollout.py`, `disclosure_receipt_rollout.py`

## Verdict

Bridge-only disclosure activation is live as **shadow**: shared-service comparison
and Bridge receipt persistence can run without flipping Holodeck/feed/task_pack
or enabling active-state continuity. Rollback remains config-only via
`bridge_force_legacy`.

## Behavior

| Surface | Service rollout | Receipt rollout |
|---|---|---|
| Bridge | `legacy` config → resolves **shadow** (T10-08) | `legacy` config → resolves **shadow**; persistence enabled for Bridge shadow |
| Holodeck / feed / task_pack | legacy | legacy |
| Active state | unchanged / off | n/a |

Rollback flags:
- `disclosure.rollout.bridge_force_legacy: true`
- `bridge.disclosure_force_legacy_v1: true`
- `disclosure.receipts.rollout.bridge_force_legacy: true`

## Verification

```bash
. .venv/bin/activate
python -m pytest tests/test_disclosure_rollout.py tests/test_disclosure_receipt_rollout.py -q
```

Result: **16 passed**.

## Residual

- Bounded-view shadow, Holodeck/feed/task-pack parity, canary cohorts, active-state continuity, metrics, and enforcement stages still ahead in T10-08
- Committed `runtime.json` still records `legacy` strings; resolver applies the cutover (config-only rollback preserved)
