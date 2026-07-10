# Reasoning-Step Capture (Thought Trace)

**Date:** Jul 2026 design thread  
**Surface:** Thought Trace — forensic replay instrument

---

## Problem

Users lose thoughts when:

- forced to label too early
- structure only appears at session close
- asked for whole ontology at once
- momentum breaks

---

## Solution

**Atomic unit:** `ReasoningStep` (not session, not formation)

```text
Drop → Hold → Trace → Mirror → Prompt → Repeat
```

| Field | Purpose |
|-------|---------|
| raw_text | Exactly what user said |
| hold_state | pre-clear / partial / crystallizing / settled |
| reasoning_move | ground, triangulate, bridge, formalize, invert… |
| prompted_by | link to prior step(s) |
| move_type | extends, revises, contrasts, grounds, bridges |
| provenance | user / inferred / confirmed |

---

## Reasoning-tuned prompting

Bot asks the **next natural move** in user's arc:

| Pattern | Ask | Don't ask |
|---------|-----|-----------|
| Grounding | "What concrete instance?" | "What's the framework?" |
| Triangulating | "More like A or B?" | "Define terms" |
| Formalizing | "What's the shape?" | "How does it feel?" |

Pilot 003 signature: `ground → triangulate → concretion → abstraction → bridge → formalize → inversion → canon`

---

## Repo gap

- `session append` exists (T0 safe)
- Structure only at close
- Need per-drop step graph + checkpoint materialization

---

## Relation to frameworks

| Layer | Role |
|-------|------|
| ThoughtShape Hold | Semantic of hold state |
| MTSF T0 events | Persistence |
| Pilot 003 | Reasoning move vocabulary |
| Personal Interface | Extend calibration to reasoning moves |
