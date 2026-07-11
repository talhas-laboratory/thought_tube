import os
import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import main
from conversation_os.repo_index import (
    classify_repo_path,
    get_repo_index_health,
    build_runtime_migration_plan,
    refresh_repo_index,
    validate_repo_index,
    watch_repo_index,
)


class RepoIndexTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        for path in [
            self.root / "src" / "conversation_os",
            self.root / "tools",
            self.root / "docs" / "plans",
            self.root / "product" / "inner_world_v1" / "data",
            self.root / "product" / "inner_world_v1" / "config",
            self.root / "context" / "substrate" / "modules",
        ]:
            path.mkdir(parents=True, exist_ok=True)

        (self.root / "AGENTS.md").write_text("# agents\n", encoding="utf-8")
        (self.root / "TENETS.md").write_text("# tenets\n", encoding="utf-8")
        (self.root / "pyproject.toml").write_text("[project]\nname='test'\n", encoding="utf-8")
        (self.root / "src" / "conversation_os" / "sample.py").write_text("def sample():\n    return 'ok'\n", encoding="utf-8")
        (self.root / "tools" / "sample_tool.py").write_text("print('ok')\n", encoding="utf-8")
        (self.root / "docs" / "plans" / "plan.md").write_text("# plan\n", encoding="utf-8")
        (self.root / "product" / "inner_world_v1" / "config" / "settings.json").write_text("{}\n", encoding="utf-8")
        (self.root / "product" / "inner_world_v1" / "data" / "runtime.json").write_text("{}\n", encoding="utf-8")
        (
            self.root / "context" / "substrate" / "modules" / "sample.json"
        ).write_text(
            json.dumps(
                {
                    "module_id": "kernel.sample.sample",
                    "path": "src/conversation_os/sample.py",
                    "layer": "kernel",
                    "owner": "test",
                    "purpose": "test module",
                    "status": "active",
                    "version": "1.0.0",
                    "public_api": ["sample"],
                    "contains": ["sample"],
                    "depends_on": [],
                    "feeds_into": [],
                    "inputs": [],
                    "outputs": [],
                    "state_owned": [],
                    "surfaces_using": [],
                }
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_classify_repo_path_distinguishes_source_docs_and_runtime_state(self) -> None:
        self.assertEqual(classify_repo_path("src/conversation_os/sample.py")["class"], "source")
        self.assertEqual(classify_repo_path("docs/plans/plan.md")["class"], "docs")
        self.assertEqual(classify_repo_path("product/inner_world_v1/data/runtime.json")["class"], "runtime_state")
        self.assertEqual(classify_repo_path("context/substrate/modules/sample.json")["class"], "contract")

    def test_refresh_repo_index_writes_registry_artifacts(self) -> None:
        result = refresh_repo_index(self.root)

        self.assertGreater(result["summary"]["classified_path_count"], 0)
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "repo_index.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "docs_index.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "product_surface_index.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "state_boundary_index.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "artifact_index.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "migration_candidates.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "registry" / "runtime_migration_plan.json").exists())
        self.assertTrue((self.root / "context" / "substrate" / "RUNTIME_MIGRATION_PLAN.md").exists())
        self.assertTrue((self.root / "context" / "substrate" / "REPO_ORGANIZATION.md").exists())

    def test_validate_repo_index_requires_refresh(self) -> None:
        validation = validate_repo_index(self.root)
        self.assertFalse(validation["fresh"])
        self.assertTrue(validation["missing_artifacts"])

    def test_repo_index_health_exposes_migration_candidates(self) -> None:
        refresh_repo_index(self.root)
        health = get_repo_index_health(self.root)

        self.assertTrue(health["fresh"])
        self.assertIn("migration_candidates", health)
        self.assertIn("docs_archive_candidates", health["migration_candidates"])
        self.assertIn("runtime_migration_plan", health)
        self.assertGreater(len(health["runtime_migration_plan"]["tranches"]), 0)

    def test_build_runtime_migration_plan_maps_product_runtime_families(self) -> None:
        refresh_repo_index(self.root)
        plan = build_runtime_migration_plan(self.root)

        self.assertEqual(plan["status"], "proposed")
        move = plan["directory_moves"][0]
        self.assertEqual(move["source"], "product/inner_world_v1/data")
        self.assertEqual(move["target"], "runtime/product_state/inner_world_v1/data")
        self.assertEqual(move["class"], "runtime_state")

    def test_watch_repo_index_refreshes_when_inputs_change(self) -> None:
        result = watch_repo_index(self.root, interval=0.0, max_iterations=1)
        self.assertEqual(result["refresh_count"], 1)

        (self.root / "docs" / "plans" / "plan.md").write_text("# updated\n", encoding="utf-8")
        result = watch_repo_index(self.root, interval=0.0, max_iterations=1)
        self.assertGreaterEqual(result["refresh_count"], 1)

    def test_cli_repo_index_refresh_and_validate(self) -> None:
        current = Path.cwd()
        try:
            os.chdir(self.root)
            refresh_exit_code = main(["repo-index", "refresh"])
            validate_exit_code = main(["repo-index", "validate"])
            health_exit_code = main(["repo-index", "health"])
            plan_exit_code = main(["repo-index", "plan"])
        finally:
            os.chdir(current)

        self.assertEqual(refresh_exit_code, 0)
        self.assertEqual(validate_exit_code, 0)
        self.assertEqual(health_exit_code, 0)
        self.assertEqual(plan_exit_code, 0)


if __name__ == "__main__":
    unittest.main()
