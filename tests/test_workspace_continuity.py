from __future__ import annotations

from pathlib import Path

from conversation_os.workspace_continuity import assemble_workspace_continuity_export, render_workspace_continuity_markdown
from conversation_os.workspace_coordination import create_workspace_task
from conversation_os.workspace_runs import begin_workspace_run, end_workspace_run
from conversation_os.workspace_store import SQLiteWorkspaceStore


def test_continuity_export_is_bounded_and_marks_canonical_revision(tmp_path: Path) -> None:
    store = SQLiteWorkspaceStore(tmp_path, database_path=tmp_path / "state" / "workspace.db")
    store.write_json(store.manifest_path("inner-world"), {"workspace_id": "inner-world", "objectives": ["Coordinate durable work."]})
    create_workspace_task(tmp_path, "inner-world", task_id="CONT-1", agent_id="codex", surface="codex", session_id="s", title="Export continuity", reasoning="Need portable state.", acceptance_criteria=["Export remains resumable."], store=store)
    run = begin_workspace_run(tmp_path, "inner-world", task_id="CONT-1", agent_id="codex", device_id="laptop", surface="codex", session_id="s", intent="Prepare handoff.", store=store)
    end_workspace_run(tmp_path, "inner-world", run_id=run["run_id"], agent_id="codex", status="handed_off", reason="Another device should resume.", store=store)

    export = assemble_workspace_continuity_export(tmp_path, "inner-world", task_id="CONT-1", store=store)
    markdown = render_workspace_continuity_markdown(export)

    assert export["canonical_revision"]
    assert export["runs"]["recent"][0]["run_id"] == run["run_id"]
    assert "canonical_revision:" in markdown
    assert "Another device should resume." in markdown
    assert "canonical store remains authoritative" in markdown
