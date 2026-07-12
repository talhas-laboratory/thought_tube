# Task Pack — Unified Metaphysical Foundation Schema Lock

- request: Extract and lock the first machine-readable contracts from the canonical version 1.1 framework
- task_type: foundation_schema_lock
- domain_overlays: ontology, epistemics, governance, storage, validation

> **Canonical copy:** [`context/task_packs/unified-metaphysical-foundation-schema-lock.md`](../../../../context/task_packs/unified-metaphysical-foundation-schema-lock.md)  
> **Canonical authority:** [`sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md`](../sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md)
> **Live coordination:** `python3 tools/workspace_coordination.py context --workspace-id unified-framework-synthesis --agent-id <agent> --surface <surface> --session-id <session>`

## Primary continuity surface

| Artifact | Path |
|----------|------|
| **Full agent workspace** | `docs/workspaces/unified-framework-synthesis/README.md` |
| **Canonical paper** | `docs/workspaces/unified-framework-synthesis/sources/thought-tube-unified-metaphysical-modeling-framework-v1.1.md` |
| Build sequence | `docs/workspaces/unified-framework-synthesis/derived/foundation-build-plan.md` |
| Current handoff | `docs/workspaces/unified-framework-synthesis/derived/handoff.md` |
| Migration evidence | `docs/workspaces/unified-framework-synthesis/sources/` and `analyses/` |

## Thread summary

1. Historical MTSF, SDS, and ThoughtShape work was compared and decomposed.
2. Conversation, personal formation, bridge, curation, and community extensions were added.
3. The material was consolidated into version 1.1 of one universal metaphysical modeling framework.
4. Version 1.1 replaces the old framework stack with a kernel → profiles → applications architecture.
5. The workspace has moved from synthesis into foundation schema lock.

## Locked decisions

- Version 1.1 is normative.
- The twelve kernel concepts remain the universal semantic foundation.
- The first implementation uses the eight-record MVP plus `BranchMembership` and `StateCommitment`.
- Maturity, epistemic standing, and governance are separate lifecycles.
- Profiles compose kernel records; applications compose profiles.
- Historical framework documents remain migration evidence.

## Next work (agreed)

1. Define the universal record envelope.
2. Define `SourceFragment`, `Referent`, `Scope`, `State`, `Claim`, `RelationInstance`, `Provenance`, and `ModelBranch`.
3. Define `BranchMembership` and `StateCommitment`.
4. Define the three lifecycle axes and valid transitions.
5. Define `ProfileDefinition` and `ProfileConformanceResult` minimally enough to validate the foundation.
6. Add valid and invalid fixtures for every contract.
7. Stop before persistence services, reasoning pipelines, surfaces, or migrations are implemented.

## Constraints

- Use the live workspace service for claims, runs, blockers, decisions, and verification.
- Refresh `CONTINUITY.md` after live workspace mutations.
- Do not add product-specific fields to the universal kernel.
- Do not implement parallel ontologies or framework-specific stores.
- Do not infer a represented State from a Claim without `StateCommitment`.
- Do not collapse the three lifecycle axes.
- Do not modify historical source documents.
- Do not create runtime services during this task.
- Run `engineering-guard assess` before substantial code changes
- Preserve exact provenance and reversible migration paths.

## Acceptance conditions

- All contracts validate through one deterministic entrypoint.
- Invalid fixtures cover branch leakage, Claim/State collapse, missing provenance, illegal lifecycle combinations, and profile semantic redefinition.
- The codebase overview validates with zero errors and warnings.
- No application or profile behavior is smuggled into the kernel.
- A follow-on task pack can implement Phase 1 without reopening primitive definitions.
