# T10-00 Reconciliation Matrix

**Workspace:** `unified-framework-synthesis`  
**Task:** `UMF-T10-00-INTEGRATION-BASELINE`  
**Author:** `cursor-cloud-a790`  
**Date:** 2026-07-22  
**Purpose:** Make “implemented” mean one checkout by declaring code authority and dispositions for the two load-bearing remotes.

## Declared integration authority

| Role | Value |
|---|---|
| Coordination / task branch (this PR) | `cursor/t10-wave-01-tasks-a790` |
| **Recommended code spine** | `origin/cursor/shape-intelligence-remediation-pass` @ `0c8f367a0e8d85d703f572493b9d8e9c02ae4349` |
| **Population import source** | `origin/codex/shape-population-production-hardening` @ `82a1c3589caf9fa743dbf67ba024b1c360649bfa` |
| Common ancestor with `main` | `55430a43aea85debea7274c61361a016db2b8b2e` (`origin/main` tip at audit) |
| Semantic authority | Unified Metaphysical Modeling Framework v1.1 |
| Coordination authority | live workspace API (`unified-framework-synthesis`) |

**Decision:** merge order is `main` → remediation-pass (spine) → Population hardening (import).  
Do not treat either remote alone as the Wave 1 release checkout.

## Remote inventory

### A. `cursor/shape-intelligence-remediation-pass` (86 commits ahead of main)

**Keep / merge (code + tests)**

| Path family | Disposition | Notes |
|---|---|---|
| `src/conversation_os/candidate_admission.py` | **merge** | Fail-empty admission |
| `src/conversation_os/disclosure_budget_allocator.py` | **merge** | Deterministic budgets |
| `src/conversation_os/orient_first_compose.py` | **merge** | Orient-first compose |
| `src/conversation_os/shape_projection_reader.py` | **merge as spine default** | Still points at legacy `profile:shape_and_semantic_addressing` — T10-01 repairs to `profile:shape` |
| `src/conversation_os/disclosure_*.py`, `evidence_resolver.py`, `*_disclosure_adapter.py` | **merge** | Disclosure stack |
| `src/conversation_os/active_state_continuity*.py` | **merge** | Present but rollout flags stay off until T10-08 |
| `src/conversation_os/aperture_*.py`, `*_certification_harness.py`, `corpus_catalog_snapshot.py` | **merge** | Certification / catalog |
| `src/conversation_os/metaphysical_kernel_profile_registry.py` | **merge** | Adds contract-only Quality/Composition/Role/`profile:shape`/Cybernetics builders |
| `src/conversation_os/reasoning_bridge.py`, `bridge_controller.py`, `knowledge_layer.py`, `holodeck.py`, `product_inner_world.py`, … | **merge** | Wire-up for aperture |
| `tests/test_*admission*`, `test_disclosure_*`, `test_orient_*`, `test_shape_*`, `test_aperture_*`, fixtures | **merge** | Focused CAE suite reported green (132 tests) on remediation |
| `product/inner_world_v1/config/runtime.json` disclosure block | **merge** | Keep rollout flags **legacy/off** (T10-08 owns activation) |
| `docs/workspaces/cognitive-aperture-exceptional/**` | **merge** | Aperture planning + integration status |
| `docs/workspaces/unified-framework-synthesis/derived/TEN_OUT_OF_TEN_GAP_PROGRAM.md` | **merge** | Already restored on this task branch |
| Shape Intelligence child workspace docs | **merge** | Continuity projections; not runtime |
| Personal cognitive exoskeleton docs | **merge** | Unrelated product catalog; keep as docs only |

**Supersede / defer**

| Item | Disposition | Notes |
|---|---|---|
| Enabling `persistent_receipts_v1` / `active_state` / bounded-view / metrics flags | **defer to T10-08** | Code merges; flags stay disabled |
| `shape_projection_reader` canonical profile id | **supersede in T10-01** | Registry already defines `profile:shape`; reader still uses legacy id |

### B. `codex/shape-population-production-hardening` (6 commits ahead of main)

**Keep / merge (code + tests + tools)**

| Path family | Disposition | Notes |
|---|---|---|
| `src/conversation_os/shape_population/**` | **merge** | Hardened Population pipeline |
| `src/conversation_os/source_content_store.py` | **merge** | Content-addressed source bytes |
| `src/conversation_os/vault_ingest.py` | **merge** | Enqueue / receipt hooks |
| `tools/run_shape_population_worker.py` | **merge** | Worker entrypoint |
| `tools/provision_shape_population_openclaw_agents.py` | **merge** | Identity provisioning |
| `product/inner_world_v1/config/agent_configs/shape_population_*.json` | **merge** | Four role configs |
| `tests/test_shape_population_*.py` + fixtures | **merge** | Independent Population suite (reported 59 focused tests on source branch) |
| Shape Intelligence Population workboard/docs updates | **merge** | Prefer Population branch versions where SIP task status is newer |

## Overlap conflict surfaces (both remotes touch)

| Path | Disposition | Resolution rule |
|---|---|---|
| `product/inner_world_v1/config/runtime.json` | **merge both** | Start from remediation (disclosure block + disabled flags). Add Population `agents.shape_population` block from Population remote. Do not enable disclosure rollout flags. |
| `product/inner_world_v1/config/runtime.sample.json` | **merge both** | Same as runtime.json |
| `src/conversation_os/shape_projection_reader.py` | **prefer remediation spine** | Files appear equivalent at headers; take remediation copy, then T10-01 rewrites profile id. Reject inventing a third reader. |
| `docs/workspaces/shape-intelligence-*/**` and SIP workboard files | **prefer Population for population continuity; prefer remediation for sibling SI docs if newer** | Docs only; never block code merge |
| `docs/workspaces/INDEX.md` | **union** | Preserve all workspace entries |

## Explicit rejects

| Item | Disposition | Why |
|---|---|---|
| Blind `git add -A` of either remote including runtime data / locks | **reject** | Staging hazard |
| Treating Population-only checkout as Wave 1 baseline | **reject** | Missing aperture stack |
| Treating remediation-only checkout as Wave 1 baseline | **reject** | Missing live `shape_population/` path |
| Enabling production disclosure flags during T10-00 | **reject** | Belongs to T10-08 |
| Collapsing `profile:shape` contracts into legacy `profile:shape_and_semantic_addressing` | **reject** | T10-01 owns the cutover |

## Required same-checkout verification (after merge)

```bash
. .venv/bin/activate
# Aperture / CAE focused suite from remediation
PYTHONPATH=src python -c "from pathlib import Path; from conversation_os.aperture_release_gate import run_focused_suite; r=run_focused_suite(Path('.')); print(r)"
# Population focused suite
pytest tests/test_shape_population_*.py tests/test_source_content_store.py -q
# Foundation / release
pytest tests/test_release_management.py tests/test_metaphysical_kernel_runtime.py tests/test_metaphysical_kernel_profile_registry.py -q
```

Release manifest must list: commit, branch, artifact fingerprints, and version slots for schema/profile/prompt/model/policy/migration/flag/corpus/benchmark revisions (see `release_management.py`).

## Exit criteria for T10-00

1. This matrix accepted in live decision/verify records.
2. One integration checkout contains both aperture modules and `shape_population/`.
3. Combined focused suites run from that checkout.
4. `build_release_manifest()` emits the extended version block.
5. No remaining “works only on the other branch” claim for Wave 1 code.

## Follow-on (not T10-00)

- T10-19: manifests for imported modules + hermetic/live split
- T10-01: cut reader/SDK to `profile:shape`
- T10-02/03: canonical mapping + live ingest worker path
- T10-08: staged disclosure activation
