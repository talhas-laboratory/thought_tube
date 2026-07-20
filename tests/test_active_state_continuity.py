from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.active_state_continuity import (
    active_state_continuity_enabled,
    apply_active_state_continuity,
    build_continuity_key,
    build_state_transition,
    load_latest_snapshot_for_workspace,
    load_latest_transition_for_key,
    merge_active_state_snapshots,
    rollback_active_state_transition,
)
from conversation_os.holodeck import holodeck_load_active_state_continuity
from conversation_os.orient_first_compose import build_active_state_snapshot
from conversation_os.reasoning_bridge import get_context_bundle, heuristic_classify_turn


class ActiveStateContinuityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "active_state": {"continuity_v1": True, "max_transitions": 50}
                    },
                    "bridge": {"orient_first_compose_v1": True},
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _snapshot(
        self,
        *,
        request_id: str,
        topic: str = "",
        lens: str = "",
        posture: str = "exploratory",
        workspace_id: str = "ws-continuity-001",
        session_id: str = "session-continuity-001",
    ) -> dict:
        return build_active_state_snapshot(
            {
                "request_id": request_id,
                "active_topic": topic,
                "user_goal": "build",
                "reasoning_posture": posture,
                "object_scope": "same_main",
                "active_workspace_id": workspace_id,
                "lens": lens,
                "attributes": {
                    "session_id": session_id,
                    "caller_hints": {"workspace_id": workspace_id, "thought_id": "thought-001"},
                },
            },
            {
                "request_id": request_id,
                "active_topic": topic,
                "user_goal": "build",
                "reasoning_posture": posture,
                "object_scope": "same_main",
            },
            workspace_layer={"workspace_id": workspace_id, "thought_id": "thought-001"},
            session_envelope={"mode": "bounded"},
        )

    def _grant(self, *, envelope: str = "bounded") -> dict:
        return {
            "grant_id": "grant-continuity-001",
            "request_id": "req-continuity-001",
            "envelope": envelope,
            "effective_layers": ["session", "workspace"],
            "effective_refs": [],
            "dimensions": [],
            "shape_maturity": "candidate",
            "cross_ocean": False,
            "token_budget": 900,
            "persistence_mode": "gated",
            "explicit_pins": [],
            "narrowing_reasons": [],
            "deny_precedence_applied": False,
            "requested_grant_ref": "grant-continuity-001",
        }

    def test_multi_turn_carries_empty_fields(self) -> None:
        self.assertTrue(active_state_continuity_enabled(self.root))
        first = self._snapshot(request_id="req-1", topic="bridge integration", lens="modular boundary")
        apply_active_state_continuity(
            self.root,
            first,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        second = self._snapshot(request_id="req-2", topic="bridge integration", lens="")
        merged, transition = apply_active_state_continuity(
            self.root,
            second,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        self.assertEqual(merged["lens"], "modular boundary")
        self.assertIn("carried:lens", transition["fields_changed"])
        self.assertTrue(transition["durable"])

    def test_incognito_leaves_no_durable_state(self) -> None:
        snapshot = self._snapshot(request_id="req-incognito", topic="secret topic")
        _, transition = apply_active_state_continuity(
            self.root,
            snapshot,
            effective_grant=self._grant(envelope="incognito"),
            session_envelope={"mode": "incognito"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        self.assertFalse(transition["durable"])
        self.assertEqual(transition["operation"], "ephemeral")
        key = build_continuity_key(session_id="session-continuity-001", workspace_id="ws-continuity-001")
        self.assertIsNone(load_latest_transition_for_key(self.root, key))

    def test_snapshot_contains_references_not_ocean_content(self) -> None:
        merged, _ = merge_active_state_snapshots(
            {"topic": "prior", "lens": "kept", "derived_from": ["workspace:ws-continuity-001"], "snapshot_id": "snap-prior"},
            self._snapshot(request_id="req-ref", topic="updated"),
        )
        payload = json.dumps(merged)
        self.assertIn("workspace:ws-continuity-001", payload)
        self.assertNotIn("seed_capsule", payload.lower())
        self.assertNotIn("semantic_capsules", payload.lower())

    def test_rollback_records_compensating_operation(self) -> None:
        snapshot = self._snapshot(request_id="req-rollback", topic="first topic", lens="first lens")
        _, transition = apply_active_state_continuity(
            self.root,
            snapshot,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        key = transition["continuity_key"]
        result = rollback_active_state_transition(
            self.root,
            continuity_key=key,
            compensates_transition_id=transition["transition_id"],
            reason="bad merge",
            surface="bridge",
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["transition"]["operation"], "rollback")
        restored = load_latest_snapshot_for_workspace(self.root, "ws-continuity-001")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored["lens"], "first lens")

    def test_multi_turn_rollback_restores_prior_snapshot(self) -> None:
        first = self._snapshot(request_id="req-t1", topic="first topic", lens="first lens")
        _, transition_t1 = apply_active_state_continuity(
            self.root,
            first,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        second = self._snapshot(request_id="req-t2", topic="second topic", lens="")
        merged_t2, transition_t2 = apply_active_state_continuity(
            self.root,
            second,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        self.assertEqual(merged_t2["topic"], "second topic")
        self.assertEqual(merged_t2["lens"], "first lens")

        result = rollback_active_state_transition(
            self.root,
            continuity_key=transition_t2["continuity_key"],
            compensates_transition_id=transition_t2["transition_id"],
            reason="undo second turn",
            surface="bridge",
        )
        self.assertEqual(result["status"], "rolled_back")
        self.assertEqual(result["restored_snapshot_id"], transition_t1["snapshot_id"])

        restored = load_latest_snapshot_for_workspace(self.root, "ws-continuity-001")
        self.assertIsNotNone(restored)
        assert restored is not None
        self.assertEqual(restored["topic"], "first topic")
        self.assertEqual(restored["lens"], "first lens")
        self.assertNotEqual(restored["topic"], "second topic")

    def test_cross_adapter_workspace_continuity(self) -> None:
        snapshot = self._snapshot(request_id="req-bridge", topic="shared workspace topic", lens="shared lens")
        apply_active_state_continuity(
            self.root,
            snapshot,
            effective_grant=self._grant(),
            session_envelope={"mode": "bounded"},
            surface="bridge",
            context_state={"active_workspace_id": "ws-continuity-001", "attributes": {"session_id": "session-continuity-001"}},
        )
        loaded = holodeck_load_active_state_continuity(self.root, "ws-continuity-001")
        self.assertIsNotNone(loaded)
        assert loaded is not None
        self.assertEqual(loaded["topic"], "shared workspace topic")
        self.assertEqual(loaded["lens"], "shared lens")

    def test_get_context_bundle_emits_transition_contract(self) -> None:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-bundle-continuity-1",
                "session_id": "session-bundle-continuity",
                "raw_text": "active state continuity",
                "caller_hints": {"workspace_id": "ws-bundle-continuity", "envelope_mode": "bounded"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        first = get_context_bundle(self.root, context)
        self.assertTrue(first.get("active_state_continuity_v1"))
        self.assertIn("active_state_transition", first)
        self.assertEqual(first["active_state_transition"].get("contract_version"), "1.0")

        context["request_id"] = "req-bundle-continuity-2"
        context["lens"] = ""
        second = get_context_bundle(self.root, context)
        transition = second.get("active_state_transition", {})
        self.assertTrue(transition.get("durable") or transition.get("operation") == "ephemeral")
        loaded = load_latest_snapshot_for_workspace(self.root, "ws-bundle-continuity")
        self.assertIsNotNone(loaded)


if __name__ == "__main__":
    unittest.main()
