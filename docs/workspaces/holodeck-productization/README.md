# Holodeck Productization — Local-First

This workspace turns the repository's proven coordination primitives into a reusable, self-hosted product for autonomous development in arbitrary repositories.

## Product thesis

Holodeck is a durable control plane for bounded autonomous development. It retains intent, scope, claims, evidence, verification, recovery, and the next safe action across agents, machines, and time.

The first release is local-first and self-hosted. It must work without a hosted control plane, while preserving an explicit approval boundary for high-risk actions.

## Initial decisions

- Product metaphor: **Holodeck**.
- Technical core: a generic **Workspace Runtime**.
- Deployment posture: local-first and self-hosted.
- Product promise: autonomy without losing control; never autonomy without escalation.

## Initial workstreams

1. Establish the reusable core boundary and migration strategy from the current Holodeck and workspace systems.
2. Define the arbitrary-repository installation and discovery experience.
3. Validate a real pilot, including safety and recovery behavior.

## Authority

- Semantic authority: this README and linked evidence.
- Coordination authority: the live workspace service for `holodeck-productization`.
- Git projections: this directory and its generated continuity export.

Read the universal [workspace protocol](../WORKSPACE-AGENT-PROTOCOL.md) before claiming work.
