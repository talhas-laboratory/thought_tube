# Vocabulary Governance — Task Execution Map

| Task | Start only when | Work in order | Deliverable and exit evidence |
|---|---|---|---|
| VOCAB-001 | Kernel and Branch dependency contracts read | 1. Extract §8/§22 obligations. 2. Define levels and records. 3. Specify mapping kinds. 4. Write promotion/evolution rules. 5. Record unresolved semantic questions. | Public governance contract that preserves source terms and branch context. |
| VOCAB-002 | VOCAB-001 accepted; Kernel G3 available | 1. Reuse `TypeDefinition` where possible. 2. Add focused registry/mapping owner if guard approves. 3. Preserve raw values. 4. Scope reads. 5. Add mapping fixtures. | Type registry/mapping behavior with no destructive substitution. |
| VOCAB-003 | VOCAB-002 passes; Branch contract available for local terms | 1. Implement proposal/review decision. 2. Version changes. 3. Identify affected records. 4. Plan reversible migration. 5. Mark stale dependents. | Promotion and evolution workflow with provenance and impact report. |
| VOCAB-004 | VOCAB-003 evidence exists | 1. Test mapping kinds. 2. Test scope/branch locality. 3. Test failed promotion. 4. Test kernel-redefinition rejection. 5. Test deprecation migration. | Adversarial conformance suite and fixture corpus. |
| VOCAB-005 | G4 passes and consumers are named | 1. Freeze version. 2. Publish mapping/promotion API. 3. State compatibility. 4. Provide profile/application example. 5. Capture SHA. | Versioned vocabulary dependency contract for profiles and products. |

A term that cannot be safely promoted is not a failed term. Preserve it at the right level and scope with its provenance.
