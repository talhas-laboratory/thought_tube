# Mobile Thought Graph Execution Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a mobile-first thought-to-execution bridge where rough brain dumps become durable thought graphs, cross-conversation context, owner-aware workflow routes, and eventually guarded expert-tool execution.

**Architecture:** Start inside the existing Conversation OS development intake path, because it already owns rough idea capture and routing into implementation workflow. The first durable object is a multi-lens `thought_graph` payload attached to a development idea record; later phases split stable logic into its own owner only if the engineering guard confirms the existing owners are insufficient. Execution stays behind approval, task packs, Holodeck/workspace contracts, and provider-specific tool adapters.

**Tech Stack:** Python 3.11, `src/conversation_os`, JSON/JSONL repo-local storage, pytest/unittest, generated module manifests under `context/substrate/modules`, CLI entrypoint `tools/conversation_os.py`.

---

## Current State

The user vision was captured in the live Conversation OS session:

- `session_id`: `session-656215987812`
- `event_id`: `event-14efdfedce5f`
- recorded development idea: `idea-087c48c836c1`
- verification already run after the initial small slice: `336 passed, 1 skipped`

The initial implementation slice already added:

- [src/conversation_os/development_intake.py](/Users/talhauddin/software/inner_space/src/conversation_os/development_intake.py): attaches a `thought_graph` payload to persisted development idea records.
- [tests/test_conversation_os.py](/Users/talhauddin/software/inner_space/tests/test_conversation_os.py): covers multi-lens thought graph persistence.

Important observed limitation:

- `development route --idea-id idea-087c48c836c1` classified the vision as `update_recipe` for `inner_world_v1`, but candidate module ranking over-weighted generic foundation modules such as `kernel.foundation.storage`. Do not use that route as approval-ready implementation guidance until the router scoring is improved.

## Operating Rules

- Do not edit raw event logs.
- Keep source and derived layers separate.
- Run `python3 tools/conversation_os.py repo-overview refresh` before substantial implementation work.
- Run `python3 tools/conversation_os.py engineering-guard assess --request "..." --purpose "..." --proposed-paths "..."` before implementation.
- Use TDD for each behavior change: write the failing test, run it red, implement, run it green.
- Refresh and validate the generated atlas after substantive edits.
- Do not auto-approve proposals or execute external tools from a thought drop.

## Target Architecture

The system should become a staged bridge:

1. **Mobile capture layer:** accepts rough user thought drops from phone, Codex, OpenClaw, Hermes, or future clients.
2. **Conversation source layer:** records every meaningful turn as session events.
3. **Meta commentary layer:** transforms conversations into derived commentary artifacts about what is happening in the conversation, without editing the raw event log.
4. **Thought graph layer:** extracts multiple size lenses from the drop or conversation and links graph nodes to commentary artifacts.
5. **Cross-conversation context layer:** compares the graph and commentary artifacts against concepts, context bubbles, thread abstractions, and prior development ideas.
6. **Workflow routing layer:** turns graph intent into owner-aware implementation routes and task packs.
7. **Bridge state layer:** tracks communication mode, implicit shifts, incoming-flow posture, and tool-routing readiness.
8. **Execution layer:** uses guarded workspaces and tool adapters for Codex, OpenClaw, Blender, Higgsfield, spreadsheets/statistics, or other expert tools.
9. **Feedback layer:** writes outcomes and corrections back into conversation deltas, user expectations, development proposals, and future route scoring.

The size lenses should stay explicit:

- `raw_drop`: preserve exact thought material as source.
- `micro_shift`: sentence or turn-level changes in tone, intent, context, and dynamic.
- `meta_commentary`: derived commentary about interaction dynamics, abstraction moves, implicit requests, uncertainty, and tool-readiness.
- `macro_conversation`: one whole-conversation reading.
- `cross_conversation`: related themes, similar prior conversations, reusable concepts, and differences.
- `workflow_path`: capture, clarify, route, guard, plan, execute, verify, archive.
- `bridge_orchestration`: incoming flow state, communication mode, expert-tool eligibility, and handoff risk.

## File Map

Expected near-term files:

- Modify [src/conversation_os/development_intake.py](/Users/talhauddin/software/inner_space/src/conversation_os/development_intake.py): stabilize thought graph capture on idea records.
- Modify [tests/test_conversation_os.py](/Users/talhauddin/software/inner_space/tests/test_conversation_os.py): add focused regression coverage.
- Modify [context/substrate/modules/assembly.development.development_intake.json](/Users/talhauddin/software/inner_space/context/substrate/modules/assembly.development.development_intake.json): update manifest once the thought graph capture responsibility is accepted.

Expected follow-on files after guard approval:

- Modify [src/conversation_os/development_router.py](/Users/talhauddin/software/inner_space/src/conversation_os/development_router.py): improve route scoring so surface and owner modules beat generic foundation modules.
- Modify [src/conversation_os/cli.py](/Users/talhauddin/software/inner_space/src/conversation_os/cli.py): expose capture and inspection commands once core behavior is stable.
- Possibly create `src/conversation_os/meta_commentary.py`: only after the guard confirms derived conversation commentary deserves a separate owner instead of staying inside `development_intake` or `meta_layer`.
- Possibly create `context/substrate/modules/kernel.analysis.meta_commentary.json`: only if the module is split out.
- Possibly create `src/conversation_os/thought_graph.py`: only after at least two call sites need the same graph builder and the guard approves a new owner.
- Possibly create `context/substrate/modules/assembly.development.thought_graph.json` or `surface.thought_graph.thought_graph.json`: only if the module is split out.

---

### Task 1: Stabilize The Existing Thought Graph Slice

**Files:**
- Modify: `src/conversation_os/development_intake.py`
- Modify: `tests/test_conversation_os.py`
- Modify: `context/substrate/modules/assembly.development.development_intake.json`

- [ ] **Step 1: Inspect the current diff**

Run:

```bash
git diff -- src/conversation_os/development_intake.py tests/test_conversation_os.py
```

Expected: the diff only contains the `thought_graph` payload builder and one focused test around `record_development_idea`.

- [ ] **Step 2: Run the focused test**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_record_development_idea_attaches_multi_lens_thought_graph -q
```

Expected: `1 passed`.

- [ ] **Step 3: Update the development intake manifest**

Add these entries to [context/substrate/modules/assembly.development.development_intake.json](/Users/talhauddin/software/inner_space/context/substrate/modules/assembly.development.development_intake.json):

```json
{
  "contains": [
    "development idea persistence",
    "development proposal persistence",
    "proposal approval records",
    "proposal-backed task pack generation",
    "idea translation orchestration",
    "development signal enrichment",
    "intent kind inference",
    "multi-lens thought graph capture for rough development ideas"
  ],
  "outputs": [
    "development idea records",
    "development proposal records",
    "proposal review records",
    "task packs",
    "technical framing payloads",
    "development signal payloads",
    "thought graph payloads"
  ]
}
```

Keep the rest of the manifest unchanged.

- [ ] **Step 4: Run the relevant regression set**

Run:

```bash
python3 -m pytest \
  tests/test_conversation_os.py::ConversationOSTestCase::test_record_development_idea_persists_translation_and_signals \
  tests/test_conversation_os.py::ConversationOSTestCase::test_record_development_idea_attaches_multi_lens_thought_graph \
  tests/test_conversation_os.py::ConversationOSTestCase::test_build_and_approve_development_proposal_persists_contract \
  tests/test_conversation_os.py::ConversationOSTestCase::test_build_proposal_task_pack_requires_approval_and_links_artifact \
  tests/test_conversation_os.py::ConversationOSTestCase::test_cli_development_flow_records_routes_proposes_and_approves \
  tests/test_conversation_os.py::ConversationOSTestCase::test_cli_development_listing_and_lookup_surfaces_persisted_artifacts \
  tests/test_conversation_os.py::ConversationOSTestCase::test_route_development_idea_prefers_surface_recipe_for_lens_mix \
  -q
```

Expected: `7 passed`.

- [ ] **Step 5: Refresh and validate the codebase overview**

Run:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py repo-overview validate
```

Expected: validation reports `fresh: true`, `error_count: 0`, `warning_count: 0`.

---

### Task 2: Make Thought Graph Shape Inspectable And Stable

**Files:**
- Modify: `src/conversation_os/development_intake.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write a failing test for graph schema stability**

Add a test near the existing development intake tests:

```python
def test_development_thought_graph_schema_is_stable_for_mobile_capture(self) -> None:
    self._write_personal_interface_profile()

    record = record_development_idea(
        self.root,
        "Phone thought: route Codex and OpenClaw into a safe execution bridge.",
        desired_effect="Create a workflow path without executing tools yet.",
        surface_hints=["inner_world"],
        source_session_id="session-phone",
        source_refs=["event-phone"],
    )

    graph = record["thought_graph"]

    self.assertEqual(graph["schema_version"], "1.0")
    self.assertEqual(graph["capture_posture"], "development_intake")
    self.assertIn("cross_conversation", [lens["lens_key"] for lens in graph["size_lenses"]])
    self.assertIn("workflow_routing", graph["dimensions"])
    self.assertIn("mobile_execution", graph["dimensions"])
    self.assertTrue(graph["inspection_hints"])
```

- [ ] **Step 2: Run the test red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_development_thought_graph_schema_is_stable_for_mobile_capture -q
```

Expected: FAIL because `schema_version`, `capture_posture`, `cross_conversation`, or `inspection_hints` are missing.

- [ ] **Step 3: Implement the minimal schema additions**

In `_build_thought_graph_payload`, add:

```python
"schema_version": "1.0",
"capture_posture": "development_intake",
"inspection_hints": [
    "Inspect `nodes` by lens for size-specific readings.",
    "Inspect `dimensions` before routing to avoid generic owner matches.",
    "Inspect `workflow_path` before building a proposal.",
],
```

Add `cross_conversation` to `THOUGHT_GRAPH_SIZE_LENSES`:

```python
{
    "lens_key": "cross_conversation",
    "label": "Cross Conversation",
    "purpose": "Compare the drop against prior themes, concepts, and related conversations.",
},
```

Add one cross-conversation node:

```python
cross_node = _graph_node(
    graph_id,
    "cross_conversation",
    0,
    "Related conversation search",
    "Use development signals, concept matches, context bubbles, and thread abstractions to compare this drop against prior material.",
    ["conversation_analysis"],
)
```

Add an edge from the macro node to `cross_node` with relation `compares_against`.

- [ ] **Step 4: Run the test green**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_development_thought_graph_schema_is_stable_for_mobile_capture -q
```

Expected: `1 passed`.

---

### Task 3: Improve Route Ranking For Thought Graph Ideas

**Files:**
- Modify: `src/conversation_os/development_router.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write a failing router test**

Add:

```python
def test_route_development_idea_prefers_surface_and_analysis_owners_for_thought_graphs(self) -> None:
    idea = {
        "idea_id": "idea-thought-graph",
        "raw_idea": "Mobile Codex brain dumps should become thought graphs with micro and macro conversation lenses.",
        "desired_effect": "Route the idea toward Inner World, development intake, and conversation analysis owners.",
        "intent_kind": "lens_composition",
        "surface_hints": ["inner_world", "personal_interface"],
        "translated_framing": {
            "target_artifacts": ["thought graph", "workflow route", "bridge state"],
            "context_notes": ["mobile execution bridge", "conversation size lenses"],
        },
        "development_signals": {
            "query_tokens": ["thought", "graph", "conversation", "lens", "bridge", "workflow"],
        },
        "thought_graph": {
            "dimensions": ["conversation_analysis", "bridge_orchestration", "workflow_routing"],
        },
    }

    route = route_development_idea(self.root, idea, limit=6)
    module_ids = [target["module_id"] for target in route["candidate_targets"]]

    self.assertEqual(route["route_kind"], "update_recipe")
    self.assertIn("surface.inner_world.product_inner_world", module_ids[:4])
    self.assertIn("assembly.development.development_intake", module_ids[:4])
    self.assertNotEqual(module_ids[0], "kernel.foundation.storage")
```

- [ ] **Step 2: Run the test red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_route_development_idea_prefers_surface_and_analysis_owners_for_thought_graphs -q
```

Expected: FAIL because generic foundation modules currently rank too high.

- [ ] **Step 3: Add thought graph tokens to `_atlas_query`**

In `src/conversation_os/development_router.py`, include:

```python
thought_graph = idea.get("thought_graph", {})
tokens.append(" ".join(thought_graph.get("dimensions", [])))
for lens in thought_graph.get("size_lenses", []):
    tokens.append(str(lens.get("lens_key", "")))
```

- [ ] **Step 4: Boost surface and assembly owners when surface hints exist**

In `rank_module_targets`, after the base `score` is read, compute an adjusted score:

```python
score = int(row.get("score", 0))
layer = str(manifest.get("layer", ""))
module_surfaces = [str(value) for value in manifest.get("surfaces_using", [])]
if surfaces and any(surface in module_surfaces for surface in surfaces):
    score += 12
if module_id in _SURFACE_MODULE_MAP.values():
    score += 8
if module_id == "assembly.development.development_intake":
    score += 8
if layer == "kernel" and module_id in {"kernel.foundation.storage", "kernel.foundation.models"}:
    score -= 10
```

Use `score` in the ranked target payload instead of the raw row score.

- [ ] **Step 5: Sort after adjusted scoring**

After building `ranked`, sort it:

```python
ranked.sort(key=lambda row: (-int(row["score"]), row["module_id"]))
```

- [ ] **Step 6: Run router tests green**

Run:

```bash
python3 -m pytest \
  tests/test_conversation_os.py::ConversationOSTestCase::test_route_development_idea_prefers_surface_recipe_for_lens_mix \
  tests/test_conversation_os.py::ConversationOSTestCase::test_route_development_idea_prefers_surface_and_analysis_owners_for_thought_graphs \
  -q
```

Expected: `2 passed`.

---

### Task 4: Add A CLI Inspection Surface Without Auto Execution

**Files:**
- Modify: `src/conversation_os/cli.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Run the engineering guard**

Run:

```bash
python3 tools/conversation_os.py engineering-guard assess \
  --request "Expose thought graph inspection for recorded development ideas through the CLI." \
  --purpose "Let mobile or hosted operators inspect a recorded idea's thought graph and route without approving or executing work." \
  --proposed-paths "src/conversation_os/cli.py,tests/test_conversation_os.py"
```

Expected: `ready: true`. If not ready, follow the guard recommendation before editing.

- [ ] **Step 2: Write a failing CLI test**

Add:

```python
def test_cli_development_thought_graph_inspects_recorded_idea(self) -> None:
    self._write_personal_interface_profile()
    idea = record_development_idea(
        self.root,
        "Mobile thought drops should become inspectable graphs.",
        desired_effect="Show graph lenses without executing tools.",
        surface_hints=["inner_world"],
        source_session_id="session-mobile",
        source_refs=["event-mobile"],
    )

    old = os.getcwd()
    os.chdir(self.root)
    try:
        output = StringIO()
        with redirect_stdout(output):
            exit_code = main(["development", "thought-graph", "--idea-id", idea["idea_id"]])
        payload = json.loads(output.getvalue())
    finally:
        os.chdir(old)

    self.assertEqual(exit_code, 0)
    self.assertEqual(payload["idea_id"], idea["idea_id"])
    self.assertEqual(payload["thought_graph"]["graph_id"], idea["thought_graph"]["graph_id"])
    self.assertIn("workflow_path", [lens["lens_key"] for lens in payload["thought_graph"]["size_lenses"]])
```

- [ ] **Step 3: Run the test red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_cli_development_thought_graph_inspects_recorded_idea -q
```

Expected: FAIL because the CLI subcommand does not exist.

- [ ] **Step 4: Add the CLI parser command**

In `build_parser`, under the `development` subparser definitions, add:

```python
development_graph = development_sub.add_parser("thought-graph")
development_graph.add_argument("--idea-id", required=True)
```

- [ ] **Step 5: Add command handling**

In `main`, inside `elif args.command == "development":`, add before the final `else`:

```python
elif args.development_command == "thought-graph":
    idea = get_development_idea(root, args.idea_id)
    if idea is None:
        raise FileNotFoundError(f"Development idea not found: {args.idea_id}")
    result = {
        "idea_id": args.idea_id,
        "thought_graph": idea.get("thought_graph", {}),
        "route": route_development_idea(root, idea, limit=6),
    }
```

- [ ] **Step 6: Run the CLI test green**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_cli_development_thought_graph_inspects_recorded_idea -q
```

Expected: `1 passed`.

---

### Task 5: Add Conversation-Level Thought Graph Capture

**Files:**
- Modify: `src/conversation_os/development_intake.py`
- Modify: `tests/test_conversation_os.py`
- Possibly modify: `src/conversation_os/cli.py`

- [ ] **Step 1: Define the behavior**

Conversation-level capture should accept:

```python
record_development_idea(
    root,
    raw_idea="...",
    desired_effect="...",
    source_session_id="session-...",
    source_refs=["event-..."],
)
```

The graph should use `source_session_id` and `source_refs` as provenance. It should not read or mutate raw event logs.

- [ ] **Step 2: Write a failing test for conversation refs**

Add:

```python
def test_thought_graph_preserves_session_and_event_provenance_without_editing_events(self) -> None:
    self._write_personal_interface_profile()
    session = session_start(self.root, "Thought graph source session")
    event = session_append(
        self.root,
        session.session_id,
        "user",
        "request",
        "Codex phone drops should become routed graph work.",
    )

    before_events = (self.root / "memory" / "events" / f"{session.session_id}.jsonl").read_text(encoding="utf-8")
    record = record_development_idea(
        self.root,
        event.content,
        desired_effect="Preserve provenance.",
        source_session_id=session.session_id,
        source_refs=[event.event_id],
    )
    after_events = (self.root / "memory" / "events" / f"{session.session_id}.jsonl").read_text(encoding="utf-8")

    self.assertEqual(before_events, after_events)
    self.assertEqual(record["thought_graph"]["source_session_id"], session.session_id)
    self.assertEqual(record["thought_graph"]["source_refs"], [event.event_id])
```

- [ ] **Step 3: Run the test**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_thought_graph_preserves_session_and_event_provenance_without_editing_events -q
```

Expected: `1 passed` if the current implementation already satisfies this. If it fails, fix only provenance handling.

---

### Task 6: Transform Conversations Into Meta Commentary Artifacts

**Files:**
- Modify first: `src/conversation_os/development_intake.py`
- Modify first: `tests/test_conversation_os.py`
- Possible later split after guard approval: `src/conversation_os/meta_commentary.py`
- Possible later manifest after split: `context/substrate/modules/kernel.analysis.meta_commentary.json`

- [ ] **Step 1: Run the engineering guard for the smallest edit surface**

Run:

```bash
python3 tools/conversation_os.py engineering-guard assess \
  --request "Add derived meta commentary artifacts to development idea thought graphs." \
  --purpose "Let the system analyze conversations across additional dimensions by storing commentary artifacts about interaction dynamics, abstraction moves, implicit requests, uncertainty, and tool readiness without editing raw event logs." \
  --proposed-paths "src/conversation_os/development_intake.py,tests/test_conversation_os.py"
```

Expected: `ready: true`. If the guard recommends `meta_layer.py` or a new owner instead, follow that recommendation and update this plan before coding.

- [ ] **Step 2: Define the v1 artifact contract**

Use this exact shape inside `thought_graph["meta_commentary_artifacts"]`:

```python
{
    "artifact_id": "meta-commentary-...",
    "artifact_type": "interaction_dynamic",
    "lens": "meta_commentary",
    "summary": "The user is in capture mode and wants the system to preserve a broad vision before narrowing implementation.",
    "analysis_dimensions": ["capture_mode", "scope_pressure", "tool_readiness"],
    "evidence_refs": ["event-..."],
    "confidence": 0.72,
    "uncertainty": ["The artifact is heuristic until turn-level analysis is available."],
}
```

Required `artifact_type` values for v1:

- `interaction_dynamic`
- `abstraction_move`
- `implicit_instruction`
- `uncertainty_marker`
- `tool_readiness`

- [ ] **Step 3: Write a failing test for meta commentary artifacts**

Add:

```python
def test_record_development_idea_derives_meta_commentary_artifacts(self) -> None:
    self._write_personal_interface_profile()

    record = record_development_idea(
        self.root,
        (
            "I have a vision and need to brain dump it first. "
            "Then Codex should transform the conversation into a plan, "
            "but it should not execute tools until the workflow is safe."
        ),
        desired_effect="Create meta commentary artifacts for deeper analysis dimensions.",
        surface_hints=["inner_world", "personal_interface"],
        source_session_id="session-meta",
        source_refs=["event-meta"],
    )

    artifacts = record["thought_graph"]["meta_commentary_artifacts"]
    artifact_types = {artifact["artifact_type"] for artifact in artifacts}

    self.assertIn("meta_commentary", [lens["lens_key"] for lens in record["thought_graph"]["size_lenses"]])
    self.assertIn("interaction_dynamic", artifact_types)
    self.assertIn("implicit_instruction", artifact_types)
    self.assertIn("tool_readiness", artifact_types)
    self.assertTrue(all(artifact["evidence_refs"] == ["event-meta"] for artifact in artifacts))
    self.assertTrue(any("tool_readiness" in artifact["analysis_dimensions"] for artifact in artifacts))
```

- [ ] **Step 4: Run the test red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_record_development_idea_derives_meta_commentary_artifacts -q
```

Expected: FAIL because `meta_commentary_artifacts` does not exist.

- [ ] **Step 5: Add the meta commentary lens**

Add this entry to `THOUGHT_GRAPH_SIZE_LENSES`:

```python
{
    "lens_key": "meta_commentary",
    "label": "Meta Commentary",
    "purpose": "Store derived commentary about the conversation's dynamics, implicit instructions, uncertainty, and tool-readiness.",
},
```

- [ ] **Step 6: Implement a private artifact builder**

Add a private helper in `development_intake.py`:

```python
def _build_meta_commentary_artifacts(
    *,
    graph_id: str,
    raw_idea: str,
    desired_effect: str,
    source_refs: List[str],
) -> List[Dict[str, Any]]:
    text = " ".join([raw_idea, desired_effect]).lower()
    artifacts: List[Dict[str, Any]] = []

    def add_artifact(
        artifact_type: str,
        summary: str,
        dimensions: List[str],
        confidence: float,
        uncertainty: List[str] | None = None,
    ) -> None:
        artifacts.append(
            {
                "artifact_id": f"{graph_id}:meta-commentary:{len(artifacts)}",
                "artifact_type": artifact_type,
                "lens": "meta_commentary",
                "summary": summary,
                "analysis_dimensions": dimensions,
                "evidence_refs": source_refs,
                "confidence": confidence,
                "uncertainty": uncertainty or [],
            }
        )

    if any(token in text for token in ("brain dump", "vision", "rough", "thought")):
        add_artifact(
            "interaction_dynamic",
            "The user is in capture mode and needs preservation before narrowing.",
            ["capture_mode", "scope_pressure"],
            0.74,
        )
    if any(token in text for token in ("micro", "macro", "lens", "dimension", "meta")):
        add_artifact(
            "abstraction_move",
            "The user is asking to analyze the conversation through multiple abstraction sizes.",
            ["abstraction_level", "analysis_dimension"],
            0.78,
        )
    if any(token in text for token in ("need", "should", "must", "workflow", "plan")):
        add_artifact(
            "implicit_instruction",
            "The thought drop contains an instruction to transform rough material into a reliable workflow.",
            ["instruction_extraction", "workflow_routing"],
            0.76,
        )
    if any(token in text for token in ("safe", "guard", "uncertain", "rough", "reliable")):
        add_artifact(
            "uncertainty_marker",
            "The drop asks for safety and reliability, so implementation should surface assumptions before execution.",
            ["uncertainty", "guardrail"],
            0.7,
            ["Heuristic marker; later versions should use turn-level evidence."],
        )
    if any(token in text for token in ("codex", "openclaw", "hermes", "tool", "tools", "execute", "execution")):
        add_artifact(
            "tool_readiness",
            "The drop references execution tools, but readiness should remain gated by approval and task packs.",
            ["tool_readiness", "execution_gate"],
            0.72,
        )

    if not artifacts:
        add_artifact(
            "interaction_dynamic",
            "The conversation needs commentary, but no strong v1 marker was detected.",
            ["low_signal"],
            0.42,
            ["Low-signal heuristic artifact."],
        )
    return artifacts
```

- [ ] **Step 7: Attach artifacts to the graph**

Inside `_build_thought_graph_payload`, after `graph_id` is created, call:

```python
meta_commentary_artifacts = _build_meta_commentary_artifacts(
    graph_id=graph_id,
    raw_idea=raw_idea,
    desired_effect=desired_effect,
    source_refs=source_refs,
)
```

Add this to the returned payload:

```python
"meta_commentary_artifacts": meta_commentary_artifacts,
```

Add one graph node summarizing the artifacts:

```python
meta_node = _graph_node(
    graph_id,
    "meta_commentary",
    0,
    "Derived conversation commentary",
    "Derived artifacts describe conversation dynamics, abstraction moves, implicit instructions, uncertainty, and tool-readiness.",
    ["conversation_analysis", "bridge_orchestration"],
)
```

Link it from the raw node with relation `derives_commentary`.

- [ ] **Step 8: Run green**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_record_development_idea_derives_meta_commentary_artifacts -q
```

Expected: `1 passed`.

- [ ] **Step 9: Add a follow-up split decision**

Do not create `meta_commentary.py` yet. After two call sites depend on the artifact builder, run the guard for:

```bash
python3 tools/conversation_os.py engineering-guard assess \
  --request "Extract meta commentary artifact generation into its own analysis owner." \
  --purpose "Reuse conversation meta commentary artifacts across development intake, personal interface bridge state, and Inner World analysis without bloating development intake." \
  --proposed-paths "src/conversation_os/meta_commentary.py,tests/test_conversation_os.py,context/substrate/modules/kernel.analysis.meta_commentary.json"
```

Only split if the guard returns `ready: true`.

---

### Task 7: Build Cross-Conversation Context Retrieval

**Files:**
- Modify: `src/conversation_os/development_intake.py`
- Modify: `tests/test_conversation_os.py`

Cross-conversation retrieval should compare both graph nodes and meta commentary artifacts against existing concepts, context bubbles, thread abstractions, and development ideas.

- [ ] **Step 1: Write a failing test using existing concept matches**

Add:

```python
def test_thought_graph_cross_conversation_lens_includes_development_signal_refs(self) -> None:
    self._write_personal_interface_profile()
    self._write_meta_rows(
        [
            self._meta_row(
                meta_id="meta-bridge",
                kind="shared_primitive",
                label="Execution bridge",
                summary="Routes rough ideas toward guarded implementation workflows.",
                source_ref="session://prior-bridge",
                chunk_id="chunk-bridge",
                confidence=0.86,
            )
        ]
    )

    record = record_development_idea(
        self.root,
        "Build a mobile execution bridge from rough thoughts to guarded workflows.",
        desired_effect="Compare this against prior bridge conversations.",
        surface_hints=["inner_world"],
    )

    cross_nodes = [
        node for node in record["thought_graph"]["nodes"]
        if node["lens"] == "cross_conversation"
    ]
    self.assertTrue(cross_nodes)
    self.assertTrue(record["thought_graph"]["related_context_refs"])
    self.assertEqual(record["thought_graph"]["related_context_refs"][0]["meta_id"], "meta-bridge")
```

- [ ] **Step 2: Run red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_thought_graph_cross_conversation_lens_includes_development_signal_refs -q
```

Expected: FAIL because `related_context_refs` is missing.

- [ ] **Step 3: Add related context refs from development signals**

In `record_development_idea`, after `translation_payload` exists, pass `development_signals` into `_build_thought_graph_payload`.

In the graph builder, add:

```python
related_context_refs = []
for row in development_signals.get("formation_candidates", [])[:5]:
    related_context_refs.append(
        {
            "meta_id": str(row.get("meta_id", "")),
            "kind": str(row.get("kind", "")),
            "label": str(row.get("label", "")),
            "source_refs": list(row.get("source_refs", [])),
            "confidence": float(row.get("confidence", 0.0)),
        }
    )
```

Add `"related_context_refs": related_context_refs` to the graph payload.

- [ ] **Step 4: Run green**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_thought_graph_cross_conversation_lens_includes_development_signal_refs -q
```

Expected: `1 passed`.

---

### Task 8: Convert Thought Graphs Into Approval-Ready Proposals

**Files:**
- Modify: `src/conversation_os/development_intake.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write a failing test for proposal graph carry-through**

Add:

```python
def test_build_development_proposal_carries_thought_graph_summary(self) -> None:
    self._write_personal_interface_profile()
    idea = record_development_idea(
        self.root,
        "Make mobile thought graphs route into guarded implementation plans.",
        desired_effect="Proposal should expose graph dimensions and uncertainty.",
        surface_hints=["inner_world"],
        source_session_id="session-graph",
        source_refs=["event-graph"],
    )

    proposal = build_development_proposal(self.root, idea["idea_id"])

    self.assertEqual(proposal["thought_graph_summary"]["graph_id"], idea["thought_graph"]["graph_id"])
    self.assertIn("workflow_routing", proposal["thought_graph_summary"]["dimensions"])
    self.assertIn("workflow_path", proposal["thought_graph_summary"]["lens_keys"])
```

- [ ] **Step 2: Run red**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_build_development_proposal_carries_thought_graph_summary -q
```

Expected: FAIL because proposal does not include `thought_graph_summary`.

- [ ] **Step 3: Add graph summary to proposal**

In `build_development_proposal`, compute:

```python
thought_graph = dict(idea.get("thought_graph") or {})
proposal["thought_graph_summary"] = {
    "graph_id": str(thought_graph.get("graph_id", "")),
    "dimensions": list(thought_graph.get("dimensions", [])),
    "lens_keys": [
        str(lens.get("lens_key", ""))
        for lens in thought_graph.get("size_lenses", [])
        if str(lens.get("lens_key", ""))
    ],
    "uncertainty": list(thought_graph.get("uncertainty", [])),
}
```

Place it before persistence.

- [ ] **Step 4: Run green**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_build_development_proposal_carries_thought_graph_summary -q
```

Expected: `1 passed`.

---

### Task 9: Add Bridge State Classification As A Separate Later Surface

**Files:**
- Start with guard; likely targets:
- Modify: `src/conversation_os/personal_interface.py`
- Modify: `tests/test_personal_interface.py`

- [ ] **Step 1: Run guard**

Run:

```bash
python3 tools/conversation_os.py engineering-guard assess \
  --request "Classify incoming thought drops into bridge communication states for mobile execution workflows." \
  --purpose "Let the system distinguish capture, clarification, planning, execution, and feedback states before adapting communication or routing tools." \
  --proposed-paths "src/conversation_os/personal_interface.py,tests/test_personal_interface.py"
```

Expected: `ready: true` or a recommendation to use another owner.

- [ ] **Step 2: Define the first states**

Use these exact states for v1:

```python
BRIDGE_FLOW_STATES = {
    "capture": "User is dumping raw thought and should not be over-constrained.",
    "clarify": "User is narrowing ambiguity or answering missing details.",
    "plan": "User wants a concrete implementation path.",
    "execute": "User has approved action and wants tools to run.",
    "feedback": "User is correcting or evaluating the result.",
}
```

- [ ] **Step 3: Test capture vs execute**

Add tests that classify:

```python
"i have a vision, brain dump this and map it later" -> "capture"
"run the approved task pack now" -> "execute"
```

- [ ] **Step 4: Keep execution gated**

The classifier must never run external tools. It should return state, confidence, and reasons only.

---

### Task 10: Add Hosted Execution Routing Only Behind Holodeck/Task Packs

**Files:**
- Modify only after guard approval:
- `src/conversation_os/holodeck.py`
- `src/conversation_os/chat_backends.py`
- provider-specific tool adapters if needed
- tests in `tests/test_conversation_os.py`

- [ ] **Step 1: Define non-negotiable gate**

Execution requires:

```text
recorded idea -> proposal -> explicit approval -> task pack -> workspace/run contract -> allowed commands/tools -> verification evidence
```

- [ ] **Step 2: Add tests before integrations**

Test that a raw thought graph cannot directly execute:

```python
with self.assertRaises(ValueError):
    execute_expert_tool_from_thought_graph(self.root, graph_id)
```

Expected error message:

```text
thought graph execution requires an approved proposal and task pack
```

- [ ] **Step 3: Add provider routes one at a time**

Recommended order:

1. Codex/local implementation task pack execution.
2. OpenClaw VPS agent execution.
3. Higgsfield/worldbuilding media execution.
4. Spreadsheet/statistics tooling.
5. Blender or other local creative tools.

Each provider must have its own test proving unsupported or unapproved execution fails closed.

---

### Task 11: Full Verification And Handoff

**Files:**
- Generated by commands:
- `context/substrate/CODEBASE_OVERVIEW.md`
- `context/substrate/CODEBASE_ATLAS.md`
- `context/substrate/codebase_map.json`
- `context/substrate/registry/*`

- [ ] **Step 1: Run all tests**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py tests/test_personal_interface.py tests/test_long_form.py tests/test_worldbuilding_studio.py tests/test_engineering_guard.py -q
```

Expected: all tests pass, with the current baseline allowing one skipped test.

- [ ] **Step 2: Refresh overview**

Run:

```bash
python3 tools/conversation_os.py repo-overview refresh
```

Expected: command exits `0` and reports generated overview/atlas/registry paths.

- [ ] **Step 3: Validate overview**

Run:

```bash
python3 tools/conversation_os.py repo-overview validate
```

Expected:

```json
{
  "fresh": true,
  "error_count": 0,
  "warning_count": 0,
  "missing_manifest_count": 0
}
```

- [ ] **Step 4: Build a task pack for the next agent if handing off**

Use the approved proposal id once a proposal exists:

```bash
python3 tools/conversation_os.py task-pack build \
  --task-id <proposal_id> \
  --request "Continue the mobile thought graph execution bridge implementation from the approved proposal." \
  --domains "development_layer,inner_world_v1,personal_interface_v1" \
  --constraints "use-approved-proposal,do-not-auto-execute-tools,preserve-source-derived-boundary"
```

Expected: JSON and markdown task pack files under `context/task_packs/`.

## Completion Criteria

The work is ready to hand off when:

- rough mobile thought drops persist as development idea records with stable thought graph payloads
- the graph includes raw, micro, meta-commentary, macro, cross-conversation, workflow, and bridge lenses
- conversations produce derived meta commentary artifacts for interaction dynamics, abstraction moves, implicit instructions, uncertainty, and tool-readiness
- related context refs come from existing synthesis/context machinery
- routing prefers meaningful owner modules over generic foundation modules
- CLI inspection exists but execution remains gated
- proposals carry graph summaries
- all tests pass
- `repo-overview validate` is clean
