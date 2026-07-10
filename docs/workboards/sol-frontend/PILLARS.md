# Frontend Pillars

Owner: `talha`  
Holodeck: `sol-frontend`  
Element: `frontend`  
Status: `binding`  
Created: `2026-06-27`

Every frontend decision in this workspace must trace to one or more pillars below. If a proposal conflicts with a pillar, the pillar wins unless an explicit decision record overrides it with provenance and rollback path.

## How to use this file

Before designing, building, or reviewing frontend work:

1. Name which pillar(s) the change serves.
2. Check whether it violates any pillar's rejections.
3. Run the pillar's decision test.
4. If two pillars tension, record the tradeoff in `DECISIONS.md` before shipping.

```text
Proposal → pillar mapping → rejection check → decision test → ship or record tension
```

---

## Pillar 1 — Thoughts land before they are understood

**Invariant:** Capture must feel pre-intentional. Structure is earned, not required at entry.

**Governs:**
- Mobile capture surface layout and copy
- Onboarding and empty states
- When categorization, tagging, or typing metadata appears
- Default AI behavior on first messages in a session

**Two surfaces (non-negotiable model):**
| Surface | Job | Feel |
|---|---|---|
| **Capture** | Raw thought dumping | Immersive, low chrome, one dominant object, fluid frame |
| **Development** | Structure, branching, collaboration | Explicit tools, hierarchy, history, transformation |

Capture primitives from research:
- Full-screen focus, dark surround / spotlight on content
- Input embedded in the scene
- Cognitive permissiveness: fragments, unfinished text, tone shifts, no early labels

**Rejects:**
- "Create a note" document mental model for first capture
- Forcing type/category before the user has dumped
- Using Development Surface patterns (sidebars, outlines, metadata panels) in Capture mode
- AI that asks clarifying questions during high-flow dumping

**Decision test:** Does this make it easier to put something down before knowing what it is?

**Sources:** chat converter `smooth-microgestures-on-mobile` (2026-06-27); product thesis on formations vs raw text.

---

## Pillar 2 — Never move the reader against their intent

**Invariant:** Scroll Engineering — reader position is sacred state.

**Governs:**
- Streaming chat and capture reply UX
- Auto-scroll behavior
- Layout shifts from images, markdown, code blocks, lazy-loaded history
- Regenerate, branch, retry, and error flows
- Reopen / resume behavior for saved conversations

**Core contract:**
```text
Reader position is state.
Auto-follow is conditional (Following | Detached).
Layout shifts must preserve anchors.
Streaming must not override intent.
```

**Following:** user at live edge → app may keep stream in view.  
**Detached:** user scrolled, selected, typed, searched, or expanded → app must not move them.

**Required behaviors:**
- New user turn starts near top of viewport; answer streams into space below
- Offscreen streaming shows indicator + "Jump to latest"
- Reopen at last meaningful user turn, not blind bottom snap
- Any interaction listed as intent signal pauses auto-follow

**Rejects:**
- Auto-scroll as default with no detach path
- Streaming tokens that yank the viewport
- Regenerate/branch that steals scroll position without warning
- Treating scroll position as disposable on every layout change

**Decision test:** If the user is reading mid-thread, does this change move them without their consent?

**Canonical framework:** `docs/workboards/sol-frontend-mobile-capture/SCROLL.md`

**Sources:** chat converter `smooth-microgestures-on-mobile` — Scroll Engineering pillar (2026-06-27).

---

## Pillar 3 — Preserve flow over visible helpfulness

**Invariant:** The AI optimizes continuation, not conversational performance.

**Governs:**
- When the assistant replies vs stays silent
- Response length, shape, and timing on mobile capture
- Mode inference: raw dump, exploration, clarification, development, emotional processing, task conversion
- Response contracts: no response, acknowledgment, continuation cue, summary, structure extraction

**Behavioral shift:**
- Not every input is a prompt expecting an answer
- AI presence varies: low in dump mode, higher in development mode
- Background structure is allowed; visible colonization of the thought is not

**Rejects:**
- Full assistant paragraphs after every fragment
- Clarifying question cascades during capture
- Turning capture into "chat with a bot" by default
- Interpretation that arrives before the user has finished moving

**Decision test:** Does this help the user keep going, or does it make them compose for the machine?

**Sources:** chat converter `smooth-microgestures-on-mobile` (2026-06-27); Personal Interface flow modes in repo.

---

## Pillar 4 — Objects move; pages don't

**Invariant:** Spatial interaction happens on objects inside a stable viewport.

**Governs:**
- Horizontal microgestures on mobile web
- Card / fragment / thought object interactions
- Lens switching and branch preview
- Feed item expand and peek behaviors

**Rules:**
- Vertical scroll = depth through content
- Horizontal gesture = adjacent semantic state on an object (lens, branch, relation)
- Use `transform: translateX`, `touch-action: pan-y`, direction locking
- **24–44px edge guard** — no horizontal gestures starting at screen edges (iOS back-swipe)
- Always provide non-gesture fallback (buttons, handles, tabs)

**Rejects:**
- Full-page horizontal carousels as primary navigation
- Edge swipes as main interaction
- Gestures without visible affordance or fallback
- Browser-fighting `preventDefault` hacks as the core design

**Decision test:** Is this gesture attached to a thought object, or is it trying to move the whole app like a slideshow?

**Sources:** chat converter `smooth-microgestures-on-mobile` (2026-06-27).

---

## Pillar 5 — Same substrate, adapted surfaces

**Invariant:** Surfaces adapt the ontology; they do not fork it.

**Governs:**
- `mobile_surface_v1`, miniapp, thoughtboard showcase, future lens UIs
- API payload shapes shared across surfaces (`preview_payload`, `expand_payload`, provenance fields)
- Bridge session binding and element routing on frontend work
- What logic lives in surface adapters vs backend

**Surface map (v1 scope):**
| Surface | Role |
|---|---|
| Morning Batch | Small daily insight delivery |
| Feed | Scrollable ocean of surfaced thoughts |
| Article / expand | Depth reveal from fragment |
| Thought-native thread | Per-thought conversation |
| Archive | History and retrieval |
| Mobile capture | Low-friction dump + optional continuation |
| Miniapp | Repo-connected inspection and feed iteration |

**Rejects:**
- Duplicate domain models per surface
- Surface-only business rules that belong in bridge/runtime
- Feed UI that invents parallel semantics unrelated to thought packets
- Mobile-only shortcuts that cannot trace provenance to shared contracts

**Decision test:** Could another surface render the same semantic object without re-implementing meaning?

**Sources:** `SYSTEMS.md` #10 Surface adapters; chat converter `product-surfaces-explanation`, `feed-surface-research`.

---

## Pillar 6 — Soft hierarchy, progressive discovery

**Invariant:** The interface needs hierarchy without feeling like a conversion funnel.

**Governs:**
- Feed layout and information density
- Entry points into depth (expand, thread, article)
- Grouping, sectioning, and visual weight
- Onboarding that teaches by exploration, not wizard steps

**Rejects:**
- Rigid dashboard / enterprise information architecture on exploratory surfaces
- Flat undifferentiated lists with no entry points
- Forcing linear paths when the product promise is non-linear thought
- Over-chrome that competes with content

**Decision test:** Does this help someone discover depth without locking them into a single path?

**Sources:** chat converter `feed-surface-research` (~May 2026); Inner Space exploratory product posture.

---

## Pillar 7 — Shape preservation under translation

**Invariant:** Output must preserve the user's intended shape, not just look polished.

**Governs:**
- Personal Interface / output formatting layer on user-facing text
- Preview and compare flows before accepting AI-shaped content
- Feedback loops that train future rendering
- Expand and rewrite affordances on feed items

**Loop:**
```text
Intent shape → execution model → artifact shape → shape delta → model update
express → render → compare → correct → remember
```

**Rejects:**
- Rewrites that change facts, numbers, URLs, or code without guard
- "Sounds good" output that drifts from user's taste profile
- One-shot generation with no compare/correct path
- Hiding that output was transformed

**Decision test:** If the user says "that's not what I meant," can the system learn what shape was lost?

**Sources:** chat converter `ai-and-digital-interfaces` (2026-05-17); Personal Interface fidelity guard in repo.

---

## Pillar 8 — One shell, many lenses (interaction grammar)

**Invariant:** Many specialized UIs share one physical-feeling interaction language.

**Governs:**
- Long-term Inner World Shell strategy (WebView + native bridges)
- Reusable primitives across frontend surfaces
- PWA packaging and native affordances (haptics, offline capture, controlled gestures)

**Shared primitives (target vocabulary):**
- fragment card
- semantic swipe
- expand-to-depth
- context drawer
- lens switcher
- bottom capture sheet
- provenance inspector
- haptic confirmation
- offline draft queue

**Motion primitives (binding extension):** see `docs/workboards/sol-frontend-mobile-capture/MOTION.md` — `motion.hold`, `motion.confirm`, `motion.follow`, `motion.settle`, `motion.reveal`, `motion.expand`, `motion.cross`, `motion.status`

**Rejects:**
- Every new feature inventing its own interaction dialect
- Building native apps per lens when a shell + web applet suffices
- Shell logic that encodes product semantics (shell is vessel, not brain)

**Decision test:** Is this a new primitive for the grammar, or a one-off that should compose existing primitives?

**Sources:** chat converter `native-feel-web-app-mcp` (2026-05-17).

---

## Pillar precedence (when tensions collide)

1. **Pillar 1** (capture) + **Pillar 2** (scroll) win in Capture mode.
2. **Pillar 5** (substrate) wins over surface convenience.
3. **Pillar 7** (shape) wins over brevity or "nice" wording.
4. **Pillar 8** (grammar) is long-range; do not block near-term shipping unless it creates a dead-end dialect.

Record explicit overrides in `DECISIONS.md`.

---

## Implementation priority (derived from pillars)

| Order | Work unit | Primary pillars |
|---|---|---|
| 1 | Scroll Engineering in mobile chat/capture | 2, 3 |
| 2 | Capture Surface UI pass | 1, 3 |
| 3 | Object-level gesture prototype | 4, 8 |
| 4 | Feed preview/expand contract alignment | 5, 6, 7 |
| 5 | Interaction grammar doc → `SurfaceProfile` | 5, 8 |
| 6 | Inner World Shell packaging | 8 |

---

## Provenance index

| Artifact | Path |
|---|---|
| Chat converter research brief | `mobile_artifacts/2026-06-27/frontend-chat-converter-research-brief.md` |
| Product element registry | `docs/product/semantic-operating-layer/ELEMENTS.md` |
| Surface adapters system | `docs/product/semantic-operating-layer/subprojects/10-surface-adapters.md` |
| Thought capture PWA | `product/thought_capture_pwa/` |
| Motion grammar | `docs/workboards/sol-frontend-mobile-capture/MOTION.md` |
| Scroll framework | `docs/workboards/sol-frontend-mobile-capture/SCROLL.md` |
| Server chat corpus | `talha@192.168.0.102:/home/talha/apps/chat_converter/output` |
