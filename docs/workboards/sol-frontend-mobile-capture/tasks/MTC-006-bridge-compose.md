# MTC-006 — Bridge compose spine (ocean-grounded insertions)

**Status:** `done`  
**Plan:** `BRIDGE_COMPOSE_PLAN.md`  
**Contracts:** `BRIDGE_SECTION.md`, `COMPOSITION.md`, `CaptureModeState`  
**Pillars:** P3, P5, P8  
**Phase:** 2  
**Gate:** MTC-008 done ✓

## Problem

The PWA captures locally and syncs deposits outbound. Nudge/shape still use `local-composer` stubs. There is no server path for the bridge to retrieve from the knowledge ocean, run behaviors, and return a **coupled insertion** the UI can render.

## Goal

On **invited assist** (nudge / shape), section adapter calls a compose API backed by `run_reasoning(surface=mobile_capture)`. Server returns a full insertion payload. PWA renders it under the provoking deposit.

**v0:** nudge/shape only — not auto-compose on silent deposit.

## Scope in

### 6a — Compose owner (backend)

- `src/conversation_os/mobile_capture_compose.py`
- `compose_mobile_capture_insertion()` → `run_reasoning()` → `project_insertion_text_direct()`
- `ReasoningRequest` with `surface="mobile_capture"` and `caller_hints` per plan
- `query_override` in caller_hints for thin early-turn retrieval

### 6b — HTTP endpoint

- `POST /api/mobile/compose` in `miniapp.py`
- Same mobile session auth as other `/api/mobile/*` routes
- Idempotency on `(session_id, local_deposit_id, intent)`

### 6c — Capture provenance

- `append_mobile_capture` / handler accepts optional `provenance` + `session_id` from payload
- Persist `local_deposit_id` on session event metadata where practical

### 6d — Section adapter read path

- `requestInsertion()` in `section-adapter.ts`
- `transportComposeInsertion()` in `transport.ts`
- `VITE_BRIDGE_SECTION_COMPOSE_ENABLED`
- Update `MOBILE_CAPTURE_SURFACE_PROFILE.bridge_reads`

### 6e — Capture stream wire-up

- `use-capture-stream` nudge/shape → `requestInsertion` → `upsertInsertion`
- Loading affordance on active unit during compose (no blocking deposit path)
- `local-composer` fallback when `insertion: null` or offline

## Scope out (v0)

- Auto-compose on every deposit
- Async poll / SSE
- `classify_preview` HTTP endpoint
- Insertion projector registry (multiple implementations)
- `bridge_sections.mobile_capture` runtime config file
- UI for `provenance_refs`
- `/conversations/{id}/reply` integration

## Acceptance criteria

- [ ] `POST /api/mobile/compose` returns server-owned `InsertionPayload` shape
- [ ] Compose calls `run_reasoning`, not `reply_in_mobile_session`
- [ ] pytest: mocked `run_reasoning` + HTTP compose success/failure
- [ ] Nudge/shape online + bridge enabled → insertion from API; offline → fallback or silent
- [ ] Deposit always succeeds when compose fails
- [ ] Re-nudge replaces insertion on same deposit (C6)
- [ ] `session_id` from capture ack used in compose requests
- [ ] No bridge imports in PWA capture components except via adapter
- [ ] `tests/test_thought_capture_bridge_section.py` still passes

## Files (expected)

**Backend**

- `src/conversation_os/mobile_capture_compose.py` (new)
- `src/conversation_os/miniapp.py`
- `src/conversation_os/product_inner_world.py` (provenance on capture if needed)
- `tests/test_conversation_os.py` or `tests/test_mobile_capture_compose.py`

**PWA**

- `product/thought_capture_pwa/src/bridge/section-adapter.ts`
- `product/thought_capture_pwa/src/bridge/transport.ts`
- `product/thought_capture_pwa/src/bridge/types.ts`
- `product/thought_capture_pwa/src/capture/use-capture-stream.ts`
- `product/thought_capture_pwa/src/bridge/section-adapter.test.ts`

## Verification

```bash
# Backend
python3 -m pytest tests/test_mobile_capture_compose.py -q   # after 6a–6b

# PWA
cd product/thought_capture_pwa && npm test

# Manual (bridge + backend required)
INNER_WORLD_BRIDGE_ENABLED=true python3 tools/run_inner_world_miniapp.py
cd product/thought_capture_pwa && VITE_BRIDGE_SECTION_SYNC_ENABLED=true VITE_BRIDGE_SECTION_COMPOSE_ENABLED=true npm run dev
```

## Blocks

- MTC-007 (develop route) — independent; may share compose owner later for `shape` + develop phase

## Follow-on (v1)

Documented in `BRIDGE_COMPOSE_PLAN.md` § v1+
