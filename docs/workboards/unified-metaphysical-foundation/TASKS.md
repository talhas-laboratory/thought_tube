# Tasks

| id | status | owner | title | gate |
|---|---|---|---|---|
| `TASK-001-lock-kernel-contracts-and-lifecycles` | blocked | cursor-cloud-agent | Lock kernel contracts and lifecycles | implementation |
| `TASK-002-build-historical-and-current-migration-fixtures` | blocked | cursor-cloud-agent | Build historical and current migration fixtures | implementation |
| `TASK-003-implement-phase-1-foundation-vertical-slice` | blocked | cursor-cloud-agent | Implement Phase 1 foundation vertical slice | implementation |
| `TASK-004-build-profile-registry-and-conformance` | blocked | cursor-cloud-agent | Build profile registry and conformance | implementation |
| `TASK-005-prove-application-sdk-with-two-consumers` | blocked | cursor-cloud-agent | Prove application SDK with two consumers | implementation |

Status values: `backlog`, `ready`, `in-progress`, `review`, `blocked`, `done`.
A task may enter `done` only when every required gate in `GATES.md` has evidence.

Audit alignment: the Phase 1 candidate branch contains work for all five tasks,
but the chain is blocked pending live-ledger reconciliation (Gap 2). Gap 1 code
repair is on branch `cursor/metaphysical-kernel-contracts-423a`.

**Local agent start:** [`LOCAL-AGENT-BOOT.md`](./LOCAL-AGENT-BOOT.md)
