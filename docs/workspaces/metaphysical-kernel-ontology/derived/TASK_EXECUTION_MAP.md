# Kernel Ontology — Task Execution Map

| Task | Start only when | Work in order | Deliverable and exit evidence |
|---|---|---|---|
| KERNEL-001 | Live status is `ready`; parent/kernel source read | 1. Extract atomic obligations. 2. Compare against Phase 1 modules/fixtures. 3. Identify gaps/deferrals. 4. Draft public contract. 5. Record ambiguity as decision. | Obligation matrix, contract version, no duplicate owner, targeted validator/fixture plan. |
| KERNEL-002 | KERNEL-001 contract accepted | 1. Choose source family/edge case. 2. Preserve raw source and identity. 3. Map only justified kernel records. 4. Emit loss/defer warnings. 5. Add valid/invalid fixtures. | Migration result plus fixture evidence for identity, provenance, commitments, and losses. |
| KERNEL-003 | Contract behavior and migration impact known | 1. Identify existing owner module. 2. Run guard. 3. Add smallest operation. 4. Thread provenance/validation. 5. Exercise end-to-end slice. | Bounded runtime operation, test, and no product-specific field/store. |
| KERNEL-004 | KERNEL-002/003 evidence exists | 1. Map each invariant to test. 2. Add adversarial cases. 3. Run focused suite. 4. Run foundation review. 5. Document limits. | Passing commands, fixture inventory, invariant coverage, residual-risk statement. |
| KERNEL-005 | G4 passes and consumers are known | 1. Freeze version. 2. Write compatibility/migration note. 3. Update dependency contracts. 4. Obtain consumer smoke proof. 5. Record SHA. | Versioned release packet usable by Branch/Vocabulary without private assumptions. |

For every task: claim and update state through the live API, not by editing `Status:` in the task packet. After any live mutation, publish/check projections and push the intentional result.
