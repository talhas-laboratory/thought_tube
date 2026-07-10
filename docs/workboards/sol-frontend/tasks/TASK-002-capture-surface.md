# TASK-002 — Capture Surface UI pass

**Status:** `planned`  
**Pillars:** P1 (Thoughts land before understood), P3 (Preserve flow)  
**Owner:** unassigned

## Problem

Mobile surface does not distinguish Capture mode from Development mode. Entry feels document-like rather than "just put it here."

## Scope in

- Full-screen capture layout (low chrome, spotlight content, embedded input)
- Mode flag or route separating capture from development
- Copy and empty states aligned with P1

## Scope out

- Scroll Engineering implementation (TASK-001) except coordination
- Full Development Surface build

## Acceptance criteria

- [ ] Capture mode identifiable in UI and routing
- [ ] No required categorization at entry
- [ ] Visual reference or screenshot in `artifacts/`
- [ ] Pillar mapping documented in PR/handoff

## Pillar rejection check

- Must not use Development patterns in Capture (P1)
- Must not add chatbot gravity on first dump (P3)
