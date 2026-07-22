# Execution handoff — Cognitive Aperture

## Fresh-agent boot

1. Read `AGENT_BOOT.md`, `GAP_MAP.md`, `REMEDIATION_GAP_OVERVIEW.md`, ADR-002, this file, then the selected leaf packet.
2. Query live coordination; never trust a projected `Status:` alone.
3. Refresh the overview and pass the engineering guard using only the task's listed paths.
4. Run the task's baseline command before editing; record exact output and the corpus revision.

## Current verified substrate

Corpus `cognitive_aperture_chat_converter_v1`: 20 sources / 6,611 chunks. The completed pipeline has 1,069 analysis units, 454 legacy Shape signatures, a 55-node / 18-edge Shape graph, 68 bubbles, and 5,540 knowledge nodes. These are derived retrieval artifacts, not framework-canonical Shapes and not a vector index. The known near-neighbour regression is recorded in `CHAT_CONVERTER_SEED_CORPUS_V1.md`.

## Implementation map

| Leaf | Smallest starting surface | Required fixtures / proof |
| --- | --- | --- |
| CAE-013 | `library_tracker.py`, `runtime_pipeline.py`, `tests/test_conversation_os.py` | versioned catalog fixture; ready/empty/stale/interrupted/unsupported cases |
| CAE-014 | framework Shape SDK + `meta_layer.py`; adapter tests | canonical unavailable, legacy candidate, AntiMatch, branch/scope/boundary preservation |
| CAE-015 | `models.py`, focused contract tests | JSON fixtures for every public contract/status; compatibility and unrepresentable-suppression tests |
| CAE-006A | `tests/` + `derived/baselines/` | machine-readable corpus-revision baseline; retain the known near-neighbour failure |
| CAE-002 | `chat_backends.py`, `reasoning_bridge.py`, `models.py` | unique suppression sentinel absent from every backend request; receipt reconstruction |
| CAE-003A | `models.py`, `reasoning_bridge.py` | full open/bounded/strict/incognito × deny/pin/persistence matrix |
| CAE-001 | `knowledge_layer.py`, candidate adapter | positive, negative, distractor, stale and shadow-decision fixtures; rollback flag |
| CAE-003B | disclosure budget owner selected by guard, bridge projection | deterministic whole-block allocation and insufficient-budget cases |
| CAE-004 | `reasoning_bridge.py`, `chat_backends.py` | strict ordering, no-evidence coherence, second-grant widening tests |
| CAE-005A | new service only after guard; `reasoning_bridge.py` adapter | storage-port contract and Bridge parity corpus fixtures |
| CAE-005B | `holodeck.py` adapter | same request → same decision as Bridge |
| CAE-007/008 | receipt/state owner selected by guard | reconstructibility, retention, incognito and transition fixtures |
| CAE-006B | shared service tests + `derived/baselines/` | Shape distractor, AntiMatch, latency/bytes/expansion report |
| CAE-009–012 | named surface module only after Stage C | per-adapter parity, feature flag, rollback and ownership evidence |

## Mandatory commands

```bash
python tools/conversation_os.py repo-overview refresh
python tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "..."
pytest -q tests/test_conversation_os.py
python tools/conversation_os.py inner-world runtime-status
python tools/conversation_os.py inner-world library-status
```

For every task, add a focused pytest command, expected positive and negative result, fixture revision/hash, changed paths, flag/rollback operation, and residual risk to the live task before review. A task without those fields is not ready to claim.

The post-implementation audit found release-blocking gaps despite the projected `done` states. Treat `REMEDIATION_GAP_OVERVIEW.md` as the remediation specification and query live coordination before changing any task status.
