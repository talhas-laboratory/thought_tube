# MTC-008 — Bridge section infrastructure

**Status:** `done` — adapter facade, provenance, tests; gate cleared for controlled bridge reads/writes  
**Contract:** `BRIDGE_SECTION.md`  
**Pillars:** P5, P8  
**Phase:** 2 (infrastructure gate)  
**Owner:** unassigned

## Problem

Phase 1 added provisional `bridge-client.ts` calling `/api/mobile/*` directly. Before real bridge integration, the PWA must exist as an isolated **bridge section**: consume bridge features without influencing control-plane behavior.

## Scope in

- `src/bridge/section-adapter.ts` — single facade for all bridge I/O
- `SurfaceProfile` slice `mobile_capture` documented and typed
- Provenance payload on every outbound sync event
- Refactor existing `bridge-client.ts` behind adapter (or replace)
- Config: `VITE_BRIDGE_SECTION_*` env contract; no changes to `runtime.json` `bridge` control block
- Dependency rule: `capture/`, `offline/`, UI must not import bridge modules except via adapter hook
- Test: adapter unit tests with mocked bridge; verify bridge package has zero imports from PWA

## Scope out

- `prepare_turn` from UI (until adapter read API defined)
- New bridge behaviors or steering rules
- Writing `.thought-tube/` from the app
- Auth UX for mobile session (separate task)

## Acceptance criteria

- [ ] `BRIDGE_SECTION.md` decision test passes on PR review
- [ ] All bridge HTTP/MCP calls route through section adapter
- [ ] Provenance fields on sync payload documented and implemented
- [ ] Dexie remains source of truth; bridge failure does not block send
- [ ] `grep` confirms no `bridge_prepare` / steering writes from `thought_capture_pwa`
- [ ] Note in `artifacts/` on adapter boundary verification

## Files (expected)

- `product/thought_capture_pwa/src/bridge/section-adapter.ts`
- `product/thought_capture_pwa/src/bridge/types.ts`
- `docs/workboards/sol-frontend-mobile-capture/BRIDGE_SECTION.md` (binding — done)
- Tests under `product/thought_capture_pwa/` or repo `tests/` for adapter only

## Blocks

- MTC-006 (mode router + bridge hook) — until this gate passes
- Any `prepare_turn` / streaming assist from capture UI

## Unblocks

- Safe bridge ingest sync
- Classify/presence hints as read-only adapter methods
