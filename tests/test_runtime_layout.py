import tempfile
import unittest
from pathlib import Path

from conversation_os.runtime_layout import product_artifact_dir, product_config_dir, product_runtime_dir, product_source_dir


class RuntimeLayoutTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_runtime_dir_falls_back_to_legacy_product_path(self) -> None:
        legacy = self.root / "product" / "inner_world_v1" / "data"
        legacy.mkdir(parents=True, exist_ok=True)

        self.assertEqual(product_runtime_dir(self.root, "inner_world_v1", "data"), legacy)

    def test_runtime_dir_prefers_canonical_runtime_path_when_present(self) -> None:
        canonical = self.root / "runtime" / "product_state" / "inner_world_v1" / "data"
        canonical.mkdir(parents=True, exist_ok=True)

        self.assertEqual(product_runtime_dir(self.root, "inner_world_v1", "data"), canonical)

    def test_artifact_dir_prefers_canonical_artifact_path_when_present(self) -> None:
        canonical = self.root / "artifacts" / "exports" / "inner_world_v1" / "exports"
        canonical.mkdir(parents=True, exist_ok=True)

        self.assertEqual(product_artifact_dir(self.root, "inner_world_v1", "exports"), canonical)

    def test_source_and_config_dirs_remain_under_product_tree(self) -> None:
        self.assertEqual(product_source_dir(self.root, "personal_interface_v1"), self.root / "product" / "personal_interface_v1")
        self.assertEqual(product_config_dir(self.root, "personal_interface_v1"), self.root / "product" / "personal_interface_v1" / "config")


if __name__ == "__main__":
    unittest.main()
