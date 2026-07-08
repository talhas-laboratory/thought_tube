import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from conversation_os.cli import init_repo
from conversation_os.mtsf_shape_eval import run_shape_utility_evals

REPO_ROOT = Path(__file__).resolve().parents[1]


class MtsfShapeEvalTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        init_repo(self.root)
        docs_link = self.root / "docs"
        if docs_link.exists() or docs_link.is_symlink():
            if docs_link.is_symlink() or docs_link.is_file():
                docs_link.unlink()
            else:
                shutil.rmtree(docs_link)
        os.symlink(REPO_ROOT / "docs", docs_link, target_is_directory=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_run_shape_utility_evals_executes_suite(self) -> None:
        result = run_shape_utility_evals(self.root, llm_preference="auto")
        self.assertEqual(result["suite"], "shape-utility")
        self.assertGreaterEqual(result["total"], 5)
        self.assertIn("interpretation", result)
        self.assertIn("runs", result)
        for row in result["runs"]:
            self.assertIn("metrics", row)
            self.assertIn("kind", row)

    def test_negative_grocery_control_is_sparse(self) -> None:
        result = run_shape_utility_evals(self.root, llm_preference="auto")
        grocery = next(row for row in result["runs"] if row["id"] == "eval-utility-negative-grocery")
        self.assertLessEqual(grocery["metrics"].get("entity_count", 99), 3)


if __name__ == "__main__":
    unittest.main()
