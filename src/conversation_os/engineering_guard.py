from __future__ import annotations

from pathlib import Path
from typing import Any

from .codebase_overview import lookup_codebase, refresh_codebase_overview


VAGUE_PURPOSE_PHRASES = {
    "make it better",
    "improve code",
    "cleanup",
    "refactor",
    "general improvement",
    "new system",
    "fix stuff",
}

OWNER_EXTRACTION_MARKERS = {
    "extract",
    "extraction",
    "dedicated module",
    "owner extraction",
    "ownership split",
    "split intentionally",
}


def _normalize_paths(proposed_paths: list[str] | None) -> list[str]:
    return [path.strip() for path in (proposed_paths or []) if path and path.strip()]


def _path_exists_or_can_exist(root: Path, relative_path: str) -> bool:
    path = root / relative_path
    return path.exists() or path.parent.exists()


def _normalized_test_targets_for_source_path(source_path: str) -> set[str]:
    if not source_path.startswith("src/") or not source_path.endswith(".py"):
        return set()
    module_relative = source_path[len("src/") :]
    stem = Path(module_relative).stem
    parent = Path(module_relative).parent
    targets = {str(Path("tests") / parent / f"test_{stem}.py")}
    if module_relative.startswith("conversation_os/"):
        targets.add("tests/test_conversation_os.py")
    return targets


def _is_allowed_test_companion(path: str, proposed_paths: list[str], recommended_paths: list[str]) -> bool:
    if not path.startswith("tests/") or not path.endswith(".py"):
        return False
    source_candidates = [
        candidate
        for candidate in list(dict.fromkeys(proposed_paths + recommended_paths))
        if candidate.startswith("src/") and candidate.endswith(".py")
    ]
    return any(path in _normalized_test_targets_for_source_path(candidate) for candidate in source_candidates)


def _looks_like_owner_extraction_intent(request: str, purpose: str) -> bool:
    text = f"{request} {purpose}".strip().lower()
    return any(marker in text for marker in OWNER_EXTRACTION_MARKERS)


def _is_allowed_adjacent_owner_module(
    path: str,
    proposed_paths: list[str],
    recommended_paths: list[str],
    *,
    request: str,
    purpose: str,
) -> bool:
    if not path.startswith("src/") or not path.endswith(".py"):
        return False
    if not recommended_paths:
        return False
    current_owner = recommended_paths[0]
    if current_owner not in proposed_paths or not current_owner.startswith("src/") or not current_owner.endswith(".py"):
        return False
    if path == current_owner:
        return True
    if not _looks_like_owner_extraction_intent(request, purpose):
        return False
    current_parent = Path(current_owner).parent
    candidate_parent = Path(path).parent
    return candidate_parent == current_parent


def _classify_warnings(
    warnings: list[str],
    proposed_paths: list[str],
    recommended_paths: list[str],
) -> tuple[list[dict[str, Any]], str | None, str]:
    blocking_issues: list[dict[str, Any]] = []

    if any("No proposed paths" in warning for warning in warnings):
        blocking_issues.append(
            {
                "code": "missing_scope",
                "message": "No proposed edit surface was supplied.",
                "suggested_fix": "Add the smallest plausible --proposed-paths list before changing code.",
            }
        )

    if any("Purpose is too vague" in warning for warning in warnings):
        blocking_issues.append(
            {
                "code": "vague_purpose",
                "message": "The purpose does not describe a concrete user or system effect.",
                "suggested_fix": "Rewrite --purpose so it states the exact behavior change and what should remain unchanged.",
            }
        )

    missing_paths = [
        warning.split(": ", 1)[1]
        for warning in warnings
        if warning.startswith("Proposed path does not exist and its parent directory is missing:")
    ]
    if missing_paths:
        blocking_issues.append(
            {
                "code": "invalid_path",
                "message": f"{len(missing_paths)} proposed path(s) do not exist and cannot be created in the current tree.",
                "paths": missing_paths,
                "suggested_fix": "Choose an existing owner path or a new file whose parent directory already exists.",
            }
        )

    ownership_mismatches = [
        warning.split(": ", 1)[1]
        for warning in warnings
        if warning.startswith("Proposed path is outside the top suggested ownership surface:")
    ]
    if ownership_mismatches:
        blocking_issues.append(
            {
                "code": "ownership_mismatch",
                "message": f"{len(ownership_mismatches)} proposed path(s) fall outside the top suggested ownership surface.",
                "paths": ownership_mismatches,
                "recommended_paths": recommended_paths[:3],
                "suggested_fix": "Narrow the change to the nearest existing owner, or justify why the recommended owner is insufficient.",
            }
        )

    if blocking_issues:
        primary_message = blocking_issues[0]["message"]
        suggested_fix = blocking_issues[0]["suggested_fix"]
        if len(blocking_issues) > 1:
            why_not_ready = f"{primary_message} {len(blocking_issues) - 1} additional blocking issue(s) are also present."
        else:
            why_not_ready = primary_message
        return blocking_issues, why_not_ready, suggested_fix

    return [], None, "Proceed with implementation in the approved surface."


def assess_change_request(
    root: Path,
    request: str,
    purpose: str,
    proposed_paths: list[str] | None,
    limit: int = 6,
) -> dict[str, Any]:
    refresh_codebase_overview(root)
    proposed_paths = _normalize_paths(proposed_paths)
    lookup_results = lookup_codebase(root, f"{request} {purpose}", limit=limit)
    warnings: list[str] = []

    normalized_purpose = purpose.strip().lower()
    if not normalized_purpose or normalized_purpose in VAGUE_PURPOSE_PHRASES or len(normalized_purpose.split()) < 4:
        warnings.append("Purpose is too vague. State the concrete user or system effect before writing code.")
    if not proposed_paths:
        warnings.append("No proposed paths supplied. Name the smallest plausible edit surface before changing code.")

    recommended_paths = [item["path"] for item in lookup_results]
    for path in proposed_paths:
        if not _path_exists_or_can_exist(root, path):
            warnings.append(f"Proposed path does not exist and its parent directory is missing: {path}")
        elif (
            recommended_paths
            and path not in recommended_paths
            and not _is_allowed_test_companion(path, proposed_paths, recommended_paths)
            and not _is_allowed_adjacent_owner_module(
                path,
                proposed_paths,
                recommended_paths,
                request=request,
                purpose=purpose,
            )
        ):
            warnings.append(f"Proposed path is outside the top suggested ownership surface: {path}")

    if any("No proposed paths" in warning for warning in warnings):
        status = "needs_scope"
    elif any("Purpose is too vague" in warning for warning in warnings):
        status = "needs_purpose"
    elif warnings:
        status = "review_targets"
    else:
        status = "ready"

    questions_to_answer = [
        "What exact behavior or user outcome should change if this code is added?",
        "Which existing module already owns most of this responsibility?",
        "What is the smallest edit surface that can satisfy the request?",
        "What should remain unchanged after this edit?",
    ]
    minimality_checks = [
        "Prefer extending an existing owner module before creating a new subsystem.",
        "Do not add abstractions unless at least two concrete call sites need them.",
        "Keep changes local to the named paths unless the assessment shows a missing owner.",
        "If the code does not clearly serve the stated purpose, do not generate it.",
    ]
    blocking_issues, why_not_ready, next_step = _classify_warnings(warnings, proposed_paths, recommended_paths)

    return {
        "ready": status == "ready",
        "status": status,
        "request": request,
        "purpose": purpose,
        "proposed_paths": proposed_paths,
        "recommended_targets": lookup_results,
        "warnings": warnings,
        "blocking_issues": blocking_issues,
        "why_not_ready": why_not_ready,
        "next_step": next_step,
        "questions_to_answer": questions_to_answer,
        "minimality_checks": minimality_checks,
    }
