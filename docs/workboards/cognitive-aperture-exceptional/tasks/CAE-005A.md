Status: done
Owner: cursor-cloud-reviewer
# CAE-005A — Disclosure service and Bridge adapter

**Stage:** C
**Priority:** high
**Depends on:** Stage B gate
**Owner paths:** new service/facade selected by guard, Bridge adapter, focused tests

## Outcome

Extract the proven Bridge disclosure path behind storage-independent ports without changing its verified decisions.

## Acceptance

- service depends on catalog/search/Shape/evidence/receipt ports;
- no product surface is imported by the service;
- Bridge parity fixtures pass;
- no full-ocean scan or unbounded walk;
- feature flag and rollback pass;
- p50/p95 and resolved-byte baseline recorded.

## Verification

- **Commit:** `4366ba8` on branch `cursor/cognitive-aperture-gap-map-24c7` (PR #32).
- **Command:** `. .venv/bin/activate && PYTHONPATH=src pytest -q tests/test_disclosure_service_bridge_parity.py`
- **Result:** parity tests pass — service path matches `_assemble_bridge_context_bundle_impl()` subset; import-boundary test confirms no product surface imports in service/ports modules.
- **Changed paths:** `src/conversation_os/disclosure_service.py`, `disclosure_ports.py`, `bridge_disclosure_adapter.py`, `tests/test_disclosure_service_bridge_parity.py`.
- **Feature flag:** `bridge.disclosure_service_v1` (default `false` in `product/inner_world_v1/config/runtime.json`).
- **Decision:** D-017.
- **Reviewer:** Stage C/D independent review (`5ac2934`) — approved.

## Rollback / risk

- Set `bridge.disclosure_service_v1: false` to restore legacy `_assemble_bridge_context_bundle_impl()` routing.
- Residual risk: service flag off by default; parity depends on synthetic capsule fixtures until corpus-backed conformance expands.
