# Mobile Surface Layer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and deploy a separate private mobile-first PWA surface for capture, personalized feed, and library on `mobile.talhaslaboratory.xyz` without replacing the existing Inner World miniapp.

**Architecture:** Add a new `mobile_surface` HTTP owner and `/api/mobile/*` namespace that reuses existing session, thought-feed, thought-detail, feedback, and thread owners. Serve a dedicated static PWA from `product/mobile_surface_v1`, protect it with app-level session auth, and deploy it as a separate home-server service and Cloudflare-backed subdomain.

**Tech Stack:** Python stdlib HTTP server, existing Conversation OS storage/session helpers, existing Inner World feed/thread owners, vanilla HTML/CSS/JS PWA assets, systemd, cloudflared, rsync, pytest.

---

## Preflight

Run these before touching code:

```bash
python3 tools/conversation_os.py repo-overview refresh
python3 tools/conversation_os.py engineering-guard assess \
  --request "Build a separate private mobile-first PWA surface for capture, feed, library, and deployment on mobile.talhaslaboratory.xyz." \
  --purpose "Let a single private user capture thoughts quickly, optionally continue the capture as a conversation, read a personalized internal feed, and revisit saved items on a separate subdomain without replacing the current miniapp." \
  --proposed-paths "src/conversation_os/mobile_surface.py,src/conversation_os/mobile_surface_api.py,product/mobile_surface_v1,tools/run_mobile_surface.py,tools/deploy_mobile_surface_to_openclaw.py,ops/systemd/inner-world-mobile.service.sample,docs/guides/deployment-guide.md,tests/test_conversation_os.py,context/substrate/modules/surface.mobile.mobile_surface.json,context/substrate/modules/surface.mobile.mobile_surface_api.json"
```

Expected:
- `repo-overview refresh` exits `0`
- guard returns `ready`

If the guard does not return `ready`, stop and narrow the file list before implementation.

## File Structure

**Create:**
- `src/conversation_os/mobile_surface.py`
- `src/conversation_os/mobile_surface_api.py`
- `product/mobile_surface_v1/index.html`
- `product/mobile_surface_v1/app.js`
- `product/mobile_surface_v1/styles.css`
- `product/mobile_surface_v1/manifest.webmanifest`
- `product/mobile_surface_v1/service-worker.js`
- `product/mobile_surface_v1/runtime-config.js`
- `tools/run_mobile_surface.py`
- `tools/deploy_mobile_surface_to_openclaw.py`
- `ops/systemd/inner-world-mobile.service.sample`
- `context/substrate/modules/surface.mobile.mobile_surface.json`
- `context/substrate/modules/surface.mobile.mobile_surface_api.json`

**Modify:**
- `tests/test_conversation_os.py`
- `docs/guides/deployment-guide.md`

**Responsibilities:**
- `mobile_surface.py`
  Browser-facing HTTP owner for the new surface. Handles static assets, cookie auth gate, and route dispatch into `/api/mobile/*`.
- `mobile_surface_api.py`
  Auth helpers, capture/session chat writes, feed adaptation, library grouping, and feedback endpoints.
- `product/mobile_surface_v1/*`
  The actual mobile PWA shell and runtime JS.
- `tools/run_mobile_surface.py`
  Local runtime entrypoint for the new surface.
- `tools/deploy_mobile_surface_to_openclaw.py`
  Remote deploy script for repo sync, systemd install, cloudflared patch, and verification.
- `ops/systemd/inner-world-mobile.service.sample`
  Template service unit for the home server.
- `context/substrate/modules/*.json`
  Module manifests required by repo formalization discipline.

### Task 1: Mobile Surface Auth And HTTP Owner

**Files:**
- Create: `src/conversation_os/mobile_surface.py`
- Create: `src/conversation_os/mobile_surface_api.py`
- Create: `context/substrate/modules/surface.mobile.mobile_surface.json`
- Create: `context/substrate/modules/surface.mobile.mobile_surface_api.json`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write the failing tests**

Add these imports near the existing `miniapp` imports in [tests/test_conversation_os.py](/Users/talhauddin/software/inner_space/tests/test_conversation_os.py):

```python
import http.cookiejar
import conversation_os.mobile_surface as mobile_surface_module
import conversation_os.mobile_surface_api as mobile_surface_api_module
from conversation_os.mobile_surface import make_mobile_surface_handler
```

Add a mobile product symlink in `ConversationOSTestCase.setUp()`:

```python
        os.symlink(
            REPO_ROOT / "product" / "mobile_surface_v1",
            self.root / "product" / "mobile_surface_v1",
            target_is_directory=True,
        )
```

Add a server helper beside `_start_test_miniapp_server()`:

```python
    def _start_test_mobile_surface_server(self):
        handler = make_mobile_surface_handler(self.root, ["research"])
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        host, port = sock.getsockname()
        sock.close()
        server = ThreadingHTTPServer((host, port), handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server, thread, f"http://{host}:{port}"
```

Add these tests:

```python
    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_surface_requires_session_for_api(self) -> None:
        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            with self.assertRaises(urllib_error.HTTPError) as ctx:
                urllib_request.urlopen(f"{base_url}/api/mobile/feed")
            self.assertEqual(ctx.exception.code, 401)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_surface_login_sets_cookie_and_serves_shell(self) -> None:
        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            opener = urllib_request.build_opener(
                urllib_request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            with opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "secret-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            ) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read().decode("utf-8"))
            self.assertTrue(payload["authenticated"])

            with urllib_request.urlopen(f"{base_url}/manifest.webmanifest") as response:
                self.assertEqual(response.status, 200)
                manifest = json.loads(response.read().decode("utf-8"))
            self.assertEqual(manifest["name"], "Inner World Mobile")
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_requires_session_for_api tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_login_sets_cookie_and_serves_shell -q
```

Expected:
- `FAIL`
- import error for `conversation_os.mobile_surface` or missing handler/function errors

- [ ] **Step 3: Write the minimal HTTP owner and auth/session API**

Create [src/conversation_os/mobile_surface_api.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface_api.py):

```python
from __future__ import annotations

import argparse
import hashlib
import hmac
import os
import secrets
from http import HTTPStatus
from pathlib import Path
from typing import Any

from .cli import session_start
from .storage import read_json, session_dir, utc_now


SESSION_COOKIE = "inner_world_mobile_session"


def _session_secret() -> str:
    password = os.getenv("INNER_WORLD_MOBILE_PASSWORD", "").strip()
    secret = os.getenv("INNER_WORLD_MOBILE_SESSION_SECRET", "").strip()
    return secret or password


def _session_signature(session_token: str) -> str:
    secret = _session_secret().encode("utf-8")
    return hmac.new(secret, session_token.encode("utf-8"), hashlib.sha256).hexdigest()


def build_session_cookie(session_token: str) -> str:
    return f"{session_token}.{_session_signature(session_token)}"


def parse_session_cookie(raw_cookie: str | None) -> str | None:
    if not raw_cookie or "." not in raw_cookie:
        return None
    token, signature = raw_cookie.rsplit(".", 1)
    expected = _session_signature(token)
    if not hmac.compare_digest(signature, expected):
        return None
    return token


def login_mobile_session(password: str) -> dict[str, Any]:
    expected = os.getenv("INNER_WORLD_MOBILE_PASSWORD", "").strip()
    if not expected or password.strip() != expected:
        raise PermissionError("invalid_password")
    session_token = secrets.token_hex(24)
    return {
        "authenticated": True,
        "session_cookie": build_session_cookie(session_token),
        "issued_at": utc_now(),
    }


def logout_mobile_session() -> dict[str, Any]:
    return {"authenticated": False}


def require_mobile_session(raw_cookie: str | None) -> str:
    session_token = parse_session_cookie(raw_cookie)
    if not session_token:
        raise PermissionError("auth_required")
    return session_token


def ensure_mobile_capture_session(root: Path, session_id: str | None = None) -> dict[str, Any]:
    existing = read_json(session_dir(root, session_id or "") / "manifest.json", default=None) if session_id else None
    if existing:
        return existing
    return session_start(
        root,
        argparse.Namespace(
            session_id=session_id,
            title="Mobile capture session",
            participants="user,assistant",
            source_type="mobile_surface",
            domains="mobile,research",
        ),
    )
```

Create [src/conversation_os/mobile_surface.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface.py):

```python
from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

from .mobile_surface_api import login_mobile_session, logout_mobile_session, require_mobile_session


def _assets_dir(root: Path) -> Path:
    return root / "product" / "mobile_surface_v1"


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    payload = handler.rfile.read(length)
    return json.loads(payload.decode("utf-8")) if payload else {}


def make_mobile_surface_handler(root: Path, domain_overlays: list[str] | None = None):
    assets_dir = _assets_dir(root)

    class Handler(BaseHTTPRequestHandler):
        def _send_json(self, payload: dict, status: int = HTTPStatus.OK, *, cookie: str | None = None) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            if cookie:
                self.send_header("Set-Cookie", cookie)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path) -> None:
            content = path.read_bytes()
            mime_type, _ = mimetypes.guess_type(path.name)
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _cookie_value(self, name: str) -> str | None:
            raw = self.headers.get("Cookie", "")
            if not raw:
                return None
            cookie = SimpleCookie()
            cookie.load(raw)
            morsel = cookie.get(name)
            return morsel.value if morsel else None

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/mobile/"):
                try:
                    require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                except PermissionError:
                    self._send_json({"error": "auth_required"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                self._send_json({"ok": True})
                return
            asset_path = assets_dir / ("index.html" if parsed.path in {"", "/"} else parsed.path.lstrip("/"))
            if asset_path.exists() and asset_path.is_file():
                self._send_file(asset_path)
                return
            self.send_response(HTTPStatus.NOT_FOUND)
            self.end_headers()

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/api/mobile/session":
                payload = _read_json_body(self)
                result = login_mobile_session(payload.get("password", ""))
                cookie = "inner_world_mobile_session={value}; Path=/; HttpOnly; SameSite=Lax".format(
                    value=result["session_cookie"]
                )
                self._send_json({"authenticated": True}, cookie=cookie)
                return
            if parsed.path == "/api/mobile/session/logout":
                logout_mobile_session()
                self._send_json(
                    {"authenticated": False},
                    cookie="inner_world_mobile_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Lax",
                )
                return
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

    return Handler


def serve_mobile_surface(root: Path, *, host: str = "127.0.0.1", port: int = 8423, domain_overlays: list[str] | None = None) -> None:
    server = ThreadingHTTPServer((host, port), make_mobile_surface_handler(root, domain_overlays or []))
    try:
        server.serve_forever()
    finally:
        server.server_close()
```

Create [context/substrate/modules/surface.mobile.mobile_surface.json](/Users/talhauddin/software/inner_space/context/substrate/modules/surface.mobile.mobile_surface.json):

```json
{
  "module_id": "surface.mobile.mobile_surface",
  "layer": "surface",
  "status": "active",
  "owner": "Browser-facing mobile HTTP surface for capture, feed, library, and session auth.",
  "purpose": "Serve the dedicated mobile surface assets and dispatch private mobile API calls into Conversation OS owners."
}
```

Create [context/substrate/modules/surface.mobile.mobile_surface_api.json](/Users/talhauddin/software/inner_space/context/substrate/modules/surface.mobile.mobile_surface_api.json):

```json
{
  "module_id": "surface.mobile.mobile_surface_api",
  "layer": "surface",
  "status": "active",
  "owner": "Mobile surface API adaptation layer for auth, capture, feed, library, and conversation payload shaping.",
  "purpose": "Translate mobile-surface requests into canonical session writes and existing Inner World read models."
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_requires_session_for_api tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_login_sets_cookie_and_serves_shell -q
```

Expected:
- `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/mobile_surface.py src/conversation_os/mobile_surface_api.py context/substrate/modules/surface.mobile.mobile_surface.json context/substrate/modules/surface.mobile.mobile_surface_api.json tests/test_conversation_os.py
git commit -m "feat: add mobile surface auth and handler scaffold"
```

### Task 2: Capture Writes And Session-Based Conversation

**Files:**
- Modify: `src/conversation_os/mobile_surface_api.py`
- Modify: `src/conversation_os/mobile_surface.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write the failing tests**

Add these tests:

```python
    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_capture_appends_session_event_and_returns_ack(self) -> None:
        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            opener = urllib_request.build_opener(
                urllib_request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            login_request = urllib_request.Request(
                f"{base_url}/api/mobile/session",
                data=json.dumps({"password": "secret-pass"}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with opener.open(login_request) as response:
                self.assertEqual(response.status, 200)

            capture_request = urllib_request.Request(
                f"{base_url}/api/mobile/capture",
                data=json.dumps({"content": "Need to connect the product feed and mobile capture."}).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            with opener.open(capture_request) as response:
                self.assertEqual(response.status, 200)
                payload = json.loads(response.read().decode("utf-8"))

            self.assertTrue(payload["session_id"].startswith("session-"))
            self.assertTrue(payload["capture_id"].startswith("event-"))
            events = read_jsonl(session_events_path(self.root, payload["session_id"]))
            self.assertEqual(events[-1]["kind"], "capture")
            self.assertIn("product feed and mobile capture", events[-1]["content"])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    @mock.patch("conversation_os.mobile_surface_api.request_openclaw_reply")
    def test_mobile_conversation_reply_appends_assistant_message(self, reply_mock) -> None:
        reply_mock.return_value = {"content": "Keep the capture path frictionless and move chat after submit.", "backend_id": "heuristic"}
        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            opener = urllib_request.build_opener(
                urllib_request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "secret-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            )
            with opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/capture",
                    data=json.dumps({"content": "The app should capture first, then invite chat."}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            ) as response:
                capture_payload = json.loads(response.read().decode("utf-8"))

            with opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/conversations/{capture_payload['session_id']}/reply",
                    data=json.dumps({"message": "Push that further."}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            ) as response:
                reply_payload = json.loads(response.read().decode("utf-8"))

            events = read_jsonl(session_events_path(self.root, capture_payload["session_id"]))
            self.assertEqual(events[-1]["actor"], "assistant")
            self.assertEqual(events[-1]["kind"], "response")
            self.assertIn("frictionless", reply_payload["assistant_message"]["content"])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_capture_appends_session_event_and_returns_ack tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_conversation_reply_appends_assistant_message -q
```

Expected:
- `FAIL`
- `404` or `{"error": "not_found"}` for the new endpoints

- [ ] **Step 3: Implement capture and conversation**

Update [src/conversation_os/mobile_surface_api.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface_api.py):

```python
from .chat_backends import request_openclaw_reply, resolve_chat_backend
from .cli import session_append, session_start
from .storage import make_id, read_jsonl, session_events_path


def append_mobile_capture(root: Path, *, session_id: str | None, content: str) -> dict[str, Any]:
    manifest = ensure_mobile_capture_session(root, session_id=session_id)
    event = session_append(
        root,
        argparse.Namespace(
            session_id=manifest["session_id"],
            actor="user",
            kind="capture",
            content=content.strip(),
            attachments="",
            tags="mobile_surface,capture",
            source_ref=None,
        ),
    )
    return {
        "capture_id": event["event_id"],
        "session_id": manifest["session_id"],
        "created_at": event["timestamp"],
        "continue_conversation_available": True,
    }


def _mobile_session_thread(session_id: str, events: list[dict[str, Any]]) -> dict[str, Any]:
    messages = [
        {
            "message_id": event["event_id"],
            "role": "assistant" if event["actor"] == "assistant" else "user",
            "content": event["content"],
            "created_at": event["timestamp"],
        }
        for event in events
        if event["actor"] in {"assistant", "user"}
    ]
    return {
        "thread_id": session_id,
        "title": "Mobile capture conversation",
        "messages": messages,
    }


def reply_in_mobile_session(root: Path, *, session_id: str, user_message: str) -> dict[str, Any]:
    events = read_jsonl(session_events_path(root, session_id))
    thread = _mobile_session_thread(session_id, events)
    context = {
        "character": "Mobile capture companion",
        "system_prompt": "Help the user continue the captured thought without flattening ambiguity. Stay concise and grounded.",
        "source_snippets": [],
    }
    backend = resolve_chat_backend(root)
    reply = request_openclaw_reply(root, context, user_message, thread, backend)
    user_event = session_append(
        root,
        argparse.Namespace(
            session_id=session_id,
            actor="user",
            kind="message",
            content=user_message.strip(),
            attachments="",
            tags="mobile_surface,conversation",
            source_ref=None,
        ),
    )
    assistant_event = session_append(
        root,
        argparse.Namespace(
            session_id=session_id,
            actor="assistant",
            kind="response",
            content=reply["content"],
            attachments="",
            tags="mobile_surface,conversation",
            source_ref=None,
        ),
    )
    return {
        "session_id": session_id,
        "user_message": user_event,
        "assistant_message": assistant_event,
        "backend_id": reply["backend_id"],
    }
```

Update [src/conversation_os/mobile_surface.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface.py):

```python
from .mobile_surface_api import (
    append_mobile_capture,
    login_mobile_session,
    logout_mobile_session,
    reply_in_mobile_session,
    require_mobile_session,
)

            if parsed.path == "/api/mobile/capture":
                require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                payload = _read_json_body(self)
                result = append_mobile_capture(root, session_id=payload.get("session_id"), content=payload.get("content", ""))
                self._send_json(result)
                return

            if parsed.path.startswith("/api/mobile/conversations/") and parsed.path.endswith("/reply"):
                require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                session_id = parsed.path[len("/api/mobile/conversations/") : -len("/reply")].strip("/")
                payload = _read_json_body(self)
                result = reply_in_mobile_session(root, session_id=session_id, user_message=payload.get("message", ""))
                self._send_json(result)
                return
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_capture_appends_session_event_and_returns_ack tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_conversation_reply_appends_assistant_message -q
```

Expected:
- `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/mobile_surface.py src/conversation_os/mobile_surface_api.py tests/test_conversation_os.py
git commit -m "feat: add mobile capture and session conversation APIs"
```

### Task 3: Feed, Detail, Feedback, And Library Adapters

**Files:**
- Modify: `src/conversation_os/mobile_surface_api.py`
- Modify: `src/conversation_os/mobile_surface.py`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write the failing tests**

Add these tests:

```python
    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_feed_adapts_existing_thought_feed(self) -> None:
        source = self.root / "mobile-feed-source.md"
        source.write_text(
            "# User\n\nThe mobile surface should feel quiet and fast.\n\n# Assistant\n\nThe feed should surface only the most relevant thing to return to.",
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=3, domain_overlays=["research"])

        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            opener = urllib_request.build_opener(
                urllib_request.HTTPCookieProcessor(http.cookiejar.CookieJar())
            )
            opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "secret-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            )
            with opener.open(f"{base_url}/api/mobile/feed") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertGreaterEqual(payload["count"], 1)
            self.assertIn("items", payload)
            self.assertIn("lead", payload["items"][0])
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_library_groups_captures_conversations_and_saved_items(self) -> None:
        source = self.root / "mobile-library-source.md"
        source.write_text(
            "# User\n\nPreserve the path back to useful thoughts.\n\n# Assistant\n\nThat means saves, threads, and captures need a clean return surface.",
            encoding="utf-8",
        )
        seed_sources(self.root, source, "conversation_library")
        derive_graph(self.root, ["research"])
        generate_daily_batch(self.root, limit=1, domain_overlays=["research"])
        thought = build_thought_feed(self.root, limit=1, domain_overlays=["research"])["thoughts"][0]
        chat_result = chat_with_thought(self.root, thought["thought_id"], "Why return here?", domain_overlays=["research"])
        save_thread(self.root, chat_result["thread"]["thread_id"], ["research"])
        record_feedback(self.root, thought["insight_id"], "relevant")

        session_payload = append_mobile_capture(self.root, session_id=None, content="Return should feel easy.")
        reply_in_mobile_session(self.root, session_id=session_payload["session_id"], user_message="Push that further.")

        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            opener = urllib_request.build_opener()
            opener.open(
                urllib_request.Request(
                    f"{base_url}/api/mobile/session",
                    data=json.dumps({"password": "secret-pass"}).encode("utf-8"),
                    method="POST",
                    headers={"Content-Type": "application/json"},
                )
            )
            with opener.open(f"{base_url}/api/mobile/library") as response:
                payload = json.loads(response.read().decode("utf-8"))
            self.assertIn("captures", payload)
            self.assertIn("conversations", payload)
            self.assertIn("saved_items", payload)
            self.assertGreaterEqual(len(payload["captures"]), 1)
            self.assertGreaterEqual(len(payload["conversations"]), 1)
            self.assertGreaterEqual(len(payload["saved_items"]), 1)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_feed_adapts_existing_thought_feed tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_library_groups_captures_conversations_and_saved_items -q
```

Expected:
- `FAIL`
- missing `/api/mobile/feed` and `/api/mobile/library`

- [ ] **Step 3: Implement mobile read models and feedback**

Update [src/conversation_os/mobile_surface_api.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface_api.py):

```python
from .product_inner_world import (
    build_thought_feed,
    chat_with_thought,
    get_thread_detail,
    get_thought_detail,
    record_feedback,
    save_thread,
)
from .storage import read_json, read_jsonl, session_dir


def build_mobile_feed(root: Path, *, domain_overlays: list[str] | None = None, limit: int = 12) -> dict[str, Any]:
    feed = build_thought_feed(root, limit=limit, domain_overlays=domain_overlays or ["research"])
    items = []
    for thought in feed.get("thoughts", []):
        preview = thought.get("preview_payload", {})
        items.append(
            {
                "item_id": thought["thought_id"],
                "thought_id": thought["thought_id"],
                "insight_id": thought["insight_id"],
                "title": preview.get("title") or thought.get("title") or thought.get("short_text", ""),
                "lead": preview.get("lead_text") or thought.get("short_text", ""),
                "summary": preview.get("what_changed") or thought.get("why_it_matters", ""),
                "evidence_status": thought.get("evidence_status", "unknown"),
                "confidence": thought.get("confidence", 0.0),
                "domain_label": thought.get("domain_label", ""),
                "feedback_state": thought.get("feedback_state", "pending"),
                "saved": bool(thought.get("active_thread")),
            }
        )
    return {"count": len(items), "items": items, "diagnostics": feed.get("diagnostics", {})}


def build_mobile_library(root: Path) -> dict[str, Any]:
    captures = []
    conversations = []
    saved_items = []

    for manifest_path in sorted((root / "memory" / "sessions").glob("*/manifest.json")):
        manifest = read_json(manifest_path, default={})
        if manifest.get("source_type") != "mobile_surface":
            continue
        session_id = manifest["session_id"]
        events = read_jsonl(session_events_path(root, session_id))
        captures.extend(
            {
                "capture_id": event["event_id"],
                "session_id": session_id,
                "content": event["content"],
                "created_at": event["timestamp"],
            }
            for event in events
            if event["kind"] == "capture"
        )
        if any(event["actor"] == "assistant" for event in events):
            conversations.append(
                {
                    "conversation_id": session_id,
                    "session_id": session_id,
                    "updated_at": events[-1]["timestamp"] if events else manifest.get("started_at"),
                    "message_count": sum(1 for event in events if event["actor"] in {"user", "assistant"}),
                    "preview": events[-1]["content"] if events else "",
                    "conversation_type": "mobile_session",
                }
            )

    threads_dir = root / "product" / "inner_world_v1" / "data" / "threads"
    for thread_path in sorted(threads_dir.glob("*.json")):
        thread = read_json(thread_path, default={})
        if thread.get("status") == "saved":
            conversations.append(
                {
                    "conversation_id": thread["thread_id"],
                    "thread_id": thread["thread_id"],
                    "updated_at": thread.get("updated_at"),
                    "message_count": len(thread.get("messages", [])),
                    "preview": thread.get("context_summary", ""),
                    "conversation_type": "thought_thread",
                }
            )

    for item in build_mobile_feed(root, limit=50)["items"]:
        if item["feedback_state"] in {"relevant", "revisit_later", "saved"}:
            saved_items.append(item)

    captures.sort(key=lambda row: row["created_at"], reverse=True)
    conversations.sort(key=lambda row: row["updated_at"], reverse=True)
    saved_items.sort(key=lambda row: (row["feedback_state"], row["title"]), reverse=True)
    return {
        "captures": captures[:30],
        "conversations": conversations[:30],
        "saved_items": saved_items[:30],
    }


def mobile_feed_feedback(root: Path, *, insight_id: str, feedback_state: str) -> dict[str, Any]:
    return record_feedback(root, insight_id, feedback_state)
```

Update [src/conversation_os/mobile_surface.py](/Users/talhauddin/software/inner_space/src/conversation_os/mobile_surface.py):

```python
from .mobile_surface_api import build_mobile_feed, build_mobile_library, mobile_feed_feedback

            if parsed.path == "/api/mobile/feed":
                require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                self._send_json(build_mobile_feed(root, domain_overlays=domain_overlays))
                return

            if parsed.path == "/api/mobile/library":
                require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                self._send_json(build_mobile_library(root))
                return

            if parsed.path == "/api/mobile/feedback":
                require_mobile_session(self._cookie_value("inner_world_mobile_session"))
                payload = _read_json_body(self)
                self._send_json(
                    mobile_feed_feedback(
                        root,
                        insight_id=payload.get("insight_id", ""),
                        feedback_state=payload.get("feedback_state", ""),
                    )
                )
                return
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_feed_adapts_existing_thought_feed tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_library_groups_captures_conversations_and_saved_items -q
```

Expected:
- `2 passed`

- [ ] **Step 5: Commit**

```bash
git add src/conversation_os/mobile_surface.py src/conversation_os/mobile_surface_api.py tests/test_conversation_os.py
git commit -m "feat: add mobile feed and library adapters"
```

### Task 4: Build The Mobile PWA Frontend

**Files:**
- Create: `product/mobile_surface_v1/index.html`
- Create: `product/mobile_surface_v1/app.js`
- Create: `product/mobile_surface_v1/styles.css`
- Create: `product/mobile_surface_v1/manifest.webmanifest`
- Create: `product/mobile_surface_v1/service-worker.js`
- Create: `product/mobile_surface_v1/runtime-config.js`
- Modify: `tests/test_conversation_os.py`

- [ ] **Step 1: Write the failing tests**

Add this test:

```python
    @mock.patch.dict(os.environ, {"INNER_WORLD_MOBILE_PASSWORD": "secret-pass"}, clear=False)
    def test_mobile_surface_serves_pwa_assets(self) -> None:
        server, thread, base_url = self._start_test_mobile_surface_server()
        try:
            with urllib_request.urlopen(f"{base_url}/") as response:
                self.assertEqual(response.status, 200)
                index_html = response.read().decode("utf-8")
            self.assertIn("./app.js", index_html)
            self.assertIn("./styles.css", index_html)
            self.assertIn("./manifest.webmanifest", index_html)

            with urllib_request.urlopen(f"{base_url}/manifest.webmanifest") as response:
                manifest = json.loads(response.read().decode("utf-8"))
            self.assertEqual(manifest["display"], "standalone")

            with urllib_request.urlopen(f"{base_url}/service-worker.js") as response:
                js = response.read().decode("utf-8")
            self.assertIn("mobile-surface-v1", js)
        finally:
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_serves_pwa_assets -q
```

Expected:
- `FAIL`
- missing files under `product/mobile_surface_v1`

- [ ] **Step 3: Create the PWA assets**

Create [product/mobile_surface_v1/index.html](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/index.html):

```html
<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <meta name="theme-color" content="#f4f1e8" />
    <title>Inner World Mobile</title>
    <link rel="manifest" href="./manifest.webmanifest" />
    <link rel="stylesheet" href="./styles.css" />
  </head>
  <body>
    <main class="app-shell">
      <section id="auth-view" class="auth-view"></section>
      <section id="app-view" class="app-view app-view--hidden">
        <header class="surface-header">
          <h1>Inner World Mobile</h1>
          <button id="logout-button" class="icon-button" type="button" aria-label="Log out">Exit</button>
        </header>
        <section id="panel-capture" class="panel panel--active"></section>
        <section id="panel-feed" class="panel"></section>
        <section id="panel-library" class="panel"></section>
        <nav class="tabbar" aria-label="Primary">
          <button class="tabbar-button tabbar-button--active" data-tab="capture" type="button">Capture</button>
          <button class="tabbar-button" data-tab="feed" type="button">Feed</button>
          <button class="tabbar-button" data-tab="library" type="button">Library</button>
        </nav>
      </section>
    </main>
    <script src="./runtime-config.js"></script>
    <script src="./app.js" defer></script>
  </body>
</html>
```

Create [product/mobile_surface_v1/app.js](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/app.js):

```javascript
const API_BASE = (window.INNER_WORLD_MOBILE_CONFIG?.apiBaseUrl || "/api/mobile").replace(/\/$/, "");

const state = {
  activeTab: "capture",
  sessionId: null,
  feed: [],
  library: { captures: [], conversations: [], saved_items: [] },
};

async function requestJSON(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    ...options,
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `request_failed_${response.status}`);
  }
  return response.json();
}

function renderAuth() {
  document.querySelector("#auth-view").innerHTML = `
    <form id="login-form" class="auth-form">
      <label class="auth-label" for="password">Private access</label>
      <input id="password" name="password" type="password" autocomplete="current-password" />
      <button type="submit">Enter</button>
    </form>
  `;
  document.querySelector("#login-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const password = new FormData(event.currentTarget).get("password");
    await requestJSON("/session", {
      method: "POST",
      body: JSON.stringify({ password }),
    });
    document.querySelector("#auth-view").innerHTML = "";
    document.querySelector("#app-view").classList.remove("app-view--hidden");
    await Promise.all([loadFeed(), loadLibrary()]);
    renderCapture();
  });
}

function renderCapture() {
  document.querySelector("#panel-capture").innerHTML = `
    <form id="capture-form" class="capture-form">
      <label class="auth-label" for="capture-input">Capture</label>
      <textarea id="capture-input" name="content" rows="7"></textarea>
      <div class="capture-actions">
        <button type="submit">Capture</button>
        <button id="continue-button" type="button" disabled>Continue conversation</button>
      </div>
      <div id="capture-status" class="capture-status"></div>
      <div id="conversation-thread" class="conversation-thread"></div>
    </form>
  `;
  document.querySelector("#capture-form").addEventListener("submit", async (event) => {
    event.preventDefault();
    const content = new FormData(event.currentTarget).get("content");
    const payload = await requestJSON("/capture", {
      method: "POST",
      body: JSON.stringify({ content, session_id: state.sessionId }),
    });
    state.sessionId = payload.session_id;
    document.querySelector("#capture-status").textContent = "Captured.";
    document.querySelector("#continue-button").disabled = false;
    await loadLibrary();
  });
  document.querySelector("#continue-button").addEventListener("click", async () => {
    const message = window.prompt("Continue the thought");
    if (!message || !state.sessionId) return;
    const payload = await requestJSON(`/conversations/${state.sessionId}/reply`, {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    const thread = document.querySelector("#conversation-thread");
    thread.innerHTML += `<article class="message message--user">${message}</article><article class="message message--assistant">${payload.assistant_message.content}</article>`;
    await loadLibrary();
  });
}

async function loadFeed() {
  const payload = await requestJSON("/feed");
  state.feed = payload.items || [];
  document.querySelector("#panel-feed").innerHTML = state.feed.map((item) => `
    <article class="feed-item">
      <h2>${item.title}</h2>
      <p>${item.lead}</p>
      <div class="feed-meta">${item.evidence_status} • ${Number(item.confidence || 0).toFixed(2)}</div>
      <div class="feed-actions">
        <button data-feedback="relevant" data-insight-id="${item.insight_id}" type="button">Relevant</button>
        <button data-feedback="revisit_later" data-insight-id="${item.insight_id}" type="button">Revisit</button>
        <button data-feedback="dismiss" data-insight-id="${item.insight_id}" type="button">Dismiss</button>
      </div>
    </article>
  `).join("");
  document.querySelectorAll("#panel-feed [data-feedback]").forEach((button) => {
    button.addEventListener("click", async () => {
      await requestJSON("/feedback", {
        method: "POST",
        body: JSON.stringify({
          insight_id: button.dataset.insightId,
          feedback_state: button.dataset.feedback,
        }),
      });
      await Promise.all([loadFeed(), loadLibrary()]);
    });
  });
}

async function loadLibrary() {
  state.library = await requestJSON("/library");
  document.querySelector("#panel-library").innerHTML = `
    <section class="library-section"><h2>Captures</h2>${state.library.captures.map((item) => `<p>${item.content}</p>`).join("")}</section>
    <section class="library-section"><h2>Conversations</h2>${state.library.conversations.map((item) => `<p>${item.preview}</p>`).join("")}</section>
    <section class="library-section"><h2>Saved</h2>${state.library.saved_items.map((item) => `<p>${item.title}</p>`).join("")}</section>
  `;
}

function installTabs() {
  document.querySelectorAll(".tabbar-button").forEach((button) => {
    button.addEventListener("click", () => {
      state.activeTab = button.dataset.tab;
      document.querySelectorAll(".tabbar-button").forEach((node) => node.classList.toggle("tabbar-button--active", node === button));
      document.querySelectorAll(".panel").forEach((panel) => panel.classList.remove("panel--active"));
      document.querySelector(`#panel-${state.activeTab}`).classList.add("panel--active");
    });
  });
}

async function logout() {
  await requestJSON("/session/logout", { method: "POST" });
  window.location.reload();
}

window.addEventListener("load", async () => {
  renderAuth();
  installTabs();
  document.querySelector("#logout-button").addEventListener("click", logout);
  if ("serviceWorker" in navigator) {
    navigator.serviceWorker.register("./service-worker.js");
  }
});
```

Create [product/mobile_surface_v1/styles.css](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/styles.css):

```css
:root {
  --paper: #f4f1e8;
  --ink: #1d1b18;
  --muted: #6d665d;
  --line: #d4cec2;
  --accent: #1f6f5f;
  --accent-soft: #d8ebe4;
  --panel: #fffdf7;
}

* { box-sizing: border-box; }
html, body { margin: 0; min-height: 100%; background: var(--paper); color: var(--ink); font-family: "Iowan Old Style", "Palatino Linotype", serif; }
body { padding: 0; }
.app-shell { min-height: 100vh; display: grid; }
.auth-view, .app-view { min-height: 100vh; }
.app-view--hidden { display: none; }
.surface-header { display: flex; justify-content: space-between; align-items: center; padding: 18px 18px 8px; }
.surface-header h1 { margin: 0; font-size: 1.2rem; }
.icon-button, .auth-form button, .capture-actions button, .feed-actions button, .tabbar-button {
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  min-height: 44px;
}
.auth-view { display: grid; place-items: center; padding: 24px; }
.auth-form { width: min(100%, 420px); display: grid; gap: 12px; }
.auth-label { font-size: 0.9rem; color: var(--muted); }
.auth-form input, .capture-form textarea {
  width: 100%;
  border: 1px solid var(--line);
  border-radius: 8px;
  background: var(--panel);
  color: var(--ink);
  padding: 14px;
  font: inherit;
}
.panel { display: none; padding: 8px 18px 112px; }
.panel--active { display: block; }
.capture-form, .feed-item, .library-section {
  display: grid;
  gap: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  padding: 16px;
}
.capture-actions, .feed-actions { display: flex; gap: 10px; flex-wrap: wrap; }
.message { border-left: 2px solid var(--line); padding-left: 10px; margin: 10px 0 0; }
.message--assistant { border-left-color: var(--accent); }
.feed-item + .feed-item, .library-section + .library-section { margin-top: 12px; }
.feed-meta { color: var(--muted); font-size: 0.9rem; }
.tabbar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  padding: 12px 14px calc(12px + env(safe-area-inset-bottom));
  background: rgba(244, 241, 232, 0.96);
  border-top: 1px solid var(--line);
}
.tabbar-button--active {
  background: var(--accent-soft);
  border-color: var(--accent);
}
```

Create [product/mobile_surface_v1/manifest.webmanifest](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/manifest.webmanifest):

```json
{
  "name": "Inner World Mobile",
  "short_name": "IW Mobile",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#f4f1e8",
  "theme_color": "#f4f1e8",
  "description": "Private mobile surface for capture, feed, and library.",
  "icons": []
}
```

Create [product/mobile_surface_v1/service-worker.js](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/service-worker.js):

```javascript
const CACHE_NAME = "mobile-surface-v1";
const CORE_ASSETS = [
  "./",
  "./index.html",
  "./app.js",
  "./styles.css",
  "./manifest.webmanifest",
  "./runtime-config.js",
];

self.addEventListener("install", (event) => {
  event.waitUntil(caches.open(CACHE_NAME).then((cache) => cache.addAll(CORE_ASSETS)));
});

self.addEventListener("fetch", (event) => {
  if (event.request.method !== "GET") return;
  event.respondWith(
    caches.match(event.request).then((cached) => cached || fetch(event.request))
  );
});
```

Create [product/mobile_surface_v1/runtime-config.js](/Users/talhauddin/software/inner_space/product/mobile_surface_v1/runtime-config.js):

```javascript
window.INNER_WORLD_MOBILE_CONFIG = Object.assign({}, window.INNER_WORLD_MOBILE_CONFIG || {}, {
  apiBaseUrl: "/api/mobile"
});
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_mobile_surface_serves_pwa_assets -q
```

Expected:
- `1 passed`

- [ ] **Step 5: Commit**

```bash
git add product/mobile_surface_v1/index.html product/mobile_surface_v1/app.js product/mobile_surface_v1/styles.css product/mobile_surface_v1/manifest.webmanifest product/mobile_surface_v1/service-worker.js product/mobile_surface_v1/runtime-config.js tests/test_conversation_os.py
git commit -m "feat: add mobile surface pwa frontend"
```

### Task 5: Local Runner, Deployment Tooling, And Docs

**Files:**
- Create: `tools/run_mobile_surface.py`
- Create: `tools/deploy_mobile_surface_to_openclaw.py`
- Create: `ops/systemd/inner-world-mobile.service.sample`
- Modify: `docs/guides/deployment-guide.md`

- [ ] **Step 1: Write the failing smoke checks**

Add this test:

```python
    def test_mobile_surface_runner_module_imports(self) -> None:
        module = importlib.import_module("conversation_os.mobile_surface")
        self.assertTrue(hasattr(module, "serve_mobile_surface"))
```

Add this script smoke check near the existing bundle tests:

```python
    def test_run_mobile_surface_script_exists(self) -> None:
        self.assertTrue((REPO_ROOT / "tools" / "run_mobile_surface.py").exists())
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_run_mobile_surface_script_exists -q
```

Expected:
- `FAIL`
- missing script file

- [ ] **Step 3: Add the runner, deploy script, and docs**

Create [tools/run_mobile_surface.py](/Users/talhauddin/software/inner_space/tools/run_mobile_surface.py):

```python
#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from conversation_os.mobile_surface import serve_mobile_surface  # noqa: E402


if __name__ == "__main__":
    serve_mobile_surface(ROOT, host="127.0.0.1", port=8423, domain_overlays=["research", "art", "entrepreneurship"])
```

Create [ops/systemd/inner-world-mobile.service.sample](/Users/talhauddin/software/inner_space/ops/systemd/inner-world-mobile.service.sample):

```ini
[Unit]
Description=Inner World Mobile surface
After=network-online.target

[Service]
Type=simple
WorkingDirectory=/home/talha/.openclaw/workspace/containers/inner-world
Environment=PYTHONPATH=/home/talha/.openclaw/workspace/containers/inner-world/src
Environment=INNER_WORLD_MOBILE_PASSWORD=change-me
ExecStart=/usr/bin/env python3 /home/talha/.openclaw/workspace/containers/inner-world/tools/run_mobile_surface.py
Restart=always
RestartSec=2

[Install]
WantedBy=default.target
```

Create [tools/deploy_mobile_surface_to_openclaw.py](/Users/talhauddin/software/inner_space/tools/deploy_mobile_surface_to_openclaw.py):

```python
#!/usr/bin/env python3
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_REMOTE = "talha@192.168.0.102"
DEFAULT_REPO_PATH = "/home/talha/.openclaw/workspace/containers/inner-world"
DEFAULT_HOSTNAME = "mobile.talhaslaboratory.xyz"
DEFAULT_PORT = 8423
SYNC_ITEMS = ["src", "tools", "product/mobile_surface_v1", "ops/systemd/inner-world-mobile.service.sample", "docs/guides/deployment-guide.md", "context", "AGENTS.md", "pyproject.toml"]


def run(cmd: list[str], *, input_text: str | None = None) -> None:
    subprocess.run(cmd, input=input_text, text=input_text is not None, check=True)


def sync_repo(remote: str, remote_repo_path: str) -> None:
    for item in SYNC_ITEMS:
        source = ROOT / item
        target = f"{remote}:{remote_repo_path}/{item}"
        if source.is_dir():
            run(["rsync", "-az", "--delete", f"{source}/", f"{target}/"])
        else:
            run(["ssh", remote, f"mkdir -p {Path(remote_repo_path, item).parent.as_posix()}"])
            run(["rsync", "-az", str(source), target])


def install_service(remote: str, remote_repo_path: str) -> None:
    unit = (ROOT / "ops" / "systemd" / "inner-world-mobile.service.sample").read_text(encoding="utf-8")
    unit = unit.replace("/home/talha/.openclaw/workspace/containers/inner-world", remote_repo_path)
    run(["ssh", remote, "mkdir -p ~/.config/systemd/user && cat > ~/.config/systemd/user/inner-world-mobile.service"], input_text=unit)
    run(["ssh", remote, "systemctl --user daemon-reload && systemctl --user enable --now inner-world-mobile.service"])


def patch_cloudflared(remote: str, hostname: str, port: int) -> None:
    script = f"""
from pathlib import Path
path = Path('/home/talha/.cloudflared/config.yml')
text = path.read_text(encoding='utf-8')
block = "  - hostname: {hostname}\\n    service: http://127.0.0.1:{port}\\n"
if block not in text:
    marker = "  - service: http_status:404\\n"
    text = text.replace(marker, block + marker, 1)
    path.write_text(text, encoding='utf-8')
"""
    run(["ssh", remote, "python3 -"], input_text=script)
    run(["ssh", remote, "systemctl --user restart cloudflared"])


if __name__ == "__main__":
    remote = DEFAULT_REMOTE
    sync_repo(remote, DEFAULT_REPO_PATH)
    install_service(remote, DEFAULT_REPO_PATH)
    patch_cloudflared(remote, DEFAULT_HOSTNAME, DEFAULT_PORT)
    run(["ssh", remote, "curl -fsS http://127.0.0.1:8423/manifest.webmanifest >/dev/null"])
```

Update [docs/guides/deployment-guide.md](/Users/talhauddin/software/inner_space/docs/guides/deployment-guide.md):

~~~md
| Mobile surface deploy | `python3 tools/deploy_mobile_surface_to_openclaw.py` | You changed the separate private mobile capture/feed/library surface and need to deploy it to `mobile.talhaslaboratory.xyz`. |
| Mobile surface local runtime | `python3 tools/run_mobile_surface.py` | You want to run the dedicated mobile surface locally on port `8423`. |
~~~

Add a new section:

~~~md
## Mobile Surface Deploy

Use the mobile-surface deploy path when you need to publish the separate private PWA to `mobile.talhaslaboratory.xyz`.

```bash
python3 tools/deploy_mobile_surface_to_openclaw.py
```

Verification:

```bash
ssh talha@192.168.0.102 'systemctl --user is-active inner-world-mobile.service'
ssh talha@192.168.0.102 'curl -fsS http://127.0.0.1:8423/manifest.webmanifest'
curl -fsS https://mobile.talhaslaboratory.xyz/manifest.webmanifest
```
~~~

- [ ] **Step 4: Run smoke checks**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py::ConversationOSTestCase::test_run_mobile_surface_script_exists -q
python3 -m py_compile src/conversation_os/mobile_surface.py src/conversation_os/mobile_surface_api.py tools/run_mobile_surface.py tools/deploy_mobile_surface_to_openclaw.py
```

Expected:
- test `PASS`
- `py_compile` exits `0`

- [ ] **Step 5: Commit**

```bash
git add tools/run_mobile_surface.py tools/deploy_mobile_surface_to_openclaw.py ops/systemd/inner-world-mobile.service.sample docs/guides/deployment-guide.md tests/test_conversation_os.py
git commit -m "feat: add mobile surface deploy tooling"
```

### Task 6: Atlas Refresh, Validation, And Full Verification

**Files:**
- Modify: generated repo-overview outputs under `context/substrate/`

- [ ] **Step 1: Run the focused surface tests**

Run:

```bash
python3 -m pytest tests/test_conversation_os.py -k "mobile_surface or openclaw_bundle_generation or miniapp_serves_feed_ui_enhancement_assets" -q
```

Expected:
- all selected tests `PASS`

- [ ] **Step 2: Refresh the codebase overview**

Run:

```bash
python3 tools/conversation_os.py repo-overview refresh
```

Expected:
- exit `0`
- generated artifacts under `context/substrate/registry/` updated

- [ ] **Step 3: Validate the overview**

Run:

```bash
python3 tools/conversation_os.py repo-overview validate
```

Expected:
- exit `0`
- no stale atlas/manifests

- [ ] **Step 4: Review the working tree**

Run:

```bash
git status --short
git diff --stat
```

Expected:
- only intended mobile-surface files and generated overview outputs changed

- [ ] **Step 5: Commit**

```bash
git add context/substrate/CODEBASE_OVERVIEW.md context/substrate/CODEBASE_ATLAS.md context/substrate/codebase_map.json context/substrate/registry context/substrate/modules/surface.mobile.mobile_surface.json context/substrate/modules/surface.mobile.mobile_surface_api.json
git commit -m "chore: refresh atlas for mobile surface layer"
```

## Self-Review

Spec coverage:
- separate mobile surface owner: covered in Task 1
- app-level private access: covered in Task 1
- append-first capture: covered in Task 2
- optional capture conversation: covered in Task 2
- internal-only personalized feed: covered in Task 3
- grouped library: covered in Task 3
- mobile-first PWA shell: covered in Task 4
- separate subdomain deployment: covered in Task 5
- atlas refresh and manifest discipline: covered in Task 6

Marker scan:
- no unresolved marker strings remain in the plan body
- deployment hostname is explicit
- runtime port is explicit

Type consistency:
- auth cookie: `inner_world_mobile_session`
- API namespace: `/api/mobile/*`
- subdomain: `mobile.talhaslaboratory.xyz`
- runtime port: `8423`
