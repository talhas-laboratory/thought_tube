"""CLI handlers for metaphysical kernel foundation operations."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from conversation_os.metaphysical_kernel_application_sdk import (
    WORLD_STUDIO_APPLICATION_ID,
    WORKSPACE_CURATOR_APPLICATION_ID,
    ApplicationContext,
    FoundationApplicationSdk,
    world_studio_capture_scene,
    workspace_curator_capture_insight,
)
from conversation_os.metaphysical_kernel_contracts import ContractValidationError, validate_fixture_bundle
from conversation_os.metaphysical_kernel_migration import migrate_source_fixture, validate_migration_fixture
from conversation_os.metaphysical_kernel_profile_registry import (
    FIELD_FORMATION_PROFILE_ID,
    FIELD_FORMATION_PROFILE_VERSION,
    ProfileRegistry,
)
from conversation_os.metaphysical_kernel_runtime import FoundationRuntime, run_vertical_slice
from conversation_os.metaphysical_kernel_store import foundation_events_path
from conversation_os.storage import utc_now

MODULE_ID = "kernel.metaphysical.cli"
CONTRACT_VERSION = "1.1.0"

KERNEL_TEST_MODULES = [
    "tests.test_metaphysical_kernel_contracts",
    "tests.test_metaphysical_kernel_migration",
    "tests.test_metaphysical_kernel_runtime",
    "tests.test_metaphysical_kernel_profile_registry",
    "tests.test_metaphysical_kernel_application_sdk",
]


def foundation_status(root: Path) -> Dict[str, Any]:
    runtime = FoundationRuntime(root)
    bundle = runtime.current_bundle()
    events_path = foundation_events_path(root)
    return {
        "store_path": str(events_path),
        "store_exists": events_path.exists(),
        "event_count": len(runtime.store.read_events()),
        "record_counts": {key: len(bundle.get(key, [])) for key in sorted(bundle)},
        "validation_errors": runtime.validate_current_bundle(),
    }


def foundation_validate(root: Path) -> Dict[str, Any]:
    runtime = FoundationRuntime(root)
    errors = runtime.validate_current_bundle()
    return {
        "valid": not errors,
        "validation_errors": errors,
        "record_counts": {key: len(runtime.current_bundle().get(key, [])) for key in runtime.current_bundle()},
    }


def foundation_test(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    modules = KERNEL_TEST_MODULES
    if args.module:
        modules = [args.module]
    command = [sys.executable, "-m", "unittest", *modules]
    if args.verbose:
        command.append("-v")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(command, cwd=root, capture_output=True, text=True, env=env)
    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
        "passed": completed.returncode == 0,
    }


def foundation_bootstrap(root: Path) -> Dict[str, Any]:
    runtime = FoundationRuntime(root, actor="service:foundation")
    registry = ProfileRegistry(runtime)
    profile = registry.bootstrap_field_formation_profile()
    return {
        "profile_id": FIELD_FORMATION_PROFILE_ID,
        "profile_version": FIELD_FORMATION_PROFILE_VERSION,
        "profile_definition_id": profile.get("envelope", {}).get("id"),
        "validation_errors": runtime.validate_current_bundle(),
    }


def foundation_capture(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    sdk = FoundationApplicationSdk(
        root,
        ApplicationContext(
            application_id=args.application_id,
            actor=args.actor,
            branch_id=args.branch_id,
            scope_id=args.scope_id,
        ),
    )
    if args.session_id:
        event = {
            "event_id": args.event_id or f"evt-{args.session_id}",
            "session_id": args.session_id,
            "timestamp": utc_now(),
            "actor": args.actor,
            "kind": args.kind,
            "content": args.content,
        }
        result = sdk.capture_source_from_event(event)
    else:
        result = sdk.capture_source(
            content_pointer=args.content_pointer,
            integrity_hash=args.integrity_hash,
            source_kind=args.source_kind,
        )
    return result.to_dict()


def foundation_slice(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    event = {
        "event_id": args.event_id,
        "session_id": args.session_id,
        "timestamp": utc_now(),
        "actor": args.actor,
        "kind": "request",
        "content": args.content,
    }
    return run_vertical_slice(
        root,
        session_event=event,
        referent_label=args.referent_label,
        claim_predicate=args.claim_predicate,
        claim_arguments=args.claim_arguments.split(",") if args.claim_arguments else [],
        branch_id=args.branch_id,
        scope_id=args.scope_id,
        adopt_state=args.adopt_state,
        state_value=args.state_value or None,
    )


def foundation_migrate_fixture(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    fixture_path = Path(args.fixture_path)
    if not fixture_path.is_absolute():
        fixture_path = root / fixture_path
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if args.execute:
        migration = migrate_source_fixture(fixture)
        return {
            "fixture_id": fixture.get("fixture_id"),
            "source_family": migration.source_family,
            "loss_report": migration.loss_report,
            "mapping_rule_count": len(migration.mapping_rules),
            "kernel_record_counts": {
                key: len(migration.kernel_bundle.get(key, []))
                for key in sorted(migration.kernel_bundle)
            },
        }
    errors = validate_migration_fixture(fixture)
    return {
        "fixture_id": fixture.get("fixture_id"),
        "valid": not errors,
        "errors": errors,
    }


def foundation_consumer(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    if args.consumer == "world-studio":
        sdk = FoundationApplicationSdk(
            root,
            ApplicationContext(
                application_id=WORLD_STUDIO_APPLICATION_ID,
                actor=args.actor,
                branch_id=args.branch_id,
                scope_id=args.scope_id,
            ),
        )
        return world_studio_capture_scene(
            sdk,
            world_id=args.world_id,
            scene_text=args.content,
            element_label=args.referent_label,
        )
    sdk = FoundationApplicationSdk(
        root,
        ApplicationContext(
            application_id=WORKSPACE_CURATOR_APPLICATION_ID,
            actor=args.actor,
            branch_id=args.branch_id,
            scope_id=args.scope_id,
        ),
    )
    return workspace_curator_capture_insight(
        sdk,
        workspace_id=args.workspace_id,
        statement=args.content,
        adopt_as_state=args.adopt_state,
    )


MIGRATION_FIXTURE_PATHS = [
    "tests/fixtures/migration/mtsf_minimal_assertion.json",
    "tests/fixtures/migration/mtsf_uncertain_identity.json",
    "tests/fixtures/migration/thoughtshape_stateclaim_hold.json",
    "tests/fixtures/migration/sds_signal_dilution.json",
    "tests/fixtures/migration/conversation_os_minimal_session.json",
]

ADVERSARIAL_STATE_FIXTURE_PATHS = [
    "tests/fixtures/metaphysical_kernel/invalid_state_branch_membership_mismatch.json",
    "tests/fixtures/metaphysical_kernel/invalid_state_scope_membership_mismatch.json",
    "tests/fixtures/metaphysical_kernel/invalid_state_missing_commitment_link.json",
    "tests/fixtures/metaphysical_kernel/invalid_state_unknown_source_claim.json",
]

FOUNDATION_TASK_IDS = [
    "TASK-001-lock-kernel-contracts-and-lifecycles",
    "TASK-002-build-historical-and-current-migration-fixtures",
    "TASK-003-implement-phase-1-foundation-vertical-slice",
    "TASK-004-build-profile-registry-and-conformance",
    "TASK-005-prove-application-sdk-with-two-consumers",
]

FOUNDATION_BLOCKER_ID = "blocker-7f7662afad54"
FOUNDATION_WORKSPACE_ID = "unified-framework-synthesis"


def _workspace_api_base() -> str:
    configured = os.environ.get("INNER_WORLD_WORKSPACE_API_BASE", "").strip()
    if configured:
        return configured
    config_path = Path.home() / ".config" / "inner-space-workspace.env"
    if config_path.is_file():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if stripped.startswith("INNER_WORLD_WORKSPACE_API_BASE="):
                return stripped.split("=", 1)[1].strip()
    return ""


def _git_head(root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    return completed.stdout.strip() if completed.returncode == 0 else ""


def foundation_reconcile_ledger(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Build reconciliation commands; execute only with explicit intent."""
    head = ""
    review = foundation_review(root, argparse.Namespace(verbose=False, in_place=False))
    verify_command = "python3 tools/conversation_os.py foundation review"
    evidence = f"branch cursor/metaphysical-kernel-contracts-423a @ {head}; {verify_command}; passed={review['passed']}"

    command_template: list[list[str]] = []
    for task_id in FOUNDATION_TASK_IDS:
        command_template.append(
            [
                "python3",
                "tools/workspace_coordination.py",
                "verify",
                "--workspace-id",
                FOUNDATION_WORKSPACE_ID,
                "--task-id",
                task_id,
                "--agent-id",
                args.agent_id,
                "--surface",
                args.surface,
                "--session-id",
                args.session_id,
                "--test-name",
                "foundation_phase1_review",
                "--result",
                "pass" if review["passed"] else "fail",
                "--evidence-ref",
                head,
                "--command-or-protocol",
                verify_command,
                "--notes",
                evidence,
            ]
        )
    command_template.append(
        [
            "python3",
            "tools/workspace_coordination.py",
            "decision",
            "--workspace-id",
            FOUNDATION_WORKSPACE_ID,
            "--task-id",
            FOUNDATION_TASK_IDS[0],
            "--agent-id",
            args.agent_id,
            "--summary",
            "Gap 1 state adoption cross-link validation repaired",
            "--reasoning",
            evidence,
        ]
    )
    if review["passed"]:
        command_template.append(
            [
                "python3",
                "tools/workspace_coordination.py",
                "resolve-blocker",
                "--workspace-id",
                FOUNDATION_WORKSPACE_ID,
                "--blocker-id",
                FOUNDATION_BLOCKER_ID,
                "--agent-id",
                args.agent_id,
                "--reasoning",
                "Gap 1 repaired with adversarial fixtures; foundation review passed.",
            ]
        )
        for task_id in FOUNDATION_TASK_IDS:
            command_template.append(
                [
                    "python3",
                    "tools/workspace_coordination.py",
                    "update-task",
                    "--workspace-id",
                    FOUNDATION_WORKSPACE_ID,
                    "--task-id",
                    task_id,
                    "--agent-id",
                    args.agent_id,
                    "--task-status",
                    "in-progress",
                    "--reasoning",
                    "Blocker resolved; resuming Phase 1 close-out.",
                ]
            )
            command_template.append(
                [
                    "python3",
                    "tools/workspace_coordination.py",
                    "update-task",
                    "--workspace-id",
                    FOUNDATION_WORKSPACE_ID,
                    "--task-id",
                    task_id,
                    "--agent-id",
                    args.agent_id,
                    "--task-status",
                    "review",
                    "--reasoning",
                    "Phase 1 implementation verified; pending merge approval.",
                ]
            )

    planned = {
        "mode": "planned",
        "workspace_id": FOUNDATION_WORKSPACE_ID,
        "api_reachable": False,
        "foundation_review_passed": review["passed"],
        "commands": [" ".join(command) for command in command_template],
        "documentation": "docs/workboards/unified-metaphysical-foundation/GAP-2-RECONCILIATION.md",
    }
    if not getattr(args, "execute", False):
        return planned

    api_base = _workspace_api_base()
    if not api_base:
        return {**planned, "mode": "offline"}

    import urllib.error
    import urllib.request

    health_url = f"{api_base.rstrip('/')}/health"
    try:
        with urllib.request.urlopen(health_url, timeout=10) as response:
            response.read()
    except (urllib.error.URLError, TimeoutError) as exc:
        return {
            "mode": "offline",
            "workspace_id": FOUNDATION_WORKSPACE_ID,
            "api_reachable": False,
            "api_base": api_base,
            "error": str(exc),
            "foundation_review_passed": review["passed"],
            "commands": [" ".join(command) for command in command_template],
            "documentation": "docs/workboards/unified-metaphysical-foundation/GAP-2-RECONCILIATION.md",
        }

    if args.dry_run:
        return {
            "mode": "dry_run",
            "workspace_id": FOUNDATION_WORKSPACE_ID,
            "api_reachable": True,
            "foundation_review_passed": review["passed"],
            "commands": [" ".join(command) for command in command_template],
        }

    results: list[Dict[str, Any]] = []
    passed = True
    for command in command_template:
        completed = subprocess.run(command, cwd=root, capture_output=True, text=True, check=False)
        entry = {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
        results.append(entry)
        if completed.returncode != 0:
            passed = False

    projection_sync: Dict[str, Any] | None = None
    if passed and review["passed"]:
        projection_sync = foundation_sync_projections(
            root,
            argparse.Namespace(
                agent_id=args.agent_id,
                surface=args.surface,
                session_id=args.session_id,
                dry_run=False,
                offline=False,
            ),
        )

    return {
        "mode": "connected",
        "workspace_id": FOUNDATION_WORKSPACE_ID,
        "api_reachable": True,
        "foundation_review_passed": review["passed"],
        "passed": passed and review["passed"],
        "results": results,
        "projection_sync": projection_sync,
    }


def foundation_sync_projections(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Publish git projections from live workspace coordination state."""
    from conversation_os.workspace_projection_sync import check_workspace_projections, sync_workspace_projections

    api_base = "" if getattr(args, "offline", False) else _workspace_api_base()
    common = {
        "api_base": api_base,
        "agent_id": getattr(args, "agent_id", "projection-sync"),
        "surface": getattr(args, "surface", "cursor"),
        "session_id": getattr(args, "session_id", "projection-sync"),
    }
    if getattr(args, "check", False):
        return check_workspace_projections(root, FOUNDATION_WORKSPACE_ID, **common)
    return sync_workspace_projections(
        root,
        FOUNDATION_WORKSPACE_ID,
        dry_run=getattr(args, "dry_run", False),
        **common,
    )


def foundation_review(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    """Run the Phase 1 reviewer checklist and return a structured pass/fail report."""
    review_root = root
    cleanup: Path | None = None
    if not args.in_place:
        import tempfile

        cleanup = Path(tempfile.mkdtemp(prefix="foundation-review-"))
        review_root = cleanup

    steps: list[Dict[str, Any]] = []

    def record(step: str, passed: bool, detail: Dict[str, Any]) -> None:
        steps.append({"step": step, "passed": passed, **detail})

    test_args = argparse.Namespace(module="", verbose=args.verbose)
    test_result = foundation_test(root, test_args)
    record(
        "unit_tests",
        test_result["passed"],
        {"test_count_modules": len(KERNEL_TEST_MODULES), "returncode": test_result["returncode"]},
    )

    bootstrap = foundation_bootstrap(review_root)
    record(
        "bootstrap_profile",
        not bootstrap["validation_errors"],
        {
            "profile_id": bootstrap["profile_id"],
            "validation_errors": bootstrap["validation_errors"],
        },
    )

    slice_result = run_vertical_slice(
        review_root,
        session_event={
            "event_id": "event-foundation-review",
            "session_id": "session-foundation-review",
            "timestamp": utc_now(),
            "actor": "agent:reviewer",
            "kind": "request",
            "content": "Automated review vertical slice.",
        },
        referent_label="Review subject",
        claim_predicate="relates",
        claim_arguments=[],
        branch_id="branch_main",
        scope_id="scope_foundation",
    )
    record(
        "vertical_slice",
        not slice_result.get("validation_errors"),
        {
            "source_fragment_id": slice_result.get("source_fragment_id"),
            "claim_id": slice_result.get("claim_id"),
            "provenance_complete": slice_result.get("provenance_trace", {}).get("complete"),
            "validation_errors": slice_result.get("validation_errors", []),
        },
    )

    adoption_slice = run_vertical_slice(
        review_root,
        session_event={
            "event_id": "event-foundation-review-adoption",
            "session_id": "session-foundation-review",
            "timestamp": utc_now(),
            "actor": "agent:reviewer",
            "kind": "request",
            "content": "Automated review State adoption.",
        },
        referent_label="Review adoption subject",
        claim_predicate="has_level",
        claim_arguments=["low"],
        branch_id="branch_main",
        scope_id="scope_foundation",
        adopt_state=True,
        state_value="low",
    )
    record(
        "state_adoption",
        not adoption_slice.get("validation_errors")
        and len(FoundationRuntime(review_root).current_bundle().get("states", [])) == 1,
        {"validation_errors": adoption_slice.get("validation_errors", [])},
    )

    runtime = FoundationRuntime(review_root)
    events_before_rejection = len(runtime.store.read_events())
    try:
        runtime.commit_state_from_claims(
            source_claim_ids=["claim-missing"],
            branch_id="branch_main",
            scope_id="scope_foundation",
            subject_refs=["ref-missing"],
            state_type="review:state",
            value="invalid",
            value_type="text",
            provenance_id=str(slice_result["source_fragment_id"]),
        )
        rejected = False
    except ContractValidationError:
        rejected = len(runtime.store.read_events()) == events_before_rejection
    record("state_adoption_rejected_without_write", rejected, {"event_count": events_before_rejection})

    validated = foundation_validate(review_root)
    record(
        "validate_bundle",
        validated["valid"],
        {"record_counts": validated["record_counts"], "validation_errors": validated["validation_errors"]},
    )

    world_studio = foundation_consumer(
        review_root,
        argparse.Namespace(
            consumer="world-studio",
            actor="agent:reviewer",
            branch_id="branch_main",
            scope_id="scope_foundation",
            content="Review harbor scene.",
            referent_label="Harbor",
            world_id="world-review",
            workspace_id="unified-framework-synthesis",
            adopt_state=False,
        ),
    )
    record(
        "consumer_world_studio",
        world_studio.get("capture", {}).get("success") and world_studio.get("claim", {}).get("success"),
        {"application": world_studio.get("application")},
    )

    workspace_curator = foundation_consumer(
        review_root,
        argparse.Namespace(
            consumer="workspace-curator",
            actor="agent:reviewer",
            branch_id="branch_main",
            scope_id="scope_foundation",
            content="Kernel contracts precede profiles.",
            referent_label="Subject",
            world_id="world-review",
            workspace_id="unified-framework-synthesis",
            adopt_state=False,
        ),
    )
    record(
        "consumer_workspace_curator",
        workspace_curator.get("capture", {}).get("success"),
        {"application": workspace_curator.get("application")},
    )

    conformance = foundation_conformance(
        review_root,
        argparse.Namespace(
            application_id="app:foundation",
            actor="agent:reviewer",
            branch_id="branch_main",
            scope_id="scope_foundation",
            profile_id=FIELD_FORMATION_PROFILE_ID,
            profile_version=FIELD_FORMATION_PROFILE_VERSION,
            evaluated_record_id="bundle",
        ),
    )
    record(
        "profile_conformance",
        conformance.get("success", False),
        {"operation": conformance.get("operation"), "validation_errors": conformance.get("validation_errors", [])},
    )

    migration_results = []
    migration_passed = True
    for fixture_rel in MIGRATION_FIXTURE_PATHS:
        fixture_path = root / fixture_rel
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        errors = validate_migration_fixture(fixture)
        migration_results.append(
            {
                "fixture_id": fixture.get("fixture_id"),
                "path": fixture_rel,
                "valid": not errors,
                "errors": errors,
            }
        )
        if errors:
            migration_passed = False
    record("migration_fixtures_validate", migration_passed, {"fixtures": migration_results})

    adversarial_results = []
    adversarial_passed = True
    for fixture_rel in ADVERSARIAL_STATE_FIXTURE_PATHS:
        fixture_path = root / fixture_rel
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        errors = validate_fixture_bundle(fixture)
        adversarial_results.append(
            {
                "path": fixture_rel,
                "rejected": bool(errors),
                "error_count": len(errors),
            }
        )
        if not errors:
            adversarial_passed = False
    record("adversarial_state_fixtures", adversarial_passed, {"fixtures": adversarial_results})

    execute_fixture = root / MIGRATION_FIXTURE_PATHS[0]
    execute_result = foundation_migrate_fixture(
        root,
        argparse.Namespace(fixture_path=str(execute_fixture), execute=True),
    )
    record(
        "migration_fixture_execute",
        bool(execute_result.get("mapping_rule_count", 0)),
        execute_result,
    )

    if cleanup is not None:
        import shutil

        shutil.rmtree(cleanup, ignore_errors=True)

    passed = all(step["passed"] for step in steps)
    return {
        "phase": "1",
        "branch": "cursor/metaphysical-kernel-contracts-423a",
        "review_root": str(review_root),
        "ephemeral": cleanup is not None,
        "passed": passed,
        "steps": steps,
        "documentation": {
            "start": "docs/workboards/unified-metaphysical-foundation/REVIEWER-START.md",
            "architecture": "docs/workboards/unified-metaphysical-foundation/PHASE-1-IMPLEMENTATION-REVIEW.md",
            "tools": "docs/workboards/unified-metaphysical-foundation/TOOLS.md",
        },
    }


def foundation_conformance(root: Path, args: argparse.Namespace) -> Dict[str, Any]:
    sdk = FoundationApplicationSdk(
        root,
        ApplicationContext(
            application_id=args.application_id,
            actor=args.actor,
            branch_id=args.branch_id,
            scope_id=args.scope_id,
            profile_id=args.profile_id,
            profile_version=args.profile_version,
        ),
    )
    result = sdk.validate_profile(evaluated_record_id=args.evaluated_record_id)
    return result.to_dict()


__all__ = [
    "MODULE_ID",
    "CONTRACT_VERSION",
    "KERNEL_TEST_MODULES",
    "foundation_status",
    "foundation_validate",
    "foundation_test",
    "foundation_bootstrap",
    "foundation_capture",
    "foundation_slice",
    "foundation_migrate_fixture",
    "foundation_consumer",
    "foundation_conformance",
    "foundation_review",
    "foundation_reconcile_ledger",
    "foundation_sync_projections",
    "MIGRATION_FIXTURE_PATHS",
    "ADVERSARIAL_STATE_FIXTURE_PATHS",
    "FOUNDATION_TASK_IDS",
]
