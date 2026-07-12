from __future__ import annotations

import subprocess
from pathlib import Path

from conversation_os.workspace_context_packet import assemble_workspace_context_packet
from conversation_os.workspace_observer import latest_workspace_snapshot, observe_workspace
from conversation_os.workspace_store import SQLiteWorkspaceStore


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _seed_repo(root: Path) -> SQLiteWorkspaceStore:
    _git(root, "init")
    _git(root, "config", "user.email", "agent@example.test")
    _git(root, "config", "user.name", "Agent")
    (root / "src").mkdir()
    (root / "docs").mkdir()
    (root / "outside").mkdir()
    (root / "src" / "modified.py").write_text("before\n", encoding="utf-8")
    (root / "src" / "deleted.py").write_text("delete me\n", encoding="utf-8")
    (root / "src" / "renamed.py").write_text("rename me\n", encoding="utf-8")
    (root / "outside" / "ignored.txt").write_text("before\n", encoding="utf-8")
    _git(root, "add", ".")
    _git(root, "commit", "-m", "initial")
    store = SQLiteWorkspaceStore(root, database_path=root / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {
            "workspace_id": "inner-world",
            "artifact_roots": ["src/", "docs/workboards/"],
            "objectives": ["Observe scoped repository state."],
        },
    )
    return store


def test_observer_records_scoped_added_modified_deleted_and_renamed_files(tmp_path: Path) -> None:
    store = _seed_repo(tmp_path)
    (tmp_path / "src" / "modified.py").write_text("after\n", encoding="utf-8")
    (tmp_path / "src" / "added.py").write_text("new\n", encoding="utf-8")
    (tmp_path / "src" / "deleted.py").unlink()
    _git(tmp_path, "mv", "src/renamed.py", "src/moved.py")
    (tmp_path / "outside" / "ignored.txt").write_text("outside change\n", encoding="utf-8")

    result = observe_workspace(tmp_path, "inner-world", store=store)

    changes = {(row["status"], row["path"], row.get("previous_path", "")) for row in result["snapshot"]["changes"]}
    assert ("added", "src/added.py", "") in changes
    assert ("modified", "src/modified.py", "") in changes
    assert ("deleted", "src/deleted.py", "") in changes
    assert ("renamed", "src/moved.py", "src/renamed.py") in changes
    assert all(not row[1].startswith("outside/") for row in changes)
    assert result["snapshot"]["source_revision"] == _git(tmp_path, "rev-parse", "HEAD")
    assert result["recorded"] is True


def test_observer_is_idempotent_and_context_reads_latest_snapshot(tmp_path: Path) -> None:
    store = _seed_repo(tmp_path)
    (tmp_path / "src" / "modified.py").write_text("after\n", encoding="utf-8")

    first = observe_workspace(tmp_path, "inner-world", store=store)
    second = observe_workspace(tmp_path, "inner-world", store=store)
    packet = assemble_workspace_context_packet(tmp_path, "inner-world", store=store)

    assert first["recorded"] is True
    assert second["recorded"] is False
    assert len(store.read_jsonl(store.repository_snapshots_path("inner-world"))) == 1
    assert latest_workspace_snapshot(tmp_path, "inner-world", store=store)["fingerprint"] == first["snapshot"]["fingerprint"]
    assert packet["repository"]["changed_files"] == ["src/modified.py"]
    assert packet["repository"]["source_revision"] == first["snapshot"]["source_revision"]
    assert packet["repository"]["observed_at"] == first["snapshot"]["observed_at"]
    assert packet["repository"]["freshness_status"] == "observed"
    atlas_path = tmp_path / "context" / "workspaces" / "inner-world" / "atlas.json"
    assert atlas_path.exists()
    assert first["snapshot"]["fingerprint"] in atlas_path.read_text(encoding="utf-8")


def test_observer_records_clean_transition_once(tmp_path: Path) -> None:
    store = _seed_repo(tmp_path)
    (tmp_path / "src" / "modified.py").write_text("after\n", encoding="utf-8")
    observe_workspace(tmp_path, "inner-world", store=store)
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-m", "change")

    clean = observe_workspace(tmp_path, "inner-world", store=store)
    repeated = observe_workspace(tmp_path, "inner-world", store=store)

    assert clean["recorded"] is True
    assert clean["snapshot"]["changes"] == []
    assert repeated["recorded"] is False


def test_observer_accepts_explicit_revision_for_rsync_projection(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(
        store.manifest_path("inner-world"),
        {"workspace_id": "inner-world", "artifact_roots": ["src/"]},
    )

    result = observe_workspace(
        tmp_path,
        "inner-world",
        store=store,
        source_revision_override="published-commit-1",
    )

    assert result["snapshot"]["source_revision"] == "published-commit-1"
    assert result["recorded"] is True
