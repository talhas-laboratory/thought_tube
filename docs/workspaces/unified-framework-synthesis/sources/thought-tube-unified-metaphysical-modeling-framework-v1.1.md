# Thought Tube Unified Metaphysical Modeling Framework

## Final Normative Specification

**Version:** 1.1  
**Status:** Canonical foundation  
**Date:** July 2026  
**Purpose:** A single, branch-aware, provenance-preserving foundation for modeling arbitrary objects, meanings, systems, transformations, agents, conversations, personal formations, and executable scenarios in a traversable metaphysical space.

---

## Abstract

This paper defines one unified modeling framework for representing almost any sufficiently expressible object, process, system, mental model, imagined world, institution, relationship, experience, or transformation as a traversable metaphysical space.

The framework does not claim to reproduce reality exhaustively or to settle metaphysics. It defines a disciplined software language for constructing explicit, revisable models of what may exist, what is claimed, how something appears from a perspective, and how selected parts of a model may be compiled into executable dynamics. Its central architectural correction is that unity applies to **identity, source continuity, and provenance**, not to a single imposed truth. The system therefore consists of one shared record universe and many explicit model branches, perspectives, modal scopes, and executable interpretations.

The framework is built around twelve formal kernel concepts: `SourceFragment`, `Referent`, `Scope`, `State`, `Occurrence`, `RelationInstance`, `Claim`, `Perspective`, `Evidence`, `Provenance`, `ModelBranch`, and `TypeDefinition`. Richer concepts—including Shape, CompositeShape, ValenceField, TransformationProcess, Agent, BeliefState, Pattern, and SimulationRun—are derived composites or optional profiles built from that kernel. This prevents the ontology from becoming a flat list of equally foundational concepts.

A Shape is defined as a bounded projection over selected records under an explicit scope and abstraction contract. A Shape may be inspected through different perspectives, dimensions, scales, and affective fields without confusing those views with the represented structure itself. A system can contain several coupled dimensional Shapes, forming a CompositeShape or “shape of shapes.” Similar structures may recur across scale and domain, but matching is treated as candidate retrieval followed by explicit structural, dynamic, mechanistic, perspectival, and valence validation—not as automatic proof of equivalence.

Transformation is first-class. Agents inhabit the modeled world through bounded observation, belief, affordance, policy, and action interfaces. Simulation is never inferred directly from descriptive language. It requires an explicit compilation boundary and a typed intermediate representation containing variables, state spaces, mechanisms, rules, timing, uncertainty, and assumptions. Valence may remain descriptive, comparative, or structural; it becomes causally operational only through explicit appraisal and valence-effect rules.

The result is one coherent framework that can preserve ambiguity, contradiction, perspective, scale, meaning, dynamics, and provenance while remaining implementable through a deliberately small kernel, governed profiles, bounded graph projections, formal branch semantics, and earned execution. The framework is organized into three strict architectural layers: a universal metaphysical kernel, reusable normative profiles, and application projections. Conversation, personal formation, worldbuilding, curation, community reasoning, and simulation are therefore built from one foundation without being mistaken for universal primitives or relegated to informal product conventions.

---

## Contents

1. [Normative status](#0-normative-status-and-supersession)
2. [Purpose and commitments](#part-i--purpose-limits-and-core-commitments)
3. [Formal core](#part-ii--formal-core)
4. [Semantic structure and Shape](#part-iii--semantic-structure-and-shape)
5. [Transformation](#part-iv--transformation)
6. [Agents and situated grounding](#part-v--agents-and-situated-grounding)
7. [Conversation and personal formation](#part-v-a--conversation-and-personal-formation)
8. [Description-to-execution compilation](#part-vi--from-description-to-execution)
9. [Traversal, lifecycle, and trust](#part-vii--traversal-lifecycle-and-trust)
10. [Software architecture](#part-viii--software-architecture)
11. [Evaluation and safety](#part-ix--evaluation-and-safety)
12. [Implementation strategy](#part-x--implementation-strategy)
13. [Worked examples](#part-xi--worked-end-to-end-example)
14. [Research boundaries and final synthesis](#part-xii--research-boundaries)
15. [Appendices](#appendix-a--compact-canonical-vocabulary)

---

# 0. Normative Status and Supersession

## 0.1 Purpose of this paper

This specification consolidates and corrects the preceding framework papers. Earlier papers supplied the necessary conceptual material: multidimensional meaning, shapes, relations, dynamics, valence, transformation, agent grounding, provenance, and simulation. They also retained unnecessary architectural separations and left several core semantics underspecified.

This paper is the normative foundation. Where prior documents differ from it in naming, architecture, primitive status, branch semantics, Shape identity, valence execution, compilation, or implementation order, this paper takes precedence. Historical frameworks remain important as provenance and migration sources, but they are no longer runtime layers that an application must coordinate.

## 0.2 One framework

The system exposes one conceptual framework, one shared record universe, one identity scheme, one provenance graph, and one family of explicit lifecycle rules.

It does **not** expose several historical frameworks that must be selected, stacked, or coordinated by the user. Historical names may remain in migration documentation only.

The architecture has three strict layers:

```text
Universal metaphysical kernel
+ governed normative profiles
+ bounded branches and views
+ application projections
= one extensible metaphysical modeling system
```

- The **kernel** defines identity, representation, epistemics, provenance, branching, scope, and vocabulary.
- A **profile** defines a reusable modeling capability by composing kernel records under additional invariants.
- An **application projection** selects profiles and presents task-specific behavior without redefining kernel truth or identity.

The canonical process is:

```text
capture source material
→ preserve ambiguity
→ establish referents and scope
→ state conditions and claims
→ connect relations and occurrences
→ derive bounded shapes
→ model transformations and agents
→ compile only sufficiently specified dynamics
→ run scenarios
→ evaluate and revise
```

Applications MAY provide specialized processes such as conversational formation, fictional-world construction, personal curation, organizational diagnosis, or simulation. Those processes MUST compile down to kernel records and governed profiles rather than create parallel stores.

## 0.3 Normative language

The terms **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** are used normatively.

- **MUST** identifies a requirement necessary to preserve the framework’s integrity.
- **SHOULD** identifies a strong default that may be overridden only with an explicit reason.
- **MAY** identifies an optional implementation choice.

## 0.4 Version 1.1 foundation improvements

Version 1.1 makes the following normative corrections and additions:

1. replaces the historical framework stack with a strict kernel → profile → application architecture;
2. replaces universal single-branch ownership with explicit BranchMembership;
3. introduces StateCommitment as the only valid Claim-to-State adoption operation;
4. separates record maturity, epistemic standing, and governance status;
5. restores Field and Formation as a formal progressive meaning profile;
6. defines ProfileDefinition and profile conformance rules;
7. formalizes conversation as a provenance-preserving modeling process;
8. defines ReasoningStep, ReasoningTrace, ReasoningSignature, and TransformationOperator;
9. defines ContextState, ContextSwitchEvent, ActiveFieldState, and four-layer context isolation;
10. defines conservative personal learning, incognito behavior, and bounded resurfacing;
11. reorders implementation around capture, formation, conversation, and bridge behavior before advanced simulation;
12. adds migration mappings, reference service boundaries, APIs, test layers, and deployment gates.

---

# Part I — Purpose, Limits, and Core Commitments

# 1. What the System Is

## 1.1 Fundamental purpose

The framework provides a general software substrate for turning raw meaning into a traversable, inspectable, revisable model.

A modeled metaphysical space may contain:

- physical, social, abstract, fictional, possible, remembered, or represented objects;
- states, qualities, processes, events, absences, and transformations;
- structural, causal, semantic, normative, temporal, and epistemic relations;
- competing claims and evidence;
- multiple perspectives and agent-specific beliefs;
- dimensions, scales, boundaries, and contexts;
- valence, salience, tension, and affective structure;
- patterns that recur across domains or scales;
- executable scenarios when sufficient operational semantics exist.

The framework is universal in **representational form**, not in factual knowledge. A universal vocabulary does not eliminate the need for domain equations, specialist ontologies, empirical calibration, or human judgment.

## 1.2 What “model anything” means

The framework can model nearly anything that can be:

- named or referred to;
- observed or sourced;
- imagined or hypothesized;
- described through conditions and relations;
- progressively clarified through interaction.

To model something means to create a structured representation that can be:

- traced to its sources;
- scoped and bounded;
- revised without losing history;
- viewed from different perspectives;
- traversed by relation, time, scale, or meaning;
- compared under declared abstraction rules;
- compiled into execution only when justified.

It does not mean that the representation is complete, true, objective, or computationally predictive.

## 1.3 Non-goals

The framework is not:

- a final ontology of reality;
- a claim that one metaphysical theory is universally correct;
- a universal causal-discovery engine;
- a guarantee that any natural-language description can be simulated;
- a substitute for scientific models, measurements, or domain expertise;
- a license to infer hidden structure without provenance;
- a single database table or one universal execution runtime.

## 1.4 The central architectural proposition

The system is best expressed as:

> **One shared record universe for identity, sources, and provenance; many explicit model branches, perspectives, modal scopes, and executable interpretations; no branch or simulation is silently promoted into reality.**

This replaces the weaker idea of one world model containing no competing truths.

---

# 2. Fundamental Commitments

## 2.1 Unity applies to records, not truth

All modeled content participates in one identity-and-provenance system. Competing interpretations MUST be represented as explicit branches, scoped claims, perspectives, or modal alternatives.

The system MUST NOT force all valid records into one globally consistent set of beliefs.

## 2.2 The map is not the territory

The system only stores representations. Even a record classified as a `State` is a modeled state, not direct access to reality.

The system MUST distinguish:

```text
represented condition
claim about that condition
perspective from which it is interpreted
operational rule used to simulate it
```

## 2.3 Partial models are legitimate

A model MAY remain:

- vague;
- qualitative;
- internally contested;
- incomplete;
- non-executable;
- local to one branch or perspective.

Incomplete models MUST NOT be completed through fabricated precision.

## 2.4 Contradiction is preserved without explosion

Opposing claims MAY coexist. Contradiction MUST be branch- and scope-aware and MUST NOT permit arbitrary unrelated inference.

## 2.5 Perspective is constitutive but bounded

Perspective affects what can be observed, interpreted, valued, and considered relevant. A perspective MUST NOT silently mutate shared records. It produces perspective-scoped claims, assessments, or views.

## 2.6 Execution is earned

A descriptive relation such as `inhibits` or `causes` does not constitute an executable rule. Compilation requires explicit operationalization, types, state domains, conditions, timing, uncertainty, and provenance.

## 2.7 Provenance is universal

Every non-raw record MUST trace back to one or more source fragments, derivation events, user actions, imported datasets, or model outputs.

## 2.8 Valence is represented structurally but executed explicitly

Valence can be part of a Shape’s meaning and comparison profile. It influences a simulation or agent only when a typed appraisal or valence-effect rule is present.

## 2.9 Scale is relative

A part at one scale may be treated as a whole system at another. Scale MUST be explicit during Shape comparison and transformation modeling.

## 2.10 Non-movement is first-class

Absence, delay, inhibition, lock-in, missing dependency, bottleneck, and refusal are legitimate modeled structures, not missing data by default.

## 2.11 Canonical vocabulary is layered

The kernel vocabulary is stable. Shared, workspace, model-local, and raw user vocabularies MAY extend it without requiring immediate global promotion.

## 2.12 Bounded views are mandatory

No user, agent, or service should traverse an unbounded universal graph by default. Every query and projection MUST have an explicit scope, branch, task, or budget.

## 2.13 Kernel, profile, and application separation

The universal kernel MUST remain domain-neutral. Reusable capabilities MUST be defined as normative profiles. User-facing products MUST be implemented as application projections over selected profiles.

An application MUST NOT:

- redefine kernel identity or provenance;
- weaken branch, scope, or execution barriers;
- introduce an ungoverned parallel ontology;
- promote local vocabulary into shared vocabulary implicitly;
- persist a runtime projection as canonical truth without an explicit promotion operation.

## 2.14 Formation is progressive

Meaning may exist before it is propositionally clear. The system MUST support progression from unresolved possibility through differentiated structure into stabilized Formation without treating early ambiguity as missing or failed data.

## 2.15 Conversation is a modeling process

Conversation is not only a query interface. A sequence of turns may create, revise, branch, suspend, connect, or stabilize a metaphysical model. Conversation-derived structure MUST remain traceable to exact source turns and user corrections.

---

# 3. The Four Irreducible Planes

The framework has one record universe but four irreducible semantic planes. They share identifiers and provenance while retaining distinct validity conditions.

## 3.1 Represented-world plane

This plane contains modeled referents, states, occurrences, relations, boundaries, and environments.

It answers:

> What does this model represent as existing, holding, or happening within this scope?

It does not claim direct access to reality.

## 3.2 Epistemic plane

This plane contains claims, evidence, confidence, contradiction, uncertainty, derivation, and promotion status.

It answers:

> What is asserted, by whom, on what basis, and with what support or opposition?

## 3.3 Perspectival plane

This plane contains perspectives, observation limits, interpretations, salience, valence, lenses, and agent beliefs.

It answers:

> How does the represented world appear from a situated position?

## 3.4 Operational plane

This plane contains executable variables, state spaces, actions, policies, transition rules, timing, probability, simulation runs, and outputs.

It answers:

> Under explicit operational assumptions, how may selected modeled states change?

## 3.5 Cross-plane contracts

Cross-plane translation MUST be explicit.

Examples:

```text
Claim → State
requires a representational commitment and branch scope

ValenceAssessment → PolicyEffect
requires an AppraisalFunction or ValenceEffectRule

RelationInstance → TransitionRule
requires compilation and validation

SimulationOutput → Evidence
requires explicit classification as model-derived evidence
and MUST NOT be treated as empirical observation
```

No plane may silently substitute for another.

---

# Part II — Formal Core

# 4. The Canonical Record Model

## 4.1 Universal record envelope

Every stored object is a record with a common envelope:

```yaml
record:
  id: stable_identifier
  type_id: canonical_or_local_type
  scope_id: optional_scope
  version: integer_or_hash
  created_at: timestamp
  created_by: actor_or_service
  provenance_id: provenance_record
  maturity_status: raw | held | differentiating | structured | stabilized_for_purpose | archived | released
  epistemic_status: not_applicable | unassessed | candidate | supported | opposed | both | unresolved | retracted
  governance_status: local | review_required | approved_for_scope | shared | deprecated | quarantined
  visibility_policy: access_rule
```

The envelope establishes identity, optional scope, history, and access. It does not define the record’s domain semantics.

`branch_id` is deliberately not universal. Raw sources, Referents, shared TypeDefinitions, and reusable Provenance may be branch-neutral or visible in several branches. Interpretive participation is represented through explicit `BranchMembership` records. A record type MAY require exactly one branch membership, but the universal envelope MUST NOT force every record to own one branch.

## 4.2 The twelve kernel concepts

The immutable kernel consists of:

1. `SourceFragment`
2. `Referent`
3. `Scope`
4. `State`
5. `Occurrence`
6. `RelationInstance`
7. `Claim`
8. `Perspective`
9. `Evidence`
10. `Provenance`
11. `ModelBranch`
12. `TypeDefinition`

Everything else is a subtype, profile, derived composite, read model, or runtime record.

This is a formalization strategy, not a claim that reality consists of exactly twelve categories.

## 4.3 Normative profile architecture

A `ProfileDefinition` is a governed TypeDefinition package that composes kernel records into a reusable modeling capability.

Every normative profile MUST declare:

```yaml
profile_definition:
  id: shared:profile_name
  version: semantic_version
  purpose: ...
  kernel_records_used: [...]
  profile_record_types: [...]
  profile_dependencies: [...]
  invariants: [...]
  allowed_transformations: [...]
  promotion_rules: [...]
  bounded_view_rules: [...]
  evaluation_dimensions: [...]
  failure_and_abstention_behavior: [...]
  migration_mappings: [...]
  steward: ...
```

Profile dependencies MUST form an acyclic graph. Profiles MAY specialize or compose kernel semantics but MUST NOT redefine them.

The initial normative profile family is:

1. Field and Formation;
2. Shape and Semantic Addressing;
3. Transformation and Dynamics;
4. Pattern and Transfer;
5. Agent and Situated Cognition;
6. Conversation and Personal Formation;
7. Execution and Simulation.

Workspace and domain profiles MAY extend this family under vocabulary governance.

---

# 5. Kernel Concepts

## 5.1 SourceFragment

A `SourceFragment` is preserved input before interpretation.

Examples:

- text span;
- image region;
- audio segment;
- imported database row;
- sensor observation;
- user gesture;
- generated output;
- external document reference.

```yaml
source_fragment:
  id: sf_123
  media_type: text
  content_pointer: ...
  author_or_origin: ...
  captured_at: ...
  integrity_hash: ...
  source_kind: user_input | document | observation | simulation_output
```

A SourceFragment MUST remain retrievable or cryptographically referential after interpretation.

## 5.2 Referent

A `Referent` is anything the model points to as a distinguishable target.

A Referent may represent:

- a person;
- an organization;
- an idea;
- a process;
- a number;
- a fictional character;
- an absence;
- a possible future;
- a relationship;
- a symbol;
- a system or subsystem.

The Referent does not determine its metaphysical category by itself. `TypeDefinition` records characterize its mode of being.

```yaml
referent:
  id: ref_company_x
  type_id: workspace:company
  canonical_label: Company X
  aliases: [X Corp]
  identity_policy: ...
```

## 5.3 Scope

A `Scope` specifies where and under what conditions a record is intended to hold.

It may contain:

```yaml
scope:
  context_refs: [...]
  temporal_scope: ...
  spatial_scope: ...
  modal_scope: actual | possible | fictional | counterfactual | desired
  scale: individual | team | organization | society
  boundary_rule: ...
  domain: ...
  task: ...
  semantic_address: ...
```

Context, boundary, environment, modality, time, dimension, and scale are therefore first-class **scope components**, but they do not all need separate kernel record types.

A Scope MAY reference richer records when required.

## 5.4 State

A `State` is a modeled condition of one or more Referents within a Scope.

```yaml
state:
  id: st_1
  subject_refs: [ref_company_x]
  state_type: workspace:liquidity
  value: low
  value_type: ordinal
  valid_scope: scope_2026_q3
```

A State is distinct from a Claim. A model may contain a State record in one branch and Claims disputing it in others.

## 5.5 Occurrence

An `Occurrence` is something represented as happening or unfolding.

Subtypes may include:

- event;
- process;
- action;
- transition;
- observation;
- recognition;
- disclosure;
- creation;
- dissolution.

```yaml
occurrence:
  id: occ_1
  type_id: workspace:restructuring
  participants: [...]
  temporal_scope: ...
  phases: [...]
```

State change and discovery MUST remain distinct Occurrence types.

## 5.6 RelationInstance

A `RelationInstance` is a typed, potentially n-ary relation among participants.

```yaml
relation_instance:
  id: rel_1
  type_id: core:inhibits
  participants:
    - role: source
      ref: st_control
    - role: target
      ref: st_initiative
  scope_id: scope_org
  qualifiers:
    direction: negative
    strength: qualitative_medium
    delay: unknown
  provenance_id: prov_1
```

Relations are reified because relations may have their own time, scope, modality, evidence, valence, strength, exceptions, and provenance.

## 5.7 Claim

A `Claim` is a truth-evaluable assertion about a Referent, State, Occurrence, RelationInstance, Shape, Pattern, or model output.

```yaml
claim:
  id: cl_1
  proposition:
    predicate: inhibits
    arguments: [st_control, st_initiative]
  claimant: user_or_agent
  branch_id: branch_a
  scope_id: scope_org
  polarity: affirmative
```

Claims MUST NOT be stored as globally true by default.

## 5.8 Perspective

A `Perspective` is a situated position from which records are observed or interpreted.

```yaml
perspective:
  id: p_employee
  holder_ref: employee_group
  role_refs: [workspace:employee]
  observation_access: ...
  interests: ...
  interpretive_assumptions: ...
  limitations: ...
```

A Perspective may belong to a user, simulated agent, collective, analytical method, or instrument.

## 5.9 Evidence

`Evidence` links a Claim to supporting or opposing material.

```yaml
evidence:
  id: ev_1
  claim_id: cl_1
  source_fragment_id: sf_survey
  stance: supports | opposes | contextualizes
  evidence_kind: empirical | testimonial | logical | model_derived
  strength: ...
  evaluator: ...
```

Simulation output MUST be classified as `model_derived`, never silently as empirical evidence.

## 5.10 Provenance

`Provenance` records how a record came to exist.

```yaml
provenance:
  id: prov_1
  source_refs: [sf_1]
  derivation_steps: [...]
  model_or_agent: ...
  prompt_or_rule_version: ...
  user_confirmations: [...]
  prior_versions: [...]
```

Every inferred, abstracted, compiled, or promoted record MUST have Provenance.

## 5.11 ModelBranch

A `ModelBranch` is a coherent, explicitly scoped selection of records, assumptions, and interpretations.

```yaml
model_branch:
  id: branch_control_failure
  parent_branch: branch_base
  branch_kind: interpretation | counterfactual | agent_belief | simulation
  assumptions: [...]
  included_records: [...]
  retracted_records: [...]
  divergence_points: [...]
  merge_status: ...
```

The main branch is a workspace default, not metaphysical truth.

## 5.12 TypeDefinition

A `TypeDefinition` defines reusable semantics without modifying the kernel.

```yaml
type_definition:
  id: workspace:trust
  namespace_level: workspace
  parent_types: [core:state_type]
  constraints: [...]
  labels: ...
  steward: ...
  version: ...
```

TypeDefinition supports domain concepts, relation types, value domains, units, semantic coordinates, and extension profiles.


## 5.13 Identity and reference management

Referent identity is not reducible to labels or embedding similarity. Every Referent type SHOULD declare an `IdentityPolicy` describing which changes preserve identity and which create a new Referent, version, derivative, fusion, split, or replacement.

```yaml
identity_policy:
  applicable_type: workspace:organization
  persistence_conditions:
    - legal_continuity
    - recognized_institutional_lineage
  non_identity_changes:
    - name_change
    - employee_turnover
  identity_breaks:
    - legal_dissolution
  unresolved_cases:
    - merger
    - radical_mission_change
```

Identity resolution may produce:

```text
same_as
possibly_same_as
derived_from
version_of
replaces
splits_into
merges_into
not_same_as
```

`same_as` MUST be used conservatively because it collapses record identity. Most uncertain cases SHOULD use weaker relations.

The system MUST distinguish:

- **type identity:** whether two records instantiate the same concept;
- **token identity:** whether they refer to the same particular;
- **version continuity:** whether one record is a later state of the same particular;
- **representational identity:** whether two expressions encode the same content;
- **functional equivalence:** whether two different things play the same role.

This distinction is essential for cross-domain comparison. Two entities may be functionally equivalent without being identical.

## 5.14 Mode of being

Modes of being are represented through TypeDefinitions and Scope rather than a universal mutually exclusive list. Common modes may include:

```text
continuant
process
quality
abstract
social
institutional
representational
fictional
possible
counterfactual
absence-dependent
```

A Referent may carry several compatible types. A corporation may be social, institutional, temporally persistent, and norm-dependent. A fictional character may be representational and fiction-scoped.

The framework does not require all philosophical theories to agree on one classification. Competing classifications may exist in different ModelBranches while sharing the same source Referent.

## 5.15 BranchMembership

A `BranchMembership` states how a record participates in a ModelBranch.

```yaml
branch_membership:
  record_id: ...
  branch_id: ...
  membership_kind: inherited | asserted | derived | retracted | hidden
  effective_scope: ...
  introduced_by: ...
  provenance: ...
```

This permits a SourceFragment, Referent, TypeDefinition, or Provenance record to be reused across branches without duplication while preserving branch-local interpretation. Claims and branch-specific States MUST have at least one explicit BranchMembership.

## 5.16 StateCommitment

A `StateCommitment` is the explicit reviewed operation by which a branch represents a condition as a State rather than merely retaining a Claim about it.

```yaml
state_commitment:
  source_claims: [...]
  resulting_state: ...
  branch_id: ...
  scope_id: ...
  commitment_kind: stipulated | user_confirmed | evidence_supported | model_assumed
  responsible_actor: ...
  reversible: true
  provenance: ...
```

A StateCommitment does not establish mind-independent truth. It records that a particular branch has adopted a represented condition for a declared purpose. Retraction or revision MUST invalidate dependent Shapes, transformations, compiled rules, and outputs.


---

# 6. Formal Invariants of the Kernel

The following invariants MUST be testable.

## 6.1 State–Claim separation

```text
For every Claim c and State s:
c may refer to s, but c is never identical to s.
```

A correction to a Claim does not automatically alter the represented State in every branch.

## 6.2 Branch-scoped assertion

Every Claim MUST have an explicit BranchMembership and Scope.

No inference rule may consume a Claim without an explicit branch resolution policy.

## 6.3 Perspective non-interference

A Perspective may create a view, assessment, belief, or scoped Claim. It MUST NOT silently mutate records outside its branch or authorized scope.

## 6.4 Provenance closure

Every non-raw record MUST have a derivation path terminating in SourceFragments, imported authoritative records, or explicit user creation.

## 6.5 Relation participant integrity

Every participant in a RelationInstance MUST resolve to an existing record or an explicit unresolved placeholder.

## 6.6 Shape derivation

A Shape MUST be derivable from selected records and an abstraction contract. Shape is not a primitive assertion about reality.

## 6.7 Simulation-output barrier

A SimulationOutput MUST NOT support a real-world empirical Claim unless an explicit evaluation step links it to external observation. It may support Claims about the model’s behavior.

## 6.8 Non-explosive contradiction

Contradictory Claims MUST NOT imply unrelated Claims.

## 6.9 Execution separation

No descriptive RelationInstance is executable until it is represented in a validated executable model.

## 6.10 Non-destructive vocabulary mapping

Mapping a local term to a shared term MUST preserve the original expression, scope, and mapping confidence.

## 6.11 Explicit state commitment

No Claim becomes a represented State merely through repetition, model fluency, confidence aggregation, or downstream use. The transition requires a StateCommitment with branch, scope, provenance, and responsible actor.

## 6.12 Profile conformance

Every profile record MUST resolve to kernel records, a versioned ProfileDefinition, and profile-specific validation results. Application projections MUST NOT bypass profile invariants.


## 6.13 Minimal formal axioms

The machine-readable formal core SHOULD encode at least the following axioms. The notation is illustrative rather than tied to one logic.

### Typing

```text
State(x)       → Record(x)
Claim(x)       → Record(x)
Perspective(x) → Record(x)
Claim(x)       → ∃b,s. hasBranchMembership(x,b) ∧ hasScope(x,s)
Relation(x)    → ∃p₁...pₙ. hasParticipant(x,pᵢ)
```

### Disjoint functional roles

```text
State(x) → ¬Claim(x)
Claim(x) → ¬Evidence(x)
SourceFragment(x) → ¬SimulationRun(x)
```

The same real-world subject may be represented by records of several kinds, but one record instance must not silently change its formal role.

### Perspective scoping

```text
PerspectiveClaim(c,p) → hasPerspective(c,p)
PerspectiveClaim(c,p) ∧ sharedState(s) does not imply modifies(c,s)
```

### Provenance

```text
DerivedRecord(x) → ∃p. hasProvenance(x,p)
Provenance(p) → terminatesInSourceOrExplicitCreation(p)
```

### Execution

```text
ExecutableRule(r) → ValidatedIRMember(r)
DescriptiveRelation(r) ↛ ExecutableRule(r)
```

The final expression means there is no automatic implication from descriptive relation to executable rule.

### Branch isolation

```text
usableInInference(c,q) → compatibleBranch(c,q) ∧ compatibleScope(c,q)
```

### State commitment

```text
adoptedState(s,b) → ∃k. StateCommitment(k) ∧ resultingState(k,s) ∧ commitsInBranch(k,b)
Claim(c) ∧ refersTo(c,s) ↛ adoptedState(s,b)
```

### Profile grounding

```text
ProfileRecord(x,p) → ProfileDefinition(p) ∧ groundedInKernelRecords(x)
ApplicationProjection(a,x) → conformsToProfileInvariants(a,x)
```

These axioms should be accompanied by machine tests and counterexamples, not only prose documentation.


---

# 7. Branch and Contradiction Semantics

## 7.1 Why branches are fundamental

A single record universe may contain:

- several user interpretations;
- competing causal hypotheses;
- different agent beliefs;
- fictional and actual worlds;
- alternative boundaries;
- counterfactual scenarios;
- superseded models.

These should share identity and provenance where appropriate without being flattened into one belief set.

## 7.2 Branch inheritance

A child branch inherits records from its parent unless it:

- retracts a record;
- replaces it with a new version;
- introduces a conflicting Claim;
- changes Scope or assumptions.

Inheritance is a read rule, not physical duplication.

## 7.3 Four-valued support semantics

Within a branch and scope, a Claim may be:

```text
supported and not opposed      = supported-only
opposed and not supported      = opposed-only
supported and opposed          = both
neither supported nor opposed  = unresolved
```

This is an evidence status, not necessarily a full truth theory. It gives the implementation a non-explosive basis for contradiction.

## 7.4 Negation and conflict

Negation MUST be explicit. A Claim may have:

```yaml
polarity: affirmative | negative
conflicts_with: [claim_id]
```

The conflict service SHOULD distinguish:

- strict logical contradiction;
- incompatible measurements;
- perspective divergence;
- temporal change;
- different scope;
- semantic ambiguity;
- competing causal explanation.

Not every apparent contradiction is a logical contradiction.

## 7.5 Branch merge

Merging branches MUST produce a `MergeAssessment` identifying:

- shared records;
- compatible additions;
- conflicting claims;
- divergent assumptions;
- scope differences;
- unresolved identity mappings.

A merge MUST NOT silently choose a winner.


## 7.6 Inference policy

Inference is always a transformation from selected records into new candidate Claims with Provenance.

An inference request MUST declare:

```yaml
inference_context:
  branches: [...]
  scope: ...
  perspective: optional
  accepted_maturity_statuses: [...]
  accepted_epistemic_statuses: [...]
  accepted_governance_statuses: [...]
  relation_families: [...]
  contradiction_policy: preserve
  output_status: candidate
```

Rules SHOULD be separated into:

- definitional inference;
- structural inference;
- temporal inference;
- causal hypothesis generation;
- agent belief inference;
- executable-state inference.

Causal hypothesis generation MUST NOT promote its outputs beyond `candidate` without evidence or explicit stipulation.

When a rule encounters `both` support status, it may:

- preserve both conclusions;
- branch the model;
- request clarification;
- abstain.

It must not select a conclusion merely because one is more fluent or narratively coherent.

## 7.7 Branch ensembles

For uncertain problems, the system MAY maintain a weighted ensemble of ModelBranches.

```yaml
branch_ensemble:
  branches:
    - id: hypothesis_a
      weight: 0.45
    - id: hypothesis_b
      weight: 0.35
    - id: hypothesis_c
      weight: 0.20
  weighting_basis: evidence_fit
  normalization_scope: current_task
```

Weights are task-relative and must not be interpreted as universal truth probabilities unless a formal probabilistic model supports that reading.


---

# 8. Vocabulary Governance

## 8.1 Vocabulary levels

The system uses five vocabulary levels:

```text
Level 1 — Kernel
stable formal concepts defined in this paper

Level 2 — Governed shared vocabulary
widely reusable relation and profile types

Level 3 — Workspace vocabulary
project- or organization-specific concepts

Level 4 — Model-local vocabulary
terms meaningful only inside one branch or model

Level 5 — Raw expression and aliases
user language preserved without forced normalization
```

## 8.2 Promotion

A local concept may be promoted when it has:

- stable usage;
- clear definition;
- distinct identity;
- demonstrated reuse;
- compatibility with existing terms;
- an assigned steward.

Promotion is optional. The system MUST remain useful without global vocabulary approval.

## 8.3 Mapping

Vocabulary mappings are records with:

```yaml
term_mapping:
  source_type: workspace:spiritual_emptiness
  target_type: shared:meaning_deficit
  mapping_kind: equivalent | narrower | broader | overlaps | analogous
  scope: ...
  confidence: ...
  provenance: ...
```

Mapping is not identity unless explicitly confirmed.

## 8.4 Governance rule

Canonical identity does not require canonical interpretation.

The framework should converge on shared terms where useful while preserving user-specific semantic distinctions.


## 8.5 Type constraints and extension safety

A TypeDefinition may declare:

- parent types;
- disjoint types;
- required participant roles;
- allowed value domains;
- identity policy;
- applicable Scope components;
- validation functions;
- display labels;
- deprecation and replacement mappings.

Workspace extensions MUST NOT redefine kernel semantics. They may specialize them.

For example, a workspace may define `workspace:trust_state` as a State type with an ordinal or continuous value domain. It may not redefine `Claim` to mean the same thing as `State`.

## 8.6 Ontology evolution

Vocabulary changes create versions rather than destructive edits. When a type changes:

1. the prior definition remains addressable;
2. affected records are identified;
3. migration is explicit and reversible;
4. semantic-loss warnings are generated;
5. dependent Shape signatures and compiled models are marked stale.

This makes vocabulary governance part of provenance rather than an administrative side process.


---

# Part III — Semantic Structure and Shape

# 8A. Field and Formation Profile

## 8A.1 Purpose

The Field and Formation Profile represents meaning that is active or consequential before it has resolved into stable Referents, Claims, or Shapes, and describes how such material progressively becomes differentiated and stabilized.

It prevents two opposite errors:

- treating raw input as if it already contains a complete ontology;
- treating pre-explicit but structured possibility as meaningless until it becomes a proposition.

## 8A.2 Field

A `Field` is a bounded profile record over SourceFragments, unresolved references, tensions, salience, contextual pressures, and candidate relations.

```yaml
field:
  source_fragments: [...]
  branch_candidates: [...]
  scope_candidates: [...]
  unresolved_referents: [...]
  active_pressures: [...]
  tensions: [...]
  salience_hints: [...]
  candidate_relations: [...]
  differentiation_status: pre_clear | partial | crystallizing
  provenance: ...
```

A Field is not a hidden metaphysical substance, a vector embedding, or an excuse for unconstrained inference. It is a traceable representation of unresolved possibility under a bounded task and context.

## 8A.3 Hold

`Hold` is a valid lifecycle operation that preserves a Field or SourceFragment without forcing differentiation. A Hold SHOULD record why structure is deferred, what remains unresolved, and what evidence or interaction could justify further resolution.

## 8A.4 Formation

A `Formation` is a stabilized, revisable composite that has acquired sufficient internal coherence to be addressed as a working whole.

```yaml
formation:
  root_referents: [...]
  supporting_claims: [...]
  states: [...]
  occurrences: [...]
  relations: [...]
  shape_refs: [...]
  unresolved_tensions: [...]
  boundary: ...
  coherence_basis: ...
  stability: provisional | emerging | stable_for_purpose
  provenance: ...
```

A Formation may represent an idea, project, worldview, artwork, institution, fictional world, identity narrative, research program, or other bounded meaningful whole. Stabilization does not imply completion or universal truth.

## 8A.5 Progressive differentiation

The default movement is:

```text
SourceFragment
→ Field
→ Hold or Branch
→ candidate Referents and Scope
→ Claims, States, Occurrences, and Relations
→ Shape
→ Formation
→ revision, transformation, composition, or release
```

Every transition MUST preserve the raw source, uncertainty, alternatives, and reasons for differentiation.

# 9. Semantic Addressing Without Mandatory Depth

## 9.1 Purpose

Semantic addressing locates a State, Claim, or relation inside a multidimensional meaning space.

The framework preserves the usefulness of dimensions, stations, and facets without requiring every model to use the same three-level hierarchy.

## 9.2 SemanticAddress

```yaml
semantic_address:
  dimension: psychological
  coordinates:
    - role: station
      value: trust
    - role: facet
      value: competence
```

The only mandatory field is `dimension` when dimensional analysis is required. `coordinates` is an ordered, extensible list.

Valid forms include:

```text
Dimension
Dimension → Facet
Dimension → Station → Facet
Dimension → Domain-specific coordinate → Subcoordinate
```

## 9.3 Dimension

A Dimension is an analytical or experiential layer through which records are organized.

Examples:

- financial;
- psychological;
- narrative;
- physical;
- social;
- legal;
- symbolic;
- operational.

Dimensions are TypeDefinitions, not kernel primitives.

## 9.4 Station

A Station is an optional coordinate role identifying a possibility-space in which a condition varies, such as trust, recognition, authority, or clarity.

It SHOULD be used when it improves comparison or traversal. It MUST NOT be inserted solely to satisfy a schema.

## 9.5 Facet

A Facet is an optional coordinate identifying a more specific aspect, such as trust in competence or recognition of meaning.

## 9.6 Progressive resolution

Semantic addresses may deepen over time:

```text
psychological
→ psychological / trust
→ psychological / trust / competence
```

Earlier forms remain valid and traceable. Refinement creates a new version or derived record rather than overwriting the original expression.

---

# 10. Shape Theory

## 10.1 Definition

A `Shape` is a bounded, scoped projection over selected records that preserves a declared set of structural features.

A Shape is not:

- the underlying object;
- a universal truth;
- merely a picture;
- automatically executable;
- necessarily stable.

## 10.2 Three-layer Shape model

### ShapeCore

`ShapeCore` contains the structural projection:

```yaml
shape_core:
  source_branch: branch_a
  scope: scope_x
  selected_nodes: [...]
  selected_relations: [...]
  boundary: ...
  abstraction_contract: ...
  temporal_projection: ...
  modal_projection: ...
  scale_context: ...
```

### ShapeView

`ShapeView` applies a situated interpretation:

```yaml
shape_view:
  shape_core_id: shape_core_1
  perspective_id: perspective_employee
  semantic_addresses: [...]
  valence_field_id: ...
  salience_field_id: ...
  lens_parameters: ...
```

### ShapeRecord

`ShapeRecord` stores a materialized or asserted Shape representation:

```yaml
shape_record:
  core_or_view_id: ...
  epistemic_status: candidate
  provenance_id: ...
  generated_by: ...
  validation_results: [...]
  version: ...
```

This separation prevents provenance, confidence, or perspective from being mistaken for intrinsic structural identity.

## 10.3 AbstractionContract

Every Shape MUST declare what it preserves and ignores.

```yaml
abstraction_contract:
  preserve:
    - relation_direction
    - functional_roles
    - feedback_structure
    - temporal_order
  ignore:
    - proper_names
    - exact_quantity
    - material_domain
  normalization_rules: [...]
  intended_use: diagnosis | comparison | simulation | expression
```

Without an AbstractionContract, Shape comparison is undefined.

## 10.4 Shape identity

Shape identity is determined by:

- selected records;
- boundary;
- branch;
- scope;
- abstraction contract;
- normalization procedure.

It is not determined by confidence or provenance, although those qualify the ShapeRecord.

## 10.5 Shapes are derived

A Shape should normally be generated from canonical records. Users MAY save, name, annotate, or promote it, but its derivation must remain reproducible.

## 10.6 Local and global Shapes

A local Shape covers a bounded subsystem or question. A global Shape is a composition of local Shapes under a wider boundary.

The framework SHOULD prefer local Shapes because they are easier to validate, compare, and compute.

---

# 11. Multidimensional and Composite Shapes

## 11.1 One object, several dimensional Shapes

The same Referent may participate in different Shapes across different dimensions.

```text
Company X
├── financial Shape
├── operational Shape
├── psychological Shape
├── social Shape
├── narrative Shape
└── brand Shape
```

Each dimensional Shape may have different topology, variables, actors, and temporal behavior.

## 11.2 DimensionalShape

A `DimensionalShape` is a ShapeCore whose scope includes a declared dimension.

```yaml
dimensional_shape:
  dimension: financial
  shape_core_id: shape_financial
```

## 11.3 CrossDimensionalCoupling

A `CrossDimensionalCoupling` is a RelationInstance or mechanism linking records located in different dimensions.

```yaml
cross_dimensional_coupling:
  source:
    dimension: financial
    record: state_revenue_decline
  target:
    dimension: psychological
    record: state_employee_fear
  relation_type: amplifies
  mechanism: perceived_instability
  delay: estimated_30_days
```

## 11.4 CompositeShape

A `CompositeShape` consists of:

```text
DimensionalShapes
+ CrossDimensionalCouplings
+ shared identity mappings
+ common boundary
+ time and scale coordination
```

Formally:

```text
CompositeShape = (S₁ ... Sₙ, C, B, T, K)
```

where:

- `Sᵢ` are component Shapes;
- `C` are cross-shape couplings;
- `B` is the composite boundary;
- `T` is temporal coordination;
- `K` is the composition contract.

## 11.5 Shape of shapes

A CompositeShape may itself participate as a node in a higher-scale Shape.

This supports recursive systemhood:

```text
component Shape
→ subsystem CompositeShape
→ organization CompositeShape
→ market CompositeShape
```

The framework supports scale-recursive comparison without assuming literal fractality.

## 11.6 EmergentState

An `EmergentState` is a State whose grounding depends on a configuration of lower-level records rather than one isolated element.

```yaml
emergent_state:
  type: institutional_fragility
  grounded_in:
    - financial_shape
    - psychological_shape
    - operational_shape
  emergence_rule: qualitative_configuration
  reduction_status: partially_reducible
```

Emergence MUST specify:

- grounding records;
- scale transition;
- aggregation or configuration rule;
- evidence and uncertainty.

---

# 12. Valence, Salience, and Tension

## 12.1 ValenceAssessment

A `ValenceAssessment` records how a target is affectively appraised by an experiencer within a Scope.

```yaml
valence_assessment:
  experiencer: employee_group
  target: restructuring_event
  dimension: security
  polarity: negative
  intensity: 0.8
  temporal_scope: current
  perspective: employee_perspective
  confidence: 0.72
  provenance: ...
```

Valence is relational and indexed. It SHOULD NOT be stored as an absolute property of an object unless the model explicitly adopts that assumption.

## 12.2 Ambivalence

Ambivalence is represented through multiple assessments rather than a forced average.

```text
restructuring
→ positive on career opportunity
→ negative on security
→ positive on organizational survival
→ negative on identity continuity
```

## 12.3 ValenceField

A `ValenceField` is a scoped distribution of ValenceAssessments over a ShapeView.

It may characterize:

- node valence;
- relation valence;
- event valence;
- path valence;
- goal valence;
- observer conflict;
- change over time.

## 12.4 SalienceAssessment

Salience records attentional importance for an observer, task, and time.

Salience is distinct from valence:

```text
high salience + negative valence = threat or aversive fixation
high salience + positive valence = desire or attraction
low salience + positive valence  = background comfort
```

## 12.5 Tension

Tension is a higher-level structural condition and MUST be typed.

Possible types include:

- logical contradiction;
- causal opposition;
- resource competition;
- value conflict;
- affective ambivalence;
- semantic ambiguity;
- structural imbalance;
- unresolved dependency.

The generic term `Tension` may summarize these forms but MUST preserve the mechanism subtype.

## 12.6 Why valence is structural

Valence is structural when it changes the meaning, comparison profile, or experienced organization of a Shape.

Two topologically identical dependence relations may differ profoundly:

```text
supportive dependence
coercive dependence
ambivalent dependence
```

Valence therefore belongs in ShapeView and Pattern comparison.

## 12.7 Why valence is not automatically causal

Negative valence does not imply avoidance. It may produce confrontation, compliance, fixation, vigilance, withdrawal, or no action.

Operational influence requires explicit bridge records.

## 12.8 AppraisalFunction

An `AppraisalFunction` derives a ValenceAssessment from situated inputs:

```text
Percept
+ BeliefState
+ Goal or Value
+ Context
→ ValenceAssessment
```

The function may be qualitative, rule-based, probabilistic, learned, or domain-specific.

## 12.9 ValenceEffectRule

A `ValenceEffectRule` specifies how valence affects operational variables or agent policy.

```yaml
valence_effect_rule:
  input:
    assessment_type: security_valence
    condition: value < -0.6
  context_conditions:
    trust_in_management: < 0.4
  effects:
    attention_weight: +0.3
    resistance_action_probability: +0.2
    cooperation_threshold: +0.15
  mechanism: perceived_threat
  provenance: ...
```

Without such a rule, valence remains descriptive and comparative.

---

# 13. Scale, Recursion, and Pattern Comparison

## 13.1 ScaleContext

Every Shape comparison MUST specify a `ScaleContext`:

```yaml
scale_context:
  level: team
  containing_system: organization_x
  component_granularity: role
  time_horizon: six_months
```

## 13.2 Recursive systemhood

The same Referent may be:

- a component in one Shape;
- a subsystem in another;
- a complete system at a lower scale;
- a participant in a larger CompositeShape.

Systemhood is therefore scope-relative.

## 13.3 Pattern

A `Pattern` is a validated abstraction over one or more ShapeCores under a declared abstraction contract.

```yaml
pattern:
  name: reinforcing_centralization_loop
  role_structure: ...
  relation_structure: ...
  dynamic_structure: ...
  required_conditions: ...
  known_counterexamples: ...
  validation_status: ...
```

## 13.4 Candidate retrieval, not automatic equivalence

Cross-domain matching is staged:

```text
candidate retrieval
→ alignment proposal
→ difference report
→ mechanism validation
→ anti-match tests
→ transfer assessment
→ confirmation or abstention
```

The system MUST distinguish candidate similarity from validated Pattern membership.

## 13.5 Similarity vector

Shape comparison returns a vector, not one hidden score:

```text
structural similarity
role similarity
dynamic similarity
mechanistic similarity
temporal similarity
valence similarity
perspective similarity
scale compatibility
intervention transferability
```

An aggregate score MAY be produced only when its weights and purpose are explicit.

## 13.6 Role reduction

Role reduction maps concrete identities to functional positions:

```text
manager → central controller
employee → local adaptive unit
approval system → control channel
```

Role mappings MUST retain provenance and alternatives.

## 13.7 AntiMatch

An `AntiMatch` records why a proposed comparison fails.

```yaml
anti_match:
  candidate_a: shape_a
  candidate_b: shape_b
  apparent_similarity: reinforcing_loop
  rejection_reasons:
    - mechanism_differs
    - reversibility_differs
    - threshold_behavior_differs
  evaluator: ...
```

## 13.8 Comparison sequence

The recommended sequence is:

1. freeze branches, scopes, and abstraction contract;
2. derive ShapeCores;
3. normalize identities and scale where justified;
4. align roles and relation topology;
5. compare dynamics and mechanisms;
6. compare temporal and affective fields;
7. identify differences and missing information;
8. run AntiMatch tests;
9. evaluate intervention transferability separately;
10. record provenance and confidence.

## 13.9 Early implementation restriction

The first Pattern engine SHOULD prioritize:

1. same domain and scale;
2. same domain across scale;
3. adjacent domains with curated mappings;
4. open cross-domain comparison only after validation data exists.


## 13.10 Pattern evaluation corpus

The Pattern engine requires a curated corpus containing:

- confirmed matches;
- partial matches;
- misleading visual matches;
- mechanism mismatches;
- scale failures;
- valence inversions;
- intervention-transfer failures;
- explicit AntiMatches.

Evaluation should measure:

```text
candidate recall
validated-match precision
abstention quality
difference-report completeness
mechanism-preservation rate
false intervention-transfer rate
```

The engine should be evaluated on whether it finds useful candidates **and** whether it declines seductive but invalid analogies.


---

# Part IV — Transformation

# 14. Transformation as a First-Class Composite

## 14.1 Definition

A `TransformationProcess` is a structured trajectory in which states, relations, topology, identity conditions, or rules change over time.

A transformation is not merely `A transforms_into B`. It includes:

```text
initial configuration
→ triggers and preconditions
→ mechanisms
→ phases and thresholds
→ branches and failures
→ resulting configuration
```

## 14.2 Canonical contract

```yaml
transformation_process:
  subject_refs: [...]
  source_branch: ...
  initial_shape: ...
  initial_states: [...]
  triggers: [...]
  preconditions: [...]
  mechanisms: [...]
  phases: [...]
  constraints: [...]
  resources: [...]
  cross_dimensional_couplings: [...]
  valence_changes: [...]
  topology_mutations: [...]
  invariants: [...]
  identity_effect: ...
  reversibility: ...
  path_dependence: ...
  branch_points: [...]
  outcomes: [...]
  provenance: ...
```

## 14.3 Transformation types

The framework may distinguish:

- state transformation;
- structural transformation;
- compositional transformation;
- generative transformation;
- destructive transformation;
- identity transformation;
- epistemic transformation;
- semantic transformation;
- normative transformation;
- rule transformation;
- emergent transformation.

These types may overlap.

## 14.4 TransformationPhase

A phase is a temporally and dynamically coherent portion of a process.

Typical phases include:

```text
latent pressure
activation
destabilization
separation
recombination
stabilization
```

Phases are domain-independent labels only when supported by the model.

## 14.5 Threshold and bifurcation

A transformation may remain stable until a threshold produces a discontinuous change. Thresholds and branch points MUST specify:

- monitored conditions;
- activation boundary;
- hysteresis if present;
- resulting branches;
- uncertainty.

## 14.6 TransformationInvariant

An invariant records what is expected to remain stable:

- identity;
- legal continuity;
- quantity;
- symbolic role;
- core purpose;
- conserved resource;
- relation constraint.

Invariants may be confirmed, assumed, approximate, intentionally preserved, or violated.

## 14.7 IdentityEffect

A transformation must state whether it produces:

```text
same entity with changed state
new version of same entity
derived entity
split
fusion
replacement
dissolution
identity unresolved
```

## 14.8 TopologyMutation

Some transformations create or remove entities and relations. The operational model must support:

- adding or retiring Referents;
- adding or removing RelationInstances;
- changing boundaries;
- creating or dissolving subsystems;
- altering rule sets.

## 14.9 Failed transformation

The framework explicitly represents:

- stalled transformation;
- partial transformation;
- symbolic-only transformation;
- reverted transformation;
- fragmented transformation;
- unintended outcome;
- transformation blocked by missing dependency.

Non-completion is not an error in the model.

## 14.10 TransformationShape

A `TransformationShape` is a ShapeCore over phases, mechanisms, thresholds, and topology mutations. It enables comparison of transformation processes across domains and scales while preserving differences in mechanism and transferability.

---

# Part V — Agents and Situated Grounding

# 15. Agents Inside the Modeled Space

## 15.1 Agent

An `Agent` is a Referent capable of receiving information, maintaining an internal state, selecting or generating actions, and producing effects.

An Agent may be:

- a person;
- a simulated organization;
- an AI system;
- a collective;
- a rule-based process;
- a fictional actor.

Agent is an extension profile, not a kernel category.

## 15.2 Shared records and internal world models

An Agent MUST NOT be given direct access to the full shared record universe by default.

The basic cycle is:

```text
shared branch and scope
→ ObservationModel
→ Percept
→ BeliefState
→ Appraisal and interpretation
→ Affordance set
→ Decision or Policy
→ Action
→ world update
```

## 15.3 ObservationModel

The ObservationModel determines what information reaches an Agent.

```yaml
observation_model:
  agent_id: agent_employee
  visible_scopes: [...]
  accessible_relation_types: [...]
  latency: ...
  noise_model: ...
  resolution: ...
  permission_filters: ...
  attention_budget: ...
```

It models visibility, access, delay, distortion, and selective attention.

## 15.4 Percept

A `Percept` is the actual information delivered to an Agent at a moment.

```yaml
percept:
  agent_id: ...
  source_records: [...]
  observed_values: ...
  uncertainty: ...
  timestamp: ...
  salience: ...
```

Percepts are not shared States. They are perspective-conditioned observations.

## 15.5 BeliefState

A `BeliefState` is an Agent-specific ModelBranch containing claims, confidence, remembered evidence, predictions, contradictions, and unknowns.

This reuse of ModelBranch prevents a separate incompatible truth system for agents.

## 15.6 BeliefUpdateRule

A BeliefUpdateRule defines how new Percepts modify an Agent’s branch.

Inputs may include:

- prior Claims;
- source trust;
- evidence kind;
- reasoning pattern;
- memory strength;
- valence;
- social pressure;
- attention;
- explicit inference rules.

The same Percept may update different Agents differently.

## 15.7 Capability

A `Capability` describes what an Agent can perform, with scope, level, cost, reliability, tool requirements, and permission dependencies.

Capability is distinct from Role. A manager may hold an approval Role but lack the current system Capability to approve.

## 15.8 Affordance

An `Affordance` is an action possibility available to a specific Agent in a specific modeled situation.

```text
Affordance = f(
  agent capabilities,
  world states,
  object properties,
  permissions,
  resources,
  scope
)
```

Affordances are derived, not fixed universal action lists.

## 15.9 Goal, Value, and DecisionCriterion

Agents may be guided by:

- explicit goals;
- values;
- obligations;
- identity consistency;
- risk tolerance;
- habits;
- emotional regulation;
- social approval;
- heuristics.

A DecisionCriterion specifies how competing considerations are combined or prioritized.

## 15.10 Policy

A `Policy` maps an Agent’s internal state and affordance set to an action distribution or plan.

Policies may be:

- deterministic;
- probabilistic;
- rule-based;
- learned;
- planning-based;
- language-model generated;
- habitual.

A policy MUST declare which records it can read and which actions it can select.

## 15.11 Action

An `Action` is an attempted Occurrence initiated by an Agent.

An Action is not identical to its outcome.

```yaml
action:
  actor: agent_a
  action_type: persuade
  target: agent_b
  preconditions: [...]
  required_resources: [...]
  intended_effects: [...]
  actual_effects: determined_by_runtime
```

## 15.12 Normative structure

Permissions, obligations, prohibitions, authority, and commitments are typed Claims or RelationInstances in a normative Scope.

They affect Affordances and consequences but do not automatically imply physical impossibility.

```text
physically possible
≠ institutionally permitted
≠ socially legitimate
```

## 15.13 Direct and indirect grounding

The modeled space grounds an Agent directly through:

- action preconditions;
- resource limits;
- permissions;
- transition rules;
- boundaries;
- available tools.

It grounds the Agent indirectly through:

- observations;
- salience;
- valence;
- memory;
- social signals;
- language;
- norms;
- beliefs about other Agents.

## 15.14 GroundingPacket

A `GroundingPacket` is the bounded runtime projection delivered to an Agent.

```yaml
grounding_packet:
  branch_id: ...
  scope_id: ...
  visible_referents: [...]
  current_percepts: [...]
  relevant_claims: [...]
  applicable_norms: [...]
  current_affordances: [...]
  goals_and_constraints: [...]
  memory_handles: [...]
  provenance_summary: ...
  token_or_compute_budget: ...
```

GroundingPackets prevent omniscience and unbounded context injection.

---

# Part V-A — Conversation and Personal Formation

# 15A. Conversation and Personal Formation Profile

## 15A.1 Purpose

The Conversation and Personal Formation Profile defines how a metaphysical model develops through interaction. Conversation is not only a query interface. A sequence of turns may capture, hold, branch, revise, connect, suspend, stabilize, or release meaningful structure.

This profile supports guided co-processing while preserving user agency. It MUST learn only from observable interaction and MUST NOT claim direct access to hidden cognition, personality, or subconscious processes.

## 15A.2 Core profile records

The profile defines:

```text
ConversationSession
ConversationTurn
ThreadBinding
ReasoningStep
ReasoningMove
ReasoningTrace
ReasoningSignature
ContextState
ContextSwitchEvent
ActiveFieldState
TransformationOperator
ReasoningResult
ReasoningLearningEvent
ResurfacingCandidate
```

These are profile records grounded in the kernel:

- a ConversationTurn preserves one or more SourceFragments;
- a ReasoningStep is an Occurrence linked to source turns;
- a ReasoningMove is a governed Occurrence or Relation type;
- a ReasoningTrace is a bounded Shape over ReasoningSteps;
- a ReasoningSignature is a provisional Pattern over repeated traces;
- ContextState and ActiveFieldState are bounded runtime projections;
- a TransformationOperator produces candidate Claims, Relations, States, Fields, or Formations through a provenance-producing operation.

## 15A.3 ConversationSession and ConversationTurn

```yaml
conversation_session:
  id: ...
  participant_refs: [...]
  main_thread_id: ...
  branch_id: ...
  workspace_binding: optional
  privacy_mode: standard | incognito
  started_at: ...
```

```yaml
conversation_turn:
  id: ...
  session_id: ...
  actor_ref: ...
  source_fragment_refs: [...]
  reply_to: optional
  timestamp: ...
  provenance: ...
```

Every meaningful turn MUST be preserved before interpretation. Generated responses are SourceFragments with `source_kind: generated_output`; they MUST NOT be treated as user beliefs or confirmations.

## 15A.4 Main thread, sidecars, and ThreadBinding

A session has one main thread as its continuity spine. Sidecars MAY isolate imported conversations, experiments, analyses, or alternate branches.

```yaml
thread_binding:
  thread_id: ...
  session_id: ...
  binding_kind: main | sidecar | imported | resumed
  branch_id: ...
  workspace_id: optional
  attached_dimensions: [...]
  isolation_policy: ...
  reintegration_status: isolated | candidate | approved | rejected
  provenance: ...
```

Sidecar content MUST remain isolated by default. Reintegration requires an explicit bridge identifying what is imported, why, into which branch and scope, and with what uncertainty.

## 15A.5 ReasoningStep, ReasoningMove, and ReasoningTrace

A `ReasoningStep` is the smallest observable unit of movement in a reasoning process.

```yaml
reasoning_step:
  id: ...
  source_turns: [...]
  hold_state: pre_clear | partial | crystallizing | settled_for_purpose
  move_type: ...
  prompted_by: [...]
  extends_or_revises: [...]
  affected_records: [...]
  confidence: ...
  provenance: ...
```

Initial ReasoningMove types MAY include:

```text
ground
differentiate
triangulate
expand
narrow
contrast
bridge
translate
formalize
invert
preserve_tension
suspend
integrate
release
seek_canon
```

A `ReasoningTrace` is a Shape over ReasoningSteps, their order, dependencies, corrections, branches, and unresolved Holds. It is editable through explicit revision records; edits MUST NOT erase the original trace.

## 15A.6 ReasoningSignature

A `ReasoningSignature` is a provisional Pattern describing recurring move sequences under specified contexts.

It MUST include contributing traces and SourceFragments, contexts in which the pattern appeared, accepted and rejected prompts, preferred abstraction shifts, ambiguity handling, stability status, and counterexamples or AntiMatches.

One conversation MUST NOT establish or materially rewrite a durable ReasoningSignature. Signatures are weak, revisable priors for assistance, not personality diagnoses or restrictions on future behavior.

## 15A.7 ContextState

`ContextState` determines which bounded world is active before reasoning.

```yaml
context_state:
  active_topic: ...
  object_scope: ...
  object_id: optional
  parent_object_id: optional
  dimension_axis: optional
  user_goal: ...
  current_tension: optional
  answer_shape: ...
  active_workspace_id: optional
  depth_mode: focused | contextual | deep | incognito
  confidence: ...
  context_layers: [...]
  source_refs: [...]
```

Four context spaces MUST remain distinct:

| Space | Meaning | Default durability |
|---|---|---|
| Session-local | Current turns, unresolved references, temporary working state | Ephemeral |
| Workspace-local | Bounded project, Formation, world, or initiative | Scoped durable |
| User-local | Confirmed preference and ReasoningSignature evidence | Slowly durable |
| Global | Shared record universe fallback | Read-only fallback |

Global context MUST NOT override current-turn or workspace evidence without an explicit reason.

## 15A.8 ContextSwitchEvent

A `ContextSwitchEvent` records meaningful movement in topic, object, branch, workspace, goal, perspective, or depth.

```yaml
context_switch_event:
  previous_context: ...
  new_context: ...
  trigger: ...
  switch_kind: local_adjustment | field_reshape | object_shift | workspace_shift
  confidence: ...
  attached_records: [...]
  detached_records: [...]
  rollback_path: ...
  provenance: ...
```

Context switching MUST be inspectable and reversible. Not every local update is a full context switch.

## 15A.9 ActiveFieldState

An `ActiveFieldState` is the smallest useful semantic working set selected from ContextState.

```yaml
active_field_state:
  source_fragment: ...
  candidate_parent_formations: [...]
  active_dimensions: [...]
  active_tensions: [...]
  constraints: [...]
  relevant_claims: [...]
  relevant_evidence: [...]
  ambiguity_level: ...
  candidate_moves: [...]
  retrieval_budget: ...
  provenance_summary: ...
```

It is a specialized BoundedView and MUST NOT become a second knowledge store.

## 15A.10 TransformationOperator and reasoning pipeline

A `TransformationOperator` is a controlled, provenance-producing reasoning move applied to a Field, fragment, Shape, or Formation.

Examples include:

```text
expand_dimension
narrow_claim
preserve_tension
find_structural_analogy
translate_symbol_to_structure
suspend_placement
integrate_into_parent
release_or_reject
```

The normative interaction cycle is:

```text
capture
→ hold
→ bind thread and workspace
→ classify ContextState
→ construct bounded ActiveFieldState
→ select a TransformationOperator or pipeline
→ produce a probe, candidate structure, or integration move
→ evaluate fit and signal preservation
→ receive user correction
→ revise the local branch
→ update personal Pattern evidence conservatively
```

A reasoning pipeline is an ordered sequence of explicit state transformations. It is not a hidden chain-of-thought transcript and MUST expose an operator trace without exposing private model reasoning.

When confidence is low, ambiguity is high, or several parent Formations remain plausible, the system SHOULD produce a probe or Hold rather than an assertion.

## 15A.11 ReasoningResult and ReasoningLearningEvent

A `ReasoningResult` stores the proposed response, affected candidate records, integration verdict, operator trace, evaluation results, and recommended next move.

A `ReasoningLearningEvent` records observable user response such as accepted, rejected, reframed, partially accepted, suspended, or ignored. Learning MUST preserve the exact correction and its context. Durable user-local change requires repeated consistent evidence or explicit confirmation.

## 15A.12 Latent processing and ResurfacingCandidate

The system MAY implement a software analogue to incubation:

```text
unresolved trace
→ deferred bounded comparison
→ provisional bridge or Pattern candidate
→ later contextual match
→ resurfacing proposal
→ user acceptance, dismissal, or revision
```

A `ResurfacingCandidate` MUST record its source traces, comparison contract, reason for present relevance, uncertainty, expiry policy, and dismissal history. It remains non-canonical until accepted, reused, or independently supported.

## 15A.13 Privacy and safety invariants

1. Save before interpret, except in incognito mode where no durable save is permitted.
2. Raw user language remains distinct from inferred structure.
3. Hold, silence, contradiction, and unresolved placement are valid.
4. Session-, workspace-, user-, and global-context records remain isolated until intentionally bridged.
5. Generated responses are not user beliefs.
6. One turn cannot create a durable personal inference.
7. A ReasoningSignature is not a diagnosis, identity, or eligibility criterion.
8. Rejected transformations become scoped negative evidence.
9. Sidecars do not pollute the main thread by default.
10. Resurfacing MUST be dismissible and MUST NOT become self-confirming evidence.

## 15A.14 Application projections

Applications MAY project this profile into different rituals while preserving the same records:

- Thought Trace: inspect ReasoningSteps and their movement;
- Inner Space Curator: place, tend, revisit, release, and compose Formations;
- World Studio: develop canon-backed fictional or conceptual worlds;
- bridge runtime: assemble bounded context and select reasoning moves;
- community reasoning: compare confirmed ReasoningSignatures under privacy and consent rules.

No surface owns a separate ontology.

---

# Part VI — From Description to Execution

# 16. The Compilation Boundary

## 16.1 Descriptive and executable topologies

A descriptive topology states what the model represents:

```text
control inhibits initiative
fear amplifies withdrawal
resource scarcity constrains growth
```

An executable topology specifies how values change:

```text
when control_intensity rises by Δc
and perceived_autonomy < threshold
schedule initiative decrease after delay d
with probability distribution P
```

The first must never be treated as the second without compilation.

## 16.2 Compilation is a separate formal operation

Compilation transforms a selected descriptive branch into an `ExecutableModelIR`.

It is not a hidden LLM interpretation step. Every generated operational element must be inspectable and sourced.

## 16.3 Compilation statuses

A compiled region progresses through:

```text
descriptive
→ operationalization candidate
→ typed
→ structurally valid
→ executable
→ calibrated
→ empirically evaluated
```

A model may stop at any stage.

---

# 17. Executable Model Intermediate Representation

## 17.1 Purpose

The `ExecutableModelIR` is the formal bridge between the shared metaphysical model and one or more runtime backends.

It prevents the canonical model from being distorted around the needs of a single simulator.

## 17.2 Canonical structure

```yaml
executable_model_ir:
  id: ir_1
  source_branch: branch_a
  source_scope: scope_org
  source_records: [...]
  entities_and_agents: [...]
  variables: [...]
  state_spaces: [...]
  events_and_actions: [...]
  mechanisms: [...]
  transition_rules: [...]
  constraints: [...]
  resources: [...]
  observation_functions: [...]
  policies: [...]
  time_model: ...
  probability_model: ...
  outputs: [...]
  assumptions: [...]
  unresolved_requirements: [...]
  validation_results: [...]
  compilation_status: ...
  provenance: ...
```

## 17.3 Variable

A Variable is an operationalized, addressable quantity or discrete condition.

```yaml
variable:
  id: var_trust
  owner_ref: employee_group
  source_state_type: workspace:trust
  data_type: real
  domain: [0.0, 1.0]
  unit: dimensionless
  observability: latent
  initial_value_source: survey_estimate
  uncertainty: ...
```

Variables require a declared type and domain.

## 17.4 StateSpace

A StateSpace defines valid configurations and transition constraints.

It may specify:

- value ranges;
- enum states;
- mutually exclusive conditions;
- terminal or absorbing states;
- impossible combinations;
- topology constraints.

## 17.5 Mechanism

A Mechanism is a structured explanatory chain connecting conditions to effects.

```yaml
mechanism:
  id: mech_control_initiative
  participants: [...]
  intermediate_states:
    - perceived_autonomy
    - risk_avoidance
  enabling_conditions: [...]
  inhibiting_conditions: [...]
  expected_timescale: ...
  evidence: [...]
```

A causal edge without a sufficiently specified mechanism may remain descriptive.

## 17.6 TransitionRule

A TransitionRule contains:

```yaml
transition_rule:
  id: rule_1
  trigger: event_or_condition_expression
  guard: boolean_expression
  effects: [typed_effect_expression]
  delay: time_expression
  probability: probability_expression
  priority: ...
  conflict_policy: ...
  source_mechanism: mech_1
  provenance: ...
```

## 17.7 Expression type system

Expressions MUST be:

- typed;
- side-effect free except inside declared effect operations;
- unit checked where quantities are used;
- deterministic unless randomness is explicit;
- bounded by permitted references.

Core value types may include:

```text
Boolean
Integer
Real
Enum
Set
Vector
Duration
Timestamp
Reference
ProbabilityDistribution
```

## 17.8 Guard expressions

Guards may reference:

- current or lagged Variables;
- events;
- resource levels;
- Agent roles and permissions;
- branch assumptions;
- thresholds;
- modal scenario parameters.

## 17.9 Effect expressions

The core IR should support a small, auditable set of effects:

```text
set(variable, value)
increment(variable, delta)
decrement(variable, delta)
emit(event)
schedule(event, delay)
transfer(resource, source, target, amount)
create_referent(type)
retire_referent(ref)
add_relation(type, participants)
remove_relation(relation_id)
```

Arbitrary code SHOULD NOT be embedded in the canonical IR.

## 17.10 TimeModel

The TimeModel declares:

- discrete, continuous, or event-driven time;
- resolution;
- ordering rules;
- simultaneity policy;
- delay semantics;
- recurrence;
- stopping conditions.

## 17.11 ProbabilityModel

The ProbabilityModel distinguishes:

- process randomness;
- parameter uncertainty;
- model uncertainty;
- Agent policy randomness;
- exogenous-event distributions.

## 17.12 Resource, Stock, and Flow

Resources may be consumable, transferable, renewable, rival, or symbolic.

Stocks accumulate. Flows change stocks.

```text
Stock(t+1) = Stock(t) + inflows − outflows
```

Resources such as trust, legitimacy, and attention may be modeled as stocks only when that operationalization is explicit and justified.

## 17.13 ObservationFunction

An ObservationFunction maps runtime state to Agent Percepts. It implements the ObservationModel within execution.

## 17.14 Runtime adapter

A runtime adapter lowers the validated IR into a specific engine:

- rule engine;
- discrete-event simulation;
- agent-based simulation;
- system dynamics;
- probabilistic program;
- differential equation solver;
- domain-specific simulator.

The adapter must report unsupported constructs rather than silently approximate them.


## 17.15 Interaction resolution

Multi-Agent execution requires an explicit resolver for simultaneous or incompatible actions.

The resolver may use:

- temporal ordering;
- priority and authority;
- resource auctions;
- negotiation;
- collision rules;
- coalition decisions;
- stochastic selection;
- domain-specific adjudication.

```yaml
interaction_resolver:
  applicable_actions: [...]
  conflict_detection: ...
  resolution_rule: ...
  fairness_or_priority_basis: ...
  provenance: ...
```

Action order MUST NOT depend accidentally on database iteration order.

## 17.16 Topology-changing execution

If the runtime permits creation or removal of Referents and relations, topology effects must be typed and reversible in the ExecutionTrace. Runtime-generated records belong to the simulation branch and do not alter descriptive branches unless explicitly imported through a reviewed operation.


---

# 18. The Compilation Calculus

## 18.1 Compilation input

Compilation begins with:

```text
selected branch
+ selected scope
+ selected ShapeCore or TransformationProcess
+ intended runtime and question
```

## 18.2 Stage 1 — Selection

Select the exact records intended for execution. The compiler MUST NOT operationalize the entire record universe.

## 18.3 Stage 2 — Classification

Each selected element is classified as one or more of:

- Agent;
- entity;
- variable candidate;
- event;
- action;
- resource;
- parameter;
- constraint;
- observation source;
- non-executable annotation.

## 18.4 Stage 3 — Relation qualification

Each candidate dynamic relation is classified as:

```text
causal
correlational
constitutive
normative
semantic
interpretive
hypothetical
unknown
```

Only causal, rule-governed, or explicitly stipulated relations may directly generate transition-rule candidates.

## 18.5 Stage 4 — Operationalization

Qualitative conditions are mapped to Variables and StateSpaces.

Every mapping must record:

- source record;
- operational definition;
- measurement or estimation method;
- loss of meaning;
- uncertainty;
- responsible actor.

## 18.6 Stage 5 — Mechanism completion

The compiler checks whether sufficient intermediate structure exists to explain the transition. Missing conditions become unresolved requirements.

## 18.7 Stage 6 — Rule candidate generation

A candidate rule is generated only when the following are present:

```text
source variable or event
target variable or topology operation
mechanism or explicit stipulation
guard conditions
effect semantics
time semantics
uncertainty representation
provenance
```

## 18.8 Stage 7 — Parameterization

Parameters may come from:

- observed data;
- domain literature;
- user assumptions;
- calibration;
- expert elicitation;
- analogy.

Their source class MUST remain visible.

## 18.9 Stage 8 — Static validation

The compiler validates:

- types;
- units;
- variable domains;
- missing initial values;
- contradictory guards;
- impossible state transitions;
- unsupported references;
- rule cycles;
- missing conflict policies;
- incomplete observation models.

## 18.10 Stage 9 — Semantic validation

The compiler compares the IR with its source Shape and Claims:

- Were important qualifiers lost?
- Was correlation converted to causation?
- Were perspective-specific Claims treated as shared States?
- Was valence assumed causal without a bridge?
- Were boundaries changed?
- Were uncertain values made exact?

## 18.11 Stage 10 — Backend validation

The selected runtime adapter verifies that it can preserve the required semantics.

## 18.12 Abstention

Compilation MUST be allowed to return:

> This model is meaningful but not operationally specified enough to execute.

Abstention is a valid and often correct output.

---

# 19. Reaction Estimation

## 19.1 Definition

A reaction estimate is a conditional distribution or set of plausible trajectories produced by an executable model under a declared intervention or event.

It is never an unconditional prediction of reality.

## 19.2 Reaction cycle

```text
initial runtime state
→ intervention or exogenous event
→ Agent observations
→ belief and appraisal updates
→ affordance changes
→ policy and action selection
→ interaction resolution
→ transition rules
→ cross-dimensional and emergent effects
→ next state
```

## 19.3 Output contract

A reaction estimate MUST contain:

- source branch and model version;
- initial-state assumptions;
- intervention;
- runtime adapter;
- parameter sources;
- trajectory distribution;
- sensitivity profile;
- explanation trace;
- unresolved assumptions;
- confidence and calibration status.

## 19.4 Qualitative estimation

Not every model requires numeric simulation. A qualitative model may output:

```text
likely direction
possible branch points
necessary conditions
major uncertainties
failure modes
```

It MUST not fabricate percentages.

## 19.5 Counterfactual branches

Counterfactuals are child ModelBranches sharing a common parent state and diverging through explicit assumptions or interventions.

## 19.6 ExecutionTrace

Every run produces an ExecutionTrace:

```yaml
execution_trace:
  run_id: ...
  events: [...]
  fired_rules: [...]
  sampled_values: [...]
  actions: [...]
  state_changes: [...]
  topology_mutations: [...]
  branch_points: [...]
```

## 19.7 Simulation-output evidence barrier

Simulation output may become Evidence only with one of the following classifications:

```text
model_behavior evidence
counterfactual illustration
hypothesis-generation evidence
empirically validated predictive evidence
```

Only the final class may support real-world predictive claims, and only after explicit external validation.


## 19.8 Calibration

Calibration estimates parameters or rule choices against observations.

A `CalibrationRecord` contains:

```yaml
calibration_record:
  model_ir: ...
  observed_dataset: ...
  parameters_before: ...
  parameters_after: ...
  method: ...
  fit_metrics: ...
  held_out_evaluation: ...
  uncertainty: ...
```

Calibration improves fit to selected observations; it does not prove the topology or mechanism correct.

## 19.9 Sensitivity and identifiability

Every consequential reaction estimate SHOULD report:

- which parameters dominate the output;
- which assumptions change the qualitative result;
- which parameters cannot be identified from available data;
- where several mechanisms produce indistinguishable outcomes.

A system that cannot distinguish two causal explanations should preserve both branches.

## 19.10 Model ensembles

Reaction estimation may execute several branches or parameter sets and combine their outputs. Ensemble results must preserve the contribution and assumptions of each member.

```text
uncertainty over outcomes
≠ only randomness inside one preferred model
```

Model-form uncertainty is often more important than parameter uncertainty.


---

# Part VII — Traversal, Lifecycle, and Trust

# 20. Traversal Semantics

## 20.1 Every traversal is scoped

A traversal query MUST specify or inherit:

- ModelBranch;
- Scope;
- task intent;
- Perspective if relevant;
- maximum depth or cost;
- permitted relation families.

## 20.2 Traversal modes

The system may traverse by:

- structural relation;
- semantic address;
- time;
- scale;
- perspective;
- causation;
- provenance;
- transformation phase;
- Pattern membership;
- valence or salience;
- possible and counterfactual branches.

## 20.3 BoundedView

A `BoundedView` is a task-specific projection with explicit inclusion rules.

```yaml
bounded_view:
  branch: ...
  scope: ...
  root_records: [...]
  relation_filters: [...]
  max_depth: ...
  relevance_budget: ...
  perspective: ...
  materialization_policy: lazy
```

## 20.4 Lazy expansion

Deep or weakly relevant structures SHOULD be represented as expandable handles. This prevents infinite graph growth from becoming infinite interface or query growth.

## 20.5 Trace traversal

Users and agents must be able to move from:

```text
output
→ rule
→ mechanism
→ source relation
→ claim
→ evidence
→ source fragment
```

This is the core trust path.

---

# 21. Progressive Formalization Lifecycle

The lifecycle is one system-wide process.

## 21.1 Capture

Preserve SourceFragments before interpretation.

## 21.2 Hold

Keep ambiguous or unresolved material without forced structure.

## 21.3 Branch

Create or select the ModelBranch in which interpretation occurs.

## 21.4 Refer

Identify candidate Referents and identity relationships.

## 21.5 Scope

Define context, boundary, time, modality, scale, and task.

## 21.6 Assert

Create candidate States, Claims, Occurrences, and RelationInstances.

## 21.7 Differentiate

Add semantic addresses, perspectives, valence, salience, or domain types where useful.

## 21.8 Shape

Derive bounded ShapeCores and ShapeViews.

## 21.9 Transform

Model mechanisms, phases, thresholds, invariants, and identity effects.

## 21.10 Compare

Retrieve and validate candidate Patterns or cross-scale similarities.

## 21.11 Ground

Construct Agent-specific ObservationModels, BeliefStates, and GroundingPackets.

## 21.12 Compile

Create and validate ExecutableModelIR.

## 21.13 Execute

Run a scenario through a declared runtime adapter.

## 21.14 Evaluate

Assess structural, epistemic, perspectival, dynamic, and empirical validity.

## 21.15 Revise

Create new versions, branches, retractions, and derivation links.

## 21.16 Release

Archive, hide, deprecate, or delete according to provenance and privacy policy.

---

# 22. Epistemic and Promotion Lifecycle

## 22.1 Orthogonal lifecycle rule

The framework MUST NOT overload one status field with maturity, epistemic standing, and governance authority. These are three orthogonal state machines.

### Record maturity

```text
raw
held
differentiating
structured
stabilized_for_purpose
archived
released
```

Maturity describes how far material has progressed from capture toward usable structure.

### Epistemic standing

```text
unassessed
candidate
supported
opposed
both
unresolved
retracted
```

Epistemic standing describes support relative to a branch and scope.

### Governance status

```text
local
review_required
approved_for_scope
shared
deprecated
quarantined
```

Governance status describes where and by whom a record may be reused.

The universal envelope uses:

```yaml
maturity_status: ...
epistemic_status: ...
governance_status: ...
```

Record types that do not require one axis MAY use `not_applicable`.

## 22.2 Common transitions

Typical transitions include:

```text
raw → held → differentiating → structured → stabilized_for_purpose
candidate → supported
candidate → opposed
supported → both
local → approved_for_scope → shared
```

`stabilized_for_purpose` and `approved_for_scope` are deliberately scoped. Neither implies universal truth.

## 22.3 PromotionRecord

Every promotion or demotion creates a record containing:

- prior status;
- new status;
- branch and scope;
- rationale;
- evidence;
- evaluator;
- timestamp.

## 22.4 Dependency propagation

When a source Claim or Relation is retracted, dependent Shapes, Patterns, rules, and simulations are marked stale or invalidated according to their derivation graph.

## 22.5 No confidence laundering

A low-confidence assumption does not become high-confidence because it appears inside a detailed Shape, Pattern, or simulation.

Confidence aggregation MUST preserve the weakest load-bearing dependencies.

## 22.6 Valid silence

The system may answer:

- unresolved;
- insufficient evidence;
- incompatible branches;
- not executable;
- comparison inconclusive.

These are correct outputs.

---

# Part VIII — Software Architecture

# 23. One Logical System, Multiple Physical Components

## 23.1 Architectural rule

The framework is one logical system because records share:

- stable identity;
- branch semantics;
- scope semantics;
- provenance;
- vocabulary governance;
- lifecycle and access rules.

It may use multiple physical technologies.

## 23.2 Recommended components

### Immutable capture log

Stores SourceFragments and record-changing events before derived processing.

### Canonical record store

Stores the kernel records, versions, branches, and TypeDefinitions.

### Graph projection store

Materializes relation-heavy views for traversal. It is a read model, not a second source of truth.

### Search and vector index

Supports lexical, semantic, and multimodal retrieval. Similarity results are candidates, not assertions.

### Branch and merge service

Resolves inheritance, retractions, conflict sets, and branch comparisons.

### Vocabulary registry

Stores TypeDefinitions, namespaces, mappings, constraints, and governance status.

### Profile registry

Stores versioned ProfileDefinitions, dependency graphs, conformance rules, migrations, and application bindings.

### Field and Formation service

Preserves unresolved Fields, performs progressive differentiation, and materializes stable-for-purpose Formations without erasing raw sources or alternatives.

### Shape service

Derives ShapeCores, ShapeViews, CompositeShapes, signatures, and bounded projections.

### Transformation service

Models phases, mechanisms, thresholds, invariants, and topology mutations.

### Agent gateway

Builds GroundingPackets and enforces observation, permission, and action contracts.

### Conversation event service

Captures ConversationSessions, turns, ThreadBindings, sidecars, ReasoningSteps, and editable ReasoningTraces before derived processing.

### Context bridge

Constructs ContextState, binds workspaces and branches, maintains four-layer context isolation, emits ContextSwitchEvents, and assembles bounded ActiveFieldStates.

### Reasoning pipeline service

Routes explicit TransformationOperators, evaluates fit and ambiguity preservation, records ReasoningResults, and persists conservative ReasoningLearningEvents.

### Resurfacing service

Runs deferred bounded comparisons over unresolved material and produces dismissible ResurfacingCandidates without promoting them automatically.

### Compilation service

Produces ExecutableModelIR, unresolved-requirement reports, and validation traces.

### Runtime adapter layer

Executes validated IR through selected simulation backends.

### Evaluation service

Runs semantic, epistemic, dynamic, pattern, and empirical evaluators.

### Provenance service

Provides end-to-end derivation traversal and stale-dependency propagation.

## 23.3 Event sourcing and versioning

Every mutation SHOULD be represented as an event:

```text
record created
claim revised
relation added
branch forked
shape materialized
rule compiled
simulation executed
record retracted
conversation turn appended
sidecar attached or detached
context switched
reasoning move accepted or rejected
resurfacing candidate dismissed or integrated
```

Current state may be materialized for speed, but historical events remain authoritative for traceability.

## 23.4 Consistency policy

Strong consistency is required for:

- identity creation;
- branch ancestry;
- provenance references;
- permissions;
- rule and simulation version binding.

Eventual consistency is acceptable for:

- search indexes;
- vector indexes;
- cached Shape projections;
- recommendation surfaces.

## 23.5 Security and privacy

Access controls may apply at:

- workspace;
- branch;
- Scope;
- record;
- SourceFragment;
- Perspective;
- field level.

Agent GroundingPackets MUST be generated after authorization filters. Private user perspectives, beliefs, and valence records must not be merged across users without explicit consent.

## 23.6 Performance strategy

The framework avoids performance collapse through:

- bounded views;
- branch-local indexes;
- lazy graph expansion;
- Shape materialization only when reused;
- cached signatures;
- task-specific relation filters;
- archival and cold storage;
- provenance summaries with expandable detail;
- asynchronous pattern comparison;
- bounded ContextState and ActiveFieldState compilation;
- slow-path resurfacing separated from turn-time response;
- runtime-specific model extraction.

The system MUST NOT construct a complete CompositeShape of the entire record universe for ordinary tasks.

---

# 24. Formalization Stack

No single formal language is required to carry the entire framework.

## 24.1 Core ontology formalization

The kernel SHOULD have a formal specification in a decidable ontology or typed schema language supporting:

- type hierarchy;
- disjointness;
- domain and range;
- cardinality where appropriate;
- identity constraints;
- relation participant constraints.

## 24.2 Record validation

Concrete records SHOULD be validated with machine-readable schemas and graph constraints.

## 24.3 Branch-aware inference

Inference rules MUST be:

- branch-scoped;
- Scope-aware;
- provenance-producing;
- non-explosive under contradiction;
- capable of abstention.

## 24.4 Operational semantics

ExecutableModelIR has a separate typed semantics for state changes, actions, timing, probability, and topology mutation.

## 24.5 Why several formalisms are necessary

The represented-world plane needs category and relation constraints. The epistemic plane needs contradiction and provenance semantics. The operational plane needs time, probability, units, and effects. Forcing all of these into one language would either reduce expressiveness or weaken guarantees.

A unified framework therefore means coherent contracts between formal systems, not one formalism pretending to solve every problem.

---

# 25. Minimal Canonical Schemas

## 25.1 Claim

```yaml
claim:
  id: cl_1
  branch_id: branch_a
  scope_id: scope_a
  proposition:
    predicate_type: core:inhibits
    arguments:
      - state_control
      - state_initiative
  polarity: affirmative
  claimant: user_1
  evidence_refs: [ev_1]
  provenance_id: prov_1
  maturity_status: structured
  epistemic_status: candidate
  governance_status: local
```

## 25.2 ShapeCore

```yaml
shape_core:
  id: shape_1
  branch_id: branch_a
  scope_id: scope_a
  root_refs: [ref_company]
  selected_records: [...]
  selected_relations: [...]
  abstraction_contract_id: ac_1
  scale_context: organization
  temporal_projection: current
```

## 25.3 Perspective-specific ShapeView

```yaml
shape_view:
  id: view_employee
  shape_core_id: shape_1
  perspective_id: p_employee
  semantic_addresses: [...]
  valence_field_id: vf_1
  salience_field_id: sf_1
```

## 25.4 ModelBranch

```yaml
model_branch:
  id: branch_b
  parent_branch: branch_a
  kind: causal_hypothesis
  assumptions: [assumption_1]
  retracted_records: [claim_4]
  added_records: [claim_8, relation_9]
  divergence_points: [claim_4]
```

## 25.5 TransitionRule

```yaml
transition_rule:
  id: rule_1
  source_ir: ir_1
  trigger:
    event: control_increase
  guard:
    and:
      - lt: [var_autonomy, 0.4]
      - gt: [var_control_delta, 0]
  effects:
    - decrement:
        variable: var_initiative
        value:
          multiply: [param_sensitivity, var_control_delta]
  delay: param_response_delay
  probability: distribution_rule_1
  provenance_id: prov_compile_1
```

---

# Part IX — Evaluation and Safety

# 26. Evaluation Dimensions

Every major output should receive a quality profile rather than one confidence score.

## 26.1 Capture fidelity

Was the source preserved accurately and completely?

## 26.2 Identity validity

Are Referents correctly separated, merged, versioned, and scoped?

## 26.3 State–Claim validity

Were modeled conditions kept distinct from assertions and beliefs?

## 26.4 Scope validity

Are boundary, time, modality, dimension, and scale explicit enough for the task?

## 26.5 Perspective validity

Does the view accurately represent the declared observer and access limitations?

## 26.6 Epistemic validity

Are support, opposition, uncertainty, and branch differences represented honestly?

## 26.7 Shape validity

Does the Shape preserve the features declared in its abstraction contract?

## 26.8 Dynamic validity

Are causal direction, mechanism, delays, feedback, and non-movement adequately represented?

## 26.9 Valence validity

Are valence and salience indexed to experiencer, dimension, context, and time? Are causal effects explicit rather than assumed?

## 26.10 Transformation validity

Are phases, invariants, topology mutations, identity effects, branches, and failures represented?

## 26.11 Pattern validity

Are similarities and differences reported separately? Have AntiMatch tests been run?

## 26.12 Agent-grounding validity

Does each Agent receive only permitted observations, relevant claims, and valid affordances?

## 26.13 Compilation validity

Does the IR preserve source semantics, types, units, uncertainty, and provenance?

## 26.14 Simulation validity

Are the runtime, parameters, initial conditions, sensitivity, calibration, and stopping conditions explicit?

## 26.15 Explanatory validity

Can every conclusion or trajectory be traced back to sources, assumptions, and rules?

## 26.16 Correction responsiveness

When a load-bearing Claim changes, are dependent Shapes, rules, and simulations invalidated or revised?

## 26.17 Profile conformance

Can every profile record be traced to kernel records and a versioned ProfileDefinition? Are application projections prevented from weakening profile invariants?

## 26.18 Field and Formation validity

Was unresolved possibility preserved without invented precision? Is Formation stability scoped to a declared purpose and supported by traceable structure?

## 26.19 Conversation trace validity

Are meaningful turns preserved exactly? Can ReasoningSteps, prompts, corrections, sidecars, and reintegration decisions be traced without treating generated text as user belief?

## 26.20 Context validity

Are session-, workspace-, user-, and global-context layers isolated? Are context switches bounded, inspectable, and reversible?

## 26.21 Personalization validity

Are ReasoningSignatures based on repeated contextual evidence, accompanied by counterexamples, and used only as weak revisable priors?

## 26.22 Resurfacing validity

Can every resurfaced candidate explain why it is relevant now, where it came from, what comparison contract was used, and how it may be dismissed?


## 26.23 ModelQualityProfile

A `ModelQualityProfile` stores separate evaluation dimensions:

```yaml
model_quality_profile:
  capture_fidelity: ...
  identity_validity: ...
  epistemic_validity: ...
  boundary_validity: ...
  perspective_validity: ...
  shape_validity: ...
  dynamic_validity: ...
  compilation_validity: ...
  empirical_validity: ...
  profile_conformance: ...
  formation_validity: ...
  conversation_trace_validity: ...
  context_validity: ...
  personalization_validity: ...
  resurfacing_validity: ...
  known_limitations: [...]
```

The system MUST NOT collapse this into a single confidence number by default.

## 26.24 Minimum sufficient model

A model is sufficient relative to a task, not absolutely complete.

For a task `Q`, the minimum sufficient model contains only the records needed to:

- answer Q at the required fidelity;
- expose load-bearing assumptions;
- represent relevant alternatives;
- support the required traversal or execution;
- explain the result.

This principle governs pruning, compilation selection, and interface disclosure.


---

# 27. Core Acceptance Tests

A conforming implementation should pass at least the following tests.

## 27.1 Ambiguous input

A vague source can remain a SourceFragment and held Claim without invented structure.

## 27.2 Contradictory branches

A Claim and its negation can coexist in one record universe without unrelated inference.

## 27.3 State–Claim separation

An Agent may hold a false Claim about a modeled State.

## 27.4 Perspective divergence

Two Perspectives can produce different ShapeViews over the same ShapeCore.

## 27.5 Multidimensional composition

One Referent can participate in several dimensional Shapes connected through cross-dimensional couplings.

## 27.6 Valence divergence

The same event can carry different valence by experiencer and dimension without being reduced to one average.

## 27.7 Valence execution barrier

A ValenceAssessment does not affect a runtime unless an explicit AppraisalFunction or ValenceEffectRule is present.

## 27.8 Recursive scale

A subsystem can be treated as a complete system under a new Scope without identity duplication.

## 27.9 Pattern abstention

A candidate Shape match can be rejected because mechanisms or boundary conditions differ.

## 27.10 Transformation identity

A model can distinguish state change, versioning, replacement, split, fusion, and dissolution.

## 27.11 Non-executable description

A meaningful causal description can remain non-executable when parameters or state mappings are absent.

## 27.12 Compilation trace

Every TransitionRule can be traced to operationalized States, Claims, mechanisms, assumptions, and sources.

## 27.13 Simulation-output barrier

A simulated trajectory cannot be promoted to empirical evidence without external validation.

## 27.14 Bounded traversal

An Agent query cannot expand beyond its authorized GroundingPacket and relevance budget.

## 27.15 Vocabulary preservation

Mapping a user-created term to a shared type does not erase the original expression.

## 27.16 Branch-neutral source reuse

One SourceFragment or Referent can participate in several branches through explicit BranchMembership without duplication or forced interpretive agreement.

## 27.17 State commitment

A supported Claim cannot silently become a represented State; an explicit reversible StateCommitment is required.

## 27.18 Lifecycle independence

A record can be structurally mature while epistemically contested and governance-local without collapsing those statuses.

## 27.19 Profile conformance

A profile record that lacks kernel grounding, profile version, or invariant validation is rejected.

## 27.20 Field preservation

A meaningful but pre-explicit fragment can remain in a Field without invented Referents, Claims, or semantic coordinates.

## 27.21 Conversation trace fidelity

A multi-turn reasoning path preserves exact source turns, prompts, corrections, branching, and unresolved Holds.

## 27.22 Sidecar isolation and reintegration

An imported sidecar cannot affect the main thread until an explicit, provenance-preserving reintegration operation is approved.

## 27.23 Context isolation

Workspace-local material does not leak into another workspace, and global fallback cannot override current-turn evidence silently.

## 27.24 Reversible context switching

A context switch records attached and detached material and can restore the prior ContextState.

## 27.25 Conservative personalization

One conversation or one accepted prompt cannot establish a durable ReasoningSignature.

## 27.26 Incognito behavior

An incognito session produces no durable ReasoningLearningEvent, profile update, or resurfacing candidate.

## 27.27 Resurfacing provenance

A resurfaced idea is dismissible, explains its present relevance, and cannot become canonical through repeated model generation alone.

---

# 28. Failure Modes and Required Defenses

## 28.1 Premature structure

**Risk:** ambiguous input is forced into precise records.  
**Defense:** Hold states, candidate status, progressive semantic resolution.

## 28.2 One-truth coercion

**Risk:** competing models are flattened into one branch.  
**Defense:** branch-first Claims, explicit conflicts, non-destructive merge.

## 28.3 Map–territory collapse

**Risk:** Shape or simulation output is treated as reality.  
**Defense:** four-plane contracts, ShapeCore/View/Record separation, output evidence barrier.

## 28.4 Ontological inflation

**Risk:** every useful concept becomes foundational.  
**Defense:** twelve-concept kernel, optional profiles, derived composites, TypeDefinitions.

## 28.5 Vocabulary bureaucracy

**Risk:** all user language requires central approval.  
**Defense:** layered namespaces and local concepts by default.

## 28.6 False causalization

**Risk:** association or interpretation becomes causation.  
**Defense:** relation qualification and compilation stages.

## 28.7 False executability

**Risk:** qualitative arrows become numeric rules.  
**Defense:** typed IR, unresolved requirements, abstention.

## 28.8 Numerical theater

**Risk:** precise numbers conceal unsupported assumptions.  
**Defense:** parameter provenance, qualitative mode, sensitivity analysis.

## 28.9 Shape seduction

**Risk:** an elegant Shape is accepted because it is aesthetically compelling.  
**Defense:** abstraction contracts, counterexamples, AntiMatches, evidence review.

## 28.10 Pattern-matching hubris

**Risk:** cross-domain resemblance is treated as equivalence.  
**Defense:** candidate retrieval, difference report, mechanism validation, separate transfer score.

## 28.11 Intervention over-transfer

**Risk:** an intervention is copied across scales or domains because topology appears similar.  
**Defense:** explicit material, temporal, normative, and Agent compatibility checks.

## 28.12 Valence determinism

**Risk:** positive or negative valence is assumed to produce one behavior.  
**Defense:** explicit appraisal and effect rules.

## 28.13 Agent omniscience

**Risk:** an Agent receives the whole shared graph.  
**Defense:** ObservationModels, GroundingPackets, access and attention budgets.

## 28.14 Infinite graph growth

**Risk:** every possible association becomes a persistent edge.  
**Defense:** bounded views, relevance thresholds, lazy expansion, archival, branch-local materialization.

## 28.15 Self-confirming simulation

**Risk:** simulation output is fed back as evidence for its own assumptions.  
**Defense:** evidence-kind separation and external validation requirements.

## 28.16 Hidden normative assumptions

**Risk:** model rules embed values without declaring them.  
**Defense:** normative Scope, explicit goals and decision criteria, perspective tracing.

## 28.17 Backend distortion

**Risk:** the model is simplified to fit a runtime.  
**Defense:** runtime capability report and semantic-loss record.

## 28.18 Profile drift

**Risk:** applications redefine profile semantics and gradually recreate parallel ontologies.  
**Defense:** versioned ProfileDefinitions, conformance tests, explicit migrations, and application bindings.

## 28.19 Conversational attribution error

**Risk:** generated text or an agent suggestion is stored as the user's belief or intention.  
**Defense:** actor-specific SourceFragments, explicit confirmation records, and conversation trace tests.

## 28.20 Context contamination

**Risk:** unrelated sessions, workspaces, users, or global material silently shape the active model.  
**Defense:** four-layer context isolation, ContextSwitchEvents, provenance summaries, and bounded ActiveFieldStates.

## 28.21 Personalization foreclosure

**Risk:** an early ReasoningSignature narrows what the system expects the user to think or how it permits them to reason.  
**Defense:** weak priors, repeated-evidence thresholds, counterexamples, expiry, user inspection, and easy reset.

## 28.22 Sidecar pollution

**Risk:** imported or experimental material alters the main continuity spine without consent.  
**Defense:** isolation-first ThreadBindings and explicit reintegration bridges.

## 28.23 Resurfacing self-confirmation

**Risk:** model-generated associations repeatedly resurface and acquire apparent importance without user or external support.  
**Defense:** provenance-preserving candidate status, dismissal memory, expiry, and promotion barriers.

---

# Part X — Implementation Strategy

# 29. Ruthlessly Minimal First Implementation

## 29.1 The first kernel slice

The first implementation should use eight record types:

```text
SourceFragment
Referent
Scope
State
Claim
RelationInstance
Provenance
ModelBranch
```

Evidence may initially be represented as a typed link from Claim to SourceFragment. Perspective and TypeDefinition should be introduced immediately after the kernel proves stable.

## 29.2 First operations

The first system needs only:

```text
capture
create branch
create referent
assert state or claim
relate records
revise or retract
trace provenance
query bounded view
append conversation turn
hold unresolved field
bind main thread or sidecar
```

## 29.3 What the first implementation must not attempt

It should not initially build:

- universal Pattern matching;
- autonomous simulation compilation;
- unrestricted user ontology promotion;
- full Agent societies;
- global CompositeShapes;
- automatic causal inference;
- durable ReasoningSignatures;
- autonomous resurfacing;
- cross-user reasoning clustering.

## 29.4 First milestone

The first milestone succeeds when a user can:

1. capture a thought;
2. preserve the raw source;
3. separate what is represented from what is claimed;
4. create two competing interpretations;
5. trace each interpretation to evidence;
6. revise one branch without corrupting the other;
7. inspect a bounded graph view;
8. preserve a short reasoning trace without inventing structure;
9. isolate and explicitly reintegrate a sidecar.

---

# 30. Staged Build Order

## Phase 1 — Capture, identity, and branch kernel

Implement the eight-record MVP, immutable event log, provenance, BranchMembership, StateCommitment, and branch inheritance.

## Phase 2 — Profile registry and lifecycle validation

Add TypeDefinition, ProfileDefinition, Perspective, Evidence, the three orthogonal lifecycle axes, schema constraints, and branch-aware inference.

## Phase 3 — Field, Formation, and conversation capture

Implement Field, Hold, Formation, ConversationSession, ConversationTurn, ThreadBinding, ReasoningStep, and ReasoningTrace. Prove exact-source preservation, sidecar isolation, and progressive differentiation.

## Phase 4 — Bounded bridge and live active field

Implement ContextState, ContextSwitchEvent, four-layer context isolation, ActiveFieldState, bounded retrieval, and incognito behavior.

## Phase 5 — Shape and semantic addressing

Implement AbstractionContract, ShapeCore, ShapeView, bounded graph derivation, semantic addressing, and Formation projections.

## Phase 6 — Symbiotic transformation pipelines

Implement explicit TransformationOperators, one `idea_embedding_v1` pipeline, ReasoningResult, evaluation, and conservative ReasoningLearningEvents. The system must prefer Hold or a probe under ambiguity.

## Phase 7 — Multidimensional, affective, and transformation structure

Add dimensional Shapes, couplings, ValenceAssessment, SalienceAssessment, TransformationProcess, mechanisms, phases, thresholds, invariants, identity effects, and topology mutations.

## Phase 8 — Restricted Pattern and resurfacing engine

Begin with same-domain Shape comparison and curated role mappings. Add AntiMatches and evaluation datasets. Introduce deferred resurfacing only after candidate provenance, dismissal, and expiry tests pass.

## Phase 9 — Agent grounding

Add ObservationModel, Percept, BeliefState branches, Capabilities, Affordances, Policies, and GroundingPackets. Reuse bridge and bounded-view contracts rather than create a second context system.

## Phase 10 — ExecutableModelIR

Define the expression type system, compilation stages, validation, semantic-loss reporting, and abstention behavior.

## Phase 11 — One runtime adapter

Choose one narrow runtime—such as a rule-based discrete-event simulator—and validate the complete trace from source to run.

## Phase 12 — Product surfaces

Build Thought Trace, Inner Space Curator, World Studio, capture, world navigation, comparison, transformation, Agent, and simulation interfaces over the stable kernel and profiles.

## Phase 13 — Calibration, community, and broader adapters

Add empirical calibration, sensitivity analysis, specialist backends, privacy-preserving ReasoningSignature comparison, and community matching only after the individual reasoning and consent boundaries are proven.

---

# 31. Recommended Product Surfaces

The product may offer different views without reintroducing separate frameworks.

## 31.1 Capture surface

Preserves raw thought and offers light, reversible structure.

## 31.2 Trace surface

Shows how Claims, Shapes, and outputs were derived. In conversation applications, Thought Trace exposes ReasoningSteps, move labels, Holds, prompted-by relations, corrections, and branching without presenting private model chain-of-thought.

## 31.3 World navigation surface

Traverses Referents, relations, Scopes, branches, dimensions, time, and provenance.

## 31.4 Shape surface

Displays bounded ShapeCores and perspective-conditioned ShapeViews.

## 31.5 Transformation surface

Shows phases, thresholds, mechanisms, invariants, and branch points.

## 31.6 Comparison surface

Presents candidate Patterns, alignment vectors, differences, and AntiMatches.

## 31.7 Agent surface

Shows what an Agent can observe, believes, values, and can do.

## 31.8 Simulation surface

Shows the operationalization boundary, unresolved requirements, scenarios, reaction estimates, and execution traces.

## 31.9 Inner Space Curator surface

Projects Formations and unresolved Fields into a personal spatial or ritual interface. Its verbs are `place`, `tend`, `revisit`, `release`, and `compose`. Revisitation may count as salience evidence but MUST NOT automatically establish truth or canonical importance.

## 31.10 Conversation bridge surface

Shows or controls the active workspace, branch, context depth, attached sidecars, and meaningful ContextSwitchEvents. It should remain mostly invisible during ordinary flow while keeping changes inspectable on demand.

## 31.11 Community reasoning surface

With explicit consent, compares sufficiently stable ReasoningSignatures to support compatible collaboration. It MUST preserve privacy, avoid diagnostic labeling, report differences and AntiMatches, and never determine eligibility through a hidden aggregate score.

The interface should expose complexity progressively rather than forcing users to manipulate ontology records directly.

---

# Part XI — Worked End-to-End Example

# 32. Organizational Control and Initiative

## 32.1 Raw capture

A user states:

> When a company increases control because performance is weak, employees stop taking initiative, which makes performance even weaker and causes management to increase control again.

This is stored as a SourceFragment without immediate formal commitment.

## 32.2 Base branch

The interpretation service creates a candidate branch containing Referents:

```text
company
management
employees
performance
control
initiative
```

It creates candidate States:

```text
control intensity: increasing
employee initiative: decreasing
performance: weak
```

And candidate Claims:

```text
increased control inhibits initiative
lower initiative contributes to weak performance
weak performance motivates additional control
```

Each Claim points to the original SourceFragment and remains `candidate`.

## 32.3 Competing branches

Branch A proposes the centralization mechanism:

```text
control
→ lower perceived autonomy
→ risk avoidance
→ reduced initiative
```

Branch B proposes an alternative:

```text
unclear goals
→ decision uncertainty
→ reduced initiative
```

Branch C proposes that control improves performance under high ambiguity.

The record universe retains shared identities while the branches preserve competing explanations.

## 32.4 Scope

The model declares:

```yaml
scope:
  organization: Company X
  time: current fiscal year
  scale: team and organization
  modality: actual-model
  boundary: internal management and employee interaction
```

External market pressure remains an environmental input, not an internal cause by default.

## 32.5 Dimensional Shapes

### Operational Shape

```text
centralized approval
→ decision delay
→ backlog
→ escalation
```

### Psychological Shape

```text
control signal
→ reduced autonomy
→ risk avoidance
→ reduced initiative
```

### Financial Shape

```text
weak performance
→ pressure to reduce variance
→ stronger control demand
```

### Narrative Shape

```text
stated innovation culture
↔ experienced distrust
→ credibility tension
```

## 32.6 CompositeShape

Cross-dimensional couplings connect the Shapes:

```text
financial pressure
→ management control
→ psychological threat
→ lower operational initiative
→ weaker performance
→ financial pressure
```

## 32.7 Perspective and valence

Management perspective:

```text
control
security valence: positive
coordination valence: positive
bureaucratic cost valence: negative
```

Employee perspective:

```text
control
autonomy valence: negative
clarity valence: potentially positive
security valence: context dependent
```

The ValenceField preserves these simultaneous assessments.

## 32.8 Valence operationalization

The model does not assume that negative autonomy valence causes resistance.

An explicit ValenceEffectRule is proposed:

```text
if autonomy valence < -0.6
and trust in management < 0.4
then probability of passive resistance increases
```

This remains a candidate until evidence or user confirmation supports it.

## 32.9 TransformationProcess

The process is modeled as:

```text
weak performance
→ control intervention
→ short-term compliance phase
→ autonomy erosion phase
→ initiative decline
→ adaptive-capacity decline
→ intensified control or intervention change
```

Invariants include organizational identity and formal reporting lines. Possible topology mutation includes removal of local decision rights.

## 32.10 Pattern comparison

The Shape service retrieves candidate analogies in other organizations and political systems. It reports:

```text
high topology similarity
medium role similarity
medium dynamic similarity
unknown mechanism similarity
low evidence for intervention transfer
```

No cross-domain intervention is recommended without further validation.

## 32.11 Compilation

The compiler selects Branch A and operationalizes:

```text
control_intensity      ∈ [0,1]
perceived_autonomy     ∈ [0,1]
initiative             ∈ [0,1]
performance            ∈ [0,1]
trust_in_management    ∈ [0,1]
```

It creates candidate mechanisms and rules with explicit parameter gaps.

The first compilation result is `incomplete` because effect strengths and delays are unsupported.

After survey data and expert assumptions are added, the model becomes executable but not calibrated.

## 32.12 Agent grounding

Management Agents observe performance frequently but employee autonomy indirectly and with delay.

Employee Agents observe control changes immediately, maintain distinct BeliefState branches, and receive role-specific affordances.

## 32.13 Counterfactual scenarios

```text
Scenario 1: increase control only
Scenario 2: increase clarity without removing decision rights
Scenario 3: participatory control redesign
Scenario 4: no intervention
```

The runtime produces conditional trajectories and an ExecutionTrace. Results are labeled model-derived and do not become empirical evidence until compared with observed outcomes.

## 32.14 Learning loop

Observed outcomes update evidence, parameters, Claims, and Pattern assessments. The original SourceFragment and branch history remain intact.

This example demonstrates the entire framework without requiring separate conceptual systems.

---


# 33. Cross-Scale Transformation Comparison

## 34.1 Small-scale process

At an individual level:

```text
fear of error
→ repeated self-monitoring
→ reduced spontaneous action
→ fewer corrective experiences
→ stronger fear of error
```

## 34.2 Organizational process

At an organizational level:

```text
fear of variance
→ centralized monitoring
→ reduced local initiative
→ fewer adaptive experiments
→ stronger fear of variance
```

## 34.3 Candidate abstraction

An AbstractionContract preserves:

- a central fear or threat state;
- monitoring or control response;
- suppression of local experimentation;
- reduced corrective feedback;
- reinforcement of the original threat state.

It ignores the concrete material substrate and proper identities.

## 34.4 Comparison result

The system may report:

```text
structural similarity: high
dynamic similarity: high
role similarity: medium-high
mechanism similarity: uncertain
valence similarity: medium
scale compatibility: medium
intervention transferability: low until validated
```

The result supports thought and hypothesis generation. It does not establish that psychological and organizational interventions are interchangeable.

## 34.5 AntiMatch condition

Suppose the individual process is maintained primarily by learned threat appraisal while the organization is maintained by legal liability and resource dependence. The apparent Shape remains useful, but the mechanism mismatch sharply limits transfer.

This example captures the proper role of cross-scale Pattern comparison: reveal structural possibility, then preserve the differences that determine action.

---

# Part XII — Research Boundaries

# 34. Open Problems

The framework deliberately leaves several questions open.

## 34.1 Formal contradiction logic

The four-valued evidence semantics provides a practical base, but the exact paraconsistent inference system requires implementation research and domain-specific testing.

## 34.2 Identity through radical transformation

No universal identity policy can determine when every transformed object remains the same object. TypeDefinitions and domain rules must supply criteria.

## 34.3 Emergence

EmergentState requires explicit grounding and scale-transition rules. The framework does not claim to solve strong emergence philosophically.

## 34.4 Reliable natural-language compilation

Translating human causal language into executable rules remains a research problem. The framework’s answer is inspectability, staged compilation, and abstention—not assumed automation.

## 34.5 Universal Pattern matching

Cross-domain Shape comparison is semantically fragile. It must be evaluated empirically and restricted by abstraction contracts.

## 34.6 Vocabulary evolution

Long-term governance must balance interoperability with local semantic sovereignty.

## 34.7 Computational tractability

Large CompositeShapes, branch ensembles, and Agent simulations may become computationally expensive. Approximation policies must remain visible.

## 34.8 Evaluation of meaning fidelity

Some semantic and affective judgments cannot be validated through one objective metric. The system needs plural evaluators and user correction loops.

---

# 35. Final Synthesis

The framework can be reduced to one disciplined movement:

```text
source
→ branch-aware representation
→ bounded structural projection
→ situated interpretation
→ explicit transformation model
→ earned operationalization
→ conditional execution
→ traced evaluation
→ revision
```

Its deepest principles are:

1. **One shared record universe does not mean one imposed truth.**
2. **The represented world, claims, perspectives, and simulations remain distinct.**
3. **A small formal kernel supports richer optional profiles.**
4. **Shape is a derived, bounded projection with an explicit abstraction contract.**
5. **A system may be composed of many interacting Shapes across dimensions and scales.**
6. **Valence shapes meaning and comparison; causal influence requires explicit rules.**
7. **Transformations include phases, mechanisms, invariants, identity effects, failures, and topology mutations.**
8. **Agents inhabit partial, situated projections rather than an omniscient world.**
9. **Descriptive relations do not execute themselves.**
10. **Compilation must be typed, traced, validated, and allowed to abstain.**
11. **Pattern matching generates candidates and difference reports, not automatic universal equivalence.**
12. **Simulation outputs are model products, not self-validating evidence.**
13. **Local language and models remain legitimate without global ontology approval.**
14. **Every operation is bounded by branch, scope, task, access, and provenance.**
15. **The kernel is universal; profiles formalize reusable capabilities; applications remain projections.**
16. **Pre-explicit Fields and stabilized Formations belong to one progressive meaning lifecycle.**
17. **Conversation may transform the model, but every move, correction, and context switch remains traceable.**
18. **Personal reasoning patterns are weak, revisable aids derived conservatively from interaction.**

The final architectural statement is:

> **Thought Tube is one branch-aware metaphysical modeling system: a universal identity-and-provenance kernel extended through governed profiles, in which arbitrary metaphysical spaces can be captured, held, represented, situated, shaped, formed, transformed, compared, developed through conversation, inhabited by agents, and selectively compiled into executable scenarios—without confusing models with reality, generated interpretation with human belief, or ambiguity with failure.**

---

# Appendix A — Compact Canonical Vocabulary

## Kernel

```text
SourceFragment
Referent
Scope
State
Occurrence
RelationInstance
Claim
Perspective
Evidence
Provenance
ModelBranch
TypeDefinition
```

## Kernel governance and commitment

```text
ProfileDefinition
BranchMembership
StateCommitment
PromotionRecord
```

## Field and Formation structures

```text
Field
Hold
Formation
```

## Derived semantic structures

```text
SemanticAddress
ShapeCore
ShapeView
ShapeRecord
DimensionalShape
CompositeShape
CrossDimensionalCoupling
EmergentState
ValenceAssessment
ValenceField
SalienceAssessment
Tension
```

## Transformation structures

```text
TransformationProcess
TransformationPhase
Threshold
TransformationInvariant
IdentityEffect
TopologyMutation
TransformationShape
```

## Pattern structures

```text
Pattern
AbstractionContract
ScaleContext
AlignmentProposal
AntiMatch
TransferAssessment
```

## Agent structures

```text
Agent
ObservationModel
Percept
BeliefState
BeliefUpdateRule
Capability
Affordance
Goal
Value
DecisionCriterion
Policy
Action
GroundingPacket
AppraisalFunction
ValenceEffectRule
```

## Execution structures

```text
ExecutableModelIR
Variable
StateSpace
Mechanism
TransitionRule
Parameter
TimeModel
ProbabilityModel
Resource
Stock
Flow
ObservationFunction
Scenario
SimulationRun
ExecutionTrace
ReactionEstimate
```

## Conversation and personal formation structures

```text
ConversationSession
ConversationTurn
ThreadBinding
ReasoningStep
ReasoningMove
ReasoningTrace
ReasoningSignature
ContextState
ContextSwitchEvent
ActiveFieldState
TransformationOperator
ReasoningResult
ReasoningLearningEvent
ResurfacingCandidate
```

---

# Appendix B — Canonical Relation Families

## Structural

```text
part_of
contains
member_of
component_of
constitutes
overlaps
bounded_by
located_in
```

## Dynamic

```text
causes
enables
inhibits
amplifies
dampens
constrains
delays
transforms_into
feeds_back_into
depends_on
```

## Grounding and dependence

```text
grounds
realizes
requires_for_existence
requires_for_identity
emerges_from
```

## Semantic

```text
represents
signifies
expresses
analogous_to
contrasts_with
instantiates_pattern
```

## Epistemic

```text
supported_by
opposed_by
inferred_from
revised_by
retracted_by
uncertain_relative_to
```

## Temporal

```text
precedes
follows
overlaps_in_time
occurs_during
persists_through
```

## Agentive and normative

```text
perceives
believes
intends
values
permits
prohibits
obligates
authorizes
attempts
```

## Trace

```text
derived_from
prompted_by
extends
revises
grounds_claim
compiled_from
validated_by
```

---

# Appendix C — Schema-Lock Decisions Before Production

The following decisions must be made before implementation is considered production-ready:

1. stable ID format and identity merge policy;
2. exact branch-inheritance and retraction semantics;
3. four-valued support representation;
4. contradiction and negation model;
5. formal kernel type hierarchy;
6. Scope serialization and comparison;
7. vocabulary namespace governance;
8. ShapeCore derivation and hashing;
9. abstraction-contract language;
10. ValenceAssessment and SalienceAssessment schemas;
11. ExecutableModelIR type and unit system;
12. rule conflict and scheduling semantics;
13. simulation-output evidence policy;
14. provenance dependency invalidation;
15. privacy and cross-user merge rules;
16. runtime adapter capability contract;
17. evaluation-result schema;
18. bounded-view cost and depth policy.
19. ProfileDefinition versioning and dependency rules;
20. BranchMembership cardinality and visibility semantics;
21. StateCommitment authority and reversal semantics;
22. orthogonal maturity, epistemic, and governance lifecycles;
23. Field differentiation and Formation stability criteria;
24. ConversationTurn attribution and generated-output boundaries;
25. ThreadBinding isolation and reintegration protocol;
26. ContextState transition and rollback semantics;
27. ActiveFieldState budget and source-layer rules;
28. ReasoningMove and TransformationOperator registries;
29. durable ReasoningSignature evidence thresholds and reset policy;
30. ResurfacingCandidate expiry, dismissal, and promotion policy.

---

# Appendix D — Minimum Viable Test Dataset

The first evaluation dataset should include:

1. one ambiguous thought that should remain held;
2. one object with two competing identity interpretations;
3. one State and a false Agent Claim about it;
4. one explicit logical contradiction;
5. one apparent contradiction resolved by temporal Scope;
6. one object with three dimensional Shapes;
7. one cross-dimensional feedback loop;
8. one ambivalent ValenceField;
9. one subsystem and whole-system Shape recurrence;
10. one seductive but invalid cross-domain match;
11. one incomplete TransformationProcess;
12. one Agent with restricted observation;
13. one descriptive causal model that must fail compilation;
14. one valid executable model with complete trace;
15. one simulation output that must not be accepted as empirical evidence.
16. one branch-neutral source used by two incompatible interpretations;
17. one supported Claim that still requires explicit StateCommitment;
18. one structurally mature but epistemically contested record;
19. one unresolved Field that must not be prematurely differentiated;
20. one Formation stabilized only for a declared purpose;
21. one conversation with a corrected ReasoningTrace;
22. one sidecar that remains isolated until explicit reintegration;
23. one workspace switch with reversible ContextSwitchEvent;
24. one global-retrieval candidate rejected because workspace evidence dominates;
25. one apparent ReasoningSignature based on too little evidence and therefore rejected;
26. one incognito conversation that produces no durable learning;
27. one resurfacing candidate that is dismissed and does not recur without new evidence.

---

# Appendix E — Definition of Done for the Foundation

The foundation is complete enough for product construction when:

- the twelve kernel concepts have formal machine-readable definitions;
- ProfileDefinition, BranchMembership, and StateCommitment have formal machine-readable definitions;
- kernel, profile, workspace vocabulary, and application projection boundaries pass conformance tests;
- branch and contradiction semantics pass adversarial tests;
- State, Claim, Perspective, and execution remain structurally separate;
- every record has provenance and applicable maturity, epistemic, and governance statuses;
- local vocabularies can coexist with shared mappings;
- ShapeCore and ShapeView can be derived reproducibly;
- multidimensional and scale-recursive composition works on bounded examples;
- valence remains perspective-indexed and cannot affect execution without a rule;
- transformations support phases, invariants, failures, and topology mutation;
- Agents receive bounded GroundingPackets;
- the compiler can produce both valid IR and principled abstention;
- one runtime adapter executes a traced scenario;
- simulation outputs remain epistemically isolated from empirical evidence;
- user corrections invalidate dependent structures predictably;
- unresolved Fields can remain held and Formations can stabilize for a bounded purpose;
- ConversationTurns, ReasoningSteps, prompts, and corrections preserve exact attribution;
- sidecars remain isolated until explicit provenance-preserving reintegration;
- ContextState and ActiveFieldState enforce session, workspace, user, and global boundaries;
- personalization resists one-turn inference and supports inspection, expiry, and reset;
- resurfacing candidates remain provisional, dismissible, and protected from self-confirmation;
- the system remains usable without exposing the ontology directly.

---

# Appendix F — Historical Framework Migration Map

Historical framework names are migration sources, not runtime layers.

| Historical concept | Canonical destination |
|---|---|
| MTSF ThoughtField | Field profile over SourceFragments, unresolved records, pressures, and tensions |
| MTSF IdeaEntity / SubEntity | Referent plus typed structural RelationInstances and Scope-relative systemhood |
| MTSF Assertion / EvidenceSpan | Claim, Evidence, SourceFragment, and Provenance |
| MTSF Shape / CandidateShape | ShapeCore plus ShapeRecord lifecycle |
| MTSF Stencil | Pattern plus AbstractionContract |
| MTSF ActivationContext | ContextState, Scope, Perspective, and BoundedView |
| MTSF actualization | Formation, application output, or compiled execution depending on purpose |
| ThoughtShape Dimension / Station / Facet | SemanticAddress coordinates governed through TypeDefinitions |
| ThoughtShape StateClaim | State, Claim, Evidence, ValenceAssessment, SalienceAssessment, and Scope |
| ThoughtShape ThoughtShape | ShapeCore, ShapeView, and CompositeShape |
| ThoughtShape Hold | Hold operation in the Field and Formation Profile |
| ThoughtShape Lens / Frame | Perspective, ShapeView, ContextState, and application projection |
| SDS State / Entity / Relation | State, Referent, and RelationInstance |
| SDS constraint / absence / bottleneck | typed State, RelationInstance, Tension, or Mechanism condition |
| SDS movement signature | TransformationShape or Pattern |
| SDS feedback loop | TransformationProcess and dynamic RelationInstances |
| SDS anti-match | AntiMatch |
| SDS transfer ledger | AlignmentProposal, TransferAssessment, Evidence, and Provenance |
| ReasoningStep capture | Conversation and Personal Formation Profile |
| ReasoningSignature | Pattern over ReasoningTraces with conservative evidence rules |
| IdeaWorld | bounded Formation or CompositeShape selected through ContextState |
| Bridge working context | ContextState plus ActiveFieldState |
| Inner Space Curator | application projection over Field, Formation, salience, and revisitation records |
| Community clustering | consent-bound application projection over validated ReasoningSignatures |

Migration MUST preserve original names, source documents, record identifiers where possible, mapping confidence, and semantic-loss warnings. No migration may silently convert an analogy into identity or a Claim into a State.

---

# Appendix G — Reference Implementation Blueprint

## G.1 Package boundaries

The reference implementation SHOULD separate the following owners:

```text
capture_log
record_store
branch_service
provenance_service
vocabulary_registry
profile_registry
field_formation_service
shape_service
transformation_service
pattern_service
conversation_event_service
context_bridge
reasoning_pipeline_service
resurfacing_service
agent_gateway
compilation_service
runtime_adapters
evaluation_service
application_projections
```

Each owner may use several physical components, but only the canonical record and event contracts may cross ownership boundaries.

## G.2 Initial persistent artifacts

The first implementation SHOULD persist:

```text
source_fragments
records
record_events
branch_memberships
state_commitments
provenance
type_definitions
profile_definitions
conversation_sessions
conversation_turns
thread_bindings
reasoning_steps
context_states
context_switch_events
active_field_snapshots
reasoning_results
reasoning_learning_events
```

Shape, Formation, ReasoningTrace, and search indexes MAY begin as reproducible projections. They should be materialized only when reuse or performance justifies it.

## G.3 Write path

```text
1. append SourceFragment or ConversationTurn
2. authorize branch, scope, workspace, and privacy mode
3. create branch-neutral identities where justified
4. attach explicit BranchMembership for interpretations
5. preserve unresolved material as Field or Hold
6. generate candidate Claims and relations with Provenance
7. require StateCommitment before adopting represented States
8. emit dependency and index events
9. materialize bounded projections asynchronously
```

The write path MUST remain valid when all semantic extraction services are unavailable. Raw capture is the irreducible durability boundary.

## G.4 Turn-time reasoning path

```text
1. capture the turn
2. load or create ConversationSession and main ThreadBinding
3. classify ContextState deterministically where possible
4. bind branch, workspace, perspective, and depth mode
5. retrieve a budgeted four-layer context bundle
6. compile ActiveFieldState
7. select a profile-conformant TransformationOperator pipeline
8. produce a probe, Hold, candidate transformation, or answer
9. evaluate source fidelity, ambiguity preservation, and fit
10. persist ReasoningResult and operator trace
11. wait for observable correction before durable learning
```

The hot path SHOULD degrade context depth before delaying the response. It MUST NOT fall back to unbounded global retrieval.

## G.5 Slow path

The slow path MAY:

- derive Shapes and Formations;
- rebuild ReasoningTraces;
- evaluate repeated move sequences;
- compare unresolved Fields under explicit AbstractionContracts;
- generate expiring ResurfacingCandidates;
- invalidate dependent projections after corrections;
- refresh search and graph indexes.

Slow-path outputs remain candidate or model-derived until reviewed or otherwise promoted.

## G.6 API contracts

The first public service contracts SHOULD include:

```text
capture_source(...)
create_branch(...)
attach_branch_membership(...)
commit_state(...)
hold_field(...)
differentiate_field(...)
derive_formation(...)
derive_shape(...)
append_turn(...)
bind_thread(...)
classify_context(...)
switch_context(...)
build_active_field(...)
run_reasoning_pipeline(...)
record_reasoning_feedback(...)
propose_resurfacing(...)
compile_model(...)
execute_model(...)
trace_provenance(...)
```

Every mutating contract MUST return created record identifiers, branch and scope, provenance, validation results, and rollback or compensating-operation information.

## G.7 Test strategy

Testing proceeds in five layers:

1. **Schema tests:** record, profile, branch, lifecycle, and expression validation.
2. **Invariant tests:** property-based and adversarial tests for provenance closure, branch isolation, StateCommitment, context isolation, and execution barriers.
3. **Golden semantic cases:** the minimum dataset in Appendix D with explicit expected Holds, branches, AntiMatches, abstentions, and corrections.
4. **Continuity tests:** multi-turn and multi-session tests verifying thread binding, sidecar isolation, context switching, personal-pattern thresholds, and resurfacing behavior.
5. **End-to-end trace tests:** source-to-Shape, source-to-reasoning-result, and source-to-execution paths with complete provenance and dependency invalidation.

No aggregate quality score may conceal failure of a load-bearing invariant.

## G.8 Deployment sequence

Each phase in Section 30 SHOULD ship behind explicit conformance gates. A later profile or application MUST NOT become canonical merely because its UI is complete. Production promotion requires:

```text
schema lock
→ migration fixtures
→ invariant tests
→ bounded evaluation corpus
→ observability and rollback
→ privacy review where personal records are involved
→ limited release
→ correction analysis
→ scoped promotion
```
