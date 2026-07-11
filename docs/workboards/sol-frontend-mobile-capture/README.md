# Mobile Thought Capture Workboard

Purpose: execute the mobile thought-capture subproject decomposed from the Smooth Microgestures conversation.

Board id: `sol-frontend-mobile-capture`  
Parent: `sol-frontend`  
Holodeck: `memory/workspaces/sol-frontend/`  
Artifact root: `product/thought_capture_pwa/`  
Owner: `talha`  
Created: `2026-06-27`  
Status: `active`

## Read order

1. `../sol-frontend/PILLARS.md` — binding decision spine
2. `SPEC.md` — subproject scope and phases
3. `SCROLL.md` — scroll primitives, fifteen rules, state machine (P2)
4. `MOTION.md` — motion primitives, tiers, agent decision flow
5. `COMPOSITION.md` — field stream, utterance types, voice hierarchy (P3)
6. `AESTHETICS.md` — spatial/presence primitives (non-literal)
7. `LIBRARY.md` — field memory overview, warmth sections, return behavior (P4)
8. `BRIDGE_SECTION.md` — section adapter boundary; gate before bridge wire-up (P5, P8)
9. `BRIDGE_COMPOSE_PLAN.md` — ocean-grounded insertion spine (MTC-006)
10. `BRIDGE_BINDING.md` — agent workspace binding (dev-time; orthogonal)
11. `DECOMPOSITION.md` — conversation breakdown
12. `CONTRACTS.md` — implementation contracts (includes scroll + motion annotations)
13. `TASKS.md`, `GATES.md`, `DECISIONS.md`

## Agent protocol

- Every task lists `pillars:`, `contract:`, and when touching scroll/streaming: `scroll_primitives:`, `intent_signals:`, `layout_rules:` per `SCROLL.md`
- When touching UI motion: `motion:`, `tier:`, `scroll_impact:` per `MOTION.md`
- When touching visual/copy: `aesthetic_primitives:` per `AESTHETICS.md`; default `literal_metaphor: none`
- When touching stream/assist layout: `composition_primitives:`, `utterance_types:`, `composition_phase:` per `COMPOSITION.md`
- When touching library overview: `library_sections:`, `aesthetic_primitives:` per `LIBRARY.md`; `literal_metaphor: none`
- Mobile UX changes need verification notes in `artifacts/`
- Adjacent backend topics (bridge subscription, capability builder) → record in `DECISIONS.md` as deferred, do not implement here

## Source evidence

| Artifact | Path |
|---|---|
| Conversation bundle | `mobile_artifacts/2026-06-27/conv_20260627_125956_smooth-microgestures-on-mobile/` |
| Prior research brief | `mobile_artifacts/2026-06-27/frontend-chat-converter-research-brief.md` |
| Legacy atlas demo | `product/mobile_surface_v1/src/mobile-app.tsx` |
| **New capture PWA** | `product/thought_capture_pwa/` |
| **PWA source doc** | `mobile_artifacts/2026-06-27/pwa-thought-capture-source-doc.md` |
| **Bridge binding** | `BRIDGE_BINDING.md` |

## Session binding

```text
#frontend — mobile capture <task>
```
