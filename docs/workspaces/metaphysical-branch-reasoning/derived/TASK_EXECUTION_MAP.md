# Branch Reasoning — Task Execution Map

| Task | Start only when | Work in order | Deliverable and exit evidence |
|---|---|---|---|
| BRANCH-001 | Kernel contract/fixtures inspected | 1. Extract §7 obligations. 2. Define input/output records. 3. Write outcome tables. 4. State absence/abstention behavior. 5. Identify smallest owner module. | Versioned branch contract with tables for inheritance, support, conflict, merge, and inference. |
| BRANCH-002 | BRANCH-001 accepted; Kernel G3 contract available | 1. Implement inheritance read logic. 2. Implement support matrix. 3. Enforce branch/scope compatibility. 4. Add retraction/replacement tests. 5. Verify source reuse. | Tested semantics for all four support values and isolation behavior. |
| BRANCH-003 | BRANCH-002 passes | 1. Create merge assessment. 2. Classify conflict. 3. Define inference request filters. 4. Emit candidate output/provenance. 5. Test abstention. | No-winner merge and no-silent-promotion inference behavior. |
| BRANCH-004 | BRANCH-003 evidence exists | 1. Attack cross-branch leakage. 2. Test false contradictions. 3. Test `both`. 4. Test bounded traversal. 5. Save minimized regressions. | Adversarial suite and evidence that contradictions do not explode. |
| BRANCH-005 | G4 passes and consumer contract targets named | 1. Freeze version. 2. State Kernel version. 3. Publish examples. 4. State limitations. 5. Capture consumer test/SHA. | Versioned dependency contract for Vocabulary and later profiles. |

Do not begin runtime coding merely because a useful data structure seems obvious. The value of BRANCH-001 is forcing every downstream consumer to rely on the same semantics.
