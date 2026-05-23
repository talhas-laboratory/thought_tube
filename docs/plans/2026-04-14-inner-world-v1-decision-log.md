# Inner World v1 Decision Log

Date: 2026-04-14
Status: review

This file is the working decision ledger for the v1 build.

## Locked Decisions

- D-001
  Decision:
  Inner World v1 is one product with one core loop and multiple domain overlays.
  Why:
  The conversation repeatedly resolves toward a shared substrate with domain specialization through overlays, not separate product branches.
  Source:
  `session_synthesis.md`, `decision_attachments.md`, `PRODUCT_THESIS.md`

- D-002
  Decision:
  OpenClaw is the substrate and wiring backend, not the product identity.
  Why:
  The conversation explicitly resolves this and also rejects forcing a separate environment.
  Source:
  `decision_attachments.md`

- D-003
  Decision:
  Inner World installs into the existing OpenClaw workspace when possible.
  Why:
  Lower friction, better privacy posture, and consistency with the resolved installation guardrail.
  Source:
  `decision_attachments.md`

- D-004
  Decision:
  The primary UI is a personal self-social thought feed.
  Why:
  The UI should feel like social media for yourself by yourself, with compact thought posts as the first surface.
  Source:
  user review input on 2026-04-14, `session_synthesis.md`

- D-005
  Decision:
  Each thought expands from a short post into a substack-like article view.
  Why:
  The short thought should stay lightweight until the user chooses to open the full explanation.
  Source:
  user review input on 2026-04-14

- D-006
  Decision:
  Each expanded thought has its own scoped chat thread.
  Why:
  The user must be able to interrogate and develop a thought directly from the thought itself.
  Source:
  user review input on 2026-04-14

- D-007
  Decision:
  Thought chat context is scoped to the selected thought, its source refs, relevant conversations, and reasoning primitives.
  Why:
  The chat should feel thought-native, not like a generic assistant with the whole archive stuffed into context.
  Source:
  user review input on 2026-04-14, `decision_attachments.md`

- D-008
  Decision:
  Saved thought chats are written back into the same conceptual space as new linked source material.
  Why:
  A useful thread should strengthen the library and become part of future context.
  Source:
  user review input on 2026-04-14

- D-009
  Decision:
  Thought chat threads can be deleted without deleting the original thought artifacts.
  Why:
  The user needs reversible conversational exploration without corrupting the base library.
  Source:
  user review input on 2026-04-14

- D-010
  Decision:
  v1 is manually seeded and local-first.
  Why:
  The conversation repeatedly chooses manual vault input over autonomous expansion for the first version.
  Source:
  `session_synthesis.md`, `PRODUCT_THESIS.md`

- D-011
  Decision:
  Reasoning primitives are first-class objects in the system.
  Why:
  The conversation explicitly prefers reasoning-primitives meta-analysis over topic-only organization.
  Source:
  `decision_attachments.md`

- D-012
  Decision:
  User feedback is the primary verification loop.
  Why:
  The conversation rejects low-precision opaque outputs and emphasizes explicit feedback.
  Source:
  `decision_attachments.md`, `inner-world-product-gap-log.md`

- D-013
  Decision:
  The core insight contract is mandatory.
  Why:
  Trust and usefulness depend on every surfaced insight being inspectable and actionable.
  Source:
  `inner-world-product-gap-log.md`, `CONTRACT.md`

- D-014
  Decision:
  v1 domain overlays are `research`, `art`, and `entrepreneurship`.
  Why:
  These are the stable domains repeatedly present in the source conversation and current thesis.
  Source:
  `PRODUCT_THESIS.md`, `session_synthesis.md`

- D-015
  Decision:
  Deferred from v1: social features, autonomous web research, graph-first UI, deep multimodal promise, real-time interruption.
  Why:
  These expand scope without improving the first proof of value.
  Source:
  `inner-world-product-gap-log.md`, `PRODUCT_THESIS.md`

## Working Decisions For Build Execution

- D-016
  Decision:
  Build the product in vertical slices, not by infrastructure layer alone.
  Why:
  This is the fastest way to get to a usable alpha and keep verification honest.
  Status:
  locked for implementation planning

- D-017
  Decision:
  The first usable alpha requires one shared core loop plus one working overlay in each domain.
  Why:
  This proves the product shape without overfitting to a single corpus.
  Status:
  locked for implementation planning

## Open Decisions To Resolve Before Full Build

- O-001
  Decision needed:
  Exact folder layout inside the live OpenClaw workspace.
  Why it matters:
  This determines deployment shape and service boundaries.

- O-002
  Decision needed:
  Exact gateway integration contract for Inner World requests and events.
  Why it matters:
  This determines how the miniapp and services communicate.

- O-003
  Decision needed:
  Exact grounded insight threshold.
  Why it matters:
  This determines what can surface safely.

- O-004
  Decision needed:
  Exact v1 miniapp route map and thread state model.
  Why it matters:
  This defines the actual user experience and prevents UI sprawl across feed, article, and thought chat.

- O-005
  Decision needed:
  Exact metric event model for accepted, dismissed, and revisited insights.
  Why it matters:
  This determines whether quality can be measured honestly.

## Decisions To Make During Build, Not Before

- B-001
  Decision:
  Final ranking weight values for evidence, novelty, usefulness, and surprise.
  Why deferred:
  These should be tuned against fixtures and real use, not guessed in advance.

- B-002
  Decision:
  Overlay-specific heuristic weights.
  Why deferred:
  These should come from fixture behavior and user review.

- B-003
  Decision:
  Whether Neo4j is needed for v1 or deferred.
  Why deferred:
  Use it only if flat-file state and lightweight derivation stop being sufficient.

## Decision Logging Rule

When a new build decision is made:

1. add it here with a stable id
2. classify it as `locked`, `open`, or `deferred`
3. write the reason in one short paragraph
4. point back to the source artifact or implementation proof
