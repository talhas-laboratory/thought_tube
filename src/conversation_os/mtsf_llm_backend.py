from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .mtsf_extraction import validate_extraction_draft
from .storage import read_json

MODULE_ID = "kernel.mtsf.llm_backend"
CONTRACT_VERSION = "1.0.0"
DEFAULT_OPENROUTER_CHAT_URL = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_OPENROUTER_MODEL = "openai/gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 90

PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "DEFAULT_OPENROUTER_MODEL",
    "resolve_mtsf_llm_settings",
    "list_llm_backend_candidates",
    "build_mtsf_extraction_messages",
    "request_openrouter_chat_completion",
    "run_llm_extraction_chain",
)
__all__ = list(PUBLIC_API)


class LlmExtractionError(RuntimeError):
    def __init__(self, message: str, *, backend_id: str = "", attempts: Optional[List[Dict[str, str]]] = None) -> None:
        super().__init__(message)
        self.backend_id = backend_id
        self.attempts = list(attempts or [])


def _runtime_config_paths(root: Path) -> List[Path]:
    return [
        root / "product" / "inner_world_v1" / "config" / "runtime.json",
        Path.home() / ".config" / "inner_space" / "world_studio_runtime.json",
    ]


def _read_runtime_config(root: Path) -> Dict[str, Any]:
    for path in _runtime_config_paths(root):
        if path.exists():
            payload = read_json(path, default={})
            if isinstance(payload, dict):
                return payload
    return {}


def resolve_mtsf_llm_settings(root: Path) -> Dict[str, Any]:
    runtime = _read_runtime_config(root)
    mtsf_llm = runtime.get("mtsf_llm", {}) if isinstance(runtime.get("mtsf_llm"), dict) else {}
    world_studio = runtime.get("world_studio", {}) if isinstance(runtime.get("world_studio", {}), dict) else {}
    visual = world_studio.get("visual_embeddings", {}) if isinstance(world_studio.get("visual_embeddings", {}), dict) else {}

    api_key = (
        os.environ.get("MTSF_OPENROUTER_API_KEY")
        or os.environ.get("OPENROUTER_API_KEY")
        or os.environ.get("WORLD_STUDIO_OPENROUTER_API_KEY")
        or mtsf_llm.get("api_key")
        or visual.get("api_key")
        or runtime.get("openrouter_api_key")
        or ""
    )
    model = (
        os.environ.get("MTSF_OPENROUTER_MODEL")
        or mtsf_llm.get("model")
        or DEFAULT_OPENROUTER_MODEL
    )
    base_url = (
        os.environ.get("MTSF_OPENROUTER_CHAT_URL")
        or mtsf_llm.get("base_url")
        or DEFAULT_OPENROUTER_CHAT_URL
    )
    timeout_seconds = int(
        os.environ.get("MTSF_OPENROUTER_TIMEOUT")
        or mtsf_llm.get("timeout_seconds")
        or DEFAULT_TIMEOUT_SECONDS
    )
    backend_order = mtsf_llm.get("backend_order")
    if not isinstance(backend_order, list) or not backend_order:
        backend_order = ["openclaw", "openrouter"]

    chat_backend = (
        os.environ.get("INNER_WORLD_CHAT_BACKEND")
        or runtime.get("chat_backend")
        or "heuristic"
    )
    return {
        "api_key": str(api_key).strip(),
        "model": str(model).strip() or DEFAULT_OPENROUTER_MODEL,
        "base_url": str(base_url).strip() or DEFAULT_OPENROUTER_CHAT_URL,
        "timeout_seconds": timeout_seconds,
        "backend_order": [str(item) for item in backend_order],
        "chat_backend": str(chat_backend),
        "openrouter_enabled": bool(api_key),
        "openclaw_enabled": str(chat_backend) in {"openclaw_local", "openclaw_gateway"},
    }


def list_llm_backend_candidates(root: Path, *, llm_preference: str = "auto") -> List[str]:
    settings = resolve_mtsf_llm_settings(root)
    preference = str(llm_preference).lower()
    if preference == "api":
        return ["openrouter"] if settings["openrouter_enabled"] else []
    if preference == "force":
        candidates: List[str] = []
        if settings["openclaw_enabled"]:
            candidates.append("openclaw")
        if settings["openrouter_enabled"]:
            candidates.append("openrouter")
        return candidates
    if preference != "auto":
        return []

    ordered: List[str] = []
    for backend_id in settings["backend_order"]:
        if backend_id == "openclaw" and settings["openclaw_enabled"]:
            ordered.append("openclaw")
        elif backend_id == "openrouter" and settings["openrouter_enabled"]:
            ordered.append("openrouter")
    return ordered


def build_mtsf_extraction_messages(
    *,
    system_prompt: str,
    skill_excerpt: str,
    envelope: Dict[str, Any],
    session_id: str,
) -> List[Dict[str, str]]:
    project = envelope.get("context", {}).get("project") or f"session:{session_id}"
    raw_content = str(envelope.get("raw_content", ""))[:8000]
    system_text = "\n".join(
        [
            system_prompt,
            "",
            "Skill reference excerpt:",
            skill_excerpt[:4000],
            "",
            "Return one ExtractionDraft JSON object only.",
        ]
    )
    user_text = (
        "Emit an ExtractionDraft JSON object for this skill input envelope.\n"
        f"Project: {project}\n"
        f"Raw content:\n{raw_content}\n\n"
        f"Envelope:\n{json.dumps(envelope, ensure_ascii=False)}"
    )
    return [
        {"role": "system", "content": system_text},
        {"role": "user", "content": user_text},
    ]


def request_openrouter_chat_completion(
    *,
    api_key: str,
    model: str,
    messages: Sequence[Dict[str, str]],
    base_url: str = DEFAULT_OPENROUTER_CHAT_URL,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Dict[str, Any]:
    payload = {
        "model": model,
        "messages": list(messages),
        "temperature": 0.1,
        "response_format": {"type": "json_object"},
    }
    request = Request(
        base_url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/talhas-laboratory/thought_tube",
            "X-Title": "Conversation OS MTSF Extraction",
        },
        data=json.dumps(payload).encode("utf-8"),
        method="POST",
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:  # noqa: S310
            body = json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")[:500]
        raise LlmExtractionError(f"openrouter_http_{exc.code}:{detail}", backend_id="openrouter") from exc
    except URLError as exc:
        raise LlmExtractionError(f"openrouter_network:{exc.reason}", backend_id="openrouter") from exc

    if isinstance(body.get("error"), dict):
        raise LlmExtractionError(
            str(body["error"].get("message", "openrouter_request_failed")),
            backend_id="openrouter",
        )

    choices = body.get("choices", [])
    if not choices:
        raise LlmExtractionError("openrouter_empty_choices", backend_id="openrouter")
    message = choices[0].get("message", {})
    content = str(message.get("content", "")).strip()
    if not content:
        raise LlmExtractionError("openrouter_empty_content", backend_id="openrouter")

    usage = body.get("usage", {}) if isinstance(body.get("usage"), dict) else {}
    return {
        "content": content,
        "model": str(body.get("model", model)),
        "usage": usage,
        "backend_id": "openrouter",
    }


def _validate_parsed_draft(root: Path, draft: Dict[str, Any]) -> None:
    report = validate_extraction_draft(root, draft)
    if report.ok:
        return
    summary = "; ".join(report.errors[:5]) or "validation_failed"
    raise LlmExtractionError(f"invalid_extraction_draft:{summary}")


def _attempt_openclaw(
    root: Path,
    *,
    session_id: str,
    envelope: Dict[str, Any],
    system_prompt: str,
    skill_excerpt: str,
    parse_draft,
) -> Dict[str, Any]:
    from .chat_backends import request_openclaw_reply, resolve_chat_backend

    backend = resolve_chat_backend(root)
    if backend["id"] not in {"openclaw_local", "openclaw_gateway"}:
        raise LlmExtractionError("openclaw_backend_not_configured", backend_id="openclaw")

    context = {
        "character": "MTSF Semantic Shape Extractor",
        "system_prompt": "\n".join([system_prompt, "", "Skill reference excerpt:", skill_excerpt[:4000]]),
        "source_snippets": [
            {
                "title": envelope.get("context", {}).get("project") or f"session:{session_id}",
                "source_ref": envelope.get("input_id", f"session:{session_id}"),
                "excerpt": str(envelope.get("raw_content", ""))[:2000],
            }
        ],
    }
    thread = {"thread_id": f"mtsf-deep-{session_id}", "title": "MTSF deep extraction", "messages": []}
    user_message = (
        "Emit an ExtractionDraft JSON object for this skill input envelope:\n"
        f"{json.dumps(envelope, indent=2, ensure_ascii=False)}"
    )
    reply = request_openclaw_reply(root, context, user_message, thread, backend)
    draft = parse_draft(reply.get("content", ""))
    _validate_parsed_draft(root, draft)
    draft["provenance"]["model_id"] = f"openclaw:{backend['id']}"
    return {
        "draft": draft,
        "source": "llm",
        "backend_id": backend["id"],
    }


def _attempt_openrouter(
    root: Path,
    *,
    session_id: str,
    envelope: Dict[str, Any],
    system_prompt: str,
    skill_excerpt: str,
    parse_draft,
) -> Dict[str, Any]:
    settings = resolve_mtsf_llm_settings(root)
    if not settings["openrouter_enabled"]:
        raise LlmExtractionError("openrouter_api_key_missing", backend_id="openrouter")

    messages = build_mtsf_extraction_messages(
        system_prompt=system_prompt,
        skill_excerpt=skill_excerpt,
        envelope=envelope,
        session_id=session_id,
    )
    reply = request_openrouter_chat_completion(
        api_key=settings["api_key"],
        model=settings["model"],
        messages=messages,
        base_url=settings["base_url"],
        timeout_seconds=settings["timeout_seconds"],
    )
    draft = parse_draft(reply["content"])
    _validate_parsed_draft(root, draft)
    draft["provenance"]["model_id"] = f"openrouter:{reply.get('model', settings['model'])}"
    return {
        "draft": draft,
        "source": "llm",
        "backend_id": "openrouter",
        "usage": reply.get("usage", {}),
    }


def run_llm_extraction_chain(
    root: Path,
    *,
    session_id: str,
    envelope: Dict[str, Any],
    system_prompt: str,
    skill_excerpt: str,
    parse_draft,
    llm_preference: str = "auto",
) -> Dict[str, Any]:
    candidates = list_llm_backend_candidates(root, llm_preference=llm_preference)
    if not candidates:
        raise LlmExtractionError(
            f"no_llm_backends_available_for:{llm_preference}",
            attempts=[{"backend": "none", "error": "no_candidates"}],
        )

    attempts: List[Dict[str, str]] = []
    for backend_id in candidates:
        try:
            if backend_id == "openclaw":
                result = _attempt_openclaw(
                    root,
                    session_id=session_id,
                    envelope=envelope,
                    system_prompt=system_prompt,
                    skill_excerpt=skill_excerpt,
                    parse_draft=parse_draft,
                )
            elif backend_id == "openrouter":
                result = _attempt_openrouter(
                    root,
                    session_id=session_id,
                    envelope=envelope,
                    system_prompt=system_prompt,
                    skill_excerpt=skill_excerpt,
                    parse_draft=parse_draft,
                )
            else:
                raise LlmExtractionError(f"unsupported_backend:{backend_id}", backend_id=backend_id)
            result["backend_attempts"] = attempts
            result["selected_backend"] = backend_id
            return result
        except Exception as exc:
            attempts.append({"backend": backend_id, "error": str(exc)})

    raise LlmExtractionError(
        "all_llm_backends_failed",
        attempts=attempts,
    )
