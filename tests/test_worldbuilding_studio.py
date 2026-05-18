import io
import json
import os
import shutil
import socket
import tempfile
import threading
import unittest
from contextlib import redirect_stdout
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib import request as urllib_request
from urllib.error import HTTPError

from conversation_os.cli import init_repo, main
from conversation_os.miniapp import make_miniapp_handler
from conversation_os.storage import read_json, read_jsonl


REPO_ROOT = Path(__file__).resolve().parents[1]


class WorldbuildingStudioTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for filename in [
            "TENETS.md",
            "AGENTS.md",
            "SESSION_PROTOCOL.md",
            "CONTEXT_ROUTING.md",
            "PRODUCT_THESIS.md",
            "pyproject.toml",
        ]:
            shutil.copy(REPO_ROOT / filename, self.root / filename)
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run_cli(self, args: list[str]) -> tuple[int, dict]:
        output = io.StringIO()
        old = os.getcwd()
        os.chdir(self.root)
        try:
            with redirect_stdout(output):
                exit_code = main(args)
        finally:
            os.chdir(old)
        return exit_code, json.loads(output.getvalue())

    def _start_server(self, static_dir: Path | None = None):
        if static_dir is None:
            static_dir = self.root / "static-test"
            static_dir.mkdir(exist_ok=True)
            (static_dir / "index.html").write_text("<html><body>ok</body></html>", encoding="utf-8")
        handler = make_miniapp_handler(self.root, static_dir, [], 12, ["/api"])
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        server = ThreadingHTTPServer((host, port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{host}:{port}"

    def _json_request(self, url: str, *, method: str = "GET", payload: dict | None = None) -> tuple[int, dict]:
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = urllib_request.Request(
            url,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"},
        )
        with urllib_request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode("utf-8"))

    def test_demo_world_compiles_scene_into_persisted_execution_packets(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene,
            create_demo_world,
            get_packet_bundle,
            worldbuilding_studio_dir,
        )

        world = create_demo_world(self.root)
        result = compile_scene(
            self.root,
            world["world_id"],
            scene_text="Mina finds the fractured mirror and recognizes the betrayal.",
            duration_seconds=12,
            aspect_ratio="16:9",
        )

        self.assertEqual(result["world_id"], world["world_id"])
        self.assertEqual(result["status"], "compiled")
        self.assertTrue(result["packet_id"].startswith("world-packet-"))
        self.assertEqual(
            set(result["artifacts"]),
            {
                "context_packet",
                "higgsfield_execution_packet",
                "remotion_composition_props",
                "evaluation",
            },
        )

        bundle = get_packet_bundle(self.root, result["packet_id"])
        context_packet = bundle["context_packet"]
        higgsfield_packet = bundle["higgsfield_execution_packet"]
        remotion_props = bundle["remotion_composition_props"]
        evaluation = bundle["evaluation"]

        self.assertEqual(context_packet["semantic_connective"]["primary_function"], "revelation")
        self.assertIn("fractured trust", context_packet["active_primitives"])
        self.assertIn("reflective surfaces externalize corrupted memory", context_packet["active_motifs"])
        self.assertIn("composition", context_packet["layer_constraints"])
        self.assertIn("facial_expression", context_packet["layer_constraints"])
        self.assertTrue(context_packet["activated_bridge_objects"])
        self.assertIn("avoid fast TikTok jump cuts", context_packet["constraints"]["hard"])
        self.assertIn("restrained symbolic drama", context_packet["taste_profile"]["style_keywords"])

        self.assertEqual(higgsfield_packet["provider"], "higgsfield")
        self.assertEqual(higgsfield_packet["tool"], "generate_video")
        self.assertEqual(higgsfield_packet["model_preference"], "cinematic_studio_3_0")
        self.assertIn("World context:", higgsfield_packet["compiled_prompt"])
        self.assertIn("Shot plan:", higgsfield_packet["compiled_prompt"])
        self.assertIn("delayed reaction", higgsfield_packet["compiled_prompt"])

        self.assertEqual(remotion_props["kind"], "composition_props")
        self.assertEqual(remotion_props["composition_id"], "WorldStudioStoryboard")
        self.assertEqual(remotion_props["metadata"]["duration_seconds"], 12)
        self.assertEqual(remotion_props["metadata"]["aspect_ratio"], "16:9")
        self.assertGreaterEqual(len(remotion_props["props"]["shots"]), 3)
        self.assertEqual(remotion_props["props"]["evaluatorSummary"], evaluation["summary"])

        packet_dir = worldbuilding_studio_dir(self.root) / "packets" / result["packet_id"]
        self.assertTrue((packet_dir / "context_packet.json").exists())
        self.assertTrue((packet_dir / "higgsfield_execution_packet.json").exists())
        self.assertTrue((packet_dir / "remotion_composition_props.json").exists())
        self.assertTrue((packet_dir / "evaluation.json").exists())

    def test_cli_demo_and_packet_lookup_return_json_payloads(self) -> None:
        exit_code, result = self._run_cli(["world-studio", "demo"])

        self.assertEqual(exit_code, 0)
        self.assertEqual(result["status"], "compiled")
        self.assertIn("world", result)
        self.assertIn("packet", result)

        packet_id = result["packet"]["packet_id"]
        lookup_code, lookup = self._run_cli(["world-studio", "get-packet", "--packet-id", packet_id])

        self.assertEqual(lookup_code, 0)
        self.assertEqual(lookup["context_packet"]["packet_id"], packet_id)
        self.assertEqual(lookup["remotion_composition_props"]["composition_id"], "WorldStudioStoryboard")

    def test_population_session_adapts_and_persists_layered_world_knowledge(self) -> None:
        from conversation_os.worldbuilding_studio import (
            answer_population_question,
            create_world,
            get_population_session,
            inspect_world_knowledge,
            start_population_session,
        )

        world = create_world(self.root, name="Ash Harbor", summary="A coastal city built on rituals and concealment.")
        current = start_population_session(self.root, world["world_id"])

        self.assertEqual(current["question_id"], "entrypoint")
        self.assertEqual(current["selection_mode"], "single")
        self.assertTrue(current["response_options"])
        self.assertIn("progress", current)
        self.assertIn("knowledge_preview", current)

        scripted_answers = {
            "entrypoint": "object",
            "anchor_object": "A salt-stained brass key that should not open any living door.",
            "core_emotion": "trust_fracture|Everyone in Ash Harbor smiles like they already know the betrayal.",
            "anchor_character": "Iris Vale is the city archivist who keeps discovering altered records with her own handwriting on them.",
            "anchor_place": "The tide archive sits under the seawall and only stays dry while the bells are ringing.",
            "world_rule": "Every oath spoken over seawater becomes physically binding by dawn.",
            "visual_tone": "ritual_cold|Wet stone, practical lamps, disciplined symmetry, and no cozy warmth.",
            "core_conflict": "The key proves the city has been rewriting who belongs inside its protections.",
            "connection_probe": "The brass key opens the tide archive, and each opening forces Iris to lose one true memory.",
        }

        asked: list[str] = []
        while not current["completed"]:
            question_id = current["question_id"]
            asked.append(question_id)
            current = answer_population_question(self.root, current["session_id"], scripted_answers[question_id])

        self.assertEqual(asked[0], "entrypoint")
        self.assertIn("anchor_object", asked)
        self.assertIn("connection_probe", asked)
        self.assertTrue(current["completed"])
        self.assertEqual(current["status"], "ready_for_generation")

        session = get_population_session(self.root, current["session_id"])
        self.assertEqual(session["world_id"], world["world_id"])
        self.assertGreaterEqual(len(session["answers"]), 8)

        knowledge = inspect_world_knowledge(self.root, world["world_id"])
        self.assertGreaterEqual(knowledge["knowledge_record_count"], 7)
        self.assertGreaterEqual(knowledge["connection_count"], 2)
        self.assertIn("object", knowledge["coverage_by_layer"])
        self.assertIn("primitive", knowledge["coverage_by_layer"])
        self.assertIn("relationship", knowledge["coverage_by_layer"])
        self.assertTrue(knowledge["records"])
        self.assertTrue(knowledge["connections"])
        self.assertTrue(any("key" in row["label"].lower() for row in knowledge["records"]))
        self.assertTrue(any("trust fracture" in primitive.lower() for primitive in knowledge["world_snapshot"]["project_primitives"]))
        self.assertTrue(knowledge["world_snapshot"]["bridge_objects"])
        self.assertIn("ritual cold", knowledge["world_snapshot"]["taste_profile"]["style_keywords"])

    def test_world_graph_projection_materializes_nodes_edges_and_recommended_actions(self) -> None:
        from conversation_os.worldbuilding_studio import (
            answer_population_question,
            create_world,
            project_world_graph,
            start_population_session,
        )

        world = create_world(self.root, name="Harbor Ritual", summary="A ritual port city shaped by salt, debt, and memory.")
        current = start_population_session(self.root, world["world_id"])
        scripted_answers = {
            "entrypoint": "emotion",
            "core_emotion": "trust_fracture|Everyone in the harbor is polite because open distrust has become ceremonial.",
            "anchor_character": "Noor keeps the city's tide ledgers and can spot edited memories by the way ink dries.",
            "anchor_place": "The debt basin is a stepped harbor where promises are audited at low tide.",
            "anchor_object": "A ledger knife used to cut old vows out of public record.",
            "world_rule": "Any vow written in salt ink becomes enforceable at the next tide change.",
            "visual_tone": "ritual_cold|Pale paper, wet stone, disciplined rooms, and no sentimental warmth.",
            "core_conflict": "The city survives by deleting the very memories that make trust possible.",
            "connection_probe": "The ledger knife lets Noor expose which vows were removed, but using it binds her into the same system.",
        }
        while not current["completed"]:
            current = answer_population_question(self.root, current["session_id"], scripted_answers[current["question_id"]])

        graph = project_world_graph(self.root, world["world_id"])

        self.assertEqual(graph["world_id"], world["world_id"])
        self.assertGreaterEqual(len(graph["nodes"]), 8)
        self.assertGreaterEqual(len(graph["edges"]), 3)
        self.assertTrue(any(node["node_type"] == "fragment" for node in graph["nodes"]))
        self.assertTrue(any(node["layer"] == "object" for node in graph["nodes"]))
        self.assertTrue(any(edge["edge_type"] == "inferred_world_link" for edge in graph["edges"]))
        self.assertIn("compile_scene", graph["recommended_actions"])
        self.assertTrue(graph["ready_for_generation"])

    def test_cli_population_flow_returns_json_payloads(self) -> None:
        create_code, created = self._run_cli(["world-studio", "create-world", "--name", "Mist Ledger"])
        self.assertEqual(create_code, 0)

        start_code, started = self._run_cli(
            ["world-studio", "populate-start", "--world-id", created["world_id"]]
        )
        self.assertEqual(start_code, 0)
        self.assertEqual(started["question_id"], "entrypoint")

        answer_code, answered = self._run_cli(
            [
                "world-studio",
                "populate-answer",
                "--session-id",
                started["session_id"],
                "--answer",
                "place",
            ]
        )
        self.assertEqual(answer_code, 0)
        self.assertEqual(answered["question_id"], "anchor_place")

        session_code, session = self._run_cli(
            ["world-studio", "population-session", "--session-id", started["session_id"]]
        )
        self.assertEqual(session_code, 0)
        self.assertEqual(session["current_question_id"], "anchor_place")

        guide_code, guide = self._run_cli(["world-studio", "guide"])
        self.assertEqual(guide_code, 0)
        self.assertEqual(guide["browser_entry"]["path"], "/world-studio.html")
        self.assertIn("inspect-graph", "\n".join(guide["cli_commands"]))
        self.assertTrue(guide["recommended_workflow"])

        graph_code, graph = self._run_cli(
            ["world-studio", "inspect-graph", "--world-id", created["world_id"]]
        )
        self.assertEqual(graph_code, 0)
        self.assertEqual(graph["world_id"], created["world_id"])
        self.assertIn("nodes", graph)

    def test_miniapp_population_api_routes(self) -> None:
        from conversation_os.worldbuilding_studio import create_world

        world = create_world(self.root, name="Mirror District", summary="A city block where reflections arrive early.")
        server, thread, base_url = self._start_server()
        try:
            status, started = self._json_request(
                f"{base_url}/api/world-studio/population/start",
                method="POST",
                payload={"world_id": world["world_id"]},
            )
            self.assertEqual(status, 200)
            self.assertEqual(started["question_id"], "entrypoint")

            status, answered = self._json_request(
                f"{base_url}/api/world-studio/population/answer",
                method="POST",
                payload={"session_id": started["session_id"], "answer": "emotion"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(answered["question_id"], "core_emotion")

            status, session = self._json_request(
                f"{base_url}/api/world-studio/population/session/{started['session_id']}"
            )
            self.assertEqual(status, 200)
            self.assertEqual(session["current_question_id"], "core_emotion")

            status, knowledge = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/knowledge"
            )
            self.assertEqual(status, 200)
            self.assertEqual(knowledge["world_id"], world["world_id"])
            self.assertIn("coverage_by_layer", knowledge)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_evidence_ingestion_creates_explicit_records_and_preserves_provenance(self) -> None:
        from conversation_os.worldbuilding_studio import (
            create_world,
            ingest_evidence,
            inspect_world_evidence,
            inspect_world_knowledge,
            next_worldbuilding_question,
        )

        world = create_world(self.root, name="Bead Forest", summary="A microverse suspended inside a droplet.")
        image_path = self.root / "pollen-reference.jpg"
        image_path.write_bytes(b"fake-image")

        text_evidence = ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "The world should feel like wonder under quiet predatory pressure. "
                "Suri tends a floating pollen observatory inside a bead of water. "
                "The capillary forest hangs in the droplet and a filament compass bends toward hunger. "
                "Every sound thickens the air into a new path. "
                "Visually it should feel bright uncanny with pearl greens, membrane light, and translucent fibers."
            ),
            source_label="microverse-notes",
        )
        image_evidence = ingest_evidence(
            self.root,
            world["world_id"],
            source_path=str(image_path),
            source_label="pollen-lattice-reference",
            note="Still image reference with translucent capillaries, pearl membranes, and surgical glare.",
        )

        self.assertEqual(text_evidence["world_id"], world["world_id"])
        self.assertEqual(text_evidence["evidence"]["modality"], "text")
        self.assertGreaterEqual(text_evidence["committed_record_count"], 5)
        self.assertEqual(image_evidence["evidence"]["modality"], "image")

        evidence = inspect_world_evidence(self.root, world["world_id"])
        knowledge = inspect_world_knowledge(self.root, world["world_id"])
        question = next_worldbuilding_question(self.root, world["world_id"])

        self.assertEqual(evidence["evidence_count"], 2)
        self.assertGreaterEqual(evidence["explicit_record_count"], 5)
        self.assertGreaterEqual(evidence["inferred_record_count"], 1)
        self.assertTrue(any(row["record_type"] == "character" for row in evidence["records"]))
        self.assertTrue(any(row["record_type"] == "visual_adjacency" for row in evidence["records"]))
        self.assertTrue(
            any(
                text_evidence["evidence"]["evidence_id"] in row.get("supporting_evidence_ids", [])
                for row in evidence["records"]
            )
        )
        self.assertIn("uncertain_records", evidence)
        self.assertTrue(any(row.get("provenance", {}).get("evidence_ids") for row in knowledge["records"]))
        self.assertIn(question["question_id"], {"core_conflict", "connection_probe"})
        self.assertIn("why_this_matters", question)

    def test_generate_canon_and_compile_scene_from_canon_persist_world_os_artifacts(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            generate_canon,
            get_packet_bundle,
            ingest_evidence,
            worldbuilding_studio_dir,
        )

        world = create_world(self.root, name="Voice Droplet", summary="A microverse built inside a listening bead.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Suri keeps a pollen observatory suspended inside a giant droplet. "
                "The capillary forest bends whenever voices rise. "
                "A filament compass points toward whatever the world wants to consume. "
                "Every sound grows a temporary airway through the droplet. "
                "The world feels like wonder turning slowly into appetite. "
                "The visual language should be bright uncanny with pearl greens, glass membranes, and clean glare. "
                "The core conflict is that Suri must speak to navigate, but every word feeds the forest."
            ),
            source_label="voice-droplet-seed",
        )

        canon = generate_canon(self.root, world["world_id"])
        scene = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Suri follows the filament compass through the capillary forest and realizes the airway is feeding on her voice.",
        )
        bundle = get_packet_bundle(self.root, scene["packet_id"])
        canon_assets_path = (
            worldbuilding_studio_dir(self.root) / "worlds" / world["world_id"] / "canon" / "canon_assets.jsonl"
        )
        shot_intents_path = (
            worldbuilding_studio_dir(self.root) / "worlds" / world["world_id"] / "scene" / "shot_intents.jsonl"
        )

        self.assertGreaterEqual(canon["canon_asset_count"], 3)
        self.assertTrue(any(asset["asset_type"] == "character" for asset in canon["canon_assets"]))
        self.assertTrue(any(asset["asset_type"] == "place" for asset in canon["canon_assets"]))
        self.assertTrue(any(asset["asset_type"] == "object" for asset in canon["canon_assets"]))
        self.assertEqual(scene["status"], "compiled")
        self.assertIn("selected_canon_assets", bundle["context_packet"])
        self.assertIn("scene_beat", bundle["context_packet"])
        self.assertIn("shot_intents", bundle["context_packet"])
        self.assertTrue(bundle["context_packet"]["selected_canon_assets"])
        self.assertIn("canon_reference_ids", bundle["higgsfield_execution_packet"])
        self.assertTrue(bundle["higgsfield_execution_packet"]["canon_reference_ids"])
        self.assertTrue(canon_assets_path.exists())
        self.assertTrue(shot_intents_path.exists())

    def test_general_world_scene_packets_do_not_reuse_demo_betrayal_grammar(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            generate_canon,
            get_packet_bundle,
            ingest_evidence,
        )

        world = create_world(self.root, name="Capillary Moon", summary="A microverse inside a listening droplet.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Suri tends a pollen observatory suspended inside a bead of water. "
                "The capillary forest bends whenever voices rise. "
                "A filament compass points toward whatever the droplet wants to consume. "
                "Every sound grows a temporary airway through the forest. "
                "The world feels like wonder turning slowly into appetite. "
                "The visual language should be bright uncanny with pearl greens, glass membranes, and clean glare. "
                "The core conflict is that Suri must speak to navigate, but every word feeds the forest."
            ),
            source_label="capillary-moon-seed",
        )
        generate_canon(self.root, world["world_id"])
        compiled = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Suri follows the filament compass through the capillary forest and realizes the airway is feeding on her voice.",
        )
        bundle = get_packet_bundle(self.root, compiled["packet_id"])
        prompt = bundle["higgsfield_execution_packet"]["compiled_prompt"].lower()
        evaluator_text = json.dumps(bundle["evaluation"]).lower()
        shot_text = json.dumps(bundle["context_packet"]["shot_plan"]).lower()

        self.assertIn("capillary", prompt)
        self.assertIn("filament compass", prompt)
        self.assertNotIn("fractured trust", prompt)
        self.assertNotIn("betrayal", evaluator_text)
        self.assertNotIn("reflective object", shot_text)
        self.assertNotIn("delayed human reaction", shot_text)

    def test_world_feeling_sentence_is_not_misclassified_as_anchor_place(self) -> None:
        from conversation_os.worldbuilding_studio import create_world, ingest_evidence, inspect_world_evidence

        world = create_world(self.root, name="Pearl Weather", summary="A bright microverse.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "The world should feel bright uncanny and precariously beautiful. "
                "Mina tends an observatory inside a bead of water. "
                "The capillary forest hangs below the lens."
            ),
            source_label="pearl-weather-seed",
        )
        evidence = inspect_world_evidence(self.root, world["world_id"])
        place_summaries = [
            row["summary"].lower()
            for row in evidence["records"]
            if row.get("layer") == "place"
        ]

        self.assertTrue(any("observatory" in summary or "capillary forest" in summary for summary in place_summaries))
        self.assertFalse(any(summary.startswith("the world should feel") for summary in place_summaries))

    def test_generate_canon_upserts_filtered_assets_without_erasing_existing_canon(self) -> None:
        from conversation_os.worldbuilding_studio import (
            create_world,
            generate_canon,
            ingest_evidence,
            worldbuilding_studio_dir,
        )

        world = create_world(self.root, name="Root Glass", summary="A glass orchard microverse.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Nera tends an orchard of glass spores inside a droplet city. "
                "A root-key opens sealed membranes. "
                "Every spoken promise becomes a visible path. "
                "The world feels bright uncanny under quiet pressure."
            ),
            source_label="root-glass-seed",
        )
        first = generate_canon(self.root, world["world_id"])
        first_ids = {asset["canon_id"] for asset in first["canon_assets"]}
        first_types = {asset["asset_type"] for asset in first["canon_assets"]}

        second = generate_canon(self.root, world["world_id"], asset_types=["character"])
        canon_path = worldbuilding_studio_dir(self.root) / "worlds" / world["world_id"] / "canon" / "canon_assets.jsonl"
        persisted = read_jsonl(canon_path)
        persisted_ids = {asset["canon_id"] for asset in persisted}
        persisted_types = {asset["asset_type"] for asset in persisted}

        self.assertIn("place", first_types)
        self.assertIn("object", first_types)
        self.assertGreaterEqual(len(persisted_ids & first_ids), 2)
        self.assertIn("place", persisted_types)
        self.assertIn("object", persisted_types)
        self.assertGreaterEqual(second["canon_asset_count"], len(first["canon_assets"]))

    def test_compile_scene_from_canon_fails_when_no_canon_can_be_generated(self) -> None:
        from conversation_os.worldbuilding_studio import compile_scene_from_canon, create_world

        world = create_world(self.root, name="Empty Shell", summary="A world with no usable records yet.")

        with self.assertRaisesRegex(ValueError, "canon"):
            compile_scene_from_canon(self.root, world["world_id"], "A person crosses an empty room.")

    def test_execution_framework_prepares_and_records_higgsfield_runs(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            execute_higgsfield_packet,
            generate_canon,
            get_execution_run,
            get_packet_bundle,
            ingest_evidence,
            list_execution_runs,
        )

        class FakeHiggsfieldClient:
            def submit(self, request_payload: dict) -> dict:
                self.request_payload = request_payload
                return {
                    "status": "completed",
                    "job_id": "job-microverse-001",
                    "results": [
                        {
                            "url": "https://cdn.higgsfield.ai/world-studio/microverse.mp4",
                            "media_type": "video",
                        }
                    ],
                    "raw_response": {"id": "job-microverse-001"},
                }

        world = create_world(self.root, name="Signal Droplet", summary="A microverse where signals grow paths.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Ari maps a signal harbor inside a droplet basin. "
                "A tuning fork reveals safe passages. "
                "Every signal becomes a visible path in the air. "
                "The world feels bright uncanny under precise pressure."
            ),
            source_label="signal-droplet-seed",
        )
        generate_canon(self.root, world["world_id"])
        packet = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Ari follows the tuning fork through a signal path as the harbor begins to answer.",
        )
        client = FakeHiggsfieldClient()
        execution = execute_higgsfield_packet(self.root, packet["packet_id"], client=client)
        run = get_execution_run(self.root, execution["execution_id"])
        executions = list_execution_runs(self.root, packet_id=packet["packet_id"])
        bundle = get_packet_bundle(self.root, packet["packet_id"])

        self.assertEqual(execution["status"], "completed")
        self.assertEqual(execution["provider_job_id"], "job-microverse-001")
        self.assertEqual(client.request_payload["tool"], "generate_video")
        self.assertEqual(client.request_payload["arguments"]["params"]["model"], "cinematic_studio_3_0")
        self.assertIn("prompt", client.request_payload["arguments"]["params"])
        self.assertTrue(execution["asset_ids"])
        self.assertEqual(run["execution_id"], execution["execution_id"])
        self.assertEqual(executions["count"], 1)
        self.assertEqual(bundle["higgsfield_execution_packet"]["status"], "completed")

    def test_execution_framework_prepared_mode_returns_agent_mcp_payload(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            execute_higgsfield_packet,
            generate_canon,
            ingest_evidence,
        )

        world = create_world(self.root, name="Prepared Droplet", summary="A microverse ready for handoff.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Io tends a lens station inside a droplet city. "
                "A pearl compass opens translucent routes. "
                "Every route forms only while someone listens. "
                "The visual language is bright uncanny with glass membranes."
            ),
            source_label="prepared-droplet-seed",
        )
        generate_canon(self.root, world["world_id"])
        packet = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Io uses the pearl compass to open a route through the droplet city.",
        )
        execution = execute_higgsfield_packet(self.root, packet["packet_id"])

        self.assertEqual(execution["status"], "prepared")
        self.assertEqual(execution["mcp_tool_call"]["namespace"], "mcp__higgsfield__")
        self.assertEqual(execution["mcp_tool_call"]["tool"], "generate_video")
        self.assertIn("params", execution["mcp_tool_call"]["arguments"])

    def test_higgsfield_cli_client_normalizes_generate_command_and_result(self) -> None:
        from conversation_os.worldbuilding_studio import HiggsfieldCliClient

        args_log = self.root / "higgsfield-cli-args.json"
        image_path = self.root / "reference.png"
        image_path.write_bytes(b"png")
        fake_cli = self.root / "fake-higgsfield"
        fake_cli.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json, sys",
                    f"with open({args_log.as_posix()!r}, 'a', encoding='utf-8') as handle:",
                    "    handle.write(json.dumps(sys.argv[1:]) + '\\n')",
                    "if sys.argv[1:3] == ['generate', 'create']:",
                    "    print(json.dumps(['11111111-2222-3333-4444-555555555555']))",
                    "else:",
                    "    print(json.dumps({",
                    "      'id': '11111111-2222-3333-4444-555555555555',",
                    "      'status': 'completed',",
                    "      'result_url': 'https://cdn.higgsfield.ai/world-studio/cli-result.mp4'",
                    "    }))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)

        client = HiggsfieldCliClient(self.root, str(fake_cli))
        result = client.submit(
            {
                "arguments": {
                    "params": {
                        "model": "seedance_2_0",
                        "prompt": "A small harbor awakens inside a droplet.",
                        "aspect_ratio": "16:9",
                        "duration": 5,
                        "medias": [{"role": "start_image", "value": str(image_path)}],
                    }
                }
            }
        )

        cli_calls = [json.loads(line) for line in args_log.read_text(encoding="utf-8").splitlines() if line.strip()]
        create_args = next(call for call in cli_calls if call[:2] == ["generate", "create"])
        wait_args = next(call for call in cli_calls if call[:2] == ["generate", "wait"])
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["job_id"], "11111111-2222-3333-4444-555555555555")
        self.assertEqual(result["results"][0]["url"], "https://cdn.higgsfield.ai/world-studio/cli-result.mp4")
        self.assertEqual(create_args[:3], ["generate", "create", "seedance_2_0"])
        self.assertIn("--prompt", create_args)
        self.assertIn("--aspect_ratio", create_args)
        self.assertIn("--duration", create_args)
        self.assertIn("--start-image", create_args)
        self.assertNotIn("--count", create_args)
        self.assertEqual(create_args[-1], "--json")
        self.assertEqual(wait_args[:3], ["generate", "wait", "11111111-2222-3333-4444-555555555555"])
        self.assertEqual(wait_args[-1], "--json")

    def test_higgsfield_cli_client_marks_image_generations_as_images(self) -> None:
        from conversation_os.worldbuilding_studio import HiggsfieldCliClient

        fake_cli = self.root / "fake-higgsfield-image"
        fake_cli.write_text(
            "\n".join(
                [
                    "#!/usr/bin/env python3",
                    "import json, sys",
                    "if sys.argv[1:3] == ['generate', 'create']:",
                    "    print(json.dumps(['aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee']))",
                    "else:",
                    "    print(json.dumps({",
                    "      'id': 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',",
                    "      'status': 'completed',",
                    "      'result_url': 'https://cdn.higgsfield.ai/world-studio/anchor.png'",
                    "    }))",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        fake_cli.chmod(0o755)

        client = HiggsfieldCliClient(self.root, str(fake_cli))
        result = client.submit({"arguments": {"params": {"model": "cinematic_studio_2_5", "prompt": "A sacred courtyard anchor."}}})

        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["results"][0]["media_type"], "image")

    def test_visual_reference_ingestion_commits_categories_traits_and_embedding_metadata(self) -> None:
        from conversation_os.worldbuilding_studio import (
            create_world,
            ingest_visual_reference,
            inspect_visual_world,
        )

        class FakeEmbeddingClient:
            model_name = "google/gemini-embedding-2-preview"

            def embed_documents(self, documents: list[dict]) -> list[dict]:
                rows = []
                for index, document in enumerate(documents):
                    rows.append(
                        {
                            "embedding": [0.9 - (index * 0.1), 0.1 + (index * 0.1), 0.4],
                            "model": self.model_name,
                            "usage": {"prompt_tokens": 12, "total_tokens": 12},
                            "modality": document.get("modality", "text"),
                        }
                    )
                return rows

        world = create_world(self.root, name="Visual Basin", summary="A world held together by visual rules.")
        image_path = self.root / "visual-reference.png"
        image_path.write_bytes(b"png")

        ingested = ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(image_path),
            source_label="droplet observatory architecture",
            note=(
                "I like the grown monolithic building style, translucent membrane glazing, "
                "pearl mineral material treatment, and restrained surgical glare."
            ),
            categories=["architecture_style", "material_style", "lighting_language"],
            liked_aspects=[
                "grown monolithic building style",
                "translucent membrane glazing",
                "pearl mineral material treatment",
                "restrained surgical glare",
            ],
            negative_constraints=["no modular steel framing", "no cozy rustic warmth"],
            scope="global",
            embedding_client=FakeEmbeddingClient(),
        )

        visual = inspect_visual_world(self.root, world["world_id"])

        self.assertEqual(ingested["world_id"], world["world_id"])
        self.assertEqual(ingested["reference"]["embedding"]["model"], "google/gemini-embedding-2-preview")
        self.assertIn("architecture_style", ingested["reference"]["categories"])
        self.assertGreaterEqual(ingested["trait_count"], 4)
        self.assertEqual(visual["reference_count"], 1)
        self.assertGreaterEqual(visual["trait_count"], 4)
        self.assertIn("architecture_style", visual["coverage_by_category"])
        self.assertTrue(any(trait["category"] == "material_style" for trait in visual["traits"]))
        self.assertTrue(any("modular steel framing" in row for row in visual["negative_constraints"]))

    def test_compile_visual_context_retrieves_relevant_traits_for_scene_query(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_visual_context,
            create_world,
            ingest_visual_reference,
        )

        class FakeEmbeddingClient:
            model_name = "google/gemini-embedding-2-preview"

            def embed_documents(self, documents: list[dict]) -> list[dict]:
                rows = []
                for document in documents:
                    text = json.dumps(document, sort_keys=True).lower()
                    if "architecture" in text or "building" in text:
                        vector = [0.99, 0.05, 0.05]
                    elif "flora" in text or "pollen" in text or "vine" in text:
                        vector = [0.05, 0.99, 0.05]
                    else:
                        vector = [0.05, 0.05, 0.99]
                    rows.append(
                        {
                            "embedding": vector,
                            "model": self.model_name,
                            "usage": {"prompt_tokens": 10, "total_tokens": 10},
                            "modality": document.get("modality", "text"),
                        }
                    )
                return rows

        world = create_world(self.root, name="Categorized Hollow", summary="A world with clear visual strata.")
        image_path = self.root / "visual-query-reference.png"
        image_path.write_bytes(b"png")

        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(image_path),
            source_label="architecture anchor",
            note="I like the grown monolithic building style and subtractive apertures.",
            categories=["architecture_style"],
            liked_aspects=["grown monolithic building style", "subtractive apertures"],
            embedding_client=FakeEmbeddingClient(),
        )
        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(image_path),
            source_label="flora anchor",
            note="I like invasive pollen vines, root lattices, and translucent hanging spores.",
            categories=["flora_style"],
            liked_aspects=["invasive pollen vines", "root lattices", "translucent hanging spores"],
            embedding_client=FakeEmbeddingClient(),
        )

        context = compile_visual_context(
            self.root,
            world["world_id"],
            query_text="A character walks through a monolithic observatory corridor with carved openings.",
            embedding_client=FakeEmbeddingClient(),
        )

        self.assertEqual(context["world_id"], world["world_id"])
        self.assertTrue(context["selected_references"])
        self.assertIn("architecture_style", context["active_categories"])
        self.assertTrue(any(trait["category"] == "architecture_style" for trait in context["selected_traits"]))
        self.assertGreaterEqual(context["selected_trait_count"], 2)

    def test_compile_scene_from_canon_includes_visual_world_context_in_packet(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            generate_canon,
            get_packet_bundle,
            ingest_evidence,
            ingest_visual_reference,
        )

        class FakeEmbeddingClient:
            model_name = "google/gemini-embedding-2-preview"

            def embed_documents(self, documents: list[dict]) -> list[dict]:
                return [
                    {
                        "embedding": [0.8, 0.2, 0.2],
                        "model": self.model_name,
                        "usage": {"prompt_tokens": 9, "total_tokens": 9},
                        "modality": document.get("modality", "text"),
                    }
                    for document in documents
                ]

        world = create_world(self.root, name="Lens Port", summary="A world where style categories matter.")
        image_path = self.root / "visual-scene-reference.png"
        image_path.write_bytes(b"png")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Mira tends a listening station inside a suspended port. "
                "A tuning fork reveals safe routes. "
                "Every spoken phrase turns into a visible corridor. "
                "The world should feel bright uncanny and pressure-held."
            ),
            source_label="lens-port-seed",
        )
        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(image_path),
            source_label="station architecture",
            note="I like monolithic grown architecture, membrane windows, mineral pearl surfaces, and surgical glare.",
            categories=["architecture_style", "material_style", "lighting_language"],
            liked_aspects=[
                "monolithic grown architecture",
                "membrane windows",
                "mineral pearl surfaces",
                "surgical glare",
            ],
            embedding_client=FakeEmbeddingClient(),
        )
        generate_canon(self.root, world["world_id"])
        compiled = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Mira follows the tuning fork through the station corridor as the route lights up around her.",
            visual_embedding_client=FakeEmbeddingClient(),
        )

        bundle = get_packet_bundle(self.root, compiled["packet_id"])
        visual_context = bundle["context_packet"]["visual_world"]

        self.assertIn("visual_world", bundle["context_packet"])
        self.assertIn("active_categories", visual_context)
        self.assertIn("architecture_style", visual_context["active_categories"])
        self.assertIn("Visual world categories:", bundle["higgsfield_execution_packet"]["compiled_prompt"])
        self.assertTrue(bundle["higgsfield_execution_packet"]["visual_reference_ids"])

    def test_seedance_packets_include_visual_reference_media_inputs(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            generate_canon,
            get_packet_bundle,
            ingest_evidence,
            ingest_visual_reference,
        )

        world = create_world(self.root, name="Ceremonial Passage", summary="A world of monumental architecture and luminous state shifts.")
        start_image = self.root / "day.jpg"
        end_image = self.root / "dream.jpg"
        start_image.write_bytes(b"day-image")
        end_image.write_bytes(b"dream-image")

        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "A solitary draped traveler crosses a ceremonial architectural world. "
                "The same place shifts between daylight calm and dream symbolism. "
                "The world feels monumental, airy, and restrained."
            ),
            source_label="ceremonial-passage-seed",
        )
        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(start_image),
            note="Warm ivory stone courtyard with carved arches and monumental daylight scale.",
            categories=["architecture_style", "lighting_language"],
        )
        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(end_image),
            note="Painterly celestial dome with crescent moon and dream texture.",
            categories=["animation_style", "architecture_style"],
        )

        generate_canon(self.root, world["world_id"])
        compiled = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "The draped traveler moves from daylight into dream through the same ceremonial world.",
            model_preference="seedance_2_0",
        )
        bundle = get_packet_bundle(self.root, compiled["packet_id"])
        medias = bundle["higgsfield_execution_packet"]["medias"]
        prompt = bundle["higgsfield_execution_packet"]["compiled_prompt"]

        self.assertEqual(bundle["higgsfield_execution_packet"]["resolved_model"], "seedance_2_0")
        self.assertEqual(len(medias), 2)
        self.assertEqual(medias[0]["role"], "start_image")
        self.assertEqual(medias[1]["role"], "end_image")
        self.assertEqual(medias[0]["value"], str(start_image))
        self.assertEqual(medias[1]["value"], str(end_image))
        self.assertNotIn("Shot plan:", prompt)
        self.assertIn("Reference-driven cinematic video.", prompt)

    def test_seedance_packets_prefer_canon_anchor_media_when_available(self) -> None:
        from conversation_os.worldbuilding_studio import (
            _upsert_canon_asset,
            compile_scene_from_canon,
            create_world,
            generate_canon,
            get_packet_bundle,
            ingest_evidence,
            ingest_visual_reference,
        )

        class FakeEmbeddingClient:
            def embed_documents(self, documents: list[dict]) -> list[dict]:
                return [
                    {
                        "embedding": [0.8, 0.2, 0.4],
                        "model": "google/gemini-embedding-2-preview",
                        "usage": {"prompt_tokens": 10, "total_tokens": 10},
                    }
                    for _ in documents
                ]

        world = create_world(self.root, name="Anchor Preference", summary="A world with canon still anchors.")
        raw_ref = self.root / "raw-day.jpg"
        raw_ref.write_bytes(b"raw-day")
        anchor_ref = self.root / "day-anchor.png"
        anchor_ref.write_bytes(b"anchor-day")

        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "A solitary draped man crosses the same sacred precinct through daylight, night, and dream. "
                "The world should preserve identity while adapting rendering behavior by state."
            ),
            source_label="anchor-preference-seed",
        )
        ingest_visual_reference(
            self.root,
            world["world_id"],
            source_path=str(raw_ref),
            note="Daylight monumental courtyard with carved arches and warm ivory stone.",
            categories=["architecture_style", "lighting_language"],
            embedding_client=FakeEmbeddingClient(),
        )
        generate_canon(self.root, world["world_id"])
        _upsert_canon_asset(
            self.root,
            world["world_id"],
            {
                "canon_id": "world-canon-day-anchor",
                "created_at": "2026-05-08T00:00:00+00:00",
                "world_id": world["world_id"],
                "asset_type": "state_anchor",
                "label": "Daylight State Anchor",
                "summary": "Daylight state anchor for the showcase.",
                "source_record_ids": [],
                "supporting_evidence_ids": [],
                "provider": "higgsfield",
                "tool": "generate_image",
                "compiled_prompt": "anchor prompt",
                "metadata": {
                    "anchor_role": "day_anchor",
                    "local_path": str(anchor_ref),
                    "tags": ["day_anchor", "three-state-showcase"],
                },
            },
        )

        compiled = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "The same draped man enters the monumental precinct in daylight and crosses toward a carved threshold.",
            model_preference="seedance_2_0",
            visual_embedding_client=FakeEmbeddingClient(),
        )
        bundle = get_packet_bundle(self.root, compiled["packet_id"])

        self.assertEqual(bundle["higgsfield_execution_packet"]["medias"], [{"role": "start_image", "value": str(anchor_ref)}])
        self.assertEqual(bundle["higgsfield_execution_packet"]["anchor_media_strategy"], "canon_anchor")

    def test_motion_objects_bind_to_entities_and_compile_into_reusable_motion_plan(self) -> None:
        from conversation_os.worldbuilding_studio import (
            bind_motion_object,
            compile_motion_plan,
            create_motion_object,
            create_world,
            inspect_motion_system,
        )

        world = create_world(self.root, name="Motion World", summary="A world for testing reusable motion grammar.")
        character_motion = create_motion_object(
            self.root,
            world["world_id"],
            label="Restrained Forward Walk",
            scope="character",
            intent="Grounded ceremonial movement",
            primary_action="walks forward with three slow measured steps",
            body_mechanics=["heel-to-toe footfalls", "relaxed shoulders", "small natural arm swing"],
            secondary_motion=["robe trails softly behind the body", "fabric settles after the final step"],
            speed="slow",
            intensity="low",
            best_clip_duration=4,
            compatible_states=["day", "night", "dream"],
        )
        camera_motion = create_motion_object(
            self.root,
            world["world_id"],
            label="Gentle Forward Drift",
            scope="camera",
            intent="Quietly support the walking subject without spectacle",
            primary_action="gently drifts forward on the same axis as the subject",
            body_mechanics=["locked horizon", "steady framing"],
            secondary_motion=["slight settling at the end of the move"],
            speed="slow",
            intensity="low",
            best_clip_duration=4,
        )
        bind_motion_object(
            self.root,
            world["world_id"],
            motion_id=character_motion["motion_id"],
            target_kind="character",
            target_id="solitary_draped_man",
            when_tags=["man", "traveler", "walk", "threshold"],
        )
        bind_motion_object(
            self.root,
            world["world_id"],
            motion_id=camera_motion["motion_id"],
            target_kind="camera",
            target_id="default",
            when_tags=["walk", "threshold"],
        )

        system = inspect_motion_system(self.root, world["world_id"])
        plan = compile_motion_plan(
            self.root,
            world["world_id"],
            scene_text="A solitary draped man walks toward the threshold with calm ceremonial intent.",
            duration_seconds=4,
        )

        self.assertEqual(system["motion_object_count"], 2)
        self.assertEqual(system["binding_count"], 2)
        self.assertEqual(plan["selected_motion_count"], 2)
        self.assertIn(character_motion["motion_id"], plan["selected_motion_ids"])
        self.assertIn(camera_motion["motion_id"], plan["selected_motion_ids"])
        self.assertEqual(plan["character_motion"][0]["label"], "Restrained Forward Walk")
        self.assertEqual(plan["camera_motion"][0]["label"], "Gentle Forward Drift")
        self.assertIn("three slow measured steps", plan["compiled_prompt"])
        self.assertIn("robe trails softly behind the body", plan["compiled_prompt"])

    def test_compile_scene_includes_motion_plan_without_requiring_anchor_images(self) -> None:
        from conversation_os.worldbuilding_studio import (
            bind_motion_object,
            compile_scene,
            create_motion_object,
            create_world,
            get_packet_bundle,
        )

        world = create_world(self.root, name="Anchorless Motion", summary="A world that relies on motion objects instead of image anchors.")
        character_motion = create_motion_object(
            self.root,
            world["world_id"],
            label="Restrained Forward Walk",
            scope="character",
            intent="Natural forward motion for a solitary figure",
            primary_action="walks forward with three slow measured steps",
            body_mechanics=["heel-to-toe footfalls", "small natural arm swing"],
            secondary_motion=["robe trails softly behind the body", "brief settling pause"],
            speed="slow",
            intensity="low",
            best_clip_duration=4,
        )
        bind_motion_object(
            self.root,
            world["world_id"],
            motion_id=character_motion["motion_id"],
            target_kind="character",
            target_id="default",
            when_tags=["man", "walk", "crosses"],
        )

        compiled = compile_scene(
            self.root,
            world["world_id"],
            "A solitary draped man crosses the silent courtyard toward a threshold.",
            duration_seconds=4,
            aspect_ratio="16:9",
            model_preference="seedance_2_0",
        )
        bundle = get_packet_bundle(self.root, compiled["packet_id"])

        self.assertIn("motion_plan", bundle["context_packet"])
        self.assertEqual(bundle["context_packet"]["motion_plan"]["selected_motion_count"], 1)
        self.assertEqual(bundle["higgsfield_execution_packet"]["medias"], [])
        self.assertIn("three slow measured steps", bundle["higgsfield_execution_packet"]["compiled_prompt"])
        self.assertIn("motionPlan", bundle["remotion_composition_props"]["props"])

    def test_cli_and_api_motion_routes_return_structured_payloads(self) -> None:
        from conversation_os.worldbuilding_studio import create_world

        world = create_world(self.root, name="Motion Routes", summary="A world for motion route coverage.")

        create_code, created = self._run_cli(
            [
                "world-studio",
                "create-motion-object",
                "--world-id",
                world["world_id"],
                "--label",
                "Restrained Forward Walk",
                "--scope",
                "character",
                "--intent",
                "Grounded ceremonial movement",
                "--primary-action",
                "walks forward with three slow measured steps",
                "--body-mechanics",
                "heel-to-toe footfalls,small natural arm swing",
                "--secondary-motion",
                "robe trails softly behind the body,brief settling pause",
                "--speed",
                "slow",
                "--intensity",
                "low",
                "--best-clip-duration",
                "4",
            ]
        )
        self.assertEqual(create_code, 0)
        self.assertIn("motion_object", created)

        bind_code, binding = self._run_cli(
            [
                "world-studio",
                "bind-motion-object",
                "--world-id",
                world["world_id"],
                "--motion-id",
                created["motion_object"]["motion_id"],
                "--target-kind",
                "character",
                "--target-id",
                "default",
                "--when-tags",
                "man,walk,crosses",
            ]
        )
        self.assertEqual(bind_code, 0)
        self.assertIn("binding", binding)

        inspect_code, inspected = self._run_cli(["world-studio", "inspect-motion-system", "--world-id", world["world_id"]])
        self.assertEqual(inspect_code, 0)
        self.assertEqual(inspected["motion_object_count"], 1)

        plan_code, planned = self._run_cli(
            [
                "world-studio",
                "compile-motion-plan",
                "--world-id",
                world["world_id"],
                "--scene-text",
                "A solitary man crosses the courtyard.",
                "--duration-seconds",
                "4",
            ]
        )
        self.assertEqual(plan_code, 0)
        self.assertEqual(planned["selected_motion_count"], 1)

        server, thread, base_url = self._start_server()
        try:
            status, api_created = self._json_request(
                f"{base_url}/api/world-studio/motion-object",
                method="POST",
                payload={
                    "world_id": world["world_id"],
                    "label": "Gentle Forward Drift",
                    "scope": "camera",
                    "intent": "Support the subject with quiet forward drift.",
                    "primary_action": "gently drifts forward on axis",
                    "body_mechanics": ["locked horizon"],
                    "secondary_motion": ["slight settling pause"],
                    "speed": "slow",
                    "intensity": "low",
                    "best_clip_duration": 4,
                },
            )
            self.assertEqual(status, 200)
            self.assertIn("motion_object", api_created)

            status, api_system = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/motion"
            )
            self.assertEqual(status, 200)
            self.assertGreaterEqual(api_system["motion_object_count"], 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_character_profile_scaffold_creates_separate_character_and_feature_objects(self) -> None:
        from conversation_os.worldbuilding_studio import (
            create_character_profile,
            inspect_character_system,
            create_world,
            update_character_feature_object,
            update_character_profile_section,
        )

        world = create_world(self.root, name="Character World", summary="A world for character semantic scaffolding.")
        created = create_character_profile(
            self.root,
            world["world_id"],
            name="The Traveler",
            summary="A solitary draped man moving through ceremonial architectural states.",
            role="primary_traveler",
        )

        self.assertEqual(created["profile"]["name"], "The Traveler")
        self.assertEqual(len(created["starter_features"]), 6)
        self.assertTrue(created["profile"]["feature_object_ids"])
        self.assertIn("identity", created["profile"]["sections"])
        self.assertIn("movement_identity", created["profile"]["sections"])

        profile = update_character_profile_section(
            self.root,
            world["world_id"],
            created["character_id"],
            section="identity",
            value={"one_line_essence": "A ceremonial traveler who never hurries but is always arriving."},
        )
        feature = update_character_feature_object(
            self.root,
            world["world_id"],
            created["starter_features"][0]["feature_id"],
            summary="Tall narrow silhouette, draped robe mass, face usually withheld by distance or shadow.",
            trait_values=["tall narrow silhouette", "draped robe mass", "withheld face"],
        )
        system = inspect_character_system(self.root, world["world_id"])

        self.assertEqual(profile["profile"]["sections"]["identity"]["one_line_essence"], "A ceremonial traveler who never hurries but is always arriving.")
        self.assertIn("tall narrow silhouette", feature["feature_object"]["trait_values"])
        self.assertEqual(system["character_profile_count"], 1)
        self.assertEqual(system["feature_object_count"], 6)
        self.assertEqual(system["profiles"][0]["name"], "The Traveler")

    def test_compile_scene_includes_selected_character_semantic_pack(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene,
            create_character_profile,
            create_world,
            get_packet_bundle,
            update_character_feature_object,
            update_character_profile_section,
        )

        world = create_world(self.root, name="Character Packet", summary="A world where character semantics should reach generation.")
        created = create_character_profile(
            self.root,
            world["world_id"],
            name="The Traveler",
            summary="A solitary draped man crossing ceremonial thresholds.",
            role="primary_traveler",
        )
        update_character_profile_section(
            self.root,
            world["world_id"],
            created["character_id"],
            section="movement_identity",
            value={"posture": "upright but unassertive", "pace": "slow measured pace"},
        )
        movement_feature = next(
            row for row in created["starter_features"] if row["feature_type"] == "movement_signature"
        )
        update_character_feature_object(
            self.root,
            world["world_id"],
            movement_feature["feature_id"],
            summary="Measured forward walk with calm weight shifts and no wasted gesture.",
            trait_values=["measured forward walk", "calm weight shifts", "no wasted gesture"],
        )

        compiled = compile_scene(
            self.root,
            world["world_id"],
            "The Traveler crosses the silent courtyard toward the threshold.",
            duration_seconds=4,
            aspect_ratio="16:9",
            model_preference="seedance_2_0",
        )
        bundle = get_packet_bundle(self.root, compiled["packet_id"])

        self.assertIn("character_profiles", bundle["context_packet"])
        self.assertEqual(bundle["context_packet"]["character_profiles"][0]["name"], "The Traveler")
        self.assertIn("Character semantic pack:", bundle["higgsfield_execution_packet"]["compiled_prompt"])
        self.assertIn("measured forward walk", bundle["higgsfield_execution_packet"]["compiled_prompt"])
        self.assertIn("characterProfiles", bundle["remotion_composition_props"]["props"])

    def test_cli_and_api_character_routes_return_structured_payloads(self) -> None:
        from conversation_os.worldbuilding_studio import create_world

        world = create_world(self.root, name="Character Routes", summary="A world for character route coverage.")
        create_code, created = self._run_cli(
            [
                "world-studio",
                "create-character-profile",
                "--world-id",
                world["world_id"],
                "--name",
                "The Traveler",
                "--summary",
                "A solitary draped man crossing ceremonial space.",
                "--role",
                "primary_traveler",
            ]
        )
        self.assertEqual(create_code, 0)
        self.assertIn("profile", created)

        inspect_code, inspected = self._run_cli(["world-studio", "inspect-character-system", "--world-id", world["world_id"]])
        self.assertEqual(inspect_code, 0)
        self.assertEqual(inspected["character_profile_count"], 1)

        update_code, updated = self._run_cli(
            [
                "world-studio",
                "update-character-profile",
                "--world-id",
                world["world_id"],
                "--character-id",
                created["character_id"],
                "--section",
                "identity",
                "--value-json",
                '{"one_line_essence": "A man who moves like ritual has already taught him patience."}',
            ]
        )
        self.assertEqual(update_code, 0)
        self.assertIn("one_line_essence", updated["profile"]["sections"]["identity"])

        server, thread, base_url = self._start_server()
        try:
            status, api_system = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/characters"
            )
            self.assertEqual(status, 200)
            self.assertEqual(api_system["character_profile_count"], 1)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_cli_and_api_visual_world_surfaces_return_structured_payloads(self) -> None:
        from conversation_os.worldbuilding_studio import create_world

        world = create_world(self.root, name="Visual Surface", summary="A world for visual command coverage.")
        image_path = self.root / "visual-cli-reference.png"
        image_path.write_bytes(b"png")

        cli_code, cli_visual = self._run_cli(
            [
                "world-studio",
                "ingest-visual-reference",
                "--world-id",
                world["world_id"],
                "--source-path",
                str(image_path),
                "--source-label",
                "visual-cli-reference",
                "--note",
                "I like pearl mineral walls, subtractive apertures, and surgical glare.",
                "--categories",
                "architecture_style,material_style,lighting_language",
            ]
        )
        self.assertEqual(cli_code, 0)
        self.assertIn("reference", cli_visual)

        inspect_code, inspected = self._run_cli(
            ["world-studio", "inspect-visual-world", "--world-id", world["world_id"]]
        )
        self.assertEqual(inspect_code, 0)
        self.assertEqual(inspected["reference_count"], 1)

        context_code, context = self._run_cli(
            [
                "world-studio",
                "compile-visual-context",
                "--world-id",
                world["world_id"],
                "--query-text",
                "A corridor cut into pearl mineral walls.",
            ]
        )
        self.assertEqual(context_code, 0)
        self.assertTrue(context["active_categories"])

        server, thread, base_url = self._start_server()
        try:
            status, api_visual = self._json_request(
                f"{base_url}/api/world-studio/ingest-visual-reference",
                method="POST",
                payload={
                    "world_id": world["world_id"],
                    "source_path": str(image_path),
                    "source_label": "api-visual-reference",
                    "note": "I like root-lattice flora and translucent spores.",
                    "categories": ["flora_style"],
                },
            )
            self.assertEqual(status, 200)
            self.assertIn("reference", api_visual)

            status, visual_world = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/visual"
            )
            self.assertEqual(status, 200)
            self.assertGreaterEqual(visual_world["reference_count"], 2)

            status, visual_context = self._json_request(
                f"{base_url}/api/world-studio/compile-visual-context",
                method="POST",
                payload={"world_id": world["world_id"], "query_text": "A root-lattice corridor with spores."},
            )
            self.assertEqual(status, 200)
            self.assertTrue(visual_context["selected_references"])
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_cli_and_api_execute_packet_surfaces_return_execution_records(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene_from_canon,
            create_world,
            generate_canon,
            ingest_evidence,
        )

        world = create_world(self.root, name="Execution Harbor", summary="A harbor for executor testing.")
        ingest_evidence(
            self.root,
            world["world_id"],
            source_text=(
                "Ira maps a membrane harbor inside a droplet basin. "
                "A pressure fork reveals safe passages. "
                "Every current records the last vow spoken near it. "
                "The visual language should be bright uncanny with lucid greens."
            ),
            source_label="execution-harbor-seed",
        )
        generate_canon(self.root, world["world_id"])
        packet = compile_scene_from_canon(
            self.root,
            world["world_id"],
            "Ira follows the pressure fork into the harbor.",
        )

        cli_code, cli_execution = self._run_cli(
            ["world-studio", "execute-packet", "--packet-id", packet["packet_id"], "--mode", "prepared"]
        )
        self.assertEqual(cli_code, 0)
        self.assertEqual(cli_execution["status"], "prepared")

        server, thread, base_url = self._start_server()
        try:
            status, api_execution = self._json_request(
                f"{base_url}/api/world-studio/execute-packet",
                method="POST",
                payload={"packet_id": packet["packet_id"], "mode": "prepared"},
            )
            self.assertEqual(status, 200)
            self.assertEqual(api_execution["status"], "prepared")

            status, executions = self._json_request(
                f"{base_url}/api/world-studio/executions?packet_id={packet['packet_id']}"
            )
            self.assertEqual(status, 200)
            self.assertEqual(executions["packet_id"], packet["packet_id"])
            self.assertGreaterEqual(executions["count"], 2)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_cli_world_os_commands_return_json_payloads(self) -> None:
        create_code, created = self._run_cli(["world-studio", "create-world", "--name", "Glass Orchard"])
        self.assertEqual(create_code, 0)

        ingest_code, ingested = self._run_cli(
            [
                "world-studio",
                "ingest-evidence",
                "--world-id",
                created["world_id"],
                "--source-text",
                (
                    "Nera tends an orchard of glass spores inside a droplet city. "
                    "A root-key opens sealed membranes. "
                    "Each spoken promise becomes a visible path in the air. "
                    "The world should feel bright uncanny and precariously beautiful."
                ),
                "--source-label",
                "glass-orchard-seed",
            ]
        )
        self.assertEqual(ingest_code, 0)
        self.assertEqual(ingested["world_id"], created["world_id"])

        question_code, question = self._run_cli(
            ["world-studio", "next-question", "--world-id", created["world_id"]]
        )
        self.assertEqual(question_code, 0)
        self.assertIn("question_id", question)

        canon_code, canon = self._run_cli(
            ["world-studio", "generate-canon", "--world-id", created["world_id"]]
        )
        self.assertEqual(canon_code, 0)
        self.assertGreaterEqual(canon["canon_asset_count"], 1)

        evidence_code, evidence = self._run_cli(
            ["world-studio", "inspect-evidence", "--world-id", created["world_id"]]
        )
        self.assertEqual(evidence_code, 0)
        self.assertEqual(evidence["world_id"], created["world_id"])
        self.assertGreaterEqual(evidence["evidence_count"], 1)

        compile_code, compiled = self._run_cli(
            [
                "world-studio",
                "compile-scene-from-canon",
                "--world-id",
                created["world_id"],
                "--scene-text",
                "Nera uses the root-key to cross a promise path that is beginning to close behind her.",
            ]
        )
        self.assertEqual(compile_code, 0)
        self.assertEqual(compiled["status"], "compiled")

    def test_miniapp_world_os_api_routes(self) -> None:
        from conversation_os.worldbuilding_studio import create_world

        world = create_world(self.root, name="Membrane Harbor", summary="A harbor grown inside a living lens.")
        server, thread, base_url = self._start_server()
        try:
            status, ingested = self._json_request(
                f"{base_url}/api/world-studio/ingest-evidence",
                method="POST",
                payload={
                    "world_id": world["world_id"],
                    "source_text": (
                        "Lio maps a membrane harbor inside a droplet basin. "
                        "A pressure fork reveals safe passages. "
                        "Every current records the last vow spoken near it. "
                        "The world should feel bright uncanny with lucid greens and reflective skin."
                    ),
                    "source_label": "membrane-harbor-seed",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(ingested["world_id"], world["world_id"])

            status, evidence = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/evidence"
            )
            self.assertEqual(status, 200)
            self.assertGreaterEqual(evidence["evidence_count"], 1)

            status, question = self._json_request(
                f"{base_url}/api/world-studio/world/{world['world_id']}/next-question"
            )
            self.assertEqual(status, 200)
            self.assertIn("question_id", question)

            status, canon = self._json_request(
                f"{base_url}/api/world-studio/generate-canon",
                method="POST",
                payload={"world_id": world["world_id"]},
            )
            self.assertEqual(status, 200)
            self.assertGreaterEqual(canon["canon_asset_count"], 1)

            status, compiled = self._json_request(
                f"{base_url}/api/world-studio/compile-scene-from-canon",
                method="POST",
                payload={
                    "world_id": world["world_id"],
                    "scene_text": "Lio follows the pressure fork into the harbor and hears the water repeat a promise back to him.",
                },
            )
            self.assertEqual(status, 200)
            self.assertEqual(compiled["status"], "compiled")
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_world_studio_guide_and_browser_page_are_served(self) -> None:
        server, thread, base_url = self._start_server(REPO_ROOT / "product" / "inner_world_v1" / "miniapp")
        try:
            status, guide = self._json_request(f"{base_url}/api/world-studio/guide")
            self.assertEqual(status, 200)
            self.assertEqual(guide["browser_entry"]["path"], "/world-studio.html")
            self.assertIn("populate-start", "\n".join(guide["cli_commands"]))
            self.assertIn("inspect-graph", "\n".join(guide["cli_commands"]))
            self.assertIn("ingest-evidence", "\n".join(guide["cli_commands"]))
            self.assertIn("generate-canon", "\n".join(guide["cli_commands"]))
            self.assertIn("compile-scene-from-canon", "\n".join(guide["cli_commands"]))
            self.assertTrue(any(route["path"].endswith("/graph") for route in guide["api_routes"]))
            self.assertIn("operator_manuscript_path", guide["docs"])
            self.assertIn("handoff_prompt", guide)

            with urllib_request.urlopen(f"{base_url}/world-studio.html") as response:
                self.assertEqual(response.status, 200)
                html = response.read().decode("utf-8")
            self.assertIn("World Studio", html)
            self.assertIn("./world-studio.js", html)
            self.assertIn("graph-canvas", html)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_asset_recording_and_evaluation_log_generation_results(self) -> None:
        from conversation_os.worldbuilding_studio import (
            compile_scene,
            create_demo_world,
            evaluate_output,
            record_generation_asset,
            worldbuilding_studio_dir,
        )

        world = create_demo_world(self.root)
        packet = compile_scene(self.root, world["world_id"], "Mina recognizes betrayal in a mirror.")
        asset = record_generation_asset(
            self.root,
            packet["packet_id"],
            provider="higgsfield",
            kind="remote_media_url",
            url="https://example.com/generated.mp4",
            media_type="video",
            metadata={"duration_seconds": 12, "asset_role": "hero_clip"},
        )
        evaluation = evaluate_output(
            self.root,
            packet["packet_id"],
            observed_text="The clip holds on a fractured mirror, delays the reaction, and avoids fast jump cuts.",
        )

        self.assertEqual(asset["packet_id"], packet["packet_id"])
        self.assertEqual(asset["provider"], "higgsfield")
        self.assertGreaterEqual(evaluation["score"], 0.7)
        rows = read_jsonl(worldbuilding_studio_dir(self.root) / "events.jsonl")
        self.assertTrue(any(row["event_type"] == "asset_recorded" for row in rows))
        self.assertTrue(any(row["event_type"] == "output_evaluated" for row in rows))

    def test_miniapp_world_studio_api_routes(self) -> None:
        server, thread, base_url = self._start_server()
        try:
            status, demo = self._json_request(f"{base_url}/api/world-studio/demo", method="POST")
            self.assertEqual(status, 200)
            self.assertEqual(demo["packet"]["status"], "compiled")

            status, worlds = self._json_request(f"{base_url}/api/world-studio/worlds")
            self.assertEqual(status, 200)
            self.assertEqual(worlds["count"], 1)

            world_id = worlds["worlds"][0]["world_id"]
            status, world = self._json_request(f"{base_url}/api/world-studio/world/{world_id}")
            self.assertEqual(status, 200)
            self.assertEqual(world["world_id"], world_id)
            self.assertIn("taste_profile", world)

            status, graph = self._json_request(f"{base_url}/api/world-studio/world/{world_id}/graph")
            self.assertEqual(status, 200)
            self.assertEqual(graph["world_id"], world_id)
            self.assertIn("nodes", graph)
            self.assertIn("edges", graph)
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=5)

    def test_mcp_wrapper_builds_world_studio_server(self) -> None:
        from conversation_os.worldbuilding_studio_mcp import build_worldbuilding_studio_mcp_server

        server = build_worldbuilding_studio_mcp_server(self.root)
        self.assertIsNotNone(server)
