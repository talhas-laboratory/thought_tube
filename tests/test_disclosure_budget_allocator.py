from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.disclosure_budget_allocator import (
    ESTIMATOR_VERSION,
    RESERVATION_VERSION,
    allocate_included_blocks,
    apply_frame_budget_to_assembly,
    build_budget_reservation,
    estimate_tokens,
)
from conversation_os.disclosure_contracts import validate_execution_bundle
from conversation_os.reasoning_bridge import (
    assemble_frame_bundle,
    deterministic_budget_enforcement_enabled,
    get_context_bundle,
    heuristic_classify_turn,
    split_frame_assembly,
)


class DisclosureBudgetAllocatorTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_estimate_tokens_is_deterministic(self) -> None:
        text = "orientation and evidence budgeting"
        self.assertEqual(estimate_tokens(text), 4)
        self.assertEqual(estimate_tokens(text), estimate_tokens(text))

    def test_whole_block_allocation_is_deterministic(self) -> None:
        blocks = [
            {"block_id": "b-global", "layer": "global", "summary": "retrieval evidence", "token_estimate": 80},
            {"block_id": "b-session", "layer": "session", "summary": "session continuity", "token_estimate": 40},
            {"block_id": "b-workspace", "layer": "workspace", "summary": "workspace binding", "token_estimate": 20},
        ]
        kwargs = {
            "token_budget": 200,
            "orientation_tokens": 10,
            "reservations": {
                "system_tokens": 20,
                "answer_tokens": 30,
                "orientation_max_tokens": 20,
            },
        }
        first = allocate_included_blocks(blocks, **kwargs)
        second = allocate_included_blocks(blocks, **kwargs)
        self.assertEqual(first["included_blocks"], second["included_blocks"])
        self.assertEqual(first["drop_ledger"], second["drop_ledger"])
        self.assertEqual(first["result_status"], "disclosed")

    def test_optional_blocks_drop_before_exceeding_budget(self) -> None:
        blocks = [
            {"block_id": "b-session", "layer": "session", "summary": "session continuity", "token_estimate": 40},
            {"block_id": "b-global", "layer": "global", "summary": "retrieval evidence", "token_estimate": 90},
        ]
        allocation = allocate_included_blocks(
            blocks,
            token_budget=120,
            orientation_tokens=0,
            reservations={"system_tokens": 0, "answer_tokens": 0, "orientation_max_tokens": 0},
        )
        included_ids = [row["block_id"] for row in allocation["included_blocks"]]
        self.assertEqual(included_ids, ["b-session"])
        self.assertEqual(len(allocation["drop_ledger"]), 1)
        self.assertEqual(allocation["drop_ledger"][0]["block_id"], "b-global")

    def test_required_block_insufficient_budget_abstains(self) -> None:
        blocks = [
            {"block_id": "b-session", "layer": "session", "summary": "session continuity", "token_estimate": 200},
        ]
        allocation = allocate_included_blocks(
            blocks,
            token_budget=100,
            orientation_tokens=0,
            reservations={"system_tokens": 0, "answer_tokens": 0, "orientation_max_tokens": 0},
            required_layers={"session"},
        )
        self.assertEqual(allocation["result_status"], "abstained_insufficient_budget")
        self.assertEqual(allocation["included_blocks"], [])

    def test_build_budget_reservation_versions(self) -> None:
        reservation = build_budget_reservation(token_budget=900, orientation_tokens=25)
        self.assertEqual(reservation["estimator_version"], ESTIMATOR_VERSION)
        self.assertEqual(reservation["reservation_version"], RESERVATION_VERSION)
        self.assertEqual(reservation["available_for_blocks"], 900 - 120 - 256 - 25)

    def test_unset_token_budget_defaults_from_depth_mode(self) -> None:
        from conversation_os.disclosure_budget_allocator import resolve_token_budget

        self.assertEqual(resolve_token_budget(0, depth_mode="contextual", policy_specified=False), 1200)
        self.assertEqual(resolve_token_budget(0, depth_mode="incognito", policy_specified=False), 0)
        self.assertEqual(resolve_token_budget(0, depth_mode="contextual", policy_specified=True), 0)

    def test_apply_frame_budget_skips_when_token_budget_unconfigured(self) -> None:
        assembly = {
            "included_blocks": [
                {"block_id": "b-session", "layer": "session", "summary": "session continuity", "token_estimate": 40}
            ],
            "assembly_status": "partial",
        }
        audit = apply_frame_budget_to_assembly(
            assembly,
            context_state={"depth_mode": "incognito"},
            effective_grant={"token_budget": 0, "token_budget_specified": True, "effective_layers": ["session"]},
            root=self.root,
        )
        self.assertFalse(audit["enforcement_enabled"])
        self.assertEqual(assembly["assembly_status"], "partial")
        self.assertEqual(len(assembly["included_blocks"]), 1)


class DisclosureBudgetBridgeIntegrationTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "execution_audit_isolation_v1": True,
                        "effective_grant_normalization_v1": True,
                        "deterministic_budget_enforcement_v1": True,
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_drop_ledger_stays_in_audit_not_execution_bundle(self) -> None:
        assembly = assemble_frame_bundle(
            {
                "request_id": "req-budget-001",
                "active_workspace_id": "ws-budget",
                "attributes": {"session_id": "session-budget"},
            },
            frame_spec={
                "frame_id": "frame-budget-001",
                "selectors": [
                    {"selector_id": "sel-session", "layer": "session"},
                    {"selector_id": "sel-global", "layer": "global"},
                ],
            },
            envelope={"mode": "bounded"},
            disclosed_layers=["session", "global"],
            session_rows=[{"event_id": "evt-1"}],
            workspace_layer={},
            user_patterns=[],
            bridge_state={},
            retrieval_bundle={"count": 2, "source_refs": ["retrieval:topic"], "query": "topic"},
        )
        budget_audit = apply_frame_budget_to_assembly(
            assembly,
            context_state={"active_topic": "topic", "user_goal": "explore"},
            effective_grant={"token_budget": 60, "effective_layers": ["session", "governed_global"]},
            root=self.root,
            session_event_count=1,
        )
        execution_bundle, frame_audit = split_frame_assembly(assembly)
        frame_audit["drop_ledger"] = list(budget_audit.get("drop_ledger", []) or [])
        validate_execution_bundle(execution_bundle)
        self.assertIn("drop_ledger", frame_audit)
        self.assertNotIn("drop_ledger", execution_bundle)
        self.assertTrue(budget_audit["drop_ledger"] or budget_audit["result_status"] == "abstained_insufficient_budget")

    def test_get_context_bundle_records_budget_audit(self) -> None:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-budget-002",
                "session_id": "",
                "raw_text": "bridge budget enforcement",
                "caller_hints": {"workspace_id": "ws-budget-002", "envelope_mode": "bounded"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "token_budget": 900,
            "include_layers": ["session", "workspace", "global"],
            "exclude_layers": [],
            "cross_ocean": False,
            "retrieval_limit": 4,
            "neighbor_limit": 2,
            "envelope_mode": "bounded",
        }
        context["attributes"] = attributes
        bundle = get_context_bundle(self.root, context)
        self.assertTrue(deterministic_budget_enforcement_enabled(self.root))
        self.assertIn("budget_audit", bundle)
        self.assertNotIn("drop_ledger", bundle["frame_bundle"])
        if bundle.get("frame_audit"):
            self.assertEqual(bundle["frame_audit"].get("drop_ledger", []), bundle["budget_audit"].get("drop_ledger", []))


if __name__ == "__main__":
    unittest.main()
