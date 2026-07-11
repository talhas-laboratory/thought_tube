# Bridge Compose — Infrastructure Plan (adjusted)

**Status:** binding plan  
**Owner:** talha  
**Applies to:** `product/thought_capture_pwa/` + `src/conversation_os/`  
**Parent:** `BRIDGE_SECTION.md`, `COMPOSITION.md`  
**Task:** MTC-006  
**Revised:** 2026-06-27 (post architecture review)

## Goal

The PWA is **interface only**. When the user invites assist (nudge / shape), the **bridge** orchestrates a response grounded in the **knowledge ocean** and **behaviors**, then returns a **coupled insertion** — not chat, not free-floating assist.

How the agent/pipeline forms prose stays **modular and server-side**. The PWA only renders what the section API returns.

---

## Non-goals

- Symmetric chat UI or `/conversations/{id}/reply` as the primary path
- PWA calling MCP, ocean, or OpenClaw directly
- Auto-compose on every silent deposit in v0 (latency + composition policy)
- PWA mutating bridge steering, behaviors, or `.thought-tube/`

---

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│  thought_capture_pwa (interface)                            │
│  deposit → Dexie → render coupled_insertion                 │
└───────────────────────────┬─────────────────────────────────┘
                            │ section-adapter (facade only)
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  Section HTTP API                                           │
│  POST /api/mobile/capture   — durability + provenance       │
│  POST /api/mobile/compose  — invited insertion only (v0)  │
└───────────────────────────┬─────────────────────────────────┘
                            ▼
┌─────────────────────────────────────────────────────────────┐
│  mobile_capture_compose (new owner)                         │
│  ReasoningRequest → run_reasoning() → project_insertion()   │
└───────────────────────────┬─────────────────────────────────┘
                            │
         classify_turn → get_context_bundle → build_retrieval_bundle
                            → route_reasoning → execute
                            ▼
              InsertionPayload (server-owned contract)
```

**Prior art:** `chat_with_thought()` when `bridge_config.enabled` — same `run_reasoning()` spine, different surface and output projection.

**Reject:** wiring compose to `reply_in_mobile_session()` — bypasses ocean retrieval and behavior routing.

---

## Layer ownership

| Layer | Owns | Does not own |
|---|---|---|
| PWA | Deposit, Dexie truth, render insertion, offline queue | Ocean, behaviors, response formation |
| Section adapter | HTTP transport, provenance, env flags | Business logic |
| Section API | Auth, idempotency, session binding | UI contracts |
| `mobile_capture_compose` | `ReasoningRequest` build, call `run_reasoning`, project insertion | Bridge routing rules |
| Bridge core | Classify, context policy, ocean retrieval, behaviors, execution | PWA types |
| Insertion projector (v0: single impl) | Map reasoning result → `InsertionPayload` | Full answer generation |

---

## v0 scope (minimal viable spine)

### User flow

1. User **deposits** — always local-first (Dexie); optional async capture sync.
2. User taps **nudge** or **shape** (invited assist) — only then call compose.
3. Deposit renders immediately; insertion arrives when compose completes (`motion.reveal`).
4. On compose failure / offline / bridge disabled → **silent** or `local-composer` fallback (existing).

**No auto-compose on deposit in v0.** Matches `COMPOSITION.md` silent-send default and avoids multi-second blocking on the hot path.

### Backend

**New owner:** `src/conversation_os/mobile_capture_compose.py` (name TBD)

```python
compose_mobile_capture_insertion(
    root,
    *,
    deposit_body: str,
    local_deposit_id: str,
    session_id: str,
    provenance: dict,
    capture_mode_state: dict,
    intent: Literal["nudge", "shape"],
    composition_phase: Literal["capture", "develop"],
) -> ComposeResult
```

**`ReasoningRequest` shape:**

```python
ReasoningRequest(
    surface="mobile_capture",
    session_id=session_id,
    raw_text=deposit_body,
    caller_hints={
        "local_deposit_id": local_deposit_id,
        "surface_id": "mobile_capture",
        "holodeck_id": "sol-frontend",
        "element_key": "frontend",
        "composition_phase": composition_phase,
        "response_contract": capture_mode_state["response_contract"],
        "intent": intent,
        "query_override": deposit_body,  # retrieval fallback when active_topic is thin
    },
)
```

**HTTP:**

```
POST /api/mobile/compose
```

Request:

```json
{
  "deposit": {
    "local_deposit_id": "uuid",
    "body": "user thought",
    "created_at": 1719494400000
  },
  "provenance": { "surface_id": "mobile_capture", "element_key": "frontend", "session_id": "…" },
  "session_id": "…",
  "capture_mode_state": { "response_contract": "continuation_cue", "ai_presence": 1 },
  "intent": "nudge",
  "composition_phase": "capture"
}
```

Response (server-owned insertion contract):

```json
{
  "insertion": {
    "utterance_type": "cue",
    "body": "…",
    "blocks": null,
    "composition_phase": "capture",
    "mode_state": { "response_contract": "continuation_cue", "ai_presence": 1 }
  },
  "reasoning": {
    "request_id": "…",
    "routing_source": "agent",
    "pipeline_id": "…",
    "bridge_behavior_ids": []
  },
  "provenance_refs": ["capsule:…"],
  "composed_at": "…"
}
```

Failure / timeout:

```json
{
  "insertion": null,
  "fallback": true,
  "error": "compose_timeout"
}
```

Deposit must never fail because compose failed.

### Insertion projector (v0)

Single implementation: **`text_direct`**.

- Input: `run_reasoning` result (`response_text`, packet, evaluation, retrieval summary)
- Output: full `InsertionPayload` per `COMPOSITION.md` utterance types
- **Server owns the contract** — PWA does not re-map `response_contract` → `utterance_type` on the happy path
- `local-composer.ts` remains **offline / degraded fallback only**

Registry / swappable projectors deferred until a second implementation exists.

### PWA (MTC-006)

Extend `section-adapter.ts`:

```typescript
requestInsertion(deposit, intent, modeState, compositionPhase): Promise<InsertionPayload | null>
```

Wire `use-capture-stream` `nudge` / `shape` → `requestInsertion` → `upsertInsertion` (replace per C6).

Env:

```bash
VITE_BRIDGE_SECTION_SYNC_ENABLED=true
VITE_BRIDGE_SECTION_COMPOSE_ENABLED=true   # compose on nudge/shape only
```

Update `SurfaceProfile.bridge_reads`:

```typescript
bridge_reads: ["compose_insertion"] as const
```

(`classify_preview` optional follow-on — not required for v0 spine.)

---

## Session, provenance, idempotency

| Rule | Detail |
|---|---|
| Session source | `session_id` from capture ack → Dexie meta; compose always sends it |
| Provenance on capture | Backend accepts and stores `provenance` on `POST /capture` (forward `local_deposit_id`, `surface_id`) |
| Idempotency key | `(session_id, local_deposit_id, intent)` — re-nudge replaces insertion (C6), same key returns or replaces consistently |
| Session bootstrap | Drop broken `POST /session` password mismatch for v0; rely on capture-created session |

---

## Operational prerequisites

Curated knowledge answers require:

| Prerequisite | Notes |
|---|---|
| Inner World on `:8422` | `python3 tools/run_inner_world_miniapp.py` |
| `INNER_WORLD_BRIDGE_ENABLED=true` | Without this, heuristic/operator fallback — not full ocean + agent path |
| Ocean data at runtime path | Local dev may need `knowledge_layer` path alignment; treat server integration tests as source of truth |
| OpenClaw agent | When `execution_mode=agent` |

Document in README when testing compose locally.

---

## Build sequence

| Step | Deliverable | Test |
|---|---|---|
| **6a** | `mobile_capture_compose.py` + `project_insertion_text_direct` | pytest with mocked `run_reasoning` |
| **6b** | `POST /api/mobile/compose` in `miniapp.py` | HTTP test in `test_conversation_os.py` |
| **6c** | Provenance on `append_mobile_capture` / capture handler | pytest |
| **6d** | `requestInsertion` in section-adapter + transport | vitest with mocked fetch |
| **6e** | Wire nudge/shape in `use-capture-stream` | manual + vitest |
| **6f** | Optional live test behind flag | `test_agent_bridge_live` pattern |

**Do not block 6d–6e on async infrastructure** — v0 may show loading state on active unit during compose.

---

## v1+ (explicitly deferred)

| Feature | When | Notes |
|---|---|---|
| Async compose (poll / SSE) | After v0 latency measured | Deposit instant; insertion streams in |
| `compose: true` on capture (single round-trip) | After idempotency proven | Reduces double HTTP |
| `classify_preview` on deposit | Light read; no full `run_reasoning` | Mode hints only |
| `compose_on_deposit: true` | Product + latency gate | Config in `bridge_sections.mobile_capture` |
| Insertion projector registry | Second projector exists | `text_direct`, `pipeline_structured`, … |
| `bridge_sections.mobile_capture` runtime config | Behavior tuning needed | Read-only profile; not control-plane |
| Provenance refs in UI | User-visible source chips | Subtle; not v0 |

---

## Config sketch (v1, not v0)

```yaml
bridge_sections:
  mobile_capture:
    insertion_projector: text_direct
    compose_on_deposit: false
    max_ai_presence_capture: 2
    default_context_policy:
      depth_mode: focused
      retrieval_limit: 8
      neighbor_limit: 4
```

v0 uses `caller_hints` only — no new runtime block required to ship the spine.

---

## Binding checks (every PR)

1. Capture works fully offline with bridge down → pass  
2. Compose failure does not block deposit → pass  
3. No PWA imports in `src/conversation_os/` → pass  
4. No bridge steering / behavior writes from PWA → pass  
5. System output is `coupled_insertion` under deposit, ≤1 in capture → pass  
6. v0 compose only on nudge/shape → pass  

---

## Related

- `BRIDGE_SECTION.md` — section boundary  
- `COMPOSITION.md` — insertion grammar  
- `CONTRACTS.md` — `CaptureModeState`  
- `docs/implementation/agent-bridge/00-summary.md` — bridge + ocean model  
- `tasks/MTC-006-bridge-compose.md` — task packet
