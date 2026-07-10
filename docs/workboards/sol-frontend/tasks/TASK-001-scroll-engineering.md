# TASK-001 — Scroll Engineering in mobile_surface_v1

**Status:** `planned`  
**Pillars:** P2 (Never move the reader against their intent), P3 (Preserve flow over visible helpfulness)  
**Owner:** unassigned

## Problem

Mobile capture/chat does not implement Scroll Engineering. Streaming and layout shifts may move the reader against their intent.

## Scope in

- `product/mobile_surface_v1/` chat/capture scroll behavior
- Following vs Detached state machine
- Jump-to-latest affordance
- Detach on select/type/expand

## Scope out

- Capture Surface visual redesign (TASK-002)
- Backend streaming protocol changes unless required

## Acceptance criteria

- [ ] Reader position tracked as explicit state
- [ ] Auto-follow only when Following
- [ ] New user message anchors near top of viewport
- [ ] Offscreen streaming shows indicator + jump action
- [ ] Manual verification notes attached

## Pillar rejection check

- Must not default auto-scroll without detach path (P2)
- Must not interrupt dump mode with scroll jumps from assistant (P3)
