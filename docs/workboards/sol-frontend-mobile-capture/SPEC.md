# Mobile Thought Capture — Subproject Spec

Status: `active`  
Owner: `talha`  
Parent element: `frontend`  
Parent holodeck: `sol-frontend`  
Bound system: `#10 Surface adapters`  
Artifact root: `product/thought_capture_pwa/` (new PWA — `mobile_artifacts/2026-06-27/pwa-thought-capture-source-doc.md`)  
Legacy reference: `product/mobile_surface_v1/` (atlas demo only)  
Workboard: `docs/workboards/sol-frontend-mobile-capture/`  
Source conversation: `mobile_artifacts/2026-06-27/conv_20260627_125956_smooth-microgestures-on-mobile/`

## One-line goal

Build a mobile web thought-capture interface where thoughts land before they are understood — with Scroll Engineering, immersive capture layout, and mode-aware AI presence.

## Responsibility

Implement the **Capture Surface** and its supporting interaction contracts in `product/thought_capture_pwa/`, decomposed from the Smooth Microgestures conversation. Every decision traces to `docs/workboards/sol-frontend/PILLARS.md`.

## Scope in

- Capture Surface UI (immersive, low-chrome, embedded input)
- Scroll Engineering (`Following` | `Detached`)
- Object-level horizontal microgestures with edge guard
- Capture mode router (v1 heuristic stub + bridge integration hook)
- AI presence levels 0–2 as default in capture mode
- Post-send soft affordances (expand, leave, extract — non-forced)
- Route split: `/capture` vs `/develop` (development stub acceptable)

## Scope out

- Bridge subscription / API key product (backend element)
- Capability builder / mental environment runtime
- Full Development Surface (phase 3 stub only)
- Native shell packaging (pillar 8 later)
- Feed / miniapp alignment (separate TASK-004 on parent board)

## First contracts

See `CONTRACTS.md`, `SCROLL.md`, and `MOTION.md`:

- `CaptureSurface` — layout and chrome rules for capture mode
- `ScrollEngine` — reader position state machine
- `GestureZone` — object-level horizontal drag rules
- `CaptureModeState` — mode + response_contract + ai_presence

## Integration

| Layer | Integration |
|---|---|
| Bridge | Section compose (`run_reasoning`, `surface=mobile_capture`) on invited nudge/shape; see `BRIDGE_COMPOSE_PLAN.md` |
| Element captures | Conversation ingested to `frontend` provisional space |
| Surface adapters | Defines `SurfaceProfile` slice for `mobile_capture` |
| Mobile artifacts | Bundle stored under `mobile_artifacts/2026-06-27/` |

## Phases

| Phase | Deliverable | Pillars | Status |
|---|---|---|---|
| **1** | Capture shell + Scroll Engineering + presence stub | P1, P2, P3 | **done** |
| **2** | Gestures + post-send affordances + bridge section | P3, P4, P5 | partial — **MTC-006** remaining |
| **3** | Development surface entry + semantic blocks | P6, P7, P8 | planned |

## Acceptance criteria

- [x] `/capture` route renders immersive capture shell (not atlas demo)
- [x] Scroll state machine implements Following / Detached with jump-to-latest
- [x] New user turn anchors near viewport top; streaming respects detach
- [x] Horizontal drag on thought object respects 32px edge guard + `touch-action: pan-y`
- [x] Default AI presence in capture is level 0–2 (no paragraph dumps on fragments)
- [x] Gates in `GATES.md` pass for shipped contracts (manual iOS notes pending)
- [x] Verification notes in `artifacts/` (MTC-001, MTC-002, MTC-003, …)

## Active workspace links

- Holodeck: `memory/workspaces/sol-frontend/`
- Materialized brief: `context/workspaces/sol-frontend/brief.md`
- Decomposition: `DECOMPOSITION.md`
- Parent pillars: `../sol-frontend/PILLARS.md`
