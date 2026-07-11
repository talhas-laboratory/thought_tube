# Decisions — Mobile Thought Capture

## Template

```markdown
### DEC-NNN — Title
- **Date:**
- **Pillars:**
- **Decision:**
- **Deferred:**
- **Sources:**
```

---

### DEC-001 — Subproject scoped from conversation bundle

- **Date:** 2026-06-27
- **Pillars:** P1–P4 (primary)
- **Decision:** Mobile Thought Capture is a dedicated subproject under `sol-frontend`, decomposed in `DECOMPOSITION.md`. v1 delivers Capture Surface + Scroll Engineering + gesture/mode stubs. Conversation bundle is canonical source evidence.
- **Deferred:** Bridge subscription, capability builder, mental environment UI generation → backend/runtime tracks.
- **Sources:** `conv_20260627_125956_smooth-microgestures-on-mobile/`

### DEC-002 — Replace atlas demo as default with capture route

- **Date:** 2026-06-27
- **Pillars:** P1, P5
- **Decision:** Atlas grid demo is not capture. Product entry is `/capture` on the new PWA. **Superseded for artifact root by DEC-005** — implementation moves to `product/thought_capture_pwa/`.
- **Deferred:** none
- **Sources:** conversation Theme B

### DEC-003 — Edge guard default 32px

- **Date:** 2026-06-27
- **Pillars:** P4
- **Decision:** Use `EDGE_GUARD_PX = 32` within the 24–44px range from conversation; tune per device in verification.
- **Deferred:** none
- **Sources:** conversation Theme A

### DEC-004 — Mode router v1 is heuristic, not ML

- **Date:** 2026-06-27
- **Pillars:** P3
- **Decision:** Client-side signals (message length, punctuation, keywords) classify mode for presence gating. Bridge integration emits state; full model routing is phase 2+ backend.
- **Deferred:** ML-based mode classification
- **Sources:** conversation Theme C

### DEC-005 — New PWA app instead of extending mobile_surface_v1

- **Date:** 2026-06-27
- **Pillars:** P1, P5, P8
- **Decision:** Thought capture ships as a new installable PWA at `product/thought_capture_pwa/`. `mobile_surface_v1` remains a topology demo. Canonical infrastructure doc: `mobile_artifacts/2026-06-27/pwa-thought-capture-source-doc.md`.
- **Deferred:** Capacitor / App Store shell until PWA phase 2+
- **Sources:** user direction; PWA platform research 2026

### DEC-006 — Motion vocabulary adopted as binding grammar extension

- **Date:** 2026-06-27
- **Pillars:** P2, P3, P4, P8
- **Decision:** Eight motion primitives (`motion.hold` … `motion.status`), four tiers, and agent decision flow documented in `MOTION.md`. Animation serves confirm/continuity/disclose/follow-through only. Contract annotations added to `CONTRACTS.md`.
- **Deferred:** Shared motion library package across miniapp (promote when second surface needs it)
- **Sources:** capture framework design session; PWA source doc §10; Pillar 8

### DEC-007 — Scroll Engineering framework adopted (parity with MOTION.md)

- **Date:** 2026-06-27
- **Pillars:** P2
- **Decision:** Fifteen rules, nine scroll primitives, intent signal bus, and agent decision flow documented in `SCROLL.md`. Types at `product/thought_capture_pwa/src/scroll/scroll-types.ts`. Scroll owns position; MOTION subordinate.
- **Deferred:** Rule 10 long-thread search/jump (phase 3)
- **Sources:** conv smooth-microgestures msgs 13–14; Pillar 2

### DEC-009 — Conversational composition as field grammar

- **Date:** 2026-06-27
- **Pillars:** P1, P3, P6, P7, P8
- **Decision:** Composition is active in Capture: one `field_stream`, user `voice_lead`, system `coupled_insertion` with contract-shaped weight. Not deferred; not chat alternation. Documented in `COMPOSITION.md`. Replaces informal “composition mostly absent in capture” framing.
- **Deferred:** `block_cluster` UI (develop phase)
- **Sources:** user revision; DECOMPOSITION Theme B/C/E

### DEC-008 — Aesthetic primitives (non-literal)

- **Date:** 2026-06-27
- **Pillars:** P1, P3, P6, P8
- **Decision:** Felt goal is low-obligation deposit + continuity + deferred structure. Expressed via abstract primitives (`open_field`, `primary_locus`, `receding_context`, etc.) in `AESTHETICS.md`. No literal Spaziergang/path/nature UI.
- **Deferred:** none
- **Sources:** user aesthetic direction; capture research Theme B

### DEC-010 — Library organized by warmth, not composition folders

- **Date:** 2026-06-27
- **Pillars:** P1, P2, P4, P6
- **Decision:** Library overview uses sections `now` / `still moving` / `resting` grouped by cognitive temperature and continuity. Composition state (`open`, `waiting`, `shaped`) appears as row badges only — not top-level folders. Documented in `LIBRARY.md`. Return uses `scroll.reopen` at last user deposit.
- **Deferred:** user-defined folders, search-first entry, semantic thread clustering beyond time gaps
- **Sources:** library UX session 2026-06-27; AESTHETICS `adjacency`, `receding_context`, `continuity`

### DEC-011 — PWA is a bridge section, not a bridge control-plane participant

- **Date:** 2026-06-27
- **Pillars:** P5, P8
- **Decision:** `thought_capture_pwa` integrates as a **bridge section** (`surface_id: mobile_capture`). It may **pull** existing bridge features (ingest, session events, optional classify/read APIs) through a section adapter facade. It must **not** mutate bridge steering, behaviors, `prepare_turn` routing, or control-plane config. Documented in `BRIDGE_SECTION.md`. **MTC-008** gates further bridge wire-up.
- **Deferred:** `SurfaceProfile` schema repo-wide promotion; `prepare_turn` from capture UI until adapter infrastructure ships
- **Sources:** user direction 2026-06-27; `subprojects/10-surface-adapters.md`
