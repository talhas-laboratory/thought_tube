from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from conversation_os.mobile_capture_compose import (
    build_mobile_capture_reasoning_request,
    compose_mobile_capture_insertion,
    project_insertion_text_direct,
)
from conversation_os.product_inner_world import append_mobile_capture, ensure_mobile_capture_session
from conversation_os.storage import read_jsonl, session_events_path


class MobileCaptureComposeTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "chat_backend": "heuristic",
                    "bridge": {
                        "enabled": True,
                        "execution_mode": "operators",
                        "fallback": "heuristic",
                    },
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_build_mobile_capture_reasoning_request_includes_surface_hints(self) -> None:
        request = build_mobile_capture_reasoning_request(
            deposit_body="Bridge compose should stay modular.",
            local_deposit_id="deposit-local-1",
            session_id="session-1",
            provenance={"holodeck_id": "sol-frontend", "element_key": "frontend"},
            capture_mode_state={
                "mode": "exploration",
                "response_contract": "continuation_cue",
                "ai_presence": 2,
                "goal_state": "preserve_flow",
                "confidence": 0.7,
            },
            intent="nudge",
            composition_phase="capture",
        )
        self.assertEqual(request.surface, "mobile_capture")
        self.assertEqual(request.session_id, "session-1")
        self.assertEqual(request.caller_hints["local_deposit_id"], "deposit-local-1")
        self.assertEqual(request.caller_hints["query_override"], "Bridge compose should stay modular.")
        self.assertEqual(request.caller_hints["classify_mode"], "heuristic")
        self.assertEqual(request.caller_hints["context_mode"], "session_only")
        self.assertEqual(request.caller_hints["depth_mode"], "focused")

    def test_project_insertion_text_direct_maps_cue(self) -> None:
        insertion = project_insertion_text_direct(
            response_text="still open around: modular compose spine",
            capture_mode_state={
                "mode": "exploration",
                "response_contract": "continuation_cue",
                "ai_presence": 2,
                "goal_state": "preserve_flow",
                "confidence": 0.7,
            },
            composition_phase="capture",
            intent="nudge",
            deposit_body="Bridge compose should stay modular.",
        )
        self.assertIsNotNone(insertion)
        assert insertion is not None
        self.assertEqual(insertion["utterance_type"], "cue")
        self.assertIn("modular compose spine", insertion["body"])

    def test_project_insertion_text_direct_maps_shape_to_block_cluster(self) -> None:
        insertion = project_insertion_text_direct(
            response_text="facet one — facet two — facet three",
            capture_mode_state={
                "mode": "development",
                "response_contract": "structural_extraction",
                "ai_presence": 3,
                "goal_state": "build_artifact",
                "confidence": 1.0,
            },
            composition_phase="develop",
            intent="shape",
            deposit_body="Bridge compose should stay modular.",
        )
        self.assertIsNotNone(insertion)
        assert insertion is not None
        self.assertEqual(insertion["utterance_type"], "block_cluster")
        self.assertEqual(len(insertion["blocks"] or []), 3)

    @mock.patch("conversation_os.mobile_capture_compose.run_reasoning")
    def test_compose_mobile_capture_insertion_routes_through_reasoning_bridge(
        self,
        run_reasoning_mock: mock.MagicMock,
    ) -> None:
        session = ensure_mobile_capture_session(self.root)
        run_reasoning_mock.return_value = {
            "context_state": {
                "request_id": "bridge-request-1",
                "attributes": {
                    "routing_source": "agent",
                    "bridge_behavior_ids": ["creative_expansion"],
                },
            },
            "route": {"pipeline_id": "intuition_expansion_v1"},
            "result": {
                "response_text": "That makes sense — what's the part you want to capture most clearly?",
                "integration_verdict": "integrate",
            },
            "frame_bundle": {"source_refs": [f"memory/events/{session['session_id']}.jsonl"]},
        }

        result = compose_mobile_capture_insertion(
            self.root,
            deposit_body="How does the bridge pull from the ocean?",
            local_deposit_id="deposit-local-1",
            session_id=session["session_id"],
            provenance={"surface_id": "mobile_capture"},
            intent="nudge",
        )

        self.assertFalse(result["fallback"])
        self.assertIsNotNone(result["insertion"])
        self.assertEqual(result["insertion"]["utterance_type"], "cue")
        self.assertIn("capture most clearly", result["insertion"]["body"])
        self.assertEqual(result["reasoning"]["pipeline_id"], "intuition_expansion_v1")
        self.assertEqual(result["reasoning"]["routing_source"], "agent")
        run_reasoning_mock.assert_called_once()
        request = run_reasoning_mock.call_args.args[1]
        self.assertEqual(request.surface, "mobile_capture")
        self.assertEqual(request.session_id, session["session_id"])
        self.assertEqual(request.raw_text, "How does the bridge pull from the ocean?")
        self.assertTrue(
            any("ongoing conversation" in item for item in request.caller_hints["constraints"])
        )

        events = read_jsonl(session_events_path(self.root, session["session_id"]))
        self.assertEqual(events[-1]["kind"], "insertion")
        self.assertEqual(events[-1]["actor"], "assistant")

    @mock.patch("conversation_os.mobile_capture_compose.run_reasoning")
    def test_compose_failure_returns_fallback_without_raising(
        self,
        run_reasoning_mock: mock.MagicMock,
    ) -> None:
        session = ensure_mobile_capture_session(self.root)
        run_reasoning_mock.side_effect = RuntimeError("bridge unavailable")

        result = compose_mobile_capture_insertion(
            self.root,
            deposit_body="Offline thought",
            local_deposit_id="deposit-local-2",
            session_id=session["session_id"],
            intent="nudge",
        )

        self.assertTrue(result["fallback"])
        self.assertIsNone(result["insertion"])
        self.assertIn("bridge unavailable", result["error"])

    @mock.patch("conversation_os.mobile_capture_compose.run_reasoning")
    def test_compose_forces_agent_reply_when_capture_mode_suppresses_ai(
        self,
        run_reasoning_mock: mock.MagicMock,
    ) -> None:
        session = ensure_mobile_capture_session(self.root)
        run_reasoning_mock.return_value = {
            "context_state": {
                "request_id": "bridge-request-2",
                "attributes": {"routing_source": "agent", "bridge_behavior_ids": []},
            },
            "route": {"pipeline_id": "problem_reframing_v1"},
            "result": {
                "response_text": "I am following. What part should we stay with?",
                "integration_verdict": "integrate",
            },
            "frame_bundle": {"source_refs": []},
        }

        result = compose_mobile_capture_insertion(
            self.root,
            deposit_body="hmm",
            local_deposit_id="deposit-local-live",
            session_id=session["session_id"],
            capture_mode_state={
                "mode": "raw_dump",
                "response_contract": "no_response",
                "ai_presence": 0,
                "goal_state": "preserve_flow",
                "confidence": 0.9,
            },
            intent="nudge",
        )

        self.assertFalse(result["fallback"])
        self.assertEqual(result["insertion"]["body"], "I am following. What part should we stay with?")
        self.assertEqual(result["insertion"]["mode_state"]["response_contract"], "continuation_cue")
        self.assertGreaterEqual(result["insertion"]["mode_state"]["ai_presence"], 1)

    def test_append_mobile_capture_persists_provenance_on_event(self) -> None:
        result = append_mobile_capture(
            self.root,
            content="Capture with provenance.",
            provenance={
                "source": "thought_capture_pwa",
                "surface_id": "mobile_capture",
                "local_deposit_id": "deposit-local-3",
            },
        )
        events = read_jsonl(session_events_path(self.root, result["session_id"]))
        self.assertEqual(events[0]["attributes"]["provenance"]["local_deposit_id"], "deposit-local-3")


if __name__ == "__main__":
    unittest.main()
