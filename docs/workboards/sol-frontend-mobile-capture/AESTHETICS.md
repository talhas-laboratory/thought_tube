# Aesthetics — Primitive Concepts

**Status:** binding  
**Owner:** talha  
**Parent:** `../sol-frontend/PILLARS.md` (extends P1, P3, P6, P8)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27

UI aesthetics are expressed through **primitive concepts**, not literal metaphors. The product should *feel* like unhurried inner movement — easy to drop thought and build from it — without depicting paths, nature, or stroll imagery.

**Reject:** obvious metaphor in copy, iconography, or layout (footprints, roads, trees, “take a walk”, notebook-as-journal clichés).

**Use:** abstract spatial, temporal, and presence primitives that compose into a coherent capture experience.

---

## Agent decision flow

Before visual or copy decisions:

```text
1. Name aesthetic primitive(s) from §Primitives
2. Check §Rejects — no literal metaphor, no document/chat defaults
3. Map pillars (P1, P3, P6 minimum for capture)
4. Run decision test (§Decision test)
5. New primitive → DECISIONS.md before use
```

Task packets / design notes may include:

```yaml
aesthetic_primitives: [open_field, receding_context, primary_locus]
pillars: [P1, P3, P6]
literal_metaphor: none
```

---

## Core felt goal (non-literal)

**Low obligation at entry. Continuity while moving. Structure only when invited.**

The user can deposit unfinished material, keep going, and later deepen — without switching mental models or performing for the system.

---

## Primitives

Composable concepts. Not visual skins.

### Spatial

| ID | Concept | Meaning |
|---|---|---|
| `open_field` | Open field | Entry has no required shape, label, or type. Space accepts anything. |
| `primary_locus` | Primary locus | One active region holds attention; not “a card” or “a note” — a focal region. |
| `receding_context` | Receding context | Prior material remains legible but yields visual and cognitive priority. |
| `continuity` | Continuity | One surface flows vertically; no discrete “documents” or page breaks. |
| `adjacency` | Adjacency | Related states sit beside the locus without navigation away (horizontal peek). |
| `depth_on_invite` | Depth on invite | More structure appears only when the user asks for it. |

### Temporal

| ID | Concept | Meaning |
|---|---|---|
| `immediate_land` | Immediate land | Deposit registers instantly; no ceremony. |
| `deferred_structure` | Deferred structure | Categories, titles, outlines arrive late or never by default. |
| `pause_without_mode_switch` | Pause without mode switch | Deepening does not feel like opening a different app. |

### Presence (system)

| ID | Concept | Meaning |
|---|---|---|
| `quiet_default` | Quiet default | System presence is low unless escalated (ties to AI presence 0–2). |
| `ambient_ack` | Ambient ack | Feedback is peripheral — state, not dialogue. |
| `invited_assist` | Invited assist | Help appears as affordance, not interruption. |

### Rhythm (capture loop)

| ID | Concept | Meaning |
|---|---|---|
| `deposit` | Deposit | User adds raw material — one action, minimal chrome. |
| `continue` | Continue | Default next move is more deposit, not processing. |
| `optional_deepen` | Optional shape | Build/expand/branch is always optional, never blocking. |

### Maps to interaction grammar (non-literal)

| Aesthetic primitive | Grammar counterpart |
|---|---|
| `primary_locus` | fragment / thought frame |
| `receding_context` | scroll + typographic recession |
| `adjacency` | semantic swipe, lens peek |
| `depth_on_invite` | expand-to-depth, Development surface |
| `ambient_ack` | `motion.confirm`, `motion.status` |
| `optional_deepen` | post-send soft affordances, `motion.reveal` |

---

## Visual expression (emergent, not literal)

Primitives **imply** treatment; they do not mandate metaphor.

| Primitive | Emergent treatment (examples) |
|---|---|
| `open_field` | Full viewport, low chrome, no empty-state lecture |
| `primary_locus` | One region at full emphasis (scale, contrast, weight) |
| `receding_context` | Reduced opacity/scale/type size for non-active material |
| `continuity` | Vertical flow, no card grid, no thread bubbles |
| `quiet_default` | No assistant block after every deposit |
| `deferred_structure` | No metadata row at send time |

**Tokens** name roles, not metaphors:

```css
/* aesthetic roles — not “path” or “forest” */
--surface-field: ...;
--locus-emphasis: ...;
--context-recede-opacity: ...;
--context-recede-scale: ...;
--accent-locus: ...;
```

---

## Decision test

1. Can the user deposit something **without deciding what it is**?
2. Does the active region hold attention **without** looking like a document or chat bubble?
3. Does older material **recede** rather than compete or vanish?
4. Is structure **deferred** unless the user invites it?
5. Is any metaphor **visible in UI** (icon, copy, illustration)? If yes → reject.

---

## Rejects (binding)

| Reject | Why |
|---|---|
| Literal stroll/path/nature UI | Cute metaphor collapses into gimmick |
| Document metaphor (title, page, note) | Violates P1 |
| Chat thread metaphor | Violates P3 |
| Dashboard / inbox on entry | Violates P6, breaks `open_field` |
| Equal visual weight for all deposits | No `receding_context` |
| Structure before deposit | Violates `deferred_structure` |
| Decorative aesthetic without primitive mapping | Uninspectable, drifts from pillars |

---

## Surface policy

| Surface | Dominant primitives |
|---|---|
| **Capture** | `open_field`, `primary_locus`, `receding_context`, `quiet_default`, `deposit`, `continue` |
| **Development** | `depth_on_invite`, `optional_deepen`, `adjacency`, `invited_assist` |

Capture max: `invited_assist` only via soft affordances — not full collaborative UI.

---

## Pillar map

| Pillar | Primitives |
|---|---|
| P1 | `open_field`, `immediate_land`, `deferred_structure` |
| P2 | `continuity`, `receding_context` (scroll owns pace) |
| P3 | `quiet_default`, `ambient_ack`, `continue` |
| P4 | `adjacency` |
| P6 | `receding_context`, `depth_on_invite`, `optional_deepen` |
| P7 | `depth_on_invite` (shape compare on expand) |
| P8 | vocabulary aligns with MOTION + gesture grammar |

---

## Provenance

- Product sentence: thoughts land before understood (P1)
- Spaziergang discussed as **felt goal**, not literal UI (2026-06-27)
- Capture research: immersive frame, low chrome, progressive revelation
- `MOTION.md`, `SCROLL.md` — subordinate expression layers

---

## Agent obligations

1. Cite aesthetic primitives in UI/copy/visual tasks.
2. Never ship literal metaphor without explicit user request and DEC entry.
3. Pair with `motion:` and `scroll_primitives:` where interaction is touched.
4. Aesthetic Gate in `GATES.md` must pass before capture UI is `done`.
