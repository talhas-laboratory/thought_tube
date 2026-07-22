from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.bridge_disclosure_adapter import (
    assemble_bridge_context_bundle,
    create_bridge_disclosure_service,
    disclose_for_bridge,
)
from conversation_os.corpus_catalog_snapshot import publish_corpus_catalog_snapshot
from conversation_os.disclosure_ports import build_inner_world_ports
from conversation_os.disclosure_service import DisclosureService, disclosure_service_enabled
from conversation_os.reasoning_bridge import (
    _assemble_bridge_context_bundle_impl,
    get_context_bundle,
    heuristic_classify_turn,
)


def _parity_subset(bundle: dict) -> dict:
    return {
        "bundle_layers": list(bundle.get("context_state", {}).get("bundle_layers", []) or []),
        "assembly_status": bundle.get("frame_bundle", {}).get("assembly_status", ""),
        "included_layers": sorted(
            row.get("layer", "")
            for row in bundle.get("frame_bundle", {}).get("included_blocks", []) or []
            if row.get("layer")
        ),
        "envelope_mode": bundle.get("session_envelope", {}).get("mode", ""),
        "global_count": int(bundle.get("global_fallback", {}).get("count", 0) or 0),
        "result_status": bundle.get("result_status", ""),
    }


class DisclosureServiceBridgeParityTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "bridge": {
                        "disclosure_service_v1": True,
                        "execution_audit_isolation_v1": True,
                        "effective_grant_normalization_v1": True,
                        "deterministic_budget_enforcement_v1": True,
                        "orient_first_compose_v1": True,
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)
        publish_corpus_catalog_snapshot(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _context(self) -> dict:
        context = heuristic_classify_turn(
            self.root,
            {
                "request_id": "req-service-001",
                "session_id": "",
                "raw_text": "build bridge integration",
                "caller_hints": {"workspace_id": "ws-service-001", "envelope_mode": "bounded"},
                "domain_hints": [],
                "source_refs": [],
            },
        )
        attributes = dict(context.get("attributes", {}) or {})
        attributes["context_policy"] = {
            "mode": "semantic_narrow",
            "depth_mode": "contextual",
            "token_budget": 1200,
            "include_layers": ["session", "workspace"],
            "exclude_layers": ["global", "user"],
            "cross_ocean": False,
            "retrieval_limit": 4,
            "neighbor_limit": 2,
            "envelope_mode": "bounded",
        }
        context["attributes"] = attributes
        return context

    def test_service_path_matches_legacy_assembler(self) -> None:
        context = self._context()
        legacy = _assemble_bridge_context_bundle_impl(self.root, context)
        service_bundle = disclose_for_bridge(self.root, context)
        self.assertTrue(service_bundle.get("disclosure_service_v1"))
        self.assertIn("disclosure_receipt", service_bundle)
        self.assertIn("corpus_catalog", service_bundle)
        self.assertEqual(_parity_subset(legacy), _parity_subset(service_bundle))

    def test_get_context_bundle_routes_through_service_when_enabled(self) -> None:
        context = self._context()
        bundle = get_context_bundle(self.root, context)
        self.assertTrue(disclosure_service_enabled(self.root))
        self.assertTrue(bundle.get("disclosure_service_v1"))
        self.assertIn("service_metrics", bundle)

    def test_service_module_avoids_product_surface_imports(self) -> None:
        service_path = Path(__file__).resolve().parents[1] / "src" / "conversation_os" / "disclosure_service.py"
        ports_path = Path(__file__).resolve().parents[1] / "src" / "conversation_os" / "disclosure_ports.py"
        banned = ("chat_backends", "holodeck", "worldbuilding_studio", "product_inner_world")
        for path in (service_path, ports_path):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            imports = {
                (node.module or "")
                for node in ast.walk(tree)
                if isinstance(node, ast.ImportFrom) and node.module
            }
            for token in banned:
                self.assertFalse(any(token in item for item in imports), f"{path.name} imports banned surface {token}")

    def test_receipt_sink_records_service_metrics(self) -> None:
        ports = build_inner_world_ports()
        service = DisclosureService(
            ports=ports,
            assemble_bridge_bundle=assemble_bridge_context_bundle,
        )
        bundle = service.disclose_for_bridge(self.root, self._context())
        self.assertGreaterEqual(int(bundle.get("service_metrics", {}).get("latency_ms", 0) or 0), 0)
        self.assertEqual(len(ports.receipt_sink.records), 1)


if __name__ == "__main__":
    unittest.main()
