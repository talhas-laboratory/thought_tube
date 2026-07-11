from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.bridge_session_retention import (
    compact_session_trace,
    retention_config,
    slim_control_packet,
    truncate_turn_text,
)
from conversation_os.bridge_session_tracking import (
    record_assistant_turn,
    start_bridge_session,
)
from conversation_os.bridge_prepare import prepare_turn
from conversation_os.storage import read_jsonl
from conversation_os.bridge_session_tracking import session_trace_path


class BridgeSessionRetentionTestCase(unittest.TestCase):
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
                        "tracking": {
                            "require_active_session": True,
                            "retention": {
                                "max_assistant_text_chars": 100,
                                "max_stored_turns": 2,
                                "compact_after_turns": 100,
                            },
                        },
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_truncate_and_slim_packet(self) -> None:
        cfg = retention_config(self.root)
        long_text = "x" * 200
        truncated = truncate_turn_text(long_text, actor="assistant", config=cfg)
        self.assertLessEqual(len(truncated), 100)
        slim = slim_control_packet(
            {
                "active_topic": "topic",
                "user_goal": "build",
                "context_policy": {"mode": "semantic_narrow", "depth_mode": "contextual", "extra": "drop"},
                "validation_warnings": ["warn"],
            }
        )
        self.assertEqual(slim["active_topic"], "topic")
        self.assertNotIn("validation_warnings", slim)

    def test_record_assistant_turn_and_compact(self) -> None:
        start_bridge_session(self.root, session_id="session-ret-001", surface="cursor")
        prepare_turn(
            self.root,
            raw_text="user turn",
            session_id="session-ret-001",
            surface="cursor",
            write_steering_file=False,
        )
        result = record_assistant_turn(
            self.root,
            session_id="session-ret-001",
            response_text="assistant reply",
        )
        self.assertEqual(result["session"]["assistant_turn_count"], 1)

        duplicate = record_assistant_turn(
            self.root,
            session_id="session-ret-001",
            response_text="assistant reply",
        )
        self.assertEqual(duplicate.get("skipped"), "duplicate_assistant_turn")

        prepare_turn(
            self.root,
            raw_text="user turn 2",
            session_id="session-ret-001",
            surface="cursor",
            write_steering_file=False,
        )
        record_assistant_turn(self.root, session_id="session-ret-001", response_text="assistant reply 2")

        compacted = compact_session_trace(self.root, "session-ret-001", keep_turns=2)
        self.assertGreater(compacted["compacted"], 0)
        trace_rows = read_jsonl(session_trace_path(self.root, "session-ret-001"))
        turn_rows = [row for row in trace_rows if row.get("type") == "turn"]
        self.assertLessEqual(len(turn_rows), 2)


if __name__ == "__main__":
    unittest.main()
