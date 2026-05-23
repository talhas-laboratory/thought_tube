import json
import os
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from conversation_os.cli import guarded_main, init_repo, main
from conversation_os.codebase_overview import load_module_manifests, lookup_codebase, refresh_codebase_overview
from conversation_os.engineering_guard import assess_change_request
from conversation_os.storage import read_json


REPO_ROOT = Path(__file__).resolve().parents[1]


class EngineeringGuardTestCase(unittest.TestCase):
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
        shutil.copytree(REPO_ROOT / "context" / "substrate", self.root / "context" / "substrate")
        os.symlink(REPO_ROOT / "src", self.root / "src", target_is_directory=True)
        os.symlink(REPO_ROOT / "tools", self.root / "tools", target_is_directory=True)
        init_repo(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _run_cli(self, args: list[str]) -> tuple[int, dict]:
        output = StringIO()
        old = os.getcwd()
        os.chdir(self.root)
        try:
            with redirect_stdout(output):
                exit_code = main(args)
        finally:
            os.chdir(old)
        return exit_code, json.loads(output.getvalue())

    def _run_guarded_cli(self, args: list[str]) -> tuple[int, dict]:
        output = StringIO()
        old = os.getcwd()
        os.chdir(self.root)
        try:
            with redirect_stdout(output):
                exit_code = guarded_main(args)
        finally:
            os.chdir(old)
        return exit_code, json.loads(output.getvalue())

    def test_refresh_codebase_overview_writes_generated_artifacts(self) -> None:
        result = refresh_codebase_overview(self.root)

        self.assertGreater(result["entry_count"], 5)
        self.assertGreater(result["module_manifest_count"], 5)
        overview_path = self.root / "context" / "substrate" / "CODEBASE_OVERVIEW.md"
        atlas_path = self.root / "context" / "substrate" / "CODEBASE_ATLAS.md"
        agent_brief_path = self.root / "context" / "substrate" / "AGENT_OPERATING_BRIEF.md"
        map_path = self.root / "context" / "substrate" / "codebase_map.json"
        module_registry_path = self.root / "context" / "substrate" / "registry" / "module_registry.json"
        module_browse_path = self.root / "context" / "substrate" / "registry" / "module_browse_map.json"
        dependency_graph_path = self.root / "context" / "substrate" / "registry" / "dependency_graph.json"
        surface_index_path = self.root / "context" / "substrate" / "registry" / "surface_index.json"
        owner_index_path = self.root / "context" / "substrate" / "registry" / "owner_index.json"
        self.assertTrue(overview_path.exists())
        self.assertTrue(atlas_path.exists())
        self.assertTrue(agent_brief_path.exists())
        self.assertTrue(map_path.exists())
        self.assertTrue(module_registry_path.exists())
        self.assertTrue(module_browse_path.exists())
        self.assertTrue(dependency_graph_path.exists())
        self.assertTrue(surface_index_path.exists())
        self.assertTrue(owner_index_path.exists())
        payload = read_json(map_path)
        self.assertIn("entries", payload)
        self.assertIn("module_manifest_count", payload)
        self.assertTrue(any(entry["path"] == "src/conversation_os/personal_interface.py" for entry in payload["entries"]))
        personal_entry = next(
            entry for entry in payload["entries"] if entry["path"] == "src/conversation_os/personal_interface.py"
        )
        self.assertEqual(personal_entry["module_manifest"]["module_id"], "surface.personal.personal_interface")
        atlas = atlas_path.read_text(encoding="utf-8")
        self.assertIn("`surface.personal.personal_interface`", atlas)
        self.assertIn("#### `builder.codebase.codebase_overview`", atlas)
        agent_brief = agent_brief_path.read_text(encoding="utf-8")
        self.assertIn("../../README.md", agent_brief)
        self.assertIn("./CODEBASE_ATLAS.md", agent_brief)
        self.assertIn("2026-04-14-inner-world-openclaw-server-architecture.md", agent_brief)
        dependency_graph = read_json(dependency_graph_path)
        self.assertIn("nodes", dependency_graph)
        self.assertIn("edges", dependency_graph)
        surface_index = read_json(surface_index_path)
        self.assertIn("surfaces", surface_index)
        owner_index = read_json(owner_index_path)
        self.assertIn("owners", owner_index)

    def test_lookup_codebase_returns_relevant_paths(self) -> None:
        refresh_codebase_overview(self.root)

        results = lookup_codebase(self.root, "personal interface rewrite mcp", limit=5)

        self.assertTrue(results)
        top_paths = [item["path"] for item in results]
        self.assertIn("src/conversation_os/personal_interface.py", top_paths)
        self.assertIn("src/conversation_os/personal_interface_mcp.py", top_paths)
        personal_result = next(item for item in results if item["path"] == "src/conversation_os/personal_interface.py")
        self.assertEqual(personal_result["module_manifest"]["module_id"], "surface.personal.personal_interface")

    def test_load_module_manifests_surfaces_seed_tranche_and_missing_modules(self) -> None:
        module_index = load_module_manifests(self.root)

        self.assertGreaterEqual(module_index["manifest_count"], 50)
        self.assertTrue(any(item["module_id"] == "kernel.library.library_tracker" for item in module_index["manifests"]))
        self.assertTrue(any(item["module_id"] == "kernel.knowledge.knowledge_layer" for item in module_index["manifests"]))
        self.assertTrue(any(item["module_id"] == "kernel.routing.task_pack_routing" for item in module_index["manifests"]))
        self.assertFalse(module_index["errors"])
        self.assertFalse(module_index["warnings"])
        self.assertFalse(module_index["missing_paths"])

    def test_assess_change_request_requires_clear_purpose_and_scope(self) -> None:
        refresh_codebase_overview(self.root)

        assessment = assess_change_request(
            self.root,
            request="add a new system",
            purpose="make it better",
            proposed_paths=[],
        )

        self.assertFalse(assessment["ready"])
        self.assertEqual(assessment["status"], "needs_scope")
        self.assertTrue(assessment["warnings"])
        self.assertTrue(any("purpose" in warning.lower() for warning in assessment["warnings"]))

    def test_assess_change_request_routes_to_relevant_existing_modules(self) -> None:
        refresh_codebase_overview(self.root)

        assessment = assess_change_request(
            self.root,
            request="adapt outgoing replies through the personal interface mcp server",
            purpose="preserve user flow while keeping rewrite logic in one place",
            proposed_paths=[
                "src/conversation_os/personal_interface.py",
                "src/conversation_os/personal_interface_mcp.py",
            ],
        )

        self.assertTrue(assessment["ready"])
        self.assertEqual(assessment["status"], "ready")
        recommended = [item["path"] for item in assessment["recommended_targets"]]
        self.assertIn("src/conversation_os/personal_interface.py", recommended)
        self.assertIn("src/conversation_os/personal_interface_mcp.py", recommended)
        self.assertTrue(assessment["questions_to_answer"])
        self.assertTrue(assessment["minimality_checks"])

    def test_cli_repo_overview_and_engineering_guard_commands(self) -> None:
        exit_code, overview = self._run_cli(["repo-overview", "refresh"])
        self.assertEqual(exit_code, 0)
        self.assertGreater(overview["entry_count"], 5)

        exit_code, validation = self._run_cli(["repo-overview", "validate"])
        self.assertEqual(exit_code, 0)
        self.assertGreaterEqual(validation["module_manifest_count"], 50)
        self.assertEqual(validation["error_count"], 0)
        self.assertEqual(validation["warning_count"], 0)
        self.assertEqual(validation["missing_manifest_count"], 0)

        exit_code, lookup = self._run_cli(["repo-overview", "lookup", "--query", "conversation os cli", "--limit", "3"])
        self.assertEqual(exit_code, 0)
        self.assertTrue(lookup["results"])

        exit_code, assessment = self._run_cli(
            [
                "engineering-guard",
                "assess",
                "--request",
                "add a clean trigger for personal interface rewrites during conversation",
                "--purpose",
                "centralize context wiring and keep the host integration thin",
                "--proposed-paths",
                "src/conversation_os/personal_interface.py,src/conversation_os/personal_interface_mcp.py",
            ]
        )
        self.assertEqual(exit_code, 0)
        self.assertTrue(assessment["ready"])

    def test_guarded_cli_task_pack_reports_stale_index_blocker(self) -> None:
        from unittest import mock

        with mock.patch(
            "conversation_os.routing.validate_codebase_index",
            return_value={
                "generated_at": "2026-05-22T00:00:00+00:00",
                "module_manifest_count": 57,
                "error_count": 0,
                "warning_count": 1,
                "missing_manifest_count": 0,
                "fresh": False,
                "stale_reasons": ["Generated codebase artifacts are older than the newest tracked source or manifest."],
                "missing_artifacts": [],
                "newest_source_path": "src/conversation_os/cli.py",
                "newest_generated_path": "context/substrate/AGENT_OPERATING_BRIEF.md",
                "errors": [],
                "warnings": ["1 tracked python modules do not yet have manifests"],
                "missing_paths": [],
            },
        ):
            exit_code, payload = self._run_guarded_cli(
                ["task-pack", "build", "--task-id", "blocked-pack", "--request", "Need research routing"]
            )

        self.assertEqual(exit_code, 1)
        self.assertEqual(payload["error"], "task_pack_index_not_ready")
        self.assertIn("codebase atlas is stale or invalid", payload["message"])


if __name__ == "__main__":
    unittest.main()
