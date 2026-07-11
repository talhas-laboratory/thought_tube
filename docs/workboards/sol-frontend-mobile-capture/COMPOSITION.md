# Conversational Composition

**Status:** binding  
**Owner:** talha  
**Parent:** `../sol-frontend/PILLARS.md` (extends P1, P3, P6, P7, P8)  
**Applies to:** `product/thought_capture_pwa/`  
**Created:** 2026-06-27  
**Revises:** prior informal framing that treated composition as “mostly absent” in Capture

Conversational composition governs how **user material** and **system insertions** coexist in one continuous field — without collapsing into chat.

---

## Purpose

Composition answers one question:

> *How does meaning accumulate across deposits while the system participates without taking the room?*

It serves four jobs:

| Job | What it protects |
|---|---|
| **Cognitive continuity** | A line of thought stays holdable as more lands — order and coupling matter |
| **Voice hierarchy** | User material leads; system speech is contract-shaped, not co-equal dialogue |
| **Presence regulation** | When the system speaks, how much, in what shape, and attached to what |
| **Escalation** | How the same stream later supports structure (blocks, branches) without a mode shock |

Composition is **not** optional in Capture. Capture **is** composed — but by **field rules**, not turn-taking.

**Wrong mental model:** alternating speakers in bubbles.  
**Right mental model:** one vertical field where user deposits are primary objects and system output is **coupled insertions** with declared weight and contract.

---

## Agent decision flow

Before layout, copy, or assist rendering:

```text
1. Name composition primitive(s) from §Primitives
2. Identify phase: capture | develop
3. Name utterance type(s) for user + system material
4. Check §Rejects — no symmetric chat, no orphan assist
5. Map pillars (P1, P3 minimum; P6/P7 if blocks)
6. Run decision test (§Decision test)
7. Declare scroll_impact + motion per MOTION.md / SCROLL.md
```

Task packets / PRs may include:

```yaml
composition_primitives: [field_stream, coupled_insertion, voice_lead]
composition_phase: capture
utterance_types: [deposit, continuation_cue]
pillars: [P1, P3]
```

---

## Primitives

### Field

| ID | Concept | Meaning |
|---|---|---|
| `field_stream` | Field stream | One continuous vertical flow — the composed surface |
| `voice_lead` | Voice lead | User deposits carry primary rhetorical weight |
| `coupled_insertion` | Coupled insertion | System output binds to a provoking deposit — never free-floating |
| `insertion_weight` | Insertion weight | Visual + rhetorical scale from `ai_presence` × `response_contract` |
| `composition_unit` | Composition unit | `{deposit + its coupled insertions}` — recession moves together |
| `phase` | Phase | `capture` (sparse assist) \| `develop` (block composition allowed) |

### Utterance types (heterogeneous stream)

Not “messages.” Typed utterances with layout rules.

| Type | Owner | Capture default |
|---|---|---|
| `deposit` | user | always allowed; full weight at locus |
| `ack` | system | presence 0–1; ≤1 short line or visual-only |
| `cue` | system | presence 2; ≤2 lines; continuation, not explanation |
| `mirror` | system | emotional_processing; contain, don't analyze |
| `sharpen` | system | clarification; restate/narrow, not interrogate |
| `block_cluster` | system | develop phase; 3–7 semantic blocks |
| `status` | system | detached/streaming/offline; peripheral only |

### Rhythm

| ID | Concept | Meaning |
|---|---|---|
| `deposit_lane` | Deposit lane | Default rhythm: deposit → optional single insertion → deposit |
| `silence_lane` | Silence lane | `no_response` — composition is user-only stretch |
| `deepen_gate` | Shape gate | User invites structure — blocks, not more dumping |

---

## How composition dictates UI / UX

### 1. Layout — coupling over alternation

| Rule | UX |
|---|---|
| **C1** | System insertions render **immediately under** their provoking `deposit` |
| **C2** | Never render assistant blocks as a parallel column or interleaved bubble row |
| **C3** | `composition_unit` recedes as one — deposit + coupled insertions share depth |
| **C4** | Active locus = active unit; insertion under locus reads at full **insertion** weight (not greyed like archived chat) |

### 2. Weight — contract × presence

Insertion weight is **not** “assistant = dim.” It is **role-specific**:

| Contract | Capture UI weight |
|---|---|
| `no_response` | nothing rendered |
| `acknowledgment_only` | minimal — one word or peripheral confirm (`motion.confirm`) |
| `continuation_cue` | secondary text, legible, ≤2 lines |
| `clarification` / `summary` | secondary, slightly denser; still under deposit |
| `emotional_mirroring` | soft secondary; no bullet analysis |
| `structural_extraction` | **develop phase only** → `block_cluster` |
| `deeper_reasoning` | **develop** or explicit deepen; never ambient in capture |

**Presence caps in capture** (P3): max sustained presence 2. Presence 3–4 changes **phase** to develop, not louder capture.

### 3. Density — one insertion per deposit (capture)

| Rule | UX |
|---|---|
| **C5** | At most **one** system insertion per deposit in capture phase |
| **C6** | Re-invoke replaces previous insertion on same deposit (no assist thread) |
| **C7** | User may deposit again without acknowledging assist — stream continues |

### 4. Motion + scroll (subordinate but binding)

| Composition event | Motion | Scroll |
|---|---|---|
| deposit lands | `motion.confirm` tier 0–1 | anchor user turn per SCROLL rules |
| insertion appears | `motion.reveal` tier 1–2 | `scroll_impact: none` in capture |
| block_cluster expands | `motion.expand` | `anchor-preserve` required |
| streaming | `motion.status` only | detached → no auto-follow |

### 5. Phase transition — composition changes shape, not container

| | Capture phase | Develop phase |
|---|---|---|
| Stream container | same `field_stream` | same field — no new “chat app” chrome |
| System shape | ack / cue / mirror / sharpen | + `block_cluster`, options, branch affordances |
| User expectation | keep going | build from what landed |
| Entry | default | **shape** / **nudge** / mode escalation |

**Reject:** hard navigation to a different visual metaphor when developing.

---

## Relationship to other frameworks

| Framework | Composition uses it for |
|---|---|
| `AESTHETICS.md` | `primary_locus`, `receding_context`, `continuity`, `quiet_default` |
| `CONTRACTS.md` | `CaptureMode`, `ResponseContract`, `AiPresenceLevel`, `SemanticBlock` |
| `MOTION.md` | insertion reveal weight; no performative assist |
| `SCROLL.md` | field_stream scroll; anchor on deposit; detach during read |
| `LIBRARY.md` | overview sections, row anatomy, reopen from library |

```text
Aesthetics → spatial feel
Composition → who speaks, in what shape, attached to what
Motion/Scroll → how change lands without breaking read position
```

---

## Decision test

1. Does the user **lead the field** (voice_lead) or are we asking them to perform for assist?
2. Is every system utterance **coupled** to a deposit (coupled_insertion)?
3. Is insertion weight justified by **contract + presence**, not default “assistant grey”?
4. Does capture respect **one insertion per deposit** and presence ≤2?
5. Would a chat app do the same layout? If yes → revisit — likely violating C1–C2.

---

## Rejects (binding)

| Reject | Why |
|---|---|
| Symmetric user/assistant bubbles | Chat metaphor; breaks voice_lead |
| Orphan assist (not under a deposit) | Breaks coupling; feels like bot interrupted |
| Assist thread under one deposit | Chat colonization; breaks C5–C6 |
| Grey-all-assist as default | Confuses insertion_weight with archive; active unit must read clearly |
| Paragraph after every fragment | Violates deposit_lane / P3 |
| Block walls in capture | Wrong phase; use deepen_gate |
| Composition without utterance type | Uninspectable layout |

---

## User-facing affordances

Primitive IDs stay technical; labels in the UI should be plain verbs.

| Label | Primitive | Phase | What it does |
|---|---|---|---|
| **nudge** | `invited_assist` + re-compose | capture | Light system insertion on this deposit — cue, ack, mirror, or sharpen. Replaces prior insertion. |
| **shape** | `deepen_gate` | develop | Extract **facets of this deposit** into one `block_cluster` insertion — not other deposits from the stream |

**Reject as button copy:** invoke, deepen, ask AI, expand, generate — too dev-y or too chatbot.

Affordances appear only on the **active composition unit** (focused deposit + coupled insertions). Default rhythm remains deposit → deposit without tapping either.

---

## Mock / implementation notes

Canvas and PWA should model:

- `StreamEntry = deposit | coupled_insertion(depositId, utterance_type, …)`
- Recession by `composition_unit` depth, not message parity
- Active unit: deposit at locus + its insertion at full insertion weight
- **nudge** / **shape** = re-compose insertion on same deposit (replace, not append thread)

Answer template construction (mock agent):

```text
classify → response_contract → utterance_type → template fill → insertion_weight → render coupled
```

---

## Pillar map

| Pillar | Composition duty |
|---|---|
| P1 | deposit_lane default; structure via deepen_gate only |
| P2 | composition changes never steal scroll anchor |
| P3 | voice_lead; presence caps; silence_lane valid |
| P6 | phase transition adds hierarchy without new container |
| P7 | sharpen/mirror preserve shape; block_cluster on develop |
| P8 | utterance types are grammar — no one-off layouts |

---

## Provenance

- DECOMPOSITION Theme B/C — capture vs chat; mode + response contract
- DECOMPOSITION Theme E — semantic blocks as develop-phase composition
- User revision — composition is active field grammar, not deferred chat
- Prior tension: grey assist treated archived vs coupled — resolved by `composition_unit` + `insertion_weight`

---

## Agent obligations

1. Cite `composition_primitives` and `utterance_types` in stream/assist UI tasks.
2. Pair with `aesthetic_primitives`, `motion:`, `scroll_primitives:` where relevant.
3. New utterance types → `DECISIONS.md` before first use.
4. Composition Gate in `GATES.md` must pass before assist UI is `done`.
