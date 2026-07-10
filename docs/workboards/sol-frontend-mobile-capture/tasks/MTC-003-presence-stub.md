# MTC-003 — Capture send + presence gating stub

**Status:** `done`  
**Contract:** `CaptureModeState`  
**Pillars:** P1, P3  
**Phase:** 1  
**Owner:** unassigned

## Problem

No mode-aware AI presence. Need v1 stub so fragment dumps don't get chatbot paragraphs.

## Scope in

- Local message list in capture UI
- Send action appends user fragment
- Default: presence 0–1 (silent or visual ack only)
- Dev overlay showing inferred `CaptureModeState` (optional, behind flag)
- Hook point for bridge `capture_mode_state` emission

## Scope out

- Full heuristic classifier (MTC-006)
- Real model streaming (bridge integration later)

## Acceptance criteria

- [x] Rapid fragment sends do not produce visible assistant paragraphs
- [x] Explicit nudge/shape affordances escalate presence (shape → level 3+)
- [x] Mode state shape matches CONTRACTS.md

## Files (expected)

- `product/thought_capture_pwa/src/capture/capture-mode.ts`
- `product/thought_capture_pwa/src/capture/local-composer.ts`
- `product/thought_capture_pwa/src/capture/use-capture-stream.ts` (integration)
