# Product Idea Catalog: Personal Cognitive Exoskeleton

## Purpose and status

This document captures the product directions developed in the Personal Cognitive Exoskeleton discussion. It is a decision surface, not an implementation plan or a claim that every idea should be built.

The common thesis is:

> A person who repeatedly performs complex, individualized, context-dependent thinking can use a governed system to preserve their relevant knowledge, reasoning structure, history, values, methods, and active state; the system can then help them think, challenge them, simulate outcomes, create, or perform explicitly authorized bounded work.

The system is never asserted to reconstruct a human mind. It models selected, observable, revisable reasoning-relevant structure and must show its evidence, uncertainty, scope, and limits.

## How to use this catalog

For each direction, evaluate:

1. **Who has the pain intensely enough to adopt it?**
2. **What is the smallest valuable workflow?**
3. **Which shared exoskeleton capabilities are actually required?**
4. **What must remain under human approval?**
5. **What proof would distinguish real value from impressive imitation?**

No direction below authorizes implementation by itself. Select one initial wedge, state its success measure, and then create a focused task pack.

---

## A. Shared product foundation

These are not separate products. They are the common architecture from which the product directions below can be assembled.

### A1. Personal Reasoning System graph

The primary model is a bounded `PersonalReasoningSystem`, not a prompt persona and not a linear reasoning trace. It is one composite entity containing selected reasoning-relevant subsystems:

```text
beliefs and knowledge
goals and intentions
values and obligations
assumptions and world models
evidence standards
attention and salience
uncertainties and unresolved tensions
memories and historical experiences
reasoning strategies
decision criteria
optional affect/valence
capabilities and available actions
```

It has three graph layers:

| Layer | Function | Durability |
|---|---|---|
| Persistent system graph | Stable topology: selected beliefs, values, methods, relations, authority boundaries | Slowly changing |
| Historical event graph | Evidence, decisions, predictions, outcomes, corrections, transitions | Durable provenance |
| Active reasoning graph | Only task-relevant entities, history, constraints, alternatives, and current states | Ephemeral and bounded |

**Why it matters:** a new fact rarely determines a decision on its own. Its role depends on what it affects, through which mechanism, under which conditions, in relation to past experience, current goals, values, and uncertainty.

**Non-negotiable design rule:** never activate a user's entire graph for every task. Compile a bounded `ActiveReasoningView` under explicit scope, authority, privacy, and retrieval budgets.

### A2. Information-to-state cycle

New material is not appended blindly to a prompt. It should travel through this cycle:

```text
source capture and deterministic normalization
→ bounded evidence packet
→ intelligence proposes information role and affected entities
→ candidate influence relations and state updates
→ validation, provenance, branch/scope checks
→ compile active reasoning view
→ decision or creative episode
→ user response and outcome evidence
→ conservative learning
```

Possible information roles include evidence, contradiction, constraint, request, threat, opportunity, analogy, feedback, value signal, contextual change, and trusted/untrusted observation.

An influence record requires a source, target, mechanism, direction, conditions, delay, evidence, uncertainty, and a declaration of whether it is descriptive, predictive, or policy-authorized. Numeric weights are future infrastructure, not a premature requirement; many influences are conditional, qualitative, delayed, nonlinear, or disputed.

### A3. Intelligence versus deterministic control

| Intelligence proposes | Deterministic services own |
|---|---|
| Meaning, source interpretation, salience, candidate Shapes, affected entities, alternative readings, transformation possibilities | Source preservation, normalization, evidence boundaries, schemas, authority, state-transition validation, versioning, branch isolation, receipts, rollback, budgets, privacy, and promotion |

This boundary is essential. The system must not make deterministic tools pretend to interpret a person's thought, but it also must not allow an unbounded model call to silently rewrite personal state.

### A4. Fidelity and alterity

Two faculties must remain distinct:

- **Fidelity:** apply the user's approved methods, values, standards, preferences, and patterns when relevant.
- **Alterity:** introduce credible disagreement, counterexamples, unfamiliar methods, AntiMatches, and alternate perspectives.

Without fidelity, the system is generic. Without alterity, it becomes an echo chamber that freezes a user's habits and identity.

### A5. Delegation ladder

The user selects authority per task, not once globally:

```text
Mirror → Scaffold → Simulate → Recommend → Execute
```

- **Mirror:** reflect the active reasoning field and likely considerations.
- **Scaffold:** guide the user through a selected process.
- **Simulate:** explore consequences or alternative branches.
- **Recommend:** produce a bounded recommendation with evidence and uncertainty.
- **Execute:** perform a reversible, explicitly authorized action through a scoped tool.

The default is mirror/scaffold. Execution requires capability, permission, costs, review rules, and an audit trail.

---

## B. Product directions

### B1. Personal Cognitive Exoskeleton — umbrella product

**Product promise:** help a user sustain and improve complex thought over time, rather than repeatedly restarting from a blank context window.

**Core user experience:** a user brings a decision, project, problem, or creation. The system retrieves the relevant active graph, shows what it believes matters, traces how new information changes the field, helps generate or evaluate options, and records the user’s correction.

**Best early users:** people with high complexity, recurrence, individuality, cost of lost context, and willingness to correct the model—founders, researchers, independent experts, strategists, serious creators, designers, and educators.

**Primary value:** continuity of reasoning, not just continuity of chat. It can preserve why prior decisions were made, which tensions are unresolved, how a user's standards apply, and why a recommendation changed.

**Proof of value:** on unfamiliar complex tasks, users judge the system's reasoning artifact as useful, editable, evidence-grounded, and recognizably compatible with their approved practices.

**Main risk:** overclaiming cognitive replication. The product must continually disclose that it is a model of observable practices and task-specific context, not the user.

### B2. Thought Mirror and Reasoning Workbench

**Product promise:** make a user's current thought visible and manipulable before trying to automate it.

**Workflow:**

```text
user supplies a problem or material
→ system maps claims, entities, tensions, constraints, uncertainty, and alternatives
→ user corrects the map
→ system proposes next reasoning moves or opposing views
→ user develops a decision/insight with preserved provenance
```

**Modes:** mirror, scaffold, challenge, alternative, and simulation. No external action is necessary.

**Why it is a strong first wedge:** it produces useful value before durable inference, persona publication, or delegated tools are reliable. It also creates the correction data needed to build a trustworthy Personal Reasoning System graph.

**Target users:** founders handling ambiguous trade-offs; researchers comparing theories; analysts building a model; writers developing a project; anyone working across long-running, interdependent questions.

**Dependencies:** bounded active view, source/evidence capture, graph explanation, user corrections, and branch-safe history. It does not require an autonomous agent.

**Main risk:** becoming a visually elaborate note-taking or mind-mapping product without demonstrably better reasoning. The system must surface causal relevance, alternative views, and meaningful state changes.

### B3. Configurable Persona / Productized Expert

**Product promise:** allow a person to publish or deploy a governed representation of selected ways they reason and work.

**Important distinction:** this is not “a chatbot that sounds like me” and must not claim to literally be the person. It is a versioned delegation artifact:

> “This agent operates from a configuration approved by this person, within a declared scope and authority boundary.”

**Persona package:**

```text
PersonaCore
  approved reasoning patterns, values, methods, boundaries
PersonaState
  temporary task state, working memory, active commitments
PersonaViews
  role- and context-scoped projections
Knowledge permissions
Tool capabilities and action authority
Evaluation suite, provenance, version, ownership, and licensing
```

**Potential users:** consultants, advisers, coaches, educators, public intellectuals, specialist operators, founders, and creators who want to expose a bounded part of their expertise without giving away unrestricted access to themselves.

**Value:** converts informal, difficult-to-scale judgment into an inspectable, limited service; supports training, intake, analysis, customer interaction, or pre-work.

**Dependencies:** PersonaCore/State/View contracts, tool permissions, versioning, user approvals, learning governance, and persona-specific evaluation.

**Main risks:** impersonation, false authority, stale guidance, silently inferred “values,” and scope creep. Start with reasoning/advice only; grant execution one explicit capability at a time.

### B4. Bounded Delegated Cognition

**Product promise:** take repeatable cognitive work off a user's hands while preserving their standards, context, and review authority.

**Examples of work that can be delegated earlier:**

- organize a research field;
- compare options against declared criteria;
- prepare a decision memo;
- identify assumptions, contradictions, and missing information;
- reconstruct a project’s decision history;
- turn a complex field into an agenda or next-step plan;
- prepare drafts for user review.

**What stays human by default:** identity-defining choices, values, moral accountability, irreversible decisions, high-stakes professional judgment, and decisions where the user has not declared authority.

**Product mechanism:** a `DecisionEpisode` retrieves the active graph, proposes state changes and options, evaluates them against declared criteria, produces an explanation, and waits for the user where required.

**Proof of value:** the user can audit why an output occurred and finds that it reduces cognitive load without obscuring important uncertainty or making decisions feel alien.

**Main risk:** a superficial automation layer claiming personalized reasoning because it uses a few preferences. Require evidence, tests, and clear refusal/hold behavior before execution.

### B5. Research Intelligence and Structural Retrieval

**Product promise:** help a user discover material relevant not only by topic but by structure, relationship, mechanism, tension, role organization, and transformation.

**Why it matters:** many high-value insights arise when a person recognizes that two different domains instantiate a similar Shape. A researcher, strategist, or creator may want “systems where scarce interpretive knowledge creates authority” rather than “documents about navigation.”

**Workflow:**

```text
research question or active problem
→ retrieve source evidence and candidate Shapes
→ intelligence proposes structural comparisons
→ anti-matches and mechanism differences are surfaced
→ user chooses whether a transfer hypothesis is useful
```

**Role of the knowledge ocean:** it is the evidence substrate, not the exoskeleton itself. The ocean preserves sources, chunks, embeddings, metadata, candidate Shapes, and links. The exoskeleton selects and interprets bounded material in light of one user's current reasoning state.

**Dependencies:** the Shape Population workflow, canonical Shape/Pattern contracts, retrieval quality, AntiMatches, provenance, and source-bound evidence packets.

**Main risk:** falsely treating semantic or embedding similarity as structural equivalence. Candidate retrieval must be followed by explicit structural, dynamic, causal, perspectival, and valence validation.

### B6. Creative Exoskeleton

**Product promise:** preserve and extend a creator's evolving creative field—taste, themes, canon, motifs, constraints, unfinished tensions, methods, and judgments—rather than only generating content in a familiar style.

**Target users:** writers, filmmakers, game designers, architects, visual artists, musicians, fashion designers, and other creators whose work is complex, individual, iterative, and dependent on continuity.

**Creative system graph can include:**

- projects, worlds, characters, artifacts, themes, and motifs;
- aesthetic values and constraints;
- reference networks and sources of inspiration;
- creator judgments, accepted/rejected directions, and revision history;
- character, world, and narrative states;
- unresolved creative tensions and possible transformations.

**Modes:**

- continuity: recover the active creative field;
- reflection: make tensions and motifs visible;
- simulation: show the consequences of a new idea;
- generation: propose candidates under selected constraints;
- critique: test coherence with the creator's own declared standards;
- divergence: deliberately escape the creator's established patterns;
- delegation: perform repetitive supporting work while preserving creative authority.

**Key principle:** the goal is not to reduce creativity to rules. It is to preserve enough structured context that a creator can make richer, more continuous, and more deliberate choices.

**Main risk:** overformalization can eliminate ambiguity, serendipity, embodied intuition, and productive misreading. The system must preserve Holds, unresolved contradictions, free experimentation, and “break my own pattern” modes.

### B7. Narrative and Storytelling Engine

**Product promise:** make narrative development causal, coherent, and personally configured by modeling a story as a changing system rather than a sequence of disconnected text generations.

**Narrative system:**

```text
characters + qualities + relationships + beliefs + goals
+ world rules + institutions + constraints
+ thematic and aesthetic Shapes
+ current tensions + causal history + possible transformations
= StoryShape
```

**Scene model:**

```text
incoming StoryShape
→ pressure/event
→ character decisions under beliefs, values, and affordances
→ consequences
→ outgoing StoryShape
```

**Capabilities:** maintain canon; track character knowledge separately from world truth; model dramatic irony; identify repeated motifs and payoffs; generate scenes from incoming/outgoing state requirements; explore branches; test whether a change breaks a world rule or character arc.

**Relation to World Studio:** World Studio is the current world/canon/scene surface. The narrative engine extends it by modeling transformations across scenes, arcs, themes, and causal consequences. It should be a Narrative Profile/application composed with World Studio, not a second fiction store.

**Main risk:** coherent simulation can still be dramatically weak. Narrative evaluation must cover tension, transformation, theme, POV, pacing, and creator intent, not only continuity.

### B8. Creative Transduction: research → abstraction → transformed world

**Product promise:** help a creator research the real world, notice what is creatively valuable, preserve selected underlying structures, and re-instantiate them as original world-native material.

This is a distinct pipeline inside the Creative Exoskeleton:

```text
research orientation
→ source discovery
→ attention and attraction
→ interpretation
→ source Shape extraction
→ abstraction contract
→ transformation
→ world-bound re-instantiation
→ narrative/artistic integration
→ evaluation and revision
```

**Research orientation:** the system learns observable preferences about source types, domains, credibility standards, interest triggers, research pathways, and stopping rules. It must not assert that it knows unconscious inspiration.

**Inspiration appraisal:** an `InspirationCandidate` records why an item mattered: selected qualities, relations, tensions, possible creative function, alternatives, evidence, uncertainty, and creator feedback.

**Abstraction contract:** the creator explicitly chooses what should survive transfer and what must be discarded.

```yaml
preserve: [selected roles, relations, tensions, mechanisms]
discard: [names, identifiers, direct particulars]
transformable: [domain, scale, mechanism, medium, temporality, valence, perspective]
```

**Transformation operators:** domain substitution, role remapping, causal inversion, scale shift, temporal compression, perspective rotation, valence shift, composition, mechanism preservation, and mechanism replacement.

**World-bound re-instantiation:** new details must follow from fictional physics, geography, institutions, material culture, language, character history, motifs, and conflicts. It cannot be a superficial rename-and-reskin operation.

**Example:** a creator may abstract from real-world non-instrument navigation the pattern “distributed environmental signals + embodied specialist knowledge + political authority + environmental disruption,” then instantiate it as listeners who read pressure memories in a living bridge. The concrete culture, mechanism, institutions, and consequences become native to the fictional world.

**Main risks:** mistaking one interpretation for a source's singular essence; cultural extraction; copyright/derivative reproduction; systematizing the creator into predictable formula; and treating provenance as permission. Every result needs source provenance, selected invariants, transformation history, world-fit review, and creator authority.

### B9. Reasoning Development Companion

**Product promise:** help a user consciously develop their reasoning repertoire instead of merely automating their existing habits.

**Why it differs from the expert persona:** people without mature or stable methods should not have their early habits canonized as an identity. The product can use the same graph but select alterity and reflection as the default.

**Possible functions:** reveal recurring moves, compare alternative methods, identify blind spots, rehearse an unfamiliar thinking mode, preserve lessons from outcomes, and help a user establish deliberate decision criteria.

**Target users:** students, early-career professionals, people changing domains, creators developing a craft, and experienced users who explicitly want to change a habit rather than reinforce it.

**Main risk:** the system can become prescriptive or therapeutic without warrant. It must frame suggestions as optional cognitive strategies, not judgments about intelligence, personality, health, or identity.

### B10. Team or institutional reasoning continuity — later extension

**Product promise:** preserve a team's decision logic, constraints, institutional memory, and reasoning patterns across turnover and long projects.

**Potential value:** a team can inspect why a decision was made, which assumptions are now stale, what evidence changed, and where perspectives differ. A founder or expert persona can be one scoped perspective inside the team graph, not an unquestionable authority.

**Why it is later:** collective reasoning introduces access control, governance, conflicting values, political dynamics, and provenance disputes. It should not be inferred from an individual-first architecture without new governance work.

---

## C. Product relationships

```text
Personal Cognitive Exoskeleton
├── Thought Mirror / Reasoning Workbench
├── Configurable Persona / Productized Expert
├── Bounded Delegated Cognition
├── Research Intelligence and Structural Retrieval
├── Creative Exoskeleton
│   ├── Narrative and Storytelling Engine
│   └── Creative Transduction Profile
├── Reasoning Development Companion
└── Later: Team/Institutional Continuity
```

The top-level exoskeleton is an architecture and product thesis. The items beneath it are potential products, modes, or vertical applications. Do not try to launch all of them together.

---

## D. Existing system support and missing work

### Already represented by the Unified Framework or adjacent system

- kernel identity, provenance, scope, state, occurrence, relation, claim, perspective, branch, and types;
- Shapes, composite Shapes, quality/sub-entity modeling, role/influence, Pattern and AntiMatch direction;
- Agent concepts: observations, Percepts, BeliefState, values, goals, decision criteria, policy, capabilities, affordances, actions;
- Conversation concepts: ReasoningStep, ReasoningMove, ReasoningTrace, ReasoningSignature, ContextState, ActiveFieldState, TransformationOperator, learning events;
- cybernetic concepts: state variables, signals, feedback, constraints, delay, regulation;
- Personal Interface calibration and World Studio canon/scene workflows;
- knowledge-ocean, evidence, critique, governance, and OpenClaw direction.

### Missing connective tissue

- `PersonalReasoningSystemCore`, subsystem, state, history, active-view, and decision-episode contracts;
- information-role classification and evidence-bound influence/update proposals;
- bounded active-graph compiler and history relevance logic;
- causal explanation contract for “why did this recommendation change?”;
- PersonaCore/PersonaState/PersonaView packaging, versioning, licensing, and authority;
- individual fidelity/alterity evaluation;
- Creative Transduction contracts, source-to-pattern fixtures, and derivative-risk gates;
- reliable retrieval over canonical Shapes and Patterns;
- long-term evaluation, correction, rollback, and privacy controls;
- user experience that makes the graph helpful rather than overwhelming.

---

## E. Product-selection decisions

These are unresolved. Choose them explicitly before a build program is approved.

| Decision | Options | Consequence |
|---|---|---|
| First product wedge | Thought mirror; expert persona; creative exoskeleton; narrative engine; research intelligence | Determines initial user, fixture corpus, UX, and evaluation |
| Primary user | Founder/expert; researcher; creator; learner | Determines data sources, permissions, and success criteria |
| Initial authority | Mirror/scaffold; simulation; recommendation; bounded execution | Determines safety and required governance |
| Primary value | Continuity; decision quality; leverage; creative originality; monetizable expertise | Determines whether the graph is perceived as useful |
| First data source | Conversations; documents; decisions; creative artifacts; research corpus | Determines what can be inferred and how quickly calibration begins |
| Learning model | Explicit configuration only; proposed patterns with approval; conservative feedback learning | Determines trust, setup friction, and adaptation speed |
| Graph visibility | Mostly hidden with explanations; explicit editable canvas; hybrid | Determines UX complexity and user agency |
| Persona publication | Private only; shareable within team; public productized expert | Determines identity, licensing, and abuse safeguards |

### Recommended sequencing, not a commitment

The lowest-risk path is:

```text
Thought Mirror
→ limited active reasoning graph
→ user-corrected patterns and state transitions
→ simulation/recommendation
→ one bounded delegation capability
→ optional shareable expert persona
```

For the creative vertical:

```text
Creative continuity and canon view
→ research and inspiration capture
→ Creative Transduction fixtures
→ narrative-state and scene transformation
→ controlled generation and critique
```

---

## F. Hard non-goals and evaluation requirements

### Non-goals

- “digital clone” claims;
- hidden-cognition or subconscious inference;
- personality diagnosis or eligibility classification;
- silent durable learning from one conversation;
- generated output treated as user belief;
- whole-life history activation by default;
- automatic structural equivalence based on embeddings;
- autonomous high-stakes decision-making;
- reskinning source material while obscuring provenance.

### Required evidence before stronger claims

1. **Fidelity:** does the system use approved methods where relevant, not merely copy tone?
2. **Alterity:** does it surface credible counterviews and avoid self-confirmation?
3. **Causal provenance:** can it explain each material state change and recommendation influence?
4. **Boundedness:** does it avoid irrelevant history and unapproved data access?
5. **Correction:** do user rejections/corrections persist with context without overgeneralizing?
6. **Outcome:** does it improve a measurable user workflow versus ordinary chat, notes, or retrieval?
7. **Safety:** can state changes be scoped, versioned, rolled back, audited, and withheld when uncertain?
8. **Creative integrity:** does transformed work preserve selected structure while becoming world-native and avoiding prohibited derivative reproduction?

## Immediate next decision

Before implementation, choose one first product wedge and one test user archetype. The workspace tasks intentionally begin with shared contracts, creative transduction, and evaluation so that a selected wedge is built on reusable foundations rather than a disposable prompt workflow.
