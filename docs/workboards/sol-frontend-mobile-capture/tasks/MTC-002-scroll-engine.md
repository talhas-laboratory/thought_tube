# MTC-002 — ScrollEngine module

**Status:** `done` — state machine, intent bus, hook, field stream integration  
**Contract:** `ScrollEngine`  
**Pillars:** P2  
**Scroll:** `scroll.follow`, `scroll.detach`, `scroll.anchor-turn`, `scroll.preserve-anchor`, `scroll.indicator`, `scroll.jump-latest`, `scroll.reopen`  
**Layout rules:** 1–9, 11–13 (see `SCROLL.md` §Fifteen rules)  
**Intent signals:** scroll, select, type, expand, regenerate, error  
**Phase:** 1  
**Owner:** unassigned

## Problem

No Scroll Engineering in capture PWA. Streaming and layout would move reader against intent.

## Scope in

- `src/scroll/scroll-engine.ts`, `scroll-intent-bus.ts`, `use-scroll-engine.ts`
- Extend `scroll-types.ts` (binding types already seeded)
- `following` | `detached` state machine per `SCROLL.md`
- Jump-to-latest, anchor-turn, preserve-anchor, reopen

## Scope out

- Long-thread search/navigation — rule 10, phase 3
- Backend streaming protocol changes unless required

## Acceptance criteria

- [ ] Detached state survives assistant token streaming (rules 7–8)
- [ ] Jump-to-latest resumes following (rule 9)
- [ ] New user turn anchored near viewport top — instant (rule 4)
- [ ] Manual verification notes (iOS Safari preferred) in `artifacts/`
- [ ] Scroll Gate in `GATES.md` passes

## Files (expected)

- `product/thought_capture_pwa/src/scroll/*`
