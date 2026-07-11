from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.knowledge_layer import load_semantic_capsules
from conversation_os.runtime_layout import product_runtime_dir


class KnowledgeLayerRuntimePathsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_load_semantic_capsules_reads_canonical_runtime_path(self) -> None:
        canonical = self.root / "runtime" / "product_state" / "inner_world_v1" / "data"
        canonical.mkdir(parents=True)
        row = {
            "capsule_id": "cap-001",
            "label": "bridge capsule",
            "summary": "retrieval fixture",
            "source_refs": [],
        }
        (canonical / "semantic_capsules.jsonl").write_text(json.dumps(row) + "\n", encoding="utf-8")

        self.assertEqual(product_runtime_dir(self.root, "inner_world_v1", "data"), canonical)
        self.assertEqual(len(load_semantic_capsules(self.root)), 1)
        self.assertEqual(load_semantic_capsules(self.root)[0]["capsule_id"], "cap-001")


if __name__ == "__main__":
    unittest.main()
