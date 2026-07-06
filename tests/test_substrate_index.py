import json
import tempfile
import unittest
from pathlib import Path

from tools import substrate_index as substrate_index_module


class SubstrateIndexTestCase(unittest.TestCase):
    def test_refresh_generates_purpose_artifacts(self) -> None:
        substrate_index_module.refresh()
        purpose_index = substrate_index_module.SUBSTRATE_ROOT / "generated" / "purpose-index.json"
        self.assertTrue(purpose_index.exists())
        payload = json.loads(purpose_index.read_text(encoding="utf-8"))
        self.assertGreaterEqual(payload["count"], 10)
        mtsf_graph = substrate_index_module.PURPOSE_ROOT / "structure.mtsf.graph.md"
        self.assertTrue(mtsf_graph.exists())
        text = mtsf_graph.read_text(encoding="utf-8")
        self.assertIn("assertion_store", text)
        self.assertIn("content_graph", text)

    def test_agent_index_links_purpose_artifacts(self) -> None:
        substrate_index_module.refresh()
        agent_index = (substrate_index_module.SUBSTRATE_ROOT / "AGENT_INDEX.md").read_text(encoding="utf-8")
        self.assertIn("structure.mtsf.system-map", agent_index)
        self.assertIn("purpose_artifact", agent_index)

    def test_structure_family_index_exists(self) -> None:
        substrate_index_module.refresh()
        family_index = substrate_index_module.FAMILIES_ROOT / "structure" / "INDEX.md"
        self.assertTrue(family_index.exists())
        self.assertIn("MTSF Progressive Graph", family_index.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
