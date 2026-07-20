from __future__ import annotations

import ast
import json
import tempfile
import unittest
from pathlib import Path

from conversation_os.aperture_operator_metrics import (
    aggregate_receipt_metrics,
    build_operator_view,
    compare_surfaces_by_revision,
    inspect_operator_view,
    load_operator_metrics_config,
    load_published_baseline_snapshots,
    operator_metrics_enabled,
    render_operator_view_summary,
)
from conversation_os.disclosure_receipts import record_disclosure_receipt
from conversation_os.library_tracker import CHAT_CONVERTER_SEED_CORPUS_REVISION
from conversation_os.reasoning_bridge import inspect_aperture_operator_view


class ApertureOperatorMetricsTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        config_dir = self.root / "product" / "inner_world_v1" / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "runtime.json").write_text(
            json.dumps(
                {
                    "disclosure": {
                        "receipts": {
                            "persistent_receipts_v1": True,
                            "rollout": {"bridge": "enforced", "holodeck": "enforced", "feed": "enforced"},
                        },
                        "operator_metrics": {"operator_metrics_v1": True},
                    }
                }
            ),
            encoding="utf-8",
        )
        runtime = self.root / "product" / "inner_world_v1" / "data" / "reasoning_runtime"
        runtime.mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def _record_sample_receipts(self) -> None:
        for surface, status, latency in (
            ("bridge", "disclosed", 12.5),
            ("holodeck", "empty_no_positive_match", 4.0),
            ("feed", "disclosed", 8.0),
        ):
            record_disclosure_receipt(
                self.root,
                request_id=f"req-{surface}",
                surface=surface,
                result_status=status,
                effective_grant={
                    "grant_id": f"grant-{surface}",
                    "request_id": f"req-{surface}",
                    "envelope": "bounded",
                    "effective_layers": ["session", "workspace"],
                },
                metrics={"latency_ms": latency, "included_block_count": 2, "omitted_block_count": 1},
                retrieval_bundle={"count": 1 if status == "disclosed" else 0, "result_status": status},
            )

    def test_aggregate_receipt_metrics_is_privacy_preserving(self) -> None:
        self._record_sample_receipts()
        view = build_operator_view(self.root)
        metrics = view["receipt_metrics"]
        self.assertEqual(metrics["receipt_count"], 3)
        self.assertEqual(metrics["by_surface"]["bridge"], 1)
        self.assertEqual(metrics["by_surface"]["holodeck"], 1)
        self.assertEqual(metrics["by_surface"]["feed"], 1)
        self.assertIn("empty_no_positive_match", metrics["by_result_status"])
        self.assertEqual(metrics["privacy_mode"], "aggregated_counts_only")
        serialized = json.dumps(metrics)
        self.assertNotIn("fixture:", serialized)
        self.assertNotIn("docs/", serialized)

    def test_compare_surfaces_by_revision_links_baselines(self) -> None:
        self._record_sample_receipts()
        view = build_operator_view(self.root)
        comparison = view["cross_surface_comparison"]
        self.assertGreaterEqual(comparison["revision_count"], 1)
        self.assertIn("bridge", comparison["cross_surface_surfaces"])
        self.assertIn("holodeck", comparison["cross_surface_surfaces"])
        self.assertIn("feed", comparison["cross_surface_surfaces"])
        first = comparison["comparisons"][0]
        self.assertEqual(first["corpus_revision"], CHAT_CONVERTER_SEED_CORPUS_REVISION)
        self.assertTrue(first["baseline_suites"])

    def test_load_published_baseline_snapshots_use_repo_artifacts(self) -> None:
        workspace_root = Path(__file__).resolve().parents[1]
        snapshots = load_published_baseline_snapshots(workspace_root)
        suite_ids = {row["baseline_suite_id"] for row in snapshots}
        self.assertIn("chat_converter_seed_v1", suite_ids)
        self.assertIn("chat_converter_seed_v1_service", suite_ids)

    def test_inspect_operator_view_is_read_only_and_flag_gated(self) -> None:
        disabled_root = Path(tempfile.mkdtemp())
        try:
            config_dir = disabled_root / "product" / "inner_world_v1" / "config"
            config_dir.mkdir(parents=True)
            (config_dir / "runtime.json").write_text("{}", encoding="utf-8")
            payload = inspect_operator_view(disabled_root)
            self.assertFalse(payload["enabled"])
            self.assertTrue(payload["read_only"])
        finally:
            import shutil

            shutil.rmtree(disabled_root)

        self._record_sample_receipts()
        payload = inspect_aperture_operator_view(self.root)
        self.assertTrue(payload["enabled"])
        self.assertTrue(payload["read_only"])
        self.assertIn("summary_markdown", payload)
        self.assertIn("Receipt count: 3", payload["summary_markdown"])

    def test_render_operator_view_summary_contains_status_counts(self) -> None:
        self._record_sample_receipts()
        view = build_operator_view(self.root)
        summary = render_operator_view_summary(view)
        self.assertIn("## Surfaces", summary)
        self.assertIn("## Result statuses", summary)
        self.assertIn("## Baselines", summary)

    def test_compare_surfaces_by_revision_without_receipts(self) -> None:
        snapshots = load_published_baseline_snapshots(Path(__file__).resolve().parents[1])
        comparison = compare_surfaces_by_revision({"by_corpus_revision": {}}, snapshots)
        self.assertGreaterEqual(comparison["revision_count"], 1)

    def test_runtime_config_defaults_flag_off(self) -> None:
        bare_root = Path(tempfile.mkdtemp())
        try:
            config = load_operator_metrics_config(bare_root)
            self.assertFalse(config["operator_metrics_v1"])
            self.assertFalse(operator_metrics_enabled(bare_root))
        finally:
            import shutil

            shutil.rmtree(bare_root)

    def test_module_avoids_control_plane_mutation_imports(self) -> None:
        module_path = Path(__file__).resolve().parents[1] / "src" / "conversation_os" / "aperture_operator_metrics.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        imports = {
            (node.module or "")
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        }
        for token in ("workspace_coordination", "bridge_controller", "holodeck"):
            self.assertFalse(any(token in item for item in imports), token)
        source = module_path.read_text(encoding="utf-8")
        self.assertIn('"mutation_paths": []', source)


if __name__ == "__main__":
    unittest.main()
