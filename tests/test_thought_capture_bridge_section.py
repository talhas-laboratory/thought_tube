"""Boundary checks for thought_capture_pwa bridge section (MTC-008)."""

from __future__ import annotations

import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PWA_ROOT = REPO_ROOT / "product" / "thought_capture_pwa"
BRIDGE_SRC = PWA_ROOT / "src" / "bridge"
CAPTURE_SRC = PWA_ROOT / "src" / "capture"
OFFLINE_SRC = PWA_ROOT / "src" / "offline"


class ThoughtCaptureBridgeSectionTests(unittest.TestCase):
    def test_section_adapter_facade_exists(self) -> None:
        self.assertTrue((BRIDGE_SRC / "section-adapter.ts").is_file())
        self.assertTrue((BRIDGE_SRC / "types.ts").is_file())
        self.assertTrue((BRIDGE_SRC / "index.ts").is_file())

    def test_provisional_bridge_client_removed(self) -> None:
        self.assertFalse((BRIDGE_SRC / "bridge-client.ts").exists())

    def test_sync_replay_uses_section_adapter(self) -> None:
        source = (OFFLINE_SRC / "sync-replay.ts").read_text(encoding="utf-8")
        self.assertIn('from "../bridge"', source)
        self.assertNotIn("bridge-client", source)

    def test_capture_ui_does_not_import_bridge_internals(self) -> None:
        for path in CAPTURE_SRC.glob("**/*.{ts,tsx}"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("bridge-client", text, msg=str(path))
            self.assertNotIn("bridge/transport", text, msg=str(path))
            if "from \"../bridge" in text or "from '../bridge" in text:
                self.fail(f"capture module imports bridge directly: {path}")

    def test_bridge_core_does_not_import_pwa_code(self) -> None:
        conversation_os = REPO_ROOT / "src" / "conversation_os"
        hits: list[str] = []
        for path in conversation_os.glob("**/*.py"):
            text = path.read_text(encoding="utf-8")
            if "from product.thought_capture" in text or "import thought_capture" in text:
                hits.append(str(path.relative_to(REPO_ROOT)))
        self.assertEqual(hits, [])


if __name__ == "__main__":
    unittest.main()
