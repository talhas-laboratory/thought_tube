from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.bridge_prepare import prepare_turn
from conversation_os.bridge_session_tracking import (
    end_bridge_session,
    get_bridge_session_trace,
    list_bridge_sessions,
    start_bridge_session,
)
from conversation_os.storage import read_jsonl, session_events_path


class BridgeSessionTrackingTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "enabled": False,
                        "tracking": {"require_active_session": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_start_end_and_trace_session(self) -> None:
        session = start_bridge_session(
            self.root,
            session_id="session-track-001",
            title="Bridge tracking test",
            surface="cursor",
            workspace_id="inner_space",
        )
        self.assertEqual(session["status"], "active")
        self.assertEqual(session["turn_count"], 0)

        result = prepare_turn(
            self.root,
            raw_text="first tracked turn",
            session_id="session-track-001",
            surface="cursor",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(result["session_id"], "session-track-001")

        ended = end_bridge_session(self.root, "session-track-001", reason="test complete")
        self.assertEqual(ended["status"], "ended")
        self.assertIsNotNone(ended["ended_at"])

        trace = get_bridge_session_trace(self.root, "session-track-001")
        self.assertEqual(trace["counts"]["events"], 3)
        self.assertEqual(trace["counts"]["trace_entries"], 3)
        self.assertEqual(trace["counts"]["turn_ledger"], 1)
        self.assertEqual(trace["trace"][0]["type"], "session_start")
        self.assertEqual(trace["trace"][-1]["type"], "session_end")

        events = read_jsonl(session_events_path(self.root, "session-track-001"))
        self.assertEqual(len(events), 3)
        self.assertEqual(events[1]["content"], "first tracked turn")

    def test_prepare_turn_requires_active_session(self) -> None:
        with self.assertRaises(ValueError):
            prepare_turn(
                self.root,
                raw_text="untracked turn",
                session_id="session-missing",
                surface="cursor",
            )

    def test_list_sessions_filters_status(self) -> None:
        start_bridge_session(self.root, session_id="session-a", surface="cursor")
        start_bridge_session(self.root, session_id="session-b", surface="mcp")
        end_bridge_session(self.root, "session-b")

        active = list_bridge_sessions(self.root, status="active")
        ended = list_bridge_sessions(self.root, status="ended")
        self.assertEqual(active["count"], 1)
        self.assertEqual(ended["count"], 1)


if __name__ == "__main__":
    unittest.main()
