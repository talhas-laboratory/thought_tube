# Library — Field Memory Overview

**Status:** binding  
**Owner:** talha  
**Parent:** `../sol-frontend/PILLARS.md` (extends P1, P2, P4, P6)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27  
**Pairs with:** `COMPOSITION.md`, `AESTHETICS.md`, `SCROLL.md`

The library is **not** a filing cabinet, inbox, or chat thread list. It is the **same field**, viewed laterally: a receded overview of composition units so the user can find a line of thought and return in one tap.

**Felt goal (non-literal):** memory of one’s own thinking — what is warm, unfinished, waiting, or settled — without depicting “mind,” brain, or path imagery.

---

## Purpose

The library answers:

> *Where was I? What is still moving? What can I pick back up?*

It serves four jobs:

| Job | What it protects |
|---|---|
| **Resume** | Return to the current line without hunting |
| **Continuity** | Deposits that belong together read as one line, not isolated notes |
| **Deferred structure** | No categories, tags, or titles required to browse |
| **Adjacency** | Overview sits beside capture (horizontal peek), not a separate app mode |

---

## Agent decision flow

Before library layout, copy, or grouping:

```text
1. Name aesthetic primitives (§Aesthetic map) — default literal_metaphor: none
2. Name composition unit anatomy (§Row anatomy)
3. Assign warmth section (§Sections) — not user-defined folders in v1
4. Check §Rejects — no chat thread, no inbox, no AI titles
5. Declare reopen behavior (§Return) — scroll.reopen at last user deposit
6. Run decision test (§Decision test)
```

Task packets / PRs may include:

```yaml
aesthetic_primitives: [adjacency, receding_context, continuity]
composition_primitives: [composition_unit, voice_lead]
library_sections: [now, still_moving, resting]
literal_metaphor: none
scroll_primitives: [scroll.reopen, scroll.navigate]
```

---

## Mental model

```text
Capture field  ←——adjacency——→  Library overview
     │                                │
     └─ one vertical stream           └─ same units, receded + grouped by warmth
```

- **Unit of list** = `composition_unit` (`deposit` + optional `coupled_insertion`)
- **Line of continuity** = temporally adjacent deposits in one sitting, or later explicit branch link
- **Thread** = informal name for a continuity line — not a chat thread UI

---

## Sections (v1)

Organize by **cognitive temperature**, not composition-state folders.

| Section ID | Label | Contains | User question |
|---|---|---|---|
| `now` | now | Focused unit + up to 2 predecessors in the same line | “What am I in right now?” |
| `still_moving` | still moving | Recent open loops and assisted units not in `now` | “What did I leave unfinished?” |
| `resting` | resting | Shaped units (`block_cluster`) and cooled older material | “What settled or took shape?” |

### Composition state as badge, not folder

| Badge | Meaning | Maps from |
|---|---|---|
| `open` | Deposit only; no coupled insertion | composition state |
| `waiting` | Assist present; user has not followed up | `coupled_insertion` ≠ `block_cluster` |
| `shaped` | Facets extracted into `block_cluster` | develop phase |

**Reject as primary organization:** `open / with assist / shaped` as top-level folders — useful metadata, wrong mental model for browse.

### Waiting affordance

Units with `waiting` badge may appear in `now` or `still_moving`. Do not hide assist behind a separate inbox. The badge is quiet — not AI preview text.

---

## Row anatomy

Each library row is one composition unit.

| Layer | Rule |
|---|---|
| **Primary** | User deposit text (truncated). Voice leads. |
| **Secondary** | State badge only: `open` · `waiting` · `shaped` |
| **Tertiary** | Optional relative time — never required in v1 |
| **Hidden** | Assistant body as row title; categories; tags; note icons |

### Recession (`receding_context`)

Within and across sections:

- Focused unit: full weight (primary locus in list context)
- `now`: slight recession for older items in the line
- `still_moving`: medium recession
- `resting`: lowest opacity / smaller type — legible, not equal weight

No card grid. No thread bubbles. One vertical stream per section.

### Continuity lines (optional visual)

In `now`, adjacent units from the same sitting may render as a **short stack** (2–3 user lines visible). Tap stack → reopen at **last user deposit** in that line.

v1 may use flat rows with recession; stacks are optional enhancement.

---

## Return behavior

Tap any library row → capture field opens on that **composition unit** so the user can explore further (nudge, shape, continue depositing).

```text
Library tap → focus deposit → animate to capture pane → field_stream at locus → scroll.reopen
```

On return, the field shows:

1. **Locus** — selected deposit at full weight
2. **Coupled insertion** — any assist or shaped blocks under that deposit
3. **Continuity context** — up to two preceding deposits, receded (`receding_context`)
4. **Affordances** — nudge / shape on the active unit when enabled

---

## Gesture & layout

| Rule | Source |
|---|---|
| Horizontal swipe opens overview | P4 `adjacency` |
| 32px edge guard | DEC-003 |
| `touch-action: pan-y` on list | P4 |
| Non-gesture fallback: explicit control to return to field | P4 |
| No full-page carousel between thoughts | P4 reject |

Header copy: `library · swipe right to field` — not “Notes,” “Threads,” or “Inbox.”

---

## Aesthetic map

| Library behavior | Primitive |
|---|---|
| Side overview | `adjacency` |
| Fading older rows | `receding_context` |
| One column, vertical flow | `continuity` |
| User words as labels | `voice_lead` (via COMPOSITION) |
| No categories at browse | `deferred_structure` |
| Quiet assist signal | `ambient_ack` |

---

## Relationship to other frameworks

| Framework | Library uses it for |
|---|---|
| `COMPOSITION.md` | Unit = deposit + coupled insertion; badges |
| `AESTHETICS.md` | Recession, adjacency, no literal metaphor |
| `SCROLL.md` | Reopen anchor; no animated scroll on navigate |
| `MOTION.md` | Pane transition tier 1–2; `scroll_impact: none` on list |
| `CONTRACTS.md` | `CaptureSurface` boundary — no Development tools in library |

---

## Decision test

1. Is the **user’s deposit** the primary label on every row?
2. Can the user find **recent / unfinished** material without filing anything?
3. Does browse feel like **the same field, receded** — not a different app?
4. Does return land on **their last deposit**, not a transcript bottom?
5. Is any **literal mind/brain/path** metaphor visible? If yes → reject.

---

## Rejects (binding)

| Reject | Why |
|---|---|
| Chat thread list with last-message preview | Violates P3, voice_lead |
| AI-generated titles as row headers | Interpretation before user owns material |
| Topic folders in v1 | Violates P1 deferred_structure |
| Grid of cards / note thumbnails | Document metaphor |
| Per-thought horizontal pager | P4 — page carousel |
| Inbox / unread counts as primary chrome | Dashboard on entry |
| Equal visual weight for all rows | No receding_context |
| Development panels in library | CaptureSurface boundary |

---

## Deferred (v2+)

- User-defined folders (only after explicit user request + DEC)
- Search-first library entry
- Semantic thread clustering beyond time gaps
- Branch preview in list rows

---

## Provenance

- Conversation: library overview via swipe, not per-thought flip
- User direction: organize as “mind” via warmth + continuity, not literal metaphor
- DEC-010

---

## Agent obligations

1. Cite `library_sections` and `aesthetic_primitives` in library UI tasks.
2. Keep composition state as **badge**, sections as **warmth**.
3. Wire return to `scroll.reopen` before marking library `done`.
4. Library Gate in `GATES.md` must pass before library UI ships.
