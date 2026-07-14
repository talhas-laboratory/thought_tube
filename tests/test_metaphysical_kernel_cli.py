from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from conversation_os.metaphysical_kernel_cli import (
    KERNEL_TEST_MODULES,
    foundation_bootstrap,
    foundation_reconcile_ledger,
    foundation_review,
    foundation_status,
    foundation_validate,
)


class MetaphysicalKernelCliTestCase(unittest.TestCase):
    def test_kernel_test_module_list_covers_phase1(self) -> None:
        self.assertEqual(len(KERNEL_TEST_MODULES), 5)

    def test_foundation_status_on_empty_root(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            result = foundation_status(Path(tmpdir))
            self.assertIn("memory/foundation/kernel_events.jsonl", result["store_path"])
            self.assertFalse(result["store_exists"])

    def test_foundation_bootstrap_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)
            bootstrap = foundation_bootstrap(root)
            self.assertEqual(bootstrap["profile_id"], "profile:field_formation")
            validated = foundation_validate(root)
            self.assertTrue(validated["valid"])

    def test_foundation_review_passes_in_ephemeral_root(self) -> None:
        import argparse

        root = Path(__file__).resolve().parents[1]
        result = foundation_review(
            root,
            argparse.Namespace(verbose=False, in_place=False),
        )
        self.assertTrue(result["passed"], result["steps"])
        self.assertTrue(result["ephemeral"])
        step_names = [step["step"] for step in result["steps"]]
        self.assertIn("adversarial_state_fixtures", step_names)

    def test_foundation_reconcile_ledger_offline_mode(self) -> None:
        import argparse

        root = Path(__file__).resolve().parents[1]
        result = foundation_reconcile_ledger(
            root,
            argparse.Namespace(
                agent_id="test-agent",
                surface="test",
                session_id="test-session",
                dry_run=False,
            ),
        )
        self.assertEqual(result["mode"], "offline")
        self.assertFalse(result["api_reachable"])
        self.assertGreaterEqual(len(result["commands"]), 1)


if __name__ == "__main__":
    unittest.main()
