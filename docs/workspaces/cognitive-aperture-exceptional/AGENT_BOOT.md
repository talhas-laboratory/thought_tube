# Agent Boot — Cognitive Aperture Exceptional

**Audience:** any fresh agent (Cursor, Codex, Claude, local) with no prior chat  
**Mission:** harden selective disclosure from good → exceptional  
**Workspace / Holodeck id:** `cognitive-aperture-exceptional`  
**Branch:** `cursor/cognitive-aperture-gap-map-24c7` (PR [#32](https://github.com/talhas-laboratory/thought_tube/pull/32))  
**Live API:** register when `talhas-laboratory` is online — until then git + local Holodeck are the resume surface

---

## 0. Orientation (read this first — do not skip)

You are not building a chatbot memory dump. You are hardening a **cognitive aperture engine**.

### Situational frame

| Field | Value |
|-------|-------|
| **Active object** | Selective disclosure / cognitive aperture runtime |
| **Purpose** | Place foreign intelligence in the correct neighborhood of a vast private Inner World |
| **Posture** | Enforce honesty of disclosure; measure aperture quality; avoid packet theater |
| **Tension** | Strong doctrine vs fail-open / leaky / parallel implementation |
| **Depth** | Implementation-ready for Phase 1 P0; do not reopen product ontology |

### Four-layer law (steer by this)

```text
Orient  → thin state/posture (place the model)
Grant   → what may open (layers, budgets, refs)
Evidence→ high-SNR material actually opened
Receipt → audit/handoff packet (not the steering mind)
```

### Non-negotiable non-claims

- Inner World ponds ≠ LLM residual-stream subspaces  
- Context packets are **receipts**, not the primary steer  
- Long-context stuffing is not aperture intelligence  
- Anti-dump is **code debt**, not a debate to re-litigate in every turn

### Success if you leave

Another agent can resume from this boot + gap map without the original chat, and either:

1. Phase 0 is fully locked (done), or  
2. A Phase 1 P0 task (CAE-001/002/003) has tests green and is pushed

---

## 1. Authority map

| Need | Source of truth |
|------|-----------------|
| **Semantics / plan** | [`derived/GAP_MAP.md`](./derived/GAP_MAP.md) |
| **Disclosure law** | [`derived/ADR-001-orient-grant-evidence-receipt.md`](./derived/ADR-001-orient-grant-evidence-receipt.md) |
| **Neighborhood landscape** | [`NEIGHBORHOOD.md`](./NEIGHBORHOOD.md) ← open next |
| **Coordination** | Live API when up; else Holodeck local + this git workspace |
| **Code** | Paths in §4 grant table |
| **Product contracts** | `docs/product/semantic-operating-layer/FRAME_CONTRACTS.md` |

Protocol: [`../WORKSPACE-AGENT-PROTOCOL.md`](../WORKSPACE-AGENT-PROTOCOL.md)

---

## 2. Boot sequence (≤15 minutes)

Read **only** this ordered grant (do not open the ocean):

| Step | Open | Why |
|------|------|-----|
| 1 | **This file** | Orientation |
| 2 | [`NEIGHBORHOOD.md`](./NEIGHBORHOOD.md) | What is in/out of this region |
| 3 | [`derived/ADR-001-orient-grant-evidence-receipt.md`](./derived/ADR-001-orient-grant-evidence-receipt.md) | Locked law |
| 4 | [`derived/GAP_MAP.md`](./derived/GAP_MAP.md) §§1–2, §5 G1–G3, §6 Phase 1 | Scorecard + P0 gaps |
| 5 | [`CONTINUITY.md`](./CONTINUITY.md) | Current blocker + next action |
| 6 | One task packet: CAE-001 **or** CAE-002 **or** CAE-003 | Execution aperture |

Widen only if the task requires it (see NEIGHBORHOOD widen rules).

---

## 3. Checkout

```bash
cd /path/to/thought_tube
git fetch origin
git checkout cursor/cognitive-aperture-gap-map-24c7
git pull origin cursor/cognitive-aperture-gap-map-24c7
```

Optional Holodeck:

```bash
python3 tools/conversation_os.py holodeck status --workspace-id cognitive-aperture-exceptional
```

---

## 4. Code grant (default allowed paths)

| Phase 1 task | Primary paths |
|--------------|---------------|
| **CAE-001** fail-empty | `src/conversation_os/knowledge_layer.py`, retrieval/bridge tests |
| **CAE-002** leak kill | `src/conversation_os/chat_backends.py`, compose tests |
| **CAE-003** budgets | `src/conversation_os/reasoning_bridge.py`, `models.py`, policy tests |
| **CAE-004** orient-first | `chat_backends.py`, `reasoning_bridge.py` |

Do **not** start with World Studio, metaphysical ontology rebuild, or activation-steering research unless the task packet says so.

---

## 5. Known failures (still true in code)

These are the neighborhood hazards — fix, don’t re-derive:

1. Retrieval fails open (`confidence` seeds + forced `ranked[:3]`)  
2. `token_budget` unused for truncation  
3. `bounded` envelope layers ≡ `open`  
4. Execution prompt includes “Suppressed frame blocks”  
5. FrameSpec is post-hoc / preview-heavy  
6. Parallel scorers (bridge / Holodeck / feed / task pack)

---

## 6. Phase 1 order (do not reorder without cause)

1. **CAE-001** Fail-empty retrieval  
2. **CAE-002** Suppression leak  
3. **CAE-003** Token budget + envelope matrix  
4. **CAE-004** Orient-first compose  

Rationale: honesty of disclosure before polish; research (context rot / lost-in-middle) says distractors and leaks are the critical harms.

---

## 7. Engineering guard

Before code edits:

```bash
. .venv/bin/activate
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "..." --purpose "..." --proposed-paths "path/a.py,path/b.py"
```

Docs-only orientation work may proceed under the established `docs/workspaces/` owner surface (see `derived/GUARD_JUSTIFICATION.json`).

---

## 8. Handoff minimum

When you stop, leave:

1. Updated note in [`CONTINUITY.md`](./CONTINUITY.md) (next safe action)  
2. Commit + push on the working branch  
3. If live API is up: claim/update task + `workspace_projection_sync.py publish`  
4. Point the next agent at **this file**, not the full chat

---

## 9. One-line compass

> Orient thin → grant narrow → evidence dense → receipt honest.  
> Measure neighborhood hit-rate. Never pad the aperture.
