# Systems

Each system should stay independently buildable, testable, and understandable. Cross-system coupling must be explicit in `CONNECTIONS.md`.

| System | Folder | Responsibility | First Contract |
|---|---|---|---|
| Purpose and motion | `subprojects/01-purpose-motion.md` | Track why the user is moving and what kind of transformation is needed. | `PurposeState` |
| Object topology | `subprojects/02-object-topology.md` | Track main spine, sidecars, sub-objects, branches, and reintegration. | `ObjectTopology` |
| Context frames and envelopes | `subprojects/03-context-frames-envelopes.md` | Define reasoning environments and enforce boundaries. | `FrameSpec`, `FrameBundle`, `SessionEnvelope` |
| Capture and promotion | `subprojects/04-capture-promotion.md` | Move material from raw evidence to reviewed durable memory. | `PromotionPolicy` |
| Correction and reversibility | `subprojects/05-correction-reversibility.md` | Make correction, discard, split, merge, rollback, and demotion first-class. | `CorrectionEvent` |
| Lens layer | `subprojects/06-lens-layer.md` | Provide bounded domain models with schemas, evaluators, and packet templates. | `LensPack` |
| Evaluators and gates | `subprojects/07-evaluators-gates.md` | Verify semantic behavior, quality, safety, and done-ness. | `SemanticGate` |
| Agent work coordination | `subprojects/08-agent-work-coordination.md` | Turn context into scoped multi-agent work with task gates and handoffs. | `WorkPacket` |
| Temporal staleness | `subprojects/09-temporal-staleness.md` | Track freshness, conflict, last verification, and outdated context risk. | `FreshnessRecord` |
| Surface adapters | `subprojects/10-surface-adapters.md` | Adapt the same substrate to Codex, OpenClaw, miniapp, mobile, and future tools. | `SurfaceProfile` |
| Shared workspace framework | `subprojects/11-shared-workspace-framework.md` | Bind product folders, Holodecks, workboards, task packs, sessions, and artifacts into one explicit coordination stack. | `WorkspaceBinding` |

## Spine Rule

No system should become a hidden second product. Each system must expose:

- one durable contract
- one owner module or doc packet
- one test strategy
- one integration point with the bridge spine
- one failure mode it explicitly handles
