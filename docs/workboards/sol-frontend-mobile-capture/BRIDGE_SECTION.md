# Bridge Section — Thought Capture PWA

**Status:** binding (infrastructure pending)  
**Owner:** talha  
**Parent:** `BRIDGE_BINDING.md` (agent workspace binding — separate concern)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27

The Thought Capture PWA is a **bridge section**: a surface adapter that **consumes** bridge capabilities without **mutating** bridge control-plane behavior.

---

## Distinction (critical)

| Concern | What it is | This PWA |
|---|---|---|
| **Bridge control plane** | `prepare_turn`, steering, behaviors, context policy, agent routing | **Does not own or change** |
| **Bridge section (this app)** | Installable surface that emits captures and optionally reads bridge outputs | **Owns UX + local state** |
| **Agent workspace binding** | Cursor/Codex steering into `product/thought_capture_pwa/` | See `BRIDGE_BINDING.md` — dev-time only |

```text
Bridge control plane          Bridge section (PWA)
─────────────────────         ────────────────────
prepare_turn, behaviors  ←── read/call (optional)
ingest, element routes   ←── write events (outbound)
steering markdown        ✗   no write path from PWA
context policy           ✗   no influence on routing
```

**Rule:** Nothing in `thought_capture_pwa` may change how the bridge classifies turns, builds steering, or selects behaviors. The app is a **client of** bridge features, not a **participant in** bridge authoring.

---

## Dependency direction

```text
thought_capture_pwa
  → bridge section adapter (facade in src/bridge/)
  → existing bridge / inner_world HTTP or MCP surfaces
  → element ingest, session events, optional prepare/classify (read-only to app UX)

bridge core
  ✗ must not import from thought_capture_pwa
  ✗ must not branch on PWA-specific UI state
```

Allowed pulls from existing bridge features (via adapter, not direct coupling):

| Bridge capability | Section use | Phase |
|---|---|---|
| Element ingest (`frontend`, `mobile_capture`) | Outbound deposit sync | 2 |
| Session / capture events | Durability + provenance | 2 |
| `run_reasoning` via section compose API | Invited insertion (nudge/shape) | 2 (MTC-006) |
| `prepare_turn` / classify preview | Mode hints (optional; deferred v1) | 2+ |
| Workspace binding metadata | Provenance headers only | 2 |
| `CaptureModeState` contract | Payload shape for compose requests | 2 |

**Reject:** embedding steering markdown in the app, writing to `.thought-tube/`, registering bridge behaviors from the PWA, or adding PWA-specific branches inside `bridge_prepare.py`.

---

## Infrastructure to establish (before wire-up)

**MTC-008** — do this before expanding `src/bridge/bridge-client.ts` or calling `prepare_turn` from UI paths.

### 1. Section adapter facade

Single module boundary: `src/bridge/section-adapter.ts` (name TBD).

- All network/MCP calls go through it
- Maps PWA types ↔ bridge contracts
- No bridge imports in `capture/`, `offline/`, or UI components

### 2. `SurfaceProfile` slice: `mobile_capture`

Per `subprojects/10-surface-adapters.md` and `SPEC.md`:

```yaml
surface_id: mobile_capture
artifact_root: product/thought_capture_pwa/
persistence: indexeddb_first
bridge_writes: [element_ingest, session_event]
bridge_reads: [compose_insertion]  # v0 MTC-006; classify_preview deferred v1
steering_authority: none
```

### 3. Provenance contract (every outbound event)

```json
{
  "source": "thought_capture_pwa",
  "surface_id": "mobile_capture",
  "display_mode": "standalone|browser",
  "element_key": "frontend",
  "holodeck_id": "sol-frontend",
  "session_id": "<bridge session | local until bound>"
}
```

### 4. Sync model (unchanged principle, section-owned)

```text
User send → Dexie (section truth) → adapter.enqueue(sync)
         → adapter.flush() when online
         → bridge ingest (idempotent by local deposit id)
```

Bridge never stores thoughts in the service worker. Section owns replay.

### 5. Config isolation

- PWA env: `VITE_BRIDGE_SECTION_*` — section endpoints only
- Repo `runtime.json` `bridge` block — unchanged by PWA work
- New config (if needed): `bridge_sections.mobile_capture` — **read-only profile**, not control-plane

### 6. Test boundary

- Section adapter tests mock bridge HTTP; no bridge unit tests import PWA
- Bridge tests unchanged when capture UI changes

---

## Provisional code (current)

Phase 1 added `src/bridge/bridge-client.ts` calling `/api/mobile/*` directly. Treat as **scaffold**:

- Replace with `section-adapter` facade per MTC-008
- Do not add `prepare_turn`, steering, or behavior hooks until infrastructure gate passes

---

## Agent obligations

1. Complete **MTC-008** before new bridge wiring tasks.
2. Route all bridge I/O through the section adapter — no stray `fetch` to bridge URLs in UI.
3. Do not modify `bridge_prepare`, behaviors, or steering generation for capture UX.
4. Cite `surface_id: mobile_capture` and provenance fields on sync tasks.

---

## Decision test

1. If this PR changes bridge routing or steering → **reject** (wrong layer).
2. If capture works fully offline with bridge down → **pass**.
3. If bridge team can ship without importing PWA code → **pass**.
4. If a new bridge feature is needed → add to adapter read API, not inline in capture components.

---

## Related

- `BRIDGE_BINDING.md` — agent dev binding (orthogonal)
- `CONTRACTS.md` — `CaptureModeState` bridge hook annotation
- `mobile_artifacts/.../pwa-thought-capture-source-doc.md` §12
- `DEC-011`
