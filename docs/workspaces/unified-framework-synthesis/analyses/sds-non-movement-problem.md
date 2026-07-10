# SDS Non-Movement Problem

**Date:** 2026-07-10  
**Framework:** System-Dynamic Signature (SDS)  
**Status:** Deep analysis — unique SDS contribution not covered by MTSF or ThoughtShape alone

See also: [fresh-comparison-jul-10.md](./fresh-comparison-jul-10.md), [sources/sds-v1.0-report.md](../sources/sds-v1.0-report.md)

---

## Core principle

> What is blocked, absent, or prevented is as important as what moves.

SDS treats **non-movement** as first-class: constraints, absences, bottlenecks, and prevented transitions are not gaps in the model — they are structural facts that explain why systems fail or stall.

---

## Why this matters for unified synthesis

| Framework | How it handles absence/blockage |
|-----------|------------------------------|
| **MTSF** | Contradiction may remain; silence is valid — but absence is not a dedicated primitive |
| **ThoughtShape** | Tension, Hold — phenomenological pressure without causal machinery |
| **SDS** | **Constraint, bottleneck, anti-match, missing information** as typed graph nodes |

SDS fills the **causal absence** layer: not just "something feels blocked" (ThoughtShape) or "contradiction persists" (MTSF), but **which edge is inhibited, which loop cannot close, which transfer fails**.

---

## SDS primitives for non-movement

| Primitive | Role |
|-----------|------|
| **Constraint** | Hard limit on state transition |
| **Bottleneck** | Rate-limiting node in flow |
| **Missing information** | Extraction flags incomplete evidence |
| **Anti-match** | Explicit rejection of false analogy (blocked transfer) |
| **Inhibits edge** | Causal relation type for dampening/blocking |
| **depends_on** | Unmet dependency prevents movement |
| **Low confidence** | Scored absence of evidence coverage |

---

## Example — brand recognition without meaning

Input: *"People recognize the logo but don't understand the brand."*

**Movement reading:** awareness campaigns → logo recall ↑ → meaning unchanged → trust gap widens (feedback loop).

**Non-movement reading:**

- **Blocked transition:** recognition → comprehension (constraint: no semantic bridge)
- **Absent signal:** meaning channel under-specified
- **Anti-match:** "maze" archetype rejected — implies hidden correct path; here there may be no path yet
- **Intervention:** clarify lead signal **before** amplifying distribution (unblock prerequisite)

---

## Product implications

1. **Thought Trace** — capture when user hits a reasoning block (move type: `stall`, `cannot-bridge`)
2. **Inner Space Curator** — "release" may mean removing a blockage pattern, not just pruning content
3. **Community pipeline** — cluster users who share **failure-mode topology**, not just success patterns
4. **SDS overlay** — attach to MTSF shapes on demand when intervention or analogy transfer is needed

---

## Stack position

Non-movement belongs in the **SDS overlay layer**, not the MTSF store or ThoughtShape grammar:

```text
ThoughtShape  →  names the tension (familiarity vs comprehension)
MTSF          →  persists the shape + evidence
SDS overlay   →  models blocked loops, anti-matches, intervention paths
```
