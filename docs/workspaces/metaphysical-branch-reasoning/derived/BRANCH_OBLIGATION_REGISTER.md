# Branch Reasoning — Obligation Register

| Area | Atomic obligation | Deliverable | Minimum test |
|---|---|---|---|
| §7.1 | Multiple interpretations share identity/provenance without one belief set | Branch domain boundary | Same referent/source in competing branches without duplication |
| §7.2 | Parent inheritance is a read rule; child may retract, replace, conflict, or change assumptions/scope | Inheritance resolver | Inherited, retracted, replaced, and locally asserted records |
| §7.3 | Support is four-valued within branch and scope | Support assessment contract | All four values with scoped evidence |
| §7.4 | Negation is explicit; apparent conflict has a typed classification | Conflict model | Scope/time/perspective divergence does not become false logical contradiction |
| §7.5 | Merge reports compatibility and uncertainty without winner selection | Merge assessment | Two conflicting claims remain unresolved after merge |
| §7.6 | Inference input is declared; output is candidate with provenance; `both` has a safe policy | Inference request/result | Preserve, branch, clarify, and abstain cases |
| §7.7 | Ensembles are task-relative weighted branches | Ensemble contract | Weight provenance and no universal probability inference |
| §20 | Every traversal is scoped and bounded | Branch-aware view integration | Depth/boundary limit prevents leakage |
| §27.2 | Contradictory branches remain valid | Acceptance fixture | Contradiction does not imply unrelated claim |
| §27.16 | Branch-neutral sources are reusable | Acceptance fixture | Shared source identity across branch-local claims |

## Contract checklist

For every new public type or operation document: required Kernel types, scope compatibility rule, branch visibility/read rule, provenance requirements, lifecycle filters, conflict/absence behavior, serialization form, version, consumer, and test fixture. A method that merely returns records is insufficient unless it says why those records are usable in the requested branch and scope.
