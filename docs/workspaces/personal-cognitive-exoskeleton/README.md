# Personal Cognitive Exoskeleton

This workspace is the dedicated lens for a governed system that helps a user sustain, inspect, develop, and—only where explicitly authorized—delegate parts of their complex individualized reasoning.

The central object is a `PersonalReasoningSystem`: a bounded composite entity whose beliefs, values, goals, memories, methods, constraints, and active tensions form a changing reasoning graph. It is not a claim to reconstruct a human mind.

## Core architecture

```text
Persistent system graph
  beliefs, values, goals, methods, memories, relationships
        +
Historical event graph
  evidence, decisions, outcomes, corrections, transformations
        +
Active reasoning view
  bounded task-relevant entities, states, history, and alternatives
        ↓
Decision episode or creative episode
        ↓
Inspectable result, user correction, and conservative learning
```

## First principles

- Model observable reasoning practices, never hidden cognition or personality.
- Keep `PersonaCore`/system topology, current state, history, and task view distinct.
- Treat incoming information as an event whose effects are proposed by intelligence and recorded through governed state transitions.
- Use bounded active graphs, never an always-active total model of a person.
- Preserve provenance, uncertainty, counterexamples, rejected interpretations, and branch boundaries.
- Fidelity to a user is only one faculty. The system must also supply alterity: credible alternatives, counterpatterns, and challenge.
- Intelligence interprets and proposes; deterministic services preserve sources, validate contracts, apply approved transitions, enforce policy, and produce receipts.
- A system may support a user's thinking without assuming responsibility for their values, irreversible choices, or identity.

## Primary applications

1. Thought mirror and reasoning workbench for complex personal or professional decisions.
2. Bounded productized expert persona, with versioned authority and permissions.
3. Creative exoskeleton, including research-to-inspiration-to-world-transduction.

## Read first

1. [Product idea catalog](derived/PRODUCT_IDEA_CATALOG.md) — all discussed product directions, shared capabilities, risks, and open decisions
2. [Lens source](sources/PERSONAL_COGNITIVE_EXOSKELETON_LENS.md) — canonical reasoning-system and creative-transduction model
3. [Unified Framework source](../unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)
4. [Ten-out-of-ten gap program](../unified-framework-synthesis/derived/TEN_OUT_OF_TEN_GAP_PROGRAM.md)
5. [Workspace protocol](../WORKSPACE-AGENT-PROTOCOL.md)
6. [Sync contract](derived/sync-contract.md)

## Agent boot

```bash
source ~/.config/inner-space-workspace.env 2>/dev/null || true
python3 tools/workspace_coordination.py context \
  --workspace-id personal-cognitive-exoskeleton \
  --agent-id <agent> --surface <surface> --session-id <session>
python3 tools/workspace_projection_sync.py check \
  --workspace-id personal-cognitive-exoskeleton
```

The live API is the authority for coordination state. Git stores semantic artifacts and synchronized projections.
