# Personal Cognitive Exoskeleton Lens

## Purpose

The Personal Cognitive Exoskeleton is a general architecture for people who repeatedly perform complex, context-dependent, individualized thinking. It is designed to increase continuity, capacity, reflection, and bounded delegation without reducing a person to a prompt, a static trait list, or an alleged replica of their mind.

Its target is not any one profession. Its value is highest where complexity, recurrence, individuality, loss of context, and capacity to correct the system are all high.

```text
Value ≈ complexity × recurrence × individuality × cost of lost context × feedback capacity
```

Strong early users include founders, independent experts, researchers, strategists, serious creators, designers, writers, architects, engineers, and educators. Mature-expertise amplification and cognitive-development support must remain separate modes: the first preserves approved practices; the second introduces alternatives and helps a user develop them.

## Ontological position

The Unified Framework is the representation and composition language for the exoskeleton. It is not asserted to be a literal or universal cognitive theory.

The system models observable, revisable reasoning practices:

- `SourceFragment`, `Evidence`, and `Provenance` preserve what was actually supplied.
- `Claim`, `BeliefState`, `Perspective`, `State`, and `ModelBranch` distinguish world, belief, uncertainty, and alternative interpretation.
- `Referent`, qualities, relations, roles, `ShapeCore`, `ShapeView`, and `CompositeShape` model organized configurations.
- `ReasoningStep`, `ReasoningMove`, `ReasoningTrace`, and `ReasoningSignature` model observed reasoning episodes and recurring patterns.
- `Goal`, `Value`, `DecisionCriterion`, `Capability`, and `Policy` model situated agency.
- Cybernetics models feedback, regulation, delay, constraint, and changing influence.

The framework can already represent the required components. The missing work is a governed Personal Reasoning System Profile and runtime that assemble them into one bounded, dynamic reasoning graph.

## Core object: PersonalReasoningSystem

A `PersonalReasoningSystem` is one bounded composite entity. It is not the person. It is a governed model of selected, externally observable reasoning-relevant structure.

```text
PersonalReasoningSystem
├── Knowledge and beliefs
├── Goals and intentions
├── Values and obligations
├── Assumptions and world models
├── Evidence standards
├── Attention and salience
├── Uncertainties and unresolved tensions
├── Memories and historical experiences
├── Reasoning strategies
├── Decision criteria
├── Optional affect/valence state
└── Capabilities and available actions
```

Each part is an entity or quality with its own state, role, relations, provenance, and possible sub-Shapes. The system has several coupled dimensional Shapes: epistemic, motivational, value, historical, attentional, relational, decision-policy, and current-problem Shapes.

## Three graph layers

### 1. Persistent system graph

The relatively stable topology: beliefs, values, goals, methods, recurring patterns, decision criteria, relationships, access boundaries, and declared update policies. This is the stable basis of a `ReasoningSystemCore`.

### 2. Historical event graph

Evidence arrivals, decisions, predictions, outcomes, corrections, accepted and rejected interpretations, and state transitions. History is path-dependent evidence, not an undifferentiated memory dump. It may affect a current view only through explicit relevance and influence relations.

### 3. Active reasoning graph

An ephemeral, bounded task view containing only the entities, current states, history, evidence, constraints, alternatives, and patterns relevant to the present episode. This avoids activating an entire user model, lowers cost, protects privacy, and prevents unrelated history from contaminating a decision.

## Information, state, and decision

Incoming content is normalized deterministically, then interpreted as a candidate `InformationEvent` and `PerceptCandidate`. The system does not merely append it to a context window.

```text
incoming source
→ normalized source and evidence boundaries
→ candidate information role and affected entities
→ bounded influence proposals
→ candidate state transition(s)
→ active reasoning graph
→ decision or creative episode
→ result, user correction, and learning evidence
```

Information roles include evidence, contradiction, constraint, request, threat, opportunity, analogy, feedback, value signal, contextual change, and observation from a trusted or untrusted source.

An influence relation must declare source, target, mechanism, direction, conditions, delay, evidence, uncertainty, and whether the effect is descriptive, predictive, or policy-authorized. Numeric weights are optional infrastructure, not a prerequisite: many relationships are qualitative, conditional, delayed, nonlinear, or contested.

The runtime never recomputes the whole graph. It retrieves and compiles an `ActiveReasoningView` under an explicit scope and budget. Intelligence proposes meaning and possible impacts. Deterministic services validate references, preserve prior state, enforce authority, record state transitions, support branches and rollback, and issue provenance receipts.

## Decision and creative episodes

A `DecisionEpisode` compiles the active graph into options, implications, uncertainties, conflicts, and recommended next moves. Its explanation must identify which information, state changes, history, values, and constraints materially influenced the result.

A `CreativeEpisode` applies the same architecture to creation. It must not make creative decisions on behalf of the creator by default. Its primary functions are continuity, reflection, simulation, controlled generation, critique, divergence, and bounded supporting delegation.

## Creative Transduction Profile

Creative work frequently moves from real-world research to transformed fictional or artistic material. This is not topic copying. It is a controlled movement from an interpreted source configuration to a world-bound re-instantiation.

```text
research orientation
→ source discovery
→ attention and attraction
→ interpretation
→ source Shape extraction
→ abstraction contract
→ transformation
→ world-bound re-instantiation
→ narrative integration
→ evaluation and revision
```

### Research orientation

The profile can model observable research practice: source types, domains, search strategies, credibility standards, interest triggers, stopping rules, and how a creator moves through adjacent material. It must not claim access to unconscious inspiration.

### Inspiration appraisal

An `InspirationCandidate` records why a source became creatively salient: selected qualities, relationships, tensions, possible functions, evidence, alternatives, uncertainty, and creator feedback.

### Source Shape and abstraction contract

The system creates one or more candidate ShapeViews of a researched phenomenon. A creator selects what to preserve, discard, or make transformable. The resulting `Pattern` captures chosen invariants, not an objectively singular essence of the source.

```yaml
abstraction_contract:
  preserve: [selected relations, tensions, roles, dynamics]
  discard: [names, identifiers, direct particulars]
  transformable: [mechanism, scale, medium, temporality, valence, perspective]
  source_provenance: [...]
```

### Transformation and re-instantiation

Useful operators include domain substitution, role remapping, causal inversion, scale shift, temporal compression, perspective rotation, valence shift, composition, mechanism preservation, and mechanism replacement.

Re-instantiation then grounds the transformed Pattern in established world canon: physics, geography, institutions, material culture, language, character history, motifs, technology, and existing conflicts. It must derive new details from world constraints, not simply reskin the source.

### Evaluation

Evaluate the result independently for source provenance, selected-invariant preservation, sufficient transformation, world coherence, narrative function, creator taste, novelty, sensitivity, and risk of prohibited derivative reproduction. The creator may deliberately preserve ambiguity or mutate a pattern beyond recognition.

## Fidelity and alterity

The exoskeleton needs two distinct faculties:

- **Fidelity:** applies the user's approved methods, standards, values, and patterns when they are relevant.
- **Alterity:** offers credible external perspectives, counterpatterns, anti-matches, and challenge so the system does not become a self-confirming echo chamber.

The user chooses the operative mode for each task: mirror, scaffold, simulate, challenge, alternative, or bounded delegation.

## Hard boundaries

1. Do not infer hidden cognition, personality, diagnosis, or identity from conversation traces.
2. Do not silently transform a candidate pattern into a durable personal rule.
3. Do not let generated text count as user belief or self-confirming learning evidence.
4. Do not collapse shared reality, user belief, fictional canon, and simulation branches.
5. Do not activate unrelated personal history without a declared relevance path and user-appropriate scope.
6. Do not allow a reasoning graph to conceal unsupported causal claims behind plausible language.
7. Do not treat source abstraction as a license for plagiarism, cultural extraction, or derivative reproduction.
8. Do not grant action authority beyond explicit, reversible, task-scoped permissions.

## Initial work program

1. Lock Personal Reasoning System Profile contracts: core, subsystem, state, information event, influence, update proposal, active view, decision episode, outcome, and learning evidence.
2. Lock Creative Transduction Profile contracts and a small, evidence-backed fixture corpus.
3. Build a non-autonomous thought-mirror prototype that records candidate state transitions and user corrections.
4. Establish fidelity, alterity, causal-provenance, privacy, and non-dependence evaluation gates before delegated actions.

## Success criterion

On an unfamiliar complex task, the system should produce a reasoning artifact a user finds useful, accurate, editable, and recognizably compatible with their approved practices—while clearly showing uncertainty, evidence, state changes, and relevant alternatives.
