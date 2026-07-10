# MTC-001 — Capture route + immersive shell

**Status:** `done`  
**Contract:** `CaptureSurface`  
**Pillars:** P1, P3  
**Motion:** `motion.confirm`, `motion.reveal` — tier 1–2, `scroll_impact: none`  
**Phase:** 1  
**Completed:** 2026-06-27

## Problem

`mobile_surface_v1` is an atlas topology demo, not a thought-capture interface. Need immersive capture shell per conversation Theme B.

**Resolution (DEC-005):** Ship capture as `product/thought_capture_pwa/` — do not extend atlas demo.

## Delivered

| Area | Implementation |
|------|----------------|
| Route | `/capture` default; `*` redirects to capture |
| Shell | `AppShell` + safe-area + vignette spotlight |
| Field | `CapturePage` → `CaptureField` vertical stream |
| Input | `CaptureInput` — elastic textarea, embedded footer, `enterkeyhint="send"` |
| Library | Horizontal swipe + nav chip to warmth overview (`LIBRARY.md`) |
| Offline | Dexie deposits; send without required metadata |
| PWA | Vite 7 + `vite-plugin-pwa`, iOS meta, icons, manifest |

## Acceptance criteria

- [x] `/capture` renders immersive shell matching CONTRACTS.md CaptureSurface invariants
- [x] No document-editor chrome; no required metadata at send
- [x] Verification notes in `artifacts/2026-06-27-mtc-001-capture-shell.md`
- [x] Pillar rejection check documented in artifact

## Files (actual)

- `product/thought_capture_pwa/src/app.tsx` — router
- `product/thought_capture_pwa/src/shell/app-shell.tsx` — safe-area wrapper
- `product/thought_capture_pwa/src/capture/capture-page.tsx` — immersive layout
- `product/thought_capture_pwa/src/capture/capture-field.tsx` — thought stream
- `product/thought_capture_pwa/src/capture/capture-input.tsx` — embedded input
- `product/thought_capture_pwa/src/capture/capture.css` — vignette, locus, field tokens
- `product/thought_capture_pwa/src/styles/aesthetic-tokens.css` — `--surface-field`, locus roles
- `product/thought_capture_pwa/index.html` — PWA + iOS meta

## Superseded paths (do not use)

- ~~`product/mobile_surface_v1/src/capture-app.tsx`~~
- Atlas demo remains at `product/mobile_surface_v1/` unchanged

## Related tasks (also done in same PWA)

- MTC-002 ScrollEngine
- MTC-003 presence gating
- MTC-004 GestureZone (phase 2, shipped early)
- MTC-005 post-send affordances (phase 2, shipped early)
- MTC-008 bridge section adapter

## Out of scope (was never MTC-001)

- Scroll behavior → MTC-002
- AI presence / compose → MTC-003
- Object gestures → MTC-004
