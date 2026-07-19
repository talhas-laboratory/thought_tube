# Active Neighborhood — Modular Disclosure

## Where you are

```text
Inner Space / Inner World
  canonical source and Shape systems (external dependencies)
    versioned retrieval projections
      cognitive aperture disclosure service (this workspace)
        Bridge and Holodeck adapters first
```

## Default grant

### Concepts

- orient / effective grant / evidence / receipt;
- admission versus ranking;
- execution versus audit;
- corpus readiness and explicit abstention;
- candidate versus canonical Shape;
- whole-block deterministic budgets;
- adapter conformance.

### Files

- this workspace boot, ADRs, design, gap map, workboard gates/decisions;
- active task packet;
- only the owner modules named by that packet.

## External dependency neighborhoods

| Neighbor | Relationship | Widen only for |
|---|---|---|
| library/runtime pipeline | supplies corpus revision, fragments, and readiness | CAE-013 contract/fixtures |
| UMF Shape and Semantic Addressing profile | owns canonical Shape projections | CAE-014 read contract |
| legacy `meta_layer` Shape signatures | provisional candidate source | CAE-014 adapter/migration |
| knowledge layer | candidate and evidence retrieval projection | CAE-001/005A |
| reasoning bridge | state, grant, and Bridge adapter | CAE-003A/B, 004, 005A |
| Holodeck | second adapter and parity consumer | CAE-005B |
| feed/task pack | later consumers | Stage D only |
| kernel bounded view | optional epistemic backend (wired via `BoundedViewEpistemicPort`, default off) | CAE-011 complete; surface opt-in only |

## Out of neighborhood

- new ingestion pipelines or vector databases;
- canonical ontology or Shape profile redesign;
- World Studio canon semantics;
- learned rerankers or activation steering;
- feed/mobile UI redesign;
- hosted multi-tenant infrastructure.

## Widen rules

- Widen one dependency at a time and name the required port or invariant.
- Return to the disclosure boundary after the contract is understood.
- Do not modify external owner modules unless the active task and engineering guard explicitly include them.
- When a dependency is unavailable, record `not_ready` behavior; do not emulate it inside the aperture.

## Self-check

Before editing, answer:

1. Is this task about disclosure or an external dependency?
2. What positive signal admits a candidate?
3. Can the execution object represent omitted content?
4. What happens when corpus/Shape readiness is absent?
5. Which exact gate proves the task complete?
