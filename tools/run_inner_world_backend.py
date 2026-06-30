#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path, PurePosixPath
from typing import Any, Iterable
from urllib.parse import parse_qs, urlparse


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
src_str = str(SRC)
if src_str in sys.path:
    sys.path.remove(src_str)
sys.path.insert(0, src_str)

from conversation_os.cli import session_import  # noqa: E402
from conversation_os import holodeck as holodeck_module  # noqa: E402
from conversation_os.chat_backends import apply_openclaw_host_telegram_fix, migrate_openclaw_telegram_bindings  # noqa: E402
from conversation_os.miniapp import serve_miniapp  # noqa: E402


GPT_BRIDGE_CONTRACT_VERSION = "2026-04-24.inner-world.v1"
GPT_API_KEY_HEADER = "X-Inner-World-Action-Key"
AUTHORIZATION_HEADER = "Authorization"
MAX_FILE_BYTES = 256 * 1024
MAX_FILE_WINDOW_LINES = 400
DEFAULT_SEARCH_TOP_K = 8
DEFAULT_GPT_BRIDGE_PORT = 8093
DEFAULT_GPT_ARTIFACT_ROOT = ROOT / "mobile_artifacts"
DEFAULT_GPT_SEARCH_ROOTS = (
    "README.md",
    "AGENTS.md",
    "PRODUCT_THESIS.md",
    "CONTEXT_ROUTING.md",
    "SESSION_PROTOCOL.md",
    "context/substrate/CODEBASE_OVERVIEW.md",
    "docs",
    "src",
    "tools",
)
DEFAULT_GPT_AUTHORITATIVE_PATHS = (
    "README.md",
    "AGENTS.md",
    "PRODUCT_THESIS.md",
    "CONTEXT_ROUTING.md",
    "SESSION_PROTOCOL.md",
    "context/substrate/CODEBASE_OVERVIEW.md",
    "docs/plans/2026-04-14-inner-world-v1-build-plan.md",
    "docs/plans/2026-04-14-inner-world-openclaw-server-architecture.md",
    "docs/plans/2026-04-14-inner-world-server-deployment-plan.md",
    "docs/building-diary/README.md",
)
DENIED_DIR_NAMES = {
    ".git",
    "__pycache__",
    ".venv",
    "node_modules",
    "dist",
    "build",
}
SEARCHABLE_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".toml",
    ".yaml",
    ".yml",
    ".py",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".html",
    ".css",
}
REQUIRED_GPT_ACTION_PATHS = [
    "/context/status-bundle",
    "/context/authoritative-bundle",
    "/repo/status",
    "/repo/search",
    "/repo/file",
    "/holodeck/list",
    "/holodeck/status",
    "/holodeck/check",
    "/holodeck/task-pack",
    "/holodeck/create",
    "/holodeck/start-run",
    "/mobile-artifacts/list",
    "/mobile-artifacts/read",
    "/mobile-artifacts/search",
    "/mobile-artifacts/save-chat",
    "/sync/local-status",
    "/openclaw/telegram-fix",
]


def _split_csv_values(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _hash_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _short_fingerprint(value: str) -> str:
    if not value:
        return ""
    return _hash_text(value)[:12]


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", value.strip().lower()).strip("-")
    return slug or "artifact"


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict[str, Any]:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    payload = handler.rfile.read(length)
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def _normalize_rel_path(path_value: str) -> str:
    text = path_value.strip()
    candidate = PurePosixPath(text)
    if not text:
        raise ValueError("path_required")
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError("path_traversal_not_allowed")
    normalized = candidate.as_posix().lstrip("./")
    if not normalized:
        raise ValueError("path_required")
    return normalized


def _frontmatter(metadata: dict[str, Any]) -> str:
    lines = ["---"]
    for key, value in metadata.items():
        lines.append(f"{key}: {json.dumps(value, ensure_ascii=False)}")
    lines.append("---")
    return "\n".join(lines)


def _parse_frontmatter(document: str) -> tuple[dict[str, Any], str]:
    if not document.startswith("---\n"):
        return {}, document
    lines = document.splitlines()
    end_index = None
    for index in range(1, len(lines)):
        if lines[index].strip() == "---":
            end_index = index
            break
    if end_index is None:
        return {}, document
    metadata: dict[str, Any] = {}
    for line in lines[1:end_index]:
        if ":" not in line:
            continue
        key, raw_value = line.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        try:
            metadata[key] = json.loads(raw_value)
        except json.JSONDecodeError:
            metadata[key] = raw_value
    body = "\n".join(lines[end_index + 1 :]).lstrip("\n")
    return metadata, body


def _text_excerpt(text: str, *, max_lines: int = 12, max_chars: int = 700) -> str:
    lines = text.splitlines()
    excerpt = "\n".join(lines[:max_lines]).strip()
    if len(excerpt) > max_chars:
        excerpt = excerpt[: max_chars - 1].rstrip() + "…"
    return excerpt


def _require_text(value: str | None, error_key: str) -> str:
    text = (value or "").strip()
    if not text:
        raise ValueError(error_key)
    return text


class InnerWorldGPTBridge:
    def __init__(
        self,
        *,
        root: Path,
        action_key: str,
        legacy_action_keys: list[str] | None = None,
        public_base_url: str = "",
        artifact_root: Path | None = None,
        domains: list[str] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.action_key = action_key.strip()
        self.accepted_action_keys = {self.action_key, *[value for value in list(legacy_action_keys or []) if value]}
        self.public_base_url = public_base_url.strip()
        self.artifact_root = (artifact_root or DEFAULT_GPT_ARTIFACT_ROOT).expanduser().resolve()
        self.domains = list(domains or [])

    def _run(self, args: list[str], *, cwd: Path | None = None, timeout: int = 20) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args,
            cwd=str(cwd or self.root),
            capture_output=True,
            text=True,
            check=False,
            timeout=timeout,
        )

    def _git(self, *args: str) -> tuple[bool, str]:
        proc = self._run(["git", *args], timeout=10)
        if proc.returncode != 0:
            return False, (proc.stderr.strip() or proc.stdout.strip())
        return True, proc.stdout.strip()

    def _resolve_repo_path(self, path_value: str) -> Path:
        normalized = _normalize_rel_path(path_value)
        candidate = (self.root / normalized).resolve()
        if candidate != self.root and self.root not in candidate.parents:
            raise ValueError("path_outside_repo")
        return candidate

    def _workspace_relative(self, path: Path) -> str:
        return path.resolve().relative_to(self.root).as_posix()

    def _repo_status_payload(self) -> dict[str, Any]:
        repo_payload = {
            "generated_at_utc": _utc_now(),
            "repo_root": str(self.root),
            "is_git_repo": False,
            "active_ref": None,
            "commit_sha": None,
            "dirty": None,
            "changed_paths": [],
        }
        ok, _ = self._git("rev-parse", "--is-inside-work-tree")
        if not ok:
            return repo_payload
        repo_payload["is_git_repo"] = True
        ok, active_ref = self._git("rev-parse", "--abbrev-ref", "HEAD")
        if ok:
            repo_payload["active_ref"] = active_ref
        ok, commit_sha = self._git("rev-parse", "HEAD")
        if ok:
            repo_payload["commit_sha"] = commit_sha
        ok, status_text = self._git("status", "--short")
        if ok:
            changed_paths: list[str] = []
            for line in status_text.splitlines():
                text = line.strip()
                if not text:
                    continue
                changed_paths.append(text[3:] if len(text) > 3 else text)
            repo_payload["dirty"] = bool(changed_paths)
            repo_payload["changed_paths"] = changed_paths
        return repo_payload

    def _is_searchable_file(self, path: Path) -> bool:
        if not path.is_file():
            return False
        if path.stat().st_size > MAX_FILE_BYTES:
            return False
        if path.suffix.lower() in SEARCHABLE_SUFFIXES:
            return True
        return path.name in {"README", "README.md", "AGENTS.md"}

    def _iter_candidate_files(self, roots: Iterable[str]) -> Iterable[Path]:
        seen: set[Path] = set()
        for root_value in roots:
            try:
                candidate = self._resolve_repo_path(root_value)
            except ValueError:
                continue
            if not candidate.exists():
                continue
            if candidate.is_file():
                if candidate not in seen and self._is_searchable_file(candidate):
                    seen.add(candidate)
                    yield candidate
                continue
            for path in candidate.rglob("*"):
                if any(part in DENIED_DIR_NAMES for part in path.parts):
                    continue
                if path in seen or not self._is_searchable_file(path):
                    continue
                seen.add(path)
                yield path

    def _read_text(self, path: Path) -> str:
        return path.read_text(encoding="utf-8", errors="ignore")

    def _build_snippet(self, content: str, query: str, terms: list[str]) -> str:
        lines = content.splitlines()
        lowered = [line.lower() for line in lines]
        query_lower = query.lower()
        for index, line in enumerate(lowered):
            if query_lower in line or any(term in line for term in terms):
                start = max(0, index - 1)
                end = min(len(lines), index + 3)
                return "\n".join(lines[start:end]).strip()
        return _text_excerpt(content, max_lines=5, max_chars=420)

    def _score_content(self, path: Path, content: str, query: str, terms: list[str]) -> float:
        path_text = self._workspace_relative(path).lower()
        content_lower = content.lower()
        score = 0.0
        if query.lower() in path_text:
            score += 4.0
        if query.lower() in content_lower:
            score += 6.0
        for term in terms:
            if term in path_text:
                score += 1.3
            count = content_lower.count(term)
            if count:
                score += min(4.5, count * 0.7)
        return round(score, 3)

    def _document_card(self, path_value: str, *, reason: str | None = None) -> dict[str, Any]:
        target = self._resolve_repo_path(path_value)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path_value)
        content = self._read_text(target)
        lines = content.splitlines()
        return {
            "path": self._workspace_relative(target),
            "title": lines[0].strip("# ").strip() if lines else target.name,
            "reason": reason,
            "start_line": 1,
            "end_line": min(len(lines), 12),
            "excerpt": _text_excerpt(content),
        }

    def _directory_count(self, path: Path) -> int:
        if not path.exists() or not path.is_dir():
            return 0
        with os.scandir(path) as entries:
            return sum(1 for entry in entries if entry.is_dir())

    def _lightweight_runtime_overview(self) -> dict[str, Any]:
        return {
            "mode": "lightweight",
            "generated_at_utc": _utc_now(),
            "full_runtime_overview_deferred": True,
            "deferred_reason": "omitted_for_action_latency_on_large_workspace",
            "surfaces": {
                "docs": (self.root / "docs").exists(),
                "src": (self.root / "src").exists(),
                "tools": (self.root / "tools").exists(),
                "context": (self.root / "context").exists(),
                "memory": (self.root / "memory").exists(),
                "product_inner_world_v1": (self.root / "product" / "inner_world_v1").exists(),
                "product_personal_interface_v1": (self.root / "product" / "personal_interface_v1").exists(),
                "mobile_artifacts": self.artifact_root.exists(),
            },
            "workspace_counts": {
                "memory_workspaces": self._directory_count(self.root / "memory" / "workspaces"),
                "context_workspaces": self._directory_count(self.root / "context" / "workspaces"),
                "mobile_artifact_days": self._directory_count(self.artifact_root),
            },
            "recommended_follow_up_tools": [
                "/context/authoritative-bundle",
                "/repo/search",
                "/repo/file",
                "/holodeck/list",
            ],
        }

    def health(self) -> dict[str, Any]:
        return {
            "contract_version": GPT_BRIDGE_CONTRACT_VERSION,
            "public_base_url": self.public_base_url or None,
            "repo_root": str(self.root),
            "artifact_root": str(self.artifact_root),
            "required_action_paths": REQUIRED_GPT_ACTION_PATHS,
        }

    def repo_status(self) -> dict[str, Any]:
        payload = self._repo_status_payload()
        payload["artifact_root"] = self._workspace_relative(self.artifact_root) if self.artifact_root.exists() else self.artifact_root.as_posix()
        return payload

    def repo_search(self, query: str, allowed_paths: list[str] | None = None, top_k: int = DEFAULT_SEARCH_TOP_K) -> dict[str, Any]:
        text = query.strip()
        if not text:
            raise ValueError("query_required")
        roots = allowed_paths or list(DEFAULT_GPT_SEARCH_ROOTS)
        terms = [term for term in re.split(r"[^a-z0-9]+", text.lower()) if len(term) >= 2]
        results: list[dict[str, Any]] = []
        for candidate in self._iter_candidate_files(roots):
            content = self._read_text(candidate)
            score = self._score_content(candidate, content, text, terms)
            if score <= 0:
                continue
            lines = content.splitlines()
            start_line = 1
            lowered_lines = [line.lower() for line in lines]
            for index, line in enumerate(lowered_lines, start=1):
                if text.lower() in line or any(term in line for term in terms):
                    start_line = index
                    break
            results.append(
                {
                    "path": self._workspace_relative(candidate),
                    "start_line": start_line,
                    "end_line": min(len(lines), start_line + 6),
                    "score": score,
                    "snippet": self._build_snippet(content, text, terms),
                }
            )
        results.sort(key=lambda item: (-float(item["score"]), str(item["path"])))
        payload = self._repo_status_payload()
        payload.update(
            {
                "query": text,
                "search_roots": roots,
                "results": results[: max(1, min(top_k, 20))],
            }
        )
        return payload

    def repo_file(self, path_value: str, start_line: int | None = None, end_line: int | None = None) -> dict[str, Any]:
        target = self._resolve_repo_path(path_value)
        if not target.exists() or not target.is_file():
            raise FileNotFoundError(path_value)
        if target.stat().st_size > MAX_FILE_BYTES:
            raise ValueError("file_too_large")
        full_content = self._read_text(target)
        lines = full_content.splitlines()
        start = max(1, start_line or 1)
        finish = min(len(lines), end_line or start + MAX_FILE_WINDOW_LINES - 1)
        if finish < start:
            raise ValueError("invalid_line_window")
        if finish - start + 1 > MAX_FILE_WINDOW_LINES:
            finish = start + MAX_FILE_WINDOW_LINES - 1
        content = "\n".join(lines[start - 1 : finish])
        payload = self._repo_status_payload()
        payload.update(
            {
                "path": self._workspace_relative(target),
                "start_line": start,
                "end_line": finish,
                "file_sha256": _hash_text(full_content),
                "full_line_count": len(lines),
                "content": content,
            }
        )
        return payload

    def context_status_bundle(self) -> dict[str, Any]:
        artifacts = self._artifact_records()
        return {
            "generated_at_utc": _utc_now(),
            "repo_status": self._repo_status_payload(),
            "runtime_overview": self._lightweight_runtime_overview(),
            "artifact_root": self._workspace_relative(self.artifact_root) if self.artifact_root.exists() else self.artifact_root.as_posix(),
            "artifact_count": len(artifacts),
            "latest_artifact_path": artifacts[0]["path"] if artifacts else None,
            "authoritative_paths": list(DEFAULT_GPT_AUTHORITATIVE_PATHS),
            "recommended_tools": REQUIRED_GPT_ACTION_PATHS,
        }

    def authoritative_bundle(self, request_text: str | None = None, extra_paths: list[str] | None = None, top_k: int = 8) -> dict[str, Any]:
        cards: list[dict[str, Any]] = []
        seen: set[str] = set()
        for path_value in list(DEFAULT_GPT_AUTHORITATIVE_PATHS) + list(extra_paths or []):
            try:
                card = self._document_card(path_value, reason="authoritative")
            except FileNotFoundError:
                continue
            if card["path"] in seen:
                continue
            seen.add(card["path"])
            cards.append(card)
        related: list[dict[str, Any]] = []
        if request_text:
            search = self.repo_search(request_text, top_k=top_k)
            for item in search["results"]:
                if item["path"] in seen:
                    continue
                related.append(item)
                seen.add(item["path"])
        return {
            "generated_at_utc": _utc_now(),
            "request_text": request_text,
            "authoritative_docs": cards,
            "related_docs": related,
        }

    def _artifact_manifest_path(self) -> Path:
        return self.artifact_root / "manifest.json"

    def _iter_artifact_files(self) -> Iterable[Path]:
        if not self.artifact_root.exists():
            return []
        files = []
        for path in self.artifact_root.rglob("*.md"):
            if path.is_file():
                files.append(path)
        return sorted(files)

    def _artifact_records(self) -> list[dict[str, Any]]:
        records: list[dict[str, Any]] = []
        for path in self._iter_artifact_files():
            metadata, body = _parse_frontmatter(self._read_text(path))
            records.append(
                {
                    "artifact_id": metadata.get("artifact_id", path.stem),
                    "title": metadata.get("title", path.stem),
                    "created_at_utc": metadata.get("created_at_utc"),
                    "updated_at_utc": metadata.get("updated_at_utc"),
                    "path": self._workspace_relative(path),
                    "tags": metadata.get("tags", []),
                    "related_paths": metadata.get("related_paths", []),
                    "session_id": metadata.get("session_id"),
                    "content_preview": _text_excerpt(body, max_lines=5, max_chars=280),
                }
            )
        records.sort(key=lambda item: str(item.get("updated_at_utc") or ""), reverse=True)
        return records

    def _write_artifact_manifest(self) -> None:
        self.artifact_root.mkdir(parents=True, exist_ok=True)
        manifest = {
            "generated_at_utc": _utc_now(),
            "artifact_root": self._workspace_relative(self.artifact_root),
            "artifacts": self._artifact_records(),
        }
        self._artifact_manifest_path().write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    def list_artifacts(self) -> dict[str, Any]:
        return {
            "artifact_root": self._workspace_relative(self.artifact_root) if self.artifact_root.exists() else self.artifact_root.as_posix(),
            "artifacts": self._artifact_records(),
        }

    def read_artifact(self, path_value: str) -> dict[str, Any]:
        path = self._resolve_repo_path(path_value)
        if not path.exists() or not path.is_file():
            raise FileNotFoundError(path_value)
        if self.artifact_root not in path.parents:
            raise ValueError("artifact_path_outside_root")
        metadata, body = _parse_frontmatter(self._read_text(path))
        return {**metadata, "path": self._workspace_relative(path), "content": body}

    def search_artifacts(self, query: str, top_k: int = DEFAULT_SEARCH_TOP_K) -> dict[str, Any]:
        text = query.strip()
        if not text:
            raise ValueError("query_required")
        terms = [term for term in re.split(r"[^a-z0-9]+", text.lower()) if len(term) >= 2]
        results: list[dict[str, Any]] = []
        for path in self._iter_artifact_files():
            metadata, body = _parse_frontmatter(self._read_text(path))
            score = self._score_content(path, body, text, terms)
            if score <= 0:
                continue
            results.append(
                {
                    "artifact_id": metadata.get("artifact_id", path.stem),
                    "title": metadata.get("title", path.stem),
                    "path": self._workspace_relative(path),
                    "score": score,
                    "snippet": self._build_snippet(body, text, terms),
                }
            )
        results.sort(key=lambda item: (-float(item["score"]), str(item["path"])))
        return {"query": text, "results": results[: max(1, min(top_k, 20))]}

    def save_chat(
        self,
        *,
        title: str,
        conversation_markdown: str,
        tags: list[str] | None = None,
        related_paths: list[str] | None = None,
        ingest_into_session: bool = True,
        domains: list[str] | None = None,
        request_text: str | None = None,
    ) -> dict[str, Any]:
        clean_title = title.strip()
        clean_conversation = conversation_markdown.strip()
        if not clean_title:
            raise ValueError("title_required")
        if not clean_conversation:
            raise ValueError("conversation_markdown_required")
        created_at = _utc_now()
        artifact_id = _hash_text(f"{clean_title}:{created_at}")[:12]
        slug = _slugify(clean_title)
        date_prefix = created_at[:10]
        target = self.artifact_root / date_prefix / f"{slug}-{artifact_id}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        metadata: dict[str, Any] = {
            "artifact_id": artifact_id,
            "title": clean_title,
            "source": "chatgpt_mobile",
            "created_at_utc": created_at,
            "updated_at_utc": created_at,
            "tags": list(tags or []),
            "related_paths": list(related_paths or []),
            "ingest_into_session": bool(ingest_into_session),
        }
        target.write_text(_frontmatter(metadata) + "\n\n" + clean_conversation + "\n", encoding="utf-8")
        import_result = None
        if ingest_into_session:
            import_result = session_import(
                self.root,
                argparse.Namespace(
                    source_path=str(target),
                    title=clean_title,
                    participants="user,assistant",
                    source_type="chatgpt_mobile",
                    domains=",".join(domains or self.domains),
                    tags="chatgpt_mobile,mobile_artifact",
                    task_id=None,
                    request=request_text or clean_title,
                    task_type="mobile_capture",
                    session_id=None,
                ),
            )
            metadata["session_id"] = import_result.get("session_id")
            metadata["artifact_refs"] = import_result.get("artifact_refs", {})
            metadata["updated_at_utc"] = _utc_now()
            target.write_text(_frontmatter(metadata) + "\n\n" + clean_conversation + "\n", encoding="utf-8")
        self._write_artifact_manifest()
        payload = self.read_artifact(self._workspace_relative(target))
        payload["import_result"] = import_result
        return payload

    def sync_local_status(self) -> dict[str, Any]:
        artifacts = self._artifact_records()
        return {
            "generated_at_utc": _utc_now(),
            "artifact_root": self._workspace_relative(self.artifact_root) if self.artifact_root.exists() else self.artifact_root.as_posix(),
            "artifact_count": len(artifacts),
            "latest_updated_at_utc": artifacts[0]["updated_at_utc"] if artifacts else None,
            "pull_hint": f"rsync -az talha@192.168.0.102:{self.artifact_root.as_posix()}/ ./mobile_artifacts/",
        }

    def holodeck_list(self, status: str = "") -> dict[str, Any]:
        return holodeck_module.holodeck_list(self.root, argparse.Namespace(status=status or None))

    def holodeck_status(self, workspace_id: str) -> dict[str, Any]:
        return holodeck_module.holodeck_status(
            self.root,
            argparse.Namespace(workspace_id=_require_text(workspace_id, "workspace_id_required")),
        )

    def holodeck_check(self, workspace_id: str) -> dict[str, Any]:
        return holodeck_module.holodeck_check(
            self.root,
            argparse.Namespace(workspace_id=_require_text(workspace_id, "workspace_id_required")),
        )

    def holodeck_task_pack(
        self,
        workspace_id: str,
        task_id: str,
        *,
        request: str = "",
        task_type: str = "implementation",
    ) -> dict[str, Any]:
        return holodeck_module.holodeck_task_pack(
            self.root,
            argparse.Namespace(
                workspace_id=_require_text(workspace_id, "workspace_id_required"),
                task_id=_require_text(task_id, "task_id_required"),
                request=request or "",
                task_type=task_type or "implementation",
            ),
        )

    def holodeck_create(
        self,
        *,
        title: str,
        goal: str,
        purpose: str,
        success_condition: str = "",
        workspace_id: str = "",
        scope_in: list[str] | None = None,
        scope_out: list[str] | None = None,
        template_key: str = "",
        domains: list[str] | None = None,
        founder_wedge: str | None = None,
        founder_user: str | None = None,
        founder_moat: str | None = None,
        founder_gtm_risk: str | None = None,
        founder_launch_metric: str | None = None,
    ) -> dict[str, Any]:
        return holodeck_module.holodeck_create(
            self.root,
            argparse.Namespace(
                workspace_id=workspace_id or None,
                title=_require_text(title, "title_required"),
                goal=_require_text(goal, "goal_required"),
                purpose=_require_text(purpose, "purpose_required"),
                success_condition=success_condition or "",
                scope_in=list(scope_in or []),
                scope_out=list(scope_out or []),
                template_key=template_key or "",
                domains=",".join(domains or []),
                founder_wedge=founder_wedge,
                founder_user=founder_user,
                founder_moat=founder_moat,
                founder_gtm_risk=founder_gtm_risk,
                founder_launch_metric=founder_launch_metric,
            ),
        )

    def holodeck_add_work_item(
        self,
        workspace_id: str,
        *,
        title: str,
        kind: str = "task",
        status: str = "proposed",
        priority: str = "medium",
        owner: str = "",
        parent_id: str = "",
        depends_on: list[str] | None = None,
        linked_artifacts: list[str] | None = None,
        linked_tests: list[str] | None = None,
        guard_status: str = "",
        guard_request: str = "",
        guard_purpose: str = "",
        guard_paths: list[str] | None = None,
        acceptance_criteria: list[str] | None = None,
        constraints: list[str] | None = None,
        work_item_id: str = "",
    ) -> dict[str, Any]:
        return holodeck_module.holodeck_add_work_item(
            self.root,
            argparse.Namespace(
                workspace_id=_require_text(workspace_id, "workspace_id_required"),
                work_item_id=work_item_id or None,
                title=_require_text(title, "title_required"),
                kind=kind or "task",
                status=status or "proposed",
                priority=priority or "medium",
                owner=owner or "",
                parent_id=parent_id or "",
                depends_on=list(depends_on or []),
                linked_artifacts=list(linked_artifacts or []),
                linked_tests=list(linked_tests or []),
                guard_status=guard_status or "",
                guard_request=guard_request or "",
                guard_purpose=guard_purpose or "",
                guard_paths=",".join(guard_paths or []),
                acceptance_criteria=list(acceptance_criteria or []),
                constraints=list(constraints or []),
            ),
        )

    def holodeck_start_run(
        self,
        workspace_id: str,
        *,
        purpose: str,
        work_item_id: str = "",
        stage: str = "",
        status: str = "active",
        allowed_paths: list[str] | None = None,
        blocked_paths: list[str] | None = None,
        allowed_commands: list[str] | None = None,
        expected_outputs: list[str] | None = None,
        verification_plan: list[str] | None = None,
        context_budget: str = "",
        stop_conditions: list[str] | None = None,
        run_id: str = "",
    ) -> dict[str, Any]:
        return holodeck_module.holodeck_start_run(
            self.root,
            argparse.Namespace(
                workspace_id=_require_text(workspace_id, "workspace_id_required"),
                run_id=run_id or None,
                work_item_id=work_item_id or "",
                stage=stage or "",
                purpose=_require_text(purpose, "purpose_required"),
                allowed_paths=list(allowed_paths or []),
                blocked_paths=list(blocked_paths or []),
                allowed_commands=list(allowed_commands or []),
                expected_outputs=list(expected_outputs or []),
                verification_plan=list(verification_plan or []),
                context_budget=context_budget or "",
                stop_conditions=list(stop_conditions or []),
                status=status or "active",
            ),
        )

    def holodeck_workspace_not_found_payload(self, workspace_id: str) -> dict[str, Any]:
        workspaces = self.holodeck_list().get("workspaces", [])
        return {
            "error": "workspace_not_found",
            "workspace_id": workspace_id,
            "message": (
                f"Holodeck workspace '{workspace_id}' does not exist. "
                "Call /holodeck/list first and use a returned workspace_id."
            ),
            "suggested_action": "call /holodeck/list before /holodeck/check",
            "available_workspaces": [
                {
                    "workspace_id": item.get("workspace_id"),
                    "label": item.get("label", ""),
                    "status": item.get("status", ""),
                }
                for item in workspaces[:10]
            ],
        }


def _privacy_policy_html() -> str:
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <title>Inner World GPT Bridge Privacy Policy</title>
</head>
<body>
  <h1>Inner World GPT Bridge Privacy Policy</h1>
  <p>This service is a private action bridge for the Inner World project.</p>
  <p>It reads project files from the configured repo root and only performs user-requested writes, including mobile conversation artifact saves and explicitly approved Holodeck workspace actions.</p>
  <p>No third-party data brokerage or advertising use is intended. Data remains on the configured Talha’s Laboratory server and is used only to fulfill explicit ChatGPT action requests for this project.</p>
</body>
</html>
"""


def _object_schema(description: str) -> dict[str, Any]:
    return {
        "description": description,
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {},
                    "additionalProperties": True,
                }
            }
        },
    }


def build_gpt_openapi(public_base_url: str | None = None) -> dict[str, Any]:
    security = [{"InnerWorldActionKey": []}]
    object_response = {
        "200": _object_schema("Successful response."),
        "401": _object_schema("Invalid or missing action key."),
    }
    schema: dict[str, Any] = {
        "openapi": "3.1.0",
        "info": {
            "title": "Inner World GPT Bridge",
            "version": GPT_BRIDGE_CONTRACT_VERSION,
            "description": (
                "Dedicated action bridge for ChatGPT mobile collaboration on the Inner World project. "
                "Provides repo context retrieval plus controlled mobile conversation artifact saves."
            ),
        },
        "security": security,
        "paths": {
            "/health": {
                "get": {
                    "operationId": "getHealth",
                    "summary": "Health check",
                    "description": "Connectivity and contract check for the Inner World GPT bridge.",
                    "security": [],
                    "responses": {"200": _object_schema("Service health payload.")},
                }
            },
            "/context/status-bundle": {
                "get": {
                    "operationId": "getContextStatusBundle",
                    "summary": "Current Inner World context bundle",
                    "description": "First call for product-aware questions. Returns repo status, runtime overview, artifact status, and authoritative paths.",
                    "security": security,
                    "responses": object_response,
                }
            },
            "/context/authoritative-bundle": {
                "post": {
                    "operationId": "postContextAuthoritativeBundle",
                    "summary": "Authoritative Inner World doc bundle",
                    "description": "Pull the canonical product, protocol, and codebase docs before broader repo search.",
                    "security": security,
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "request_text": {"type": "string"},
                                        "extra_paths": {"type": "array", "items": {"type": "string"}},
                                        "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                                    },
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
            "/repo/status": {
                "get": {
                    "operationId": "getRepoStatus",
                    "summary": "Repo status",
                    "description": "Returns repo root metadata and git status when available.",
                    "security": security,
                    "responses": object_response,
                }
            },
            "/repo/search": {
                "get": {
                    "operationId": "getRepoSearch",
                    "summary": "Scoped repo search (fallback)",
                    "description": "Fallback GET search for repo questions.",
                    "security": security,
                    "parameters": [
                        {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "allowed_paths", "in": "query", "required": False, "schema": {"type": "array", "items": {"type": "string"}}},
                        {"name": "top_k", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8}},
                    ],
                    "responses": object_response,
                },
                "post": {
                    "operationId": "postRepoSearch",
                    "summary": "Scoped repo search",
                    "description": "Primary repo search tool for Inner World questions.",
                    "security": security,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "allowed_paths": {"type": "array", "items": {"type": "string"}},
                                        "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                                    },
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                },
            },
            "/repo/file": {
                "get": {
                    "operationId": "getRepoFile",
                    "summary": "Read a repo file window (fallback)",
                    "description": "Read a bounded window from a repo file by relative path.",
                    "security": security,
                    "parameters": [
                        {"name": "path", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "start_line", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                        {"name": "end_line", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1}},
                    ],
                    "responses": object_response,
                },
                "post": {
                    "operationId": "postRepoFile",
                    "summary": "Read a repo file window",
                    "description": "Primary exact file read for the Inner World repo.",
                    "security": security,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "path": {"type": "string"},
                                        "start_line": {"type": "integer", "minimum": 1},
                                        "end_line": {"type": "integer", "minimum": 1},
                                    },
                                    "required": ["path"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                },
            },
            "/holodeck/list": {
                "get": {
                    "operationId": "getHolodeckList",
                    "summary": "List Holodecks",
                    "description": "List Holodeck workspaces, optionally filtered by status.",
                    "security": security,
                    "parameters": [
                        {
                            "name": "status",
                            "in": "query",
                            "required": False,
                            "schema": {
                                "type": "string",
                                "enum": ["active", "paused", "blocked", "closed", "archived"],
                            },
                        }
                    ],
                    "responses": object_response,
                }
            },
            "/holodeck/status": {
                "get": {
                    "operationId": "getHolodeckStatus",
                    "summary": "Read Holodeck status",
                    "description": (
                        "Read the current snapshot for one Holodeck workspace. "
                        "Use a workspace_id returned by /holodeck/list or by /holodeck/create; do not guess from the app or repo name."
                    ),
                    "security": security,
                    "parameters": [
                        {"name": "workspace_id", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": object_response,
                }
            },
            "/holodeck/check": {
                "get": {
                    "operationId": "getHolodeckCheck",
                    "summary": "Check Holodeck health",
                    "description": (
                        "Run readiness, drift, inquiry, and constraint checks for one Holodeck workspace. "
                        "Call /holodeck/list first to get a valid workspace_id; do not guess from the app or repo name."
                    ),
                    "security": security,
                    "parameters": [
                        {"name": "workspace_id", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": object_response,
                }
            },
            "/holodeck/task-pack": {
                "post": {
                    "operationId": "postHolodeckTaskPack",
                    "summary": "Build a Holodeck task pack",
                    "description": (
                        "Build the canonical handoff pack for a Holodeck work item. "
                        "Use a workspace_id returned by /holodeck/list or /holodeck/create."
                    ),
                    "security": security,
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "workspace_id": {"type": "string"},
                                        "task_id": {"type": "string"},
                                        "request": {"type": "string"},
                                        "task_type": {"type": "string"},
                                    },
                                    "required": ["workspace_id", "task_id"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
            "/holodeck/create": {
                "post": {
                    "operationId": "postHolodeckCreate",
                    "summary": "Create a Holodeck",
                    "description": "Create a new Holodeck workspace for a bounded project objective.",
                    "security": security,
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "workspace_id": {"type": "string"},
                                        "title": {"type": "string"},
                                        "goal": {"type": "string"},
                                        "purpose": {"type": "string"},
                                        "success_condition": {"type": "string"},
                                        "scope_in": {"type": "array", "items": {"type": "string"}},
                                        "scope_out": {"type": "array", "items": {"type": "string"}},
                                        "template_key": {"type": "string"},
                                        "domains": {"type": "array", "items": {"type": "string"}},
                                        "founder_wedge": {"type": "string"},
                                        "founder_user": {"type": "string"},
                                        "founder_moat": {"type": "string"},
                                        "founder_gtm_risk": {"type": "string"},
                                        "founder_launch_metric": {"type": "string"},
                                    },
                                    "required": ["title", "goal", "purpose"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
            "/holodeck/start-run": {
                "post": {
                    "operationId": "postHolodeckStartRun",
                    "summary": "Start a Holodeck run contract",
                    "description": "Start an explicit agent operating contract inside a Holodeck workspace.",
                    "security": security,
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "workspace_id": {"type": "string"},
                                        "run_id": {"type": "string"},
                                        "work_item_id": {"type": "string"},
                                        "stage": {"type": "string"},
                                        "purpose": {"type": "string"},
                                        "status": {"type": "string"},
                                        "allowed_paths": {"type": "array", "items": {"type": "string"}},
                                        "blocked_paths": {"type": "array", "items": {"type": "string"}},
                                        "allowed_commands": {"type": "array", "items": {"type": "string"}},
                                        "expected_outputs": {"type": "array", "items": {"type": "string"}},
                                        "verification_plan": {"type": "array", "items": {"type": "string"}},
                                        "context_budget": {"type": "string"},
                                        "stop_conditions": {"type": "array", "items": {"type": "string"}},
                                    },
                                    "required": ["workspace_id", "purpose", "stop_conditions"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
            "/mobile-artifacts/list": {
                "get": {
                    "operationId": "getMobileArtifactsList",
                    "summary": "List saved mobile artifacts",
                    "description": "List conversation artifacts stored in the project-local mobile_artifacts folder.",
                    "security": security,
                    "responses": object_response,
                }
            },
            "/mobile-artifacts/read": {
                "get": {
                    "operationId": "getMobileArtifactsRead",
                    "summary": "Read a saved mobile artifact",
                    "description": "Read one artifact in full after list or search discovery.",
                    "security": security,
                    "parameters": [
                        {"name": "path", "in": "query", "required": True, "schema": {"type": "string"}},
                    ],
                    "responses": object_response,
                }
            },
            "/mobile-artifacts/search": {
                "get": {
                    "operationId": "getMobileArtifactsSearch",
                    "summary": "Search saved mobile artifacts (fallback)",
                    "description": "Fallback GET search for saved mobile artifacts.",
                    "security": security,
                    "parameters": [
                        {"name": "query", "in": "query", "required": True, "schema": {"type": "string"}},
                        {"name": "top_k", "in": "query", "required": False, "schema": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8}},
                    ],
                    "responses": object_response,
                },
                "post": {
                    "operationId": "postMobileArtifactsSearch",
                    "summary": "Search saved mobile artifacts",
                    "description": "Search existing mobile conversation artifacts before saving a new one.",
                    "security": security,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "query": {"type": "string"},
                                        "top_k": {"type": "integer", "minimum": 1, "maximum": 20, "default": 8},
                                    },
                                    "required": ["query"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                },
            },
            "/mobile-artifacts/save-chat": {
                "post": {
                    "operationId": "postMobileArtifactsSaveChat",
                    "summary": "Save the current ChatGPT collaboration as a mobile artifact",
                    "description": "Writes a markdown artifact into mobile_artifacts and can also import it into the repo session pipeline.",
                    "security": security,
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "title": {"type": "string"},
                                        "conversation_markdown": {"type": "string"},
                                        "tags": {"type": "array", "items": {"type": "string"}},
                                        "related_paths": {"type": "array", "items": {"type": "string"}},
                                        "ingest_into_session": {"type": "boolean", "default": True},
                                        "domains": {"type": "array", "items": {"type": "string"}},
                                        "request_text": {"type": "string"},
                                    },
                                    "required": ["title", "conversation_markdown"],
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
            "/sync/local-status": {
                "get": {
                    "operationId": "getSyncLocalStatus",
                    "summary": "Local artifact sync status",
                    "description": "Shows the current mobile_artifacts surface and a pull hint for syncing it elsewhere.",
                    "security": security,
                    "responses": object_response,
                }
            },
            "/openclaw/telegram-fix": {
                "post": {
                    "operationId": "postOpenclawTelegramFix",
                    "summary": "Repair Telegram agent bindings in OpenClaw config",
                    "description": "Migrates legacy channels.telegram.accounts.*.agentId values into top-level bindings and can restart the OpenClaw gateway.",
                    "security": security,
                    "x-openai-isConsequential": True,
                    "requestBody": {
                        "required": False,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "object",
                                    "properties": {
                                        "restart_gateway": {"type": "boolean", "default": True},
                                    },
                                }
                            }
                        },
                    },
                    "responses": object_response,
                }
            },
        },
        "components": {
            "securitySchemes": {
                "InnerWorldActionKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": GPT_API_KEY_HEADER,
                }
            },
            "schemas": {},
        },
    }
    if public_base_url:
        schema["servers"] = [{"url": public_base_url}]
    return schema


def make_gpt_bridge_handler(bridge: InnerWorldGPTBridge):
    class InnerWorldGPTBridgeHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def _send_json(self, payload: dict[str, Any], status_code: int = HTTPStatus.OK) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, content: str, status_code: int = HTTPStatus.OK) -> None:
            body = content.encode("utf-8")
            self.send_response(status_code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _auth_failed(self) -> None:
            api_key = self.headers.get(GPT_API_KEY_HEADER, "").strip()
            authorization = self.headers.get(AUTHORIZATION_HEADER, "").strip()
            bearer_token = ""
            if authorization.lower().startswith("bearer "):
                bearer_token = authorization[7:].strip()
            auth_debug = {
                "event": "auth_failed",
                "path": self.path,
                "method": self.command,
                "host": self.headers.get("Host", ""),
                "user_agent": self.headers.get("User-Agent", ""),
                "has_custom_header": bool(api_key),
                "custom_header_fingerprint": _short_fingerprint(api_key),
                "has_bearer_header": bool(bearer_token),
                "bearer_fingerprint": _short_fingerprint(bearer_token),
                "cf_ray": self.headers.get("Cf-Ray", ""),
            }
            print(json.dumps(auth_debug, ensure_ascii=False), file=sys.stderr, flush=True)
            self._send_json({"error": "invalid_action_key"}, status_code=HTTPStatus.UNAUTHORIZED)

        def _presented_action_key(self) -> str:
            api_key = self.headers.get(GPT_API_KEY_HEADER, "").strip()
            if api_key:
                return api_key
            authorization = self.headers.get(AUTHORIZATION_HEADER, "").strip()
            if authorization.lower().startswith("bearer "):
                return authorization[7:].strip()
            return ""

        def _require_api_key(self) -> bool:
            return self._presented_action_key() in bridge.accepted_action_keys

        def _handle_error(self, error: Exception) -> None:
            error_map = {
                "query_required": (HTTPStatus.BAD_REQUEST, "query_required"),
                "path_required": (HTTPStatus.BAD_REQUEST, "path_required"),
                "path_traversal_not_allowed": (HTTPStatus.BAD_REQUEST, "path_traversal_not_allowed"),
                "path_outside_repo": (HTTPStatus.BAD_REQUEST, "path_outside_repo"),
                "file_too_large": (HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "file_too_large"),
                "invalid_line_window": (HTTPStatus.BAD_REQUEST, "invalid_line_window"),
                "artifact_path_outside_root": (HTTPStatus.BAD_REQUEST, "artifact_path_outside_root"),
                "title_required": (HTTPStatus.BAD_REQUEST, "title_required"),
                "goal_required": (HTTPStatus.BAD_REQUEST, "goal_required"),
                "purpose_required": (HTTPStatus.BAD_REQUEST, "purpose_required"),
                "workspace_id_required": (HTTPStatus.BAD_REQUEST, "workspace_id_required"),
                "task_id_required": (HTTPStatus.BAD_REQUEST, "task_id_required"),
                "conversation_markdown_required": (HTTPStatus.BAD_REQUEST, "conversation_markdown_required"),
            }
            if isinstance(error, FileNotFoundError):
                message = str(error)
                if message.startswith("Workspace not found: "):
                    workspace_id = message.split("Workspace not found: ", 1)[1].strip()
                    self._send_json(bridge.holodeck_workspace_not_found_payload(workspace_id), status_code=HTTPStatus.NOT_FOUND)
                    return
                self._send_json({"error": "not_found"}, status_code=HTTPStatus.NOT_FOUND)
                return
            if isinstance(error, ValueError):
                status_code, message = error_map.get(str(error), (HTTPStatus.BAD_REQUEST, str(error)))
                self._send_json({"error": message}, status_code=status_code)
                return
            self._send_json({"error": str(error) or "internal_error"}, status_code=HTTPStatus.INTERNAL_SERVER_ERROR)

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            query_params = parse_qs(parsed.query)
            try:
                if path == "/health":
                    self._send_json(bridge.health())
                    return
                if path == "/openapi.json":
                    self._send_json(build_gpt_openapi(bridge.public_base_url))
                    return
                if path == "/privacy-policy":
                    self._send_html(_privacy_policy_html())
                    return
                if not self._require_api_key():
                    self._auth_failed()
                    return
                if path == "/context/status-bundle":
                    self._send_json(bridge.context_status_bundle())
                    return
                if path == "/repo/status":
                    self._send_json(bridge.repo_status())
                    return
                if path == "/repo/search":
                    allowed_paths = [value.strip() for value in query_params.get("allowed_paths", []) if value.strip()]
                    top_k = int((query_params.get("top_k", ["8"])[0] or "8").strip())
                    self._send_json(bridge.repo_search(query_params.get("query", [""])[0], allowed_paths, top_k))
                    return
                if path == "/repo/file":
                    start_line = query_params.get("start_line", [None])[0]
                    end_line = query_params.get("end_line", [None])[0]
                    self._send_json(
                        bridge.repo_file(
                            query_params.get("path", [""])[0],
                            int(start_line) if start_line else None,
                            int(end_line) if end_line else None,
                        )
                    )
                    return
                if path == "/holodeck/list":
                    self._send_json(bridge.holodeck_list(query_params.get("status", [""])[0]))
                    return
                if path == "/holodeck/status":
                    self._send_json(bridge.holodeck_status(query_params.get("workspace_id", [""])[0]))
                    return
                if path == "/holodeck/check":
                    self._send_json(bridge.holodeck_check(query_params.get("workspace_id", [""])[0]))
                    return
                if path == "/mobile-artifacts/list":
                    self._send_json(bridge.list_artifacts())
                    return
                if path == "/mobile-artifacts/read":
                    self._send_json(bridge.read_artifact(query_params.get("path", [""])[0]))
                    return
                if path == "/mobile-artifacts/search":
                    top_k = int((query_params.get("top_k", ["8"])[0] or "8").strip())
                    self._send_json(bridge.search_artifacts(query_params.get("query", [""])[0], top_k))
                    return
                if path == "/sync/local-status":
                    self._send_json(bridge.sync_local_status())
                    return
                self._send_json({"error": "not_found"}, status_code=HTTPStatus.NOT_FOUND)
            except Exception as exc:  # noqa: BLE001
                self._handle_error(exc)

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            try:
                if not self._require_api_key():
                    self._auth_failed()
                    return
                payload = _read_json_body(self)
                if path == "/context/authoritative-bundle":
                    self._send_json(
                        bridge.authoritative_bundle(
                            request_text=(payload.get("request_text") or "").strip() or None,
                            extra_paths=payload.get("extra_paths") or [],
                            top_k=int(payload.get("top_k") or 8),
                        )
                    )
                    return
                if path == "/repo/search":
                    self._send_json(
                        bridge.repo_search(
                            payload.get("query") or "",
                            payload.get("allowed_paths") or [],
                            int(payload.get("top_k") or 8),
                        )
                    )
                    return
                if path == "/repo/file":
                    self._send_json(
                        bridge.repo_file(
                            payload.get("path") or "",
                            payload.get("start_line"),
                            payload.get("end_line"),
                        )
                    )
                    return
                if path == "/holodeck/task-pack":
                    self._send_json(
                        bridge.holodeck_task_pack(
                            payload.get("workspace_id") or "",
                            payload.get("task_id") or "",
                            request=payload.get("request") or "",
                            task_type=payload.get("task_type") or "implementation",
                        )
                    )
                    return
                if path == "/holodeck/create":
                    self._send_json(
                        bridge.holodeck_create(
                            workspace_id=payload.get("workspace_id") or "",
                            title=payload.get("title") or "",
                            goal=payload.get("goal") or "",
                            purpose=payload.get("purpose") or "",
                            success_condition=payload.get("success_condition") or "",
                            scope_in=payload.get("scope_in") or [],
                            scope_out=payload.get("scope_out") or [],
                            template_key=payload.get("template_key") or "",
                            domains=payload.get("domains") or [],
                            founder_wedge=payload.get("founder_wedge"),
                            founder_user=payload.get("founder_user"),
                            founder_moat=payload.get("founder_moat"),
                            founder_gtm_risk=payload.get("founder_gtm_risk"),
                            founder_launch_metric=payload.get("founder_launch_metric"),
                        )
                    )
                    return
                if path == "/holodeck/start-run":
                    self._send_json(
                        bridge.holodeck_start_run(
                            payload.get("workspace_id") or "",
                            run_id=payload.get("run_id") or "",
                            work_item_id=payload.get("work_item_id") or "",
                            stage=payload.get("stage") or "",
                            purpose=payload.get("purpose") or "",
                            status=payload.get("status") or "active",
                            allowed_paths=payload.get("allowed_paths") or [],
                            blocked_paths=payload.get("blocked_paths") or [],
                            allowed_commands=payload.get("allowed_commands") or [],
                            expected_outputs=payload.get("expected_outputs") or [],
                            verification_plan=payload.get("verification_plan") or [],
                            context_budget=payload.get("context_budget") or "",
                            stop_conditions=payload.get("stop_conditions") or [],
                        )
                    )
                    return
                if path == "/mobile-artifacts/search":
                    self._send_json(
                        bridge.search_artifacts(
                            payload.get("query") or "",
                            int(payload.get("top_k") or 8),
                        )
                    )
                    return
                if path == "/mobile-artifacts/save-chat":
                    self._send_json(
                        bridge.save_chat(
                            title=payload.get("title") or "",
                            conversation_markdown=payload.get("conversation_markdown") or "",
                            tags=payload.get("tags") or [],
                            related_paths=payload.get("related_paths") or [],
                            ingest_into_session=bool(payload.get("ingest_into_session", True)),
                            domains=payload.get("domains") or [],
                            request_text=(payload.get("request_text") or "").strip() or None,
                        )
                    )
                    return
                if path == "/openclaw/telegram-fix":
                    self._send_json(
                        apply_openclaw_host_telegram_fix(
                            bridge.root,
                            apply=True,
                            restart_gateway=bool(payload.get("restart_gateway", True)),
                        )
                    )
                    return
                self._send_json({"error": "not_found"}, status_code=HTTPStatus.NOT_FOUND)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid_json"}, status_code=HTTPStatus.BAD_REQUEST)
            except Exception as exc:  # noqa: BLE001
                self._handle_error(exc)

    return InnerWorldGPTBridgeHandler


def serve_gpt_bridge(
    root: Path,
    *,
    host: str,
    port: int,
    action_key: str,
    legacy_action_keys: list[str] | None = None,
    public_base_url: str = "",
    artifact_root: Path | None = None,
    domains: list[str] | None = None,
) -> None:
    if not action_key.strip():
        raise SystemExit("INNER_WORLD_GPT_ACTION_KEY or --gpt-action-key is required in gpt_bridge mode.")
    bridge = InnerWorldGPTBridge(
        root=root,
        action_key=action_key,
        legacy_action_keys=legacy_action_keys,
        public_base_url=public_base_url,
        artifact_root=artifact_root,
        domains=domains,
    )
    try:
        preview = migrate_openclaw_telegram_bindings(root, apply=False)
        fix_result = apply_openclaw_host_telegram_fix(
            root,
            apply=True,
            restart_gateway=bool(preview.get("changes")),
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"event": "telegram_binding_autofix_failed", "error": str(exc)}, ensure_ascii=False), file=sys.stderr, flush=True)
    else:
        if fix_result.get("applied") or fix_result.get("changes"):
            print(
                json.dumps({"event": "telegram_binding_autofix", **fix_result}, ensure_ascii=False, default=str),
                file=sys.stderr,
                flush=True,
            )
    handler = make_gpt_bridge_handler(bridge)
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the Inner World backend for local/OpenClaw UI or GPT bridge mode.")
    parser.add_argument("--mode", choices=["app", "gpt_bridge"], default="app")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8421)
    parser.add_argument("--domains", default="research,art,entrepreneurship")
    parser.add_argument("--limit", type=int, default=12)
    parser.add_argument("--api-prefixes", default="/api,/apps/api/inner-world")
    parser.add_argument("--skip-refresh-on-start", action="store_true")
    parser.add_argument("--gpt-action-key", default=os.getenv("INNER_WORLD_GPT_ACTION_KEY", ""))
    parser.add_argument("--gpt-legacy-action-keys", default=os.getenv("INNER_WORLD_GPT_LEGACY_ACTION_KEYS", ""))
    parser.add_argument("--gpt-public-base-url", default=os.getenv("INNER_WORLD_GPT_PUBLIC_BASE_URL", ""))
    parser.add_argument("--gpt-artifact-root", default=os.getenv("INNER_WORLD_GPT_ARTIFACT_ROOT", ""))
    return parser


if __name__ == "__main__":
    args = build_parser().parse_args()
    domains = [item.strip() for item in args.domains.split(",") if item.strip()]
    if args.mode == "gpt_bridge":
        serve_gpt_bridge(
            ROOT,
            host=args.host,
            port=args.port or DEFAULT_GPT_BRIDGE_PORT,
            action_key=args.gpt_action_key,
            legacy_action_keys=_split_csv_values(args.gpt_legacy_action_keys),
            public_base_url=args.gpt_public_base_url,
            artifact_root=Path(args.gpt_artifact_root).expanduser().resolve() if args.gpt_artifact_root else DEFAULT_GPT_ARTIFACT_ROOT,
            domains=domains,
        )
    else:
        prefixes = [item.strip() for item in args.api_prefixes.split(",") if item.strip()]
        serve_miniapp(
            ROOT,
            host=args.host,
            port=args.port,
            domain_overlays=domains,
            limit=args.limit,
            api_prefixes=prefixes,
            refresh_on_start=not args.skip_refresh_on_start,
        )
