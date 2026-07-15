from __future__ import annotations

import base64
import binascii
import hashlib
import hmac
import json
import mimetypes
import os
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from textwrap import dedent
from typing import List
from urllib.parse import parse_qs, urlparse

from .chat_backends import (
    apply_openclaw_model_control,
    get_openclaw_model_control_state,
    rollback_openclaw_model_control,
    stage_openclaw_agent_model,
)
from .mobile_capture_compose import compose_mobile_capture_insertion
from .product_inner_world import (
    append_mobile_capture,
    build_mobile_feed,
    build_mobile_library,
    build_thought_archive,
    build_thought_feed,
    chat_with_thought,
    create_link_alias_resolution,
    delete_thread,
    derive_graph,
    ensure_mobile_capture_session,
    generate_daily_batch,
    get_chunk_pond_detail,
    get_dimension_model_role_status,
    get_link_governance_state,
    get_linking_overview,
    get_retrieval_bundle,
    get_runtime_overview,
    reply_in_mobile_session,
    save_mobile_feed_item,
    search_library_dimensions,
    get_source_item_detail,
    get_thread_detail,
    get_thought_detail,
    record_feedback,
    save_thread,
    update_dimension_model_role_binding,
    update_chunk_pond_detail,
    update_link_governance,
)
from .release_management import build_release_manifest, build_rollback_plan
from .builder_behavior import compose_builder_packet_input
from .self_improvement_agent import draft_self_improvement_packet
from .self_improvement import build_self_improvement_chat_response, interpret_self_improvement_turn
from .worldbuilding_studio import (
    answer_population_question as worldstudio_answer_population_question,
    bind_motion_object as worldstudio_bind_motion_object,
    compile_scene as worldstudio_compile_scene,
    compile_scene_from_canon as worldstudio_compile_scene_from_canon,
    compile_motion_plan as worldstudio_compile_motion_plan,
    compile_visual_context as worldstudio_compile_visual_context,
    create_character_profile as worldstudio_create_character_profile,
    create_motion_object as worldstudio_create_motion_object,
    create_world as worldstudio_create_world,
    execute_higgsfield_packet as worldstudio_execute_higgsfield_packet,
    generate_canon as worldstudio_generate_canon,
    get_execution_run as worldstudio_get_execution_run,
    get_population_session as worldstudio_get_population_session,
    get_world_studio_guide as worldstudio_get_guide,
    ingest_evidence as worldstudio_ingest_evidence,
    ingest_visual_reference as worldstudio_ingest_visual_reference,
    inspect_character_system as worldstudio_inspect_character_system,
    inspect_motion_system as worldstudio_inspect_motion_system,
    inspect_visual_world as worldstudio_inspect_visual_world,
    list_execution_runs as worldstudio_list_execution_runs,
    project_world_graph as worldstudio_project_graph,
    get_world as worldstudio_get_world,
    inspect_world_evidence as worldstudio_inspect_world_evidence,
    inspect_world_knowledge as worldstudio_inspect_world_knowledge,
    list_worlds as worldstudio_list_worlds,
    next_worldbuilding_question as worldstudio_next_question,
    run_demo as worldstudio_run_demo,
    start_population_session as worldstudio_start_population_session,
    update_character_feature_object as worldstudio_update_character_feature_object,
    update_character_profile_section as worldstudio_update_character_profile_section,
)
from .workspace_os_api import (
    workspace_os_dashboard_payload,
    workspace_os_live_catalog,
    workspace_os_live_context,
    workspace_os_live_gate,
    workspace_os_live_health,
)


MODULE_ID = "surface.inner_world.miniapp"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "build_miniapp_ui_enhancement_assets",
    "inject_miniapp_ui_enhancement",
    "make_miniapp_handler",
    "serve_miniapp",
)
__all__ = list(PUBLIC_API)

_MOBILE_SESSION_COOKIE_NAME = "inner_world_mobile_session"
_MOBILE_SESSION_PAYLOAD = "mobile-session"


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    payload = handler.rfile.read(length)
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def _canonical_api_path(path: str, api_prefixes: List[str]) -> str | None:
    for prefix in api_prefixes:
        normalized = prefix.rstrip("/") or "/"
        if path == normalized:
            return "/"
        if path.startswith(f"{normalized}/"):
            suffix = path[len(normalized) :]
            return suffix or "/"
    return None


def _mobile_surface_dir(root: Path) -> Path:
    return root / "product" / "mobile_surface_v1"


def _thought_capture_pwa_dir(root: Path) -> Path:
    return root / "product" / "thought_capture_pwa" / "dist"


def _normalize_host_header(host_header: str | None) -> str:
    if not host_header:
        return ""
    return host_header.split(":", 1)[0].strip().lower()


def _configured_mobile_hostname() -> str:
    return _normalize_host_header(os.environ.get("INNER_WORLD_MOBILE_HOSTNAME"))


def _configured_capture_hostname() -> str:
    return _normalize_host_header(os.environ.get("INNER_WORLD_CAPTURE_HOSTNAME"))


def _configured_capture_username() -> str:
    return (os.environ.get("INNER_WORLD_CAPTURE_USERNAME") or "capture").strip() or "capture"


def _resolve_static_asset(base_dir: Path, relative: str) -> Path | None:
    candidate = (base_dir / relative).resolve()
    try:
        candidate.relative_to(base_dir.resolve())
    except ValueError:
        return None
    if candidate.exists() and candidate.is_file():
        return candidate
    return None


def _self_improvement_console_html(
    *,
    api_base: str = "/api",
    capture_href: str = "",
    meta_href: str = "",
) -> str:
    switch_html = ""
    if capture_href or meta_href:
        switch_html = f"""
                <nav class="capture-switch" aria-label="Surface mode">
                  <a class="capture-switch__chip" href="{capture_href or '/capture'}">capture</a>
                  <a class="capture-switch__chip capture-switch__chip--active" href="{meta_href or '/meta'}">meta</a>
                </nav>
        """
    html = dedent(
        """
        <!doctype html>
        <html lang="en">
          <head>
            <meta charset="utf-8" />
            <meta name="viewport" content="width=device-width, initial-scale=1" />
            <title>Self Improvement Console</title>
            <style>
              :root {
                color-scheme: light;
                --bg: #f3f1ea;
                --panel: #fffdf8;
                --ink: #1f1c18;
                --muted: #6b6257;
                --line: #d7cdbf;
                --accent: #1d6c5a;
                --accent-strong: #14493d;
                --accent-soft: #dcefe9;
                --note: #7b5f18;
                --note-soft: #f6ebc9;
                --risk: #8c3d0f;
                --risk-soft: #f6e2d5;
                --warn: #9f5a11;
              }
              * { box-sizing: border-box; }
              body {
                margin: 0;
                font-family: Georgia, "Iowan Old Style", "Times New Roman", serif;
                background:
                  linear-gradient(180deg, rgba(255,255,255,0.45), rgba(243,241,234,0.92)),
                  linear-gradient(120deg, #efe8db, #f7f4ee 52%, #ece6da);
                color: var(--ink);
              }
              main {
                max-width: 1040px;
                margin: 0 auto;
                padding: 32px 20px 48px;
              }
              header {
                display: grid;
                gap: 10px;
                margin-bottom: 24px;
              }
              .capture-switch {
                display: flex;
                gap: 10px;
                margin-bottom: 2px;
              }
              .capture-switch__chip {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                min-height: 44px;
                padding: 0 16px;
                border-radius: 999px;
                border: 1px solid var(--line);
                background: rgba(255, 255, 255, 0.7);
                color: var(--muted);
                text-decoration: none;
                font-size: 13px;
                letter-spacing: 0.08em;
                text-transform: lowercase;
              }
              .capture-switch__chip--active {
                background: var(--accent-soft);
                color: var(--accent-strong);
                border-color: rgba(29, 108, 90, 0.25);
              }
              h1 {
                margin: 0;
                font-size: 38px;
                line-height: 1;
                font-weight: 600;
              }
              p {
                margin: 0;
                color: var(--muted);
                font-size: 16px;
                line-height: 1.5;
              }
              .grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
                gap: 18px;
              }
              section {
                background: rgba(255, 253, 248, 0.95);
                border: 1px solid var(--line);
                border-radius: 8px;
                padding: 18px;
                min-height: 280px;
                display: grid;
                gap: 12px;
                align-content: start;
              }
              h2 {
                margin: 0;
                font-size: 18px;
              }
              label {
                display: grid;
                gap: 6px;
                font-size: 13px;
                color: var(--muted);
              }
              .hero {
                display: grid;
                gap: 14px;
              }
              .state-strip {
                display: grid;
                gap: 10px;
                padding: 14px 16px;
                border: 1px solid var(--line);
                border-radius: 8px;
                background: linear-gradient(135deg, rgba(255,255,255,0.7), rgba(240,235,224,0.9));
              }
              .chip-row, .stack-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
              }
              .chip {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 6px 10px;
                border-radius: 999px;
                border: 1px solid var(--line);
                background: white;
                color: var(--muted);
                font-size: 12px;
                letter-spacing: 0.03em;
                text-transform: uppercase;
              }
              .chip.mode-meta, .chip.state-operate {
                background: var(--accent-soft);
                color: var(--accent-strong);
                border-color: rgba(29, 108, 90, 0.25);
              }
              .chip.mode-note, .chip.state-discuss {
                background: var(--note-soft);
                color: var(--note);
                border-color: rgba(123, 95, 24, 0.2);
              }
              .chip.risk-high, .chip.risk-critical {
                background: var(--risk-soft);
                color: var(--risk);
                border-color: rgba(140, 61, 15, 0.18);
              }
              .segment {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
              }
              .segment button {
                background: rgba(255, 255, 255, 0.7);
                color: var(--ink);
                border: 1px solid var(--line);
              }
              .segment button.active {
                background: var(--accent);
                border-color: var(--accent);
                color: white;
              }
              .segment button.note-active {
                background: #8c6a18;
                border-color: #8c6a18;
              }
              .subtle {
                color: var(--muted);
                font-size: 12px;
                line-height: 1.5;
              }
              .control-row {
                display: flex;
                flex-wrap: wrap;
                gap: 10px;
                align-items: center;
              }
              textarea, input {
                width: 100%;
                border: 1px solid var(--line);
                border-radius: 6px;
                background: #fffdf9;
                color: var(--ink);
                padding: 10px 12px;
                font: inherit;
              }
              textarea {
                min-height: 140px;
                resize: vertical;
              }
              button {
                border: 0;
                border-radius: 6px;
                padding: 11px 14px;
                background: var(--accent);
                color: white;
                font: inherit;
                cursor: pointer;
              }
              button:hover { background: var(--accent-strong); }
              button.secondary {
                background: transparent;
                color: var(--ink);
                border: 1px solid var(--line);
              }
              button.secondary:hover {
                background: rgba(255,255,255,0.75);
              }
              button:disabled {
                cursor: not-allowed;
                opacity: 0.55;
              }
              pre {
                margin: 0;
                white-space: pre-wrap;
                word-break: break-word;
                background: #f8f4ec;
                border: 1px solid var(--line);
                border-radius: 6px;
                padding: 12px;
                min-height: 160px;
                max-height: 420px;
                overflow: auto;
                font-size: 12px;
              }
              .status {
                color: var(--warn);
                font-size: 12px;
              }
              .info-panel {
                display: grid;
                gap: 8px;
                padding: 14px 16px;
                border: 1px solid var(--line);
                border-radius: 8px;
                background: rgba(248, 244, 236, 0.9);
              }
              .info-title {
                font-size: 12px;
                letter-spacing: 0.08em;
                text-transform: uppercase;
                color: var(--muted);
              }
            </style>
          </head>
          <body>
            <main>
              <header>
                __SWITCH_HTML__
                <h1>Self Improvement Console</h1>
                <p>Switch between note and meta, discuss an idea without operationalizing it, then move into governed change work when it is ready.</p>
                <p data-compat-endpoint="/api/self-improvement/interpret" hidden></p>
                <p data-compat-endpoint="/api/self-improvement/chat" hidden></p>
                <p data-compat-endpoint="/api/self-improvement/packet" hidden></p>
                <p data-compat-endpoint="/api/self-improvement/release/candidate" hidden></p>
              </header>
              <div class="grid">
                <section>
                  <div class="hero">
                    <h2>Mode Chat</h2>
                    <div class="state-strip">
                      <div class="chip-row">
                        <span id="mode-chip" class="chip mode-meta">Meta</span>
                        <span id="state-chip" class="chip state-discuss">Discuss</span>
                        <span id="risk-chip" class="chip">Risk: provisional</span>
                      </div>
                      <div id="state-summary">Meta discuss keeps the idea provisional. Nothing operationalizes until you explicitly move into operate.</div>
                      <div class="subtle" id="state-guidance">Use note for raw capture, meta discuss to shape a change, and meta operate when you want governed packet creation.</div>
                    </div>
                    <div>
                      <div class="info-title">Surface Mode</div>
                      <div class="segment">
                        <button type="button" id="mode-note">Note</button>
                        <button type="button" id="mode-meta">Meta</button>
                      </div>
                    </div>
                    <div>
                      <div class="info-title">Meta State</div>
                      <div class="segment">
                        <button type="button" id="state-discuss">Discuss</button>
                        <button type="button" id="state-operate">Operate</button>
                      </div>
                    </div>
                  </div>
                  <label>
                    Message
                    <textarea id="packet-text">Should we change how the bridge handles sidecar context?</textarea>
                  </label>
                  <div class="subtle">`Ctrl/Cmd + Enter` sends. `Operate` should be used only when you want a governed change packet drafted immediately.</div>
                  <label>
                    Session Id
                    <input id="packet-session" value="web-self-improve-session" />
                  </label>
                  <label>
                    Turn Id
                    <input id="packet-turn" value="web-self-improve-turn" />
                  </label>
                  <div class="control-row">
                    <button id="interpret-submit">Send Message</button>
                    <button type="button" class="secondary" id="promote-operate">Promote to Operate</button>
                    <button type="button" class="secondary" id="reset-chat">Reset Draft</button>
                  </div>
                  <div id="chat-status" class="status"></div>
                  <pre id="chat-output"></pre>
                  <div class="info-panel">
                    <div class="info-title">Packet Preview</div>
                    <div id="packet-preview-status" class="subtle">No packet drafted. Stay in discuss until the change is concrete.</div>
                    <pre id="packet-preview-output"></pre>
                  </div>
                </section>
                <section>
                  <h2>Improvement Packet</h2>
                  <p class="subtle">Manual packet creation stays available, but the preferred path is to reach it through `meta -> operate` so the packet carries explicit conversational intent.</p>
                  <button id="packet-submit">Create Packet</button>
                  <div id="packet-status" class="status"></div>
                  <pre id="packet-output"></pre>
                </section>
                <section>
                  <h2>Release Candidate</h2>
                  <label>
                    Release Id
                    <input id="release-id" value="self-improve-web-release" />
                  </label>
                  <button id="release-submit">Build Manifest</button>
                  <div id="release-status" class="status"></div>
                  <pre id="release-output"></pre>
                </section>
                <section>
                  <h2>Rollback Plan</h2>
                  <label>
                    Current Release
                    <input id="rollback-current" value="inner-world-current" />
                  </label>
                  <label>
                    Previous Release
                    <input id="rollback-previous" value="inner-world-previous" />
                  </label>
                  <button id="rollback-submit">Build Rollback Plan</button>
                  <div id="rollback-status" class="status"></div>
                  <pre id="rollback-output"></pre>
                </section>
              </div>
            </main>
            <script>
              function inferSelfImprovementApiBase() {
                const path = window.location.pathname || "";
                const marker = "/self-improvement";
                if (path.endsWith(marker)) {
                  const base = path.slice(0, -marker.length);
                  return base || "/api";
                }
                return "/api";
              }

              const selfImprovementApiBase = __API_BASE_JSON__;

              function apiPath(suffix) {
                return `${selfImprovementApiBase}${suffix}`;
              }

              async function postJson(path, payload) {
                const response = await fetch(path, {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify(payload),
                });
                const data = await response.json();
                if (!response.ok) {
                  throw new Error(data.error || "request_failed");
                }
                return data;
              }

              function wireButton(buttonId, statusId, outputId, buildPayload) {
                const button = document.getElementById(buttonId);
                const status = document.getElementById(statusId);
                const output = document.getElementById(outputId);
                button.addEventListener("click", async () => {
                  status.textContent = "Working...";
                  output.textContent = "";
                  try {
                    const { path, payload } = buildPayload();
                    const result = await postJson(path, payload);
                    output.textContent = JSON.stringify(result, null, 2);
                    status.textContent = "";
                  } catch (error) {
                    status.textContent = String(error.message || error);
                  }
                });
              }

              const appState = {
                surfaceMode: "meta",
                metaState: "discuss",
                transcript: [],
                pending: false,
              };

              function humanizeRisk(interpretation) {
                if (!interpretation) {
                  return "provisional";
                }
                if (interpretation.surface_mode !== "meta") {
                  return "none";
                }
                return interpretation.risk || "provisional";
              }

              function toggleActive(buttonId, isActive, extraClass) {
                const button = document.getElementById(buttonId);
                button.classList.toggle("active", isActive);
                if (extraClass) {
                  button.classList.toggle(extraClass, isActive);
                }
              }

              function setBusy(isBusy) {
                appState.pending = isBusy;
                [
                  "interpret-submit",
                  "promote-operate",
                  "reset-chat",
                  "packet-submit",
                  "release-submit",
                  "rollback-submit",
                  "mode-note",
                  "mode-meta",
                  "state-discuss",
                  "state-operate",
                ].forEach((id) => {
                  document.getElementById(id).disabled = isBusy;
                });
              }

              function updateStateChrome(interpretation) {
                const modeChip = document.getElementById("mode-chip");
                const stateChip = document.getElementById("state-chip");
                const riskChip = document.getElementById("risk-chip");
                const summary = document.getElementById("state-summary");
                const guidance = document.getElementById("state-guidance");
                const packetButton = document.getElementById("packet-submit");
                const promoteButton = document.getElementById("promote-operate");
                const resolvedMode = interpretation ? interpretation.surface_mode : appState.surfaceMode;
                const resolvedState = interpretation ? interpretation.meta_state : appState.metaState;
                const risk = humanizeRisk(interpretation);

                toggleActive("mode-note", resolvedMode === "note", "note-active");
                toggleActive("mode-meta", resolvedMode === "meta");
                toggleActive("state-discuss", resolvedState === "discuss");
                toggleActive("state-operate", resolvedMode === "meta" && resolvedState === "operate");

                modeChip.textContent = resolvedMode === "note" ? "Note" : "Meta";
                modeChip.className = `chip mode-${resolvedMode}`;
                stateChip.textContent = resolvedState === "operate" ? "Operate" : "Discuss";
                stateChip.className = `chip state-${resolvedState}`;
                riskChip.textContent = `Risk: ${risk}`;
                riskChip.className = `chip risk-${risk}`;

                if (resolvedMode === "note") {
                  summary.textContent = "Note mode captures thought without operational behavior. This is safe for raw reflection and context capture.";
                  guidance.textContent = "Switch into meta only when you want to reason about the product/system itself.";
                } else if (resolvedState === "operate") {
                  summary.textContent = "Meta operate is armed. Sending the next message will draft a governed change packet and surface required tests and release gates.";
                  guidance.textContent = "Use operate only when the request is concrete enough to become tracked implementation work.";
                } else {
                  summary.textContent = "Meta discuss keeps the idea provisional. You can refine intent, scope, and risks before turning it into tracked change.";
                  guidance.textContent = "Promote to operate only after the implementation direction is explicit enough to test and release safely.";
                }

                packetButton.disabled = appState.pending || !(resolvedMode === "meta" && resolvedState === "operate");
                promoteButton.disabled = appState.pending || !(resolvedMode === "meta" && resolvedState === "discuss");
              }

              function renderTranscript() {
                const output = document.getElementById("chat-output");
                output.textContent = appState.transcript.map((row) => {
                  return `[${row.actor}] ${row.text}`;
                }).join("\\n\\n");
              }

              function renderPacketPreview(packet, interpretation) {
                const status = document.getElementById("packet-preview-status");
                const output = document.getElementById("packet-preview-output");
                if (!packet) {
                  status.textContent = interpretation.next_action;
                  output.textContent = JSON.stringify(
                    {
                      mode: interpretation.surface_mode,
                      state: interpretation.meta_state,
                      domain: interpretation.domain,
                      risk: interpretation.risk,
                    },
                    null,
                    2,
                  );
                  return;
                }
                status.textContent = `Packet drafted for ${packet.classification.domain}. Required tests: ${packet.gates.required_tests.join(", ")}.`;
                output.textContent = JSON.stringify(packet, null, 2);
                document.getElementById("packet-output").textContent = JSON.stringify(packet, null, 2);
              }

              document.getElementById("mode-note").addEventListener("click", () => {
                appState.surfaceMode = "note";
                appState.metaState = "discuss";
                updateStateChrome();
              });
              document.getElementById("mode-meta").addEventListener("click", () => {
                appState.surfaceMode = "meta";
                if (appState.metaState !== "operate") {
                  appState.metaState = "discuss";
                }
                updateStateChrome();
              });
              document.getElementById("state-discuss").addEventListener("click", () => {
                appState.metaState = "discuss";
                updateStateChrome();
              });
              document.getElementById("state-operate").addEventListener("click", () => {
                appState.surfaceMode = "meta";
                appState.metaState = "operate";
                updateStateChrome();
              });
              document.getElementById("promote-operate").addEventListener("click", () => {
                appState.surfaceMode = "meta";
                appState.metaState = "operate";
                updateStateChrome();
              });
              document.getElementById("reset-chat").addEventListener("click", () => {
                appState.transcript = [];
                document.getElementById("chat-status").textContent = "";
                document.getElementById("packet-preview-status").textContent = "No packet drafted. Stay in discuss until the change is concrete.";
                document.getElementById("packet-preview-output").textContent = "";
                renderTranscript();
                updateStateChrome();
              });

              async function submitModeChat() {
                const status = document.getElementById("chat-status");
                try {
                  setBusy(true);
                  const message = document.getElementById("packet-text").value;
                  appState.transcript.push({ actor: "user", text: message });
                  const result = await postJson(apiPath("/self-improvement/chat"), {
                    text: message,
                    surface_mode: appState.surfaceMode,
                    meta_state: appState.metaState,
                    session_id: document.getElementById("packet-session").value,
                    turn_id: document.getElementById("packet-turn").value,
                  });
                  const interpretation = result.interpretation;
                  appState.surfaceMode = interpretation.surface_mode;
                  appState.metaState = interpretation.meta_state;
                  appState.transcript.push({
                    actor: "assistant",
                    text: `${result.assistant_text} Domain: ${interpretation.domain}. Next: ${interpretation.next_action}`,
                  });
                  if (result.packet) {
                    appState.transcript.push({
                      actor: "packet",
                      text: JSON.stringify(result.packet, null, 2),
                    });
                  }
                  renderTranscript();
                  renderPacketPreview(result.packet, interpretation);
                  updateStateChrome(interpretation);
                  status.textContent = "";
                } catch (error) {
                  status.textContent = String(error.message || error);
                } finally {
                  setBusy(false);
                  updateStateChrome();
                }
              }

              document.getElementById("interpret-submit").addEventListener("click", submitModeChat);
              document.getElementById("packet-text").addEventListener("keydown", (event) => {
                if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
                  event.preventDefault();
                  if (!appState.pending) {
                    submitModeChat();
                  }
                }
              });

              wireButton("packet-submit", "packet-status", "packet-output", () => ({
                path: apiPath("/self-improvement/packet"),
                payload: {
                  text: document.getElementById("packet-text").value,
                  session_id: document.getElementById("packet-session").value,
                  turn_id: document.getElementById("packet-turn").value,
                  surface_mode: appState.surfaceMode,
                  meta_state: appState.metaState,
                },
              }));

              wireButton("release-submit", "release-status", "release-output", () => ({
                path: apiPath("/self-improvement/release/candidate"),
                payload: { release_id: document.getElementById("release-id").value },
              }));

              wireButton("rollback-submit", "rollback-status", "rollback-output", () => ({
                path: apiPath("/self-improvement/release/rollback-plan"),
                payload: {
                  current_release_id: document.getElementById("rollback-current").value,
                  previous_release_id: document.getElementById("rollback-previous").value,
                },
              }));
              updateStateChrome();
            </script>
          </body>
        </html>
        """
    ).strip() + "\n"
    return (
        html.replace("__SWITCH_HTML__", switch_html)
        .replace("__API_BASE_JSON__", json.dumps(api_base.rstrip("/") or "/api"))
    )


def _sign_mobile_session(password: str) -> str:
    signature = hmac.new(
        password.encode("utf-8"),
        _MOBILE_SESSION_PAYLOAD.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return f"{_MOBILE_SESSION_PAYLOAD}.{signature}"


def _verify_mobile_session(cookie_value: str | None, password: str | None) -> bool:
    if not cookie_value or not password or "." not in cookie_value:
        return False
    payload, signature = cookie_value.rsplit(".", 1)
    if payload != _MOBILE_SESSION_PAYLOAD:
        return False
    expected_signature = hmac.new(
        password.encode("utf-8"),
        payload.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(signature, expected_signature)


_FEED_UI_ENHANCEMENT_CSS = "feed-ui-enhancement.css"
_FEED_UI_ENHANCEMENT_JS = "feed-ui-enhancement.js"
_CONVERSATION_ATLAS_ROUTE = "/conversation-atlas.html"
_CONVERSATION_ATLAS_MOBILE_ROUTE = "/conversation-atlas-mobile.html"


def _conversation_atlas_specimen() -> dict:
    return {
        "title": "Conversation Atlas / This Thread",
        "shared_threads": [
            "main-thread",
            "control-topology",
            "context-workshop",
            "assembly-layer",
            "display-surface",
            "mobilegrid-runtime",
            "holodeck-translation",
        ],
        "translation_layer": {
            "shared": [
                "Same branch identity and thread lineage across desktop and mobile",
                "Same user location primitives: thread, status, coupling, abstraction band",
                "Same knowledge buckets feeding both surfaces",
                "Same promotion and open-question markers",
            ],
            "desktop_unique": [
                "Wide-map orientation across time and neighboring branches",
                "Diagrammatic comparison between distant clusters",
                "Visible topology for scanning drift and promotion",
            ],
            "mobile_unique": [
                "Thumb-first focus on the active path and immediate neighbors",
                "One-handed progression through buckets and branch cards",
                "Fast return to where-am-I without decoding the whole map",
            ],
        },
        "bands": [
            {
                "id": "entry",
                "range": "01 to 07",
                "title": "Opening thesis from this thread",
                "summary": "This conversation begins by defining the product as a layer between a person and intelligence, with self-communication and personalization at the center.",
                "nodes": [
                    {
                        "id": "u.01",
                        "role": "user",
                        "kind": "seed",
                        "title": "We need a layer between the user and intelligence.",
                        "summary": "The opening input frames intelligence as upstream material and asks for an efficient layer between the person and it.",
                        "thread": "main-thread",
                        "status": "main spine",
                        "coupling": "shared with every later branch",
                    },
                    {
                        "id": "a.02",
                        "role": "agent",
                        "kind": "reframe",
                        "title": "This becomes a self-communication surface.",
                        "summary": "The reply reframes the product as a place where a person can meet, reflect, and restructure their own thought.",
                        "thread": "main-thread",
                        "status": "promoted branch",
                        "coupling": "coupled to product and ontology",
                    },
                    {
                        "id": "u.03",
                        "role": "user",
                        "kind": "refinement",
                        "title": "Personalization must become core.",
                        "summary": "The thread insists that in a new era of cognitive tools, personalization cannot be a feature layered on top.",
                        "thread": "main-thread",
                        "status": "promoted branch",
                        "coupling": "shared with assembly and context",
                    },
                    {
                        "id": "u.04",
                        "role": "user",
                        "kind": "open",
                        "title": "What exactly is being refined?",
                        "summary": "The thread opens the question of whether the layer primarily refines thought, attention, feeling, decision-making, or self-model.",
                        "thread": "main-thread",
                        "status": "open question",
                        "coupling": "isolated until resolved",
                    },
                    {
                        "id": "a.05",
                        "role": "agent",
                        "kind": "synthesis",
                        "title": "The job is transformation, not generation.",
                        "summary": "The thread stabilizes around a first principle: the product refines intelligence into the right form for the moment rather than merely generating answers.",
                        "thread": "main-thread",
                        "status": "promoted branch",
                        "coupling": "shared with every major branch",
                    },
                    {
                        "id": "u.06",
                        "role": "user",
                        "kind": "constraint",
                        "title": "Track the flow without flattening it.",
                        "summary": "The user asks the assistant to organize itself around the flow of input and preserve the shape of the thread as it unfolds.",
                        "thread": "main-thread",
                        "status": "operating rule",
                        "coupling": "shared with control topology",
                    },
                ],
            },
            {
                "id": "control",
                "range": "08 to 14",
                "title": "Meta mode and topology control",
                "summary": "This part of the thread defines how contexts should couple, isolate, route, and reintegrate without polluting the main spine.",
                "nodes": [
                    {
                        "id": "u.08",
                        "role": "user",
                        "kind": "mode",
                        "title": "Introduce a meta mode.",
                        "summary": "The user asks for a meta mode where the assistant can be adjusted in real time while the conversation continues.",
                        "thread": "control-topology",
                        "status": "main spine",
                        "coupling": "shared with orchestration only",
                    },
                    {
                        "id": "u.09",
                        "role": "user",
                        "kind": "topology",
                        "title": "Couple only specific dimensions.",
                        "summary": "The thread specifies that some domains should pass between contexts while others should remain isolated in a latent-topographical sense.",
                        "thread": "control-topology",
                        "status": "promoted branch",
                        "coupling": "shared with sidecars only",
                    },
                    {
                        "id": "a.10",
                        "role": "agent",
                        "kind": "synthesis",
                        "title": "Topology control over context flow.",
                        "summary": "The assistant names the emerging pattern as topology control over context flow, with explicit sidecars and reintegration bridges.",
                        "thread": "control-topology",
                        "status": "promoted branch",
                        "coupling": "coupled to UI state",
                    },
                    {
                        "id": "u.11",
                        "role": "user",
                        "kind": "command",
                        "title": "Hashtags should route and isolate.",
                        "summary": "The user declares hashtags to be control syntax for mode switching or modular context isolation inside the thread.",
                        "thread": "control-topology",
                        "status": "operating rule",
                        "coupling": "shared with parser and routing",
                    },
                    {
                        "id": "u.12",
                        "role": "user",
                        "kind": "perturbation",
                        "title": "Track outside influences too.",
                        "summary": "The thread extends the model to include outside influences as forces acting on conceptual topology.",
                        "thread": "control-topology",
                        "status": "promoted branch",
                        "coupling": "shared with measurement layer",
                    },
                    {
                        "id": "a.14",
                        "role": "agent",
                        "kind": "measurement",
                        "title": "Difference needs controlled observables.",
                        "summary": "The response proposes controlled observables for measuring conceptual shifts rather than claiming direct access to raw hidden state.",
                        "thread": "control-topology",
                        "status": "open method",
                        "coupling": "shared with latent navigation",
                    },
                ],
            },
            {
                "id": "context",
                "range": "15 to 21",
                "title": "Context as workshop and navigation system",
                "summary": "This thread turns context into an instrument set and treats the atlas as a navigation surface that helps the user stay oriented in flow.",
                "nodes": [
                    {
                        "id": "u.15",
                        "role": "user",
                        "kind": "turn",
                        "title": "Context should be stored as tooling.",
                        "summary": "The conversation defines context as the instrument set used to bend, filter, compress, and crystallize intelligence.",
                        "thread": "context-workshop",
                        "status": "main spine",
                        "coupling": "shared with personalization",
                    },
                    {
                        "id": "a.16",
                        "role": "agent",
                        "kind": "synthesis",
                        "title": "The product is the workshop, not the archive.",
                        "summary": "The response sharpens the point: the product is a context workshop, not merely a storage vault.",
                        "thread": "context-workshop",
                        "status": "promoted branch",
                        "coupling": "coupled to interface",
                    },
                    {
                        "id": "u.17",
                        "role": "user",
                        "kind": "location",
                        "title": "Help the user know where they are.",
                        "summary": "The thread says the atlas should help the user stay in flow without losing where they are mentally.",
                        "thread": "context-workshop",
                        "status": "promoted branch",
                        "coupling": "shared with display surface",
                    },
                    {
                        "id": "a.18",
                        "role": "agent",
                        "kind": "navigation",
                        "title": "Model current position in the thought space.",
                        "summary": "The response identifies thread, abstraction level, neighborhood, motion direction, and stability as coordinates for locating the user.",
                        "thread": "context-workshop",
                        "status": "working model",
                        "coupling": "shared with control topology",
                    },
                    {
                        "id": "u.19",
                        "role": "user",
                        "kind": "design",
                        "title": "The atlas should be a conversation substrate.",
                        "summary": "The thread explicitly rejects a generic dashboard feeling and pushes toward a thought-support environment.",
                        "thread": "context-workshop",
                        "status": "design principle",
                        "coupling": "shared with display surface",
                    },
                    {
                        "id": "u.21",
                        "role": "user",
                        "kind": "save",
                        "title": "Save before compression.",
                        "summary": "The thread introduces an operating requirement: save and checkpoint the conversation before context compression erases usable continuity.",
                        "thread": "context-workshop",
                        "status": "operating rule",
                        "coupling": "shared with session system",
                    },
                ],
            },
            {
                "id": "assembly",
                "range": "22 to 30",
                "title": "Invisible infrastructure and mobilegrid runtime",
                "summary": "The thread moves from thesis into stack design: raw provider, management layer, missing final assembly, and a stable versus preview mobile runtime.",
                "nodes": [
                    {
                        "id": "u.22",
                        "role": "user",
                        "kind": "stack",
                        "title": "ChatGPT, OpenClaw, and a missing final assembly layer.",
                        "summary": "The thread names ChatGPT as raw provider, OpenClaw as management, and a missing final assembly or personalization layer between them and the user.",
                        "thread": "assembly-layer",
                        "status": "main spine",
                        "coupling": "shared with platform design",
                    },
                    {
                        "id": "a.23",
                        "role": "agent",
                        "kind": "system",
                        "title": "The missing layer is adaptation, not another model.",
                        "summary": "The response argues that this missing layer is adaptation and orchestration, not another model.",
                        "thread": "assembly-layer",
                        "status": "promoted branch",
                        "coupling": "shared with personalization",
                    },
                    {
                        "id": "u.24",
                        "role": "user",
                        "kind": "gap",
                        "title": "Behavior must adjust reliably.",
                        "summary": "The thread asks for a reliable system that can intelligently adjust behavior from rough, non-technical input.",
                        "thread": "assembly-layer",
                        "status": "promoted branch",
                        "coupling": "coupled to personalization",
                    },
                    {
                        "id": "u.25",
                        "role": "user",
                        "kind": "substrate",
                        "title": "Be the invisible infrastructure under many tools.",
                        "summary": "The thread says the product should sit invisibly beneath tools like Codex, Claude, and OpenClaw as communicative infrastructure.",
                        "thread": "assembly-layer",
                        "status": "platform thesis",
                        "coupling": "shared with mobilegrid runtime",
                    },
                    {
                        "id": "u.26",
                        "role": "user",
                        "kind": "material",
                        "title": "Cognitive clay.",
                        "summary": "The thread introduces `cognitive clay` as the metaphor for a user-shaped medium that can hold form and still be reworked.",
                        "thread": "assembly-layer",
                        "status": "promoted metaphor",
                        "coupling": "shared with personal interface",
                    },
                    {
                        "id": "u.27",
                        "role": "user",
                        "kind": "host",
                        "title": "Mobilegrid should be the stable surface.",
                        "summary": "The deployment part of the thread settles on `mobilegrid` as the stable phone-facing surface with a separate preview surface.",
                        "thread": "mobilegrid-runtime",
                        "status": "deployment decision",
                        "coupling": "shared with runtime only",
                    },
                    {
                        "id": "a.28",
                        "role": "agent",
                        "kind": "deploy",
                        "title": "Preview continuously, publish selectively.",
                        "summary": "The response recommends preview continuously and publish selectively, with local iteration and low-cost promotion.",
                        "thread": "mobilegrid-runtime",
                        "status": "recommended pattern",
                        "coupling": "shared with OpenClaw routing",
                    },
                    {
                        "id": "u.30",
                        "role": "user",
                        "kind": "approval",
                        "title": "Phone stays in approval mode.",
                        "summary": "The thread chooses approval mode for the phone rather than full remote control.",
                        "thread": "mobilegrid-runtime",
                        "status": "locked decision",
                        "coupling": "shared with deployment surface",
                    },
                ],
            },
            {
                "id": "display",
                "range": "31 to 40",
                "title": "Tree interface, holodeck translator, and live growth",
                "summary": "The later thread turns toward the atlas UI itself, then toward an MCP translation layer and holodeck-like architect that can turn rough intent into buildable systems.",
                "nodes": [
                    {
                        "id": "u.31",
                        "role": "user",
                        "kind": "display",
                        "title": "Use a growing tree as the display form.",
                        "summary": "The thread uses archival taxonomy and timeline references as the visual language for the desktop atlas.",
                        "thread": "display-surface",
                        "status": "main spine",
                        "coupling": "shared with user interface",
                    },
                    {
                        "id": "a.32",
                        "role": "agent",
                        "kind": "synthesis",
                        "title": "The atlas is an orientation layer.",
                        "summary": "The response defines the tree as an orientation layer rather than a decorative visualization.",
                        "thread": "display-surface",
                        "status": "promoted branch",
                        "coupling": "coupled to main thread",
                    },
                    {
                        "id": "u.33",
                        "role": "user",
                        "kind": "architect",
                        "title": "Use an MCP translation layer as a demiurge.",
                        "summary": "The thread imagines Codex as a demiurge-like architect that translates rough dumps into technically coherent features and systems.",
                        "thread": "holodeck-translation",
                        "status": "new spine branch",
                        "coupling": "shared with holodeck only",
                    },
                    {
                        "id": "a.34",
                        "role": "agent",
                        "kind": "translation",
                        "title": "Interpretive expansion plus contextual binding.",
                        "summary": "The response breaks the translation layer into interpretive expansion, contextual binding, clarification routing, and implementation shaping.",
                        "thread": "holodeck-translation",
                        "status": "working schema",
                        "coupling": "shared with architect layer",
                    },
                    {
                        "id": "u.35",
                        "role": "user",
                        "kind": "holodeck",
                        "title": "The holodeck should grow dormant concepts too.",
                        "summary": "The thread asks for dormant concepts to keep growing when nearby systems evolve, even before implementation.",
                        "thread": "holodeck-translation",
                        "status": "open system requirement",
                        "coupling": "shared with backlog and synthesis",
                    },
                    {
                        "id": "a.36",
                        "role": "agent",
                        "kind": "tracking",
                        "title": "A living incompleteness tracker is needed.",
                        "summary": "The response proposes a living incompleteness tracker instead of a dead backlog.",
                        "thread": "holodeck-translation",
                        "status": "promoted branch",
                        "coupling": "shared with growth engine",
                    },
                    {
                        "id": "u.37",
                        "role": "user",
                        "kind": "artifact",
                        "title": "Desktop atlas should read like a populated document.",
                        "summary": "This current request pushes the desktop atlas to use the conversation itself as the population substrate rather than generic mock content.",
                        "thread": "display-surface",
                        "status": "design request",
                        "coupling": "shared with specimen layer",
                    },
                    {
                        "id": "u.38",
                        "role": "user",
                        "kind": "restore",
                        "title": "Bring back the strict reference style.",
                        "summary": "The user rejects richer editorial chrome and asks to return to sparse taxonomy and archival-band language.",
                        "thread": "display-surface",
                        "status": "locked design constraint",
                        "coupling": "shared with desktop only",
                    },
                    {
                        "id": "u.39",
                        "role": "user",
                        "kind": "constraint",
                        "title": "Leave mobile untouched.",
                        "summary": "The mobile experience is explicitly protected while the desktop atlas continues to evolve.",
                        "thread": "display-surface",
                        "status": "locked scope",
                        "coupling": "isolated from mobile",
                    },
                    {
                        "id": "u.40",
                        "role": "user",
                        "kind": "open",
                        "title": "Promotion rules still need governance.",
                        "summary": "The atlas is legible and inhabited, but the policy for promotion, dormancy, and reintegration is still unfinished.",
                        "thread": "display-surface",
                        "status": "open question",
                        "coupling": "not yet shared",
                    },
                ],
            },
        ],
    }


def _conversation_atlas_mobile_mockup_html() -> str:
    payload = json.dumps(_conversation_atlas_specimen())
    return (
        dedent(
            f"""
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
                <title>Conversation Atlas Mobile</title>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
                <link
                  href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Instrument+Sans:wght@400;500;600;700&display=swap"
                  rel="stylesheet"
                />
                <style>
                  :root {{
                    --paper: #f6efe2;
                    --paper-strong: #fcf7ef;
                    --ink: #17120f;
                    --ink-soft: #5b524a;
                    --ink-faint: #91877a;
                    --line: rgba(32, 24, 18, 0.14);
                    --line-strong: rgba(32, 24, 18, 0.24);
                    --accent: #9a6b2f;
                    --accent-soft: rgba(154, 107, 47, 0.12);
                    --shadow: 0 18px 36px rgba(56, 42, 29, 0.10);
                    --viewport-h: 438px;
                  }}

                  * {{ box-sizing: border-box; }}
                  html, body {{
                    margin: 0;
                    min-height: 100%;
                    background: var(--paper);
                    color: var(--ink);
                    font-family: "Instrument Sans", sans-serif;
                    scroll-behavior: smooth;
                  }}
                  body {{
                    background-image:
                      linear-gradient(rgba(27, 24, 21, 0.025) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(27, 24, 21, 0.025) 1px, transparent 1px);
                    background-size: 28px 28px;
                  }}
                  a {{ color: inherit; text-decoration: none; }}
                  .mobile-page {{
                    width: min(100%, 480px);
                    margin: 0 auto;
                    padding: max(12px, env(safe-area-inset-top)) 12px calc(178px + env(safe-area-inset-bottom));
                  }}
                  .mobile-head {{
                    position: sticky;
                    top: 0;
                    z-index: 20;
                    margin: 0 -12px 14px;
                    padding: 14px 12px 12px;
                    background: linear-gradient(180deg, rgba(246,239,226,0.97), rgba(246,239,226,0.82));
                    backdrop-filter: blur(18px);
                    border-bottom: 1px solid var(--line);
                  }}
                  .mobile-kicker, .sheet-label, .tray-label, .metric-label, .card-meta, .tab-range {{
                    margin: 0;
                    color: var(--ink-faint);
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.7rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                  }}
                  .mobile-title, .sheet-title, .card-title {{
                    margin: 0;
                    font-family: "Cormorant Garamond", serif;
                    letter-spacing: -0.02em;
                  }}
                  .mobile-title {{
                    margin-top: 6px;
                    font-size: 2.6rem;
                    line-height: 0.94;
                  }}
                  .mobile-copy, .metric-copy, .card-copy, .sheet-copy, .tray-copy {{
                    margin: 0;
                    color: var(--ink-soft);
                    line-height: 1.55;
                  }}
                  .mobile-copy {{ margin-top: 10px; font-size: 0.88rem; }}
                  .metrics {{
                    display: none;
                  }}
                  .deck-shell {{
                    margin-top: 6px;
                    padding: 0 0 18px;
                    overflow: clip;
                  }}
                  .metric-grid {{
                    display: none;
                  }}
                  .tab-rail {{
                    display: flex;
                    gap: 10px;
                    overflow-x: auto;
                    padding-bottom: 8px;
                    margin-bottom: 12px;
                    scroll-snap-type: x proximity;
                    -webkit-overflow-scrolling: touch;
                  }}
                  .tab-rail::-webkit-scrollbar {{
                    height: 7px;
                  }}
                  .tab-rail::-webkit-scrollbar-thumb {{
                    background: rgba(32, 24, 18, 0.16);
                    border-radius: 999px;
                  }}
                  .deck-tab {{
                    flex: 0 0 auto;
                    width: 168px;
                    scroll-snap-align: start;
                    padding: 12px;
                    border: 1px solid var(--line);
                    border-radius: 0;
                    background:
                      linear-gradient(180deg, rgba(255,255,255,0.58), rgba(250,246,238,0.4)),
                      repeating-linear-gradient(90deg, rgba(74, 58, 43, 0.016) 0 1px, transparent 1px 8px);
                    text-align: left;
                    transition: transform 180ms ease, border-color 180ms ease, background 180ms ease, box-shadow 180ms ease;
                  }}
                  .deck-tab.is-active {{
                    transform: translateY(-1px) scale(1.01);
                    border-color: rgba(154, 107, 47, 0.34);
                    background: var(--paper-strong);
                    box-shadow: inset 0 0 0 1px rgba(154,107,47,0.12);
                  }}
                  .tab-title {{
                    margin: 6px 0 0;
                    font-size: 0.98rem;
                    line-height: 1.25;
                    color: var(--ink);
                    font-weight: 600;
                  }}
                  .tab-summary {{
                    margin: 8px 0 0;
                    color: var(--ink-soft);
                    font-size: 0.75rem;
                    line-height: 1.45;
                  }}
                  .motion-note {{
                    margin: 0 0 14px;
                    color: var(--ink-faint);
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.68rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                  }}
                  .atlas-viewport {{
                    position: relative;
                    min-height: var(--viewport-h);
                    border-radius: 0;
                    overflow: hidden;
                    background:
                      radial-gradient(circle at center, rgba(255,255,255,0.42), rgba(255,255,255,0.08) 58%, rgba(255,255,255,0) 74%);
                    touch-action: none;
                  }}
                  .atlas-viewport::before,
                  .atlas-viewport::after {{
                    content: "";
                    position: absolute;
                    inset: 0;
                    pointer-events: none;
                  }}
                  .atlas-viewport::before {{
                    background-image:
                      linear-gradient(rgba(27, 24, 21, 0.03) 1px, transparent 1px),
                      linear-gradient(90deg, rgba(27, 24, 21, 0.03) 1px, transparent 1px);
                    background-size: 36px 36px;
                    opacity: 0.55;
                  }}
                  .atlas-viewport::after {{
                    background:
                      radial-gradient(circle at center, rgba(246,239,226,0) 36%, rgba(246,239,226,0.30) 70%, rgba(246,239,226,0.92) 100%);
                  }}
                  .focus-ring {{
                    position: absolute;
                    inset: 50% auto auto 50%;
                    width: min(82vw, 314px);
                    height: 336px;
                    transform: translate(-50%, -50%);
                    border: 0;
                    border-radius: 0;
                    box-shadow: 0 0 0 999px rgba(246,239,226,0.02);
                    pointer-events: none;
                    z-index: 2;
                  }}
                  .focus-caption {{
                    position: absolute;
                    left: 50%;
                    top: calc(50% + 184px);
                    transform: translateX(-50%);
                    z-index: 2;
                    margin: 0;
                    padding: 5px 10px;
                    border-radius: 0;
                    background: transparent;
                    border: 0;
                    color: var(--ink-faint);
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.66rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    pointer-events: none;
                  }}
                  .card-field {{
                    position: absolute;
                    inset: 0;
                  }}
                  .node-card {{
                    position: absolute;
                    left: 50%;
                    top: 50%;
                    width: min(82vw, 314px);
                    border: 1px solid var(--line);
                    border-radius: 0;
                    background:
                      linear-gradient(180deg, rgba(255,255,255,0.76), rgba(247,240,228,0.62)),
                      repeating-linear-gradient(0deg, rgba(74, 58, 43, 0.028) 0 1px, transparent 1px 6px),
                      repeating-linear-gradient(90deg, rgba(74, 58, 43, 0.018) 0 1px, transparent 1px 10px);
                    padding: 14px;
                    text-align: left;
                    min-height: 336px;
                    box-shadow: 0 8px 18px rgba(56, 42, 29, 0.06);
                    transform-origin: center center;
                    opacity: 0;
                    filter: blur(8px);
                    pointer-events: none;
                    transition:
                      opacity 360ms cubic-bezier(0.22, 1, 0.36, 1),
                      transform 520ms cubic-bezier(0.16, 1, 0.3, 1),
                      border-color 180ms ease,
                      box-shadow 260ms ease,
                      background 260ms ease,
                      filter 360ms ease;
                  }}
                  .node-card.is-active {{
                    border-color: var(--line-strong);
                    background: var(--paper-strong);
                    box-shadow:
                      inset 0 0 0 1px rgba(138, 106, 63, 0.18),
                      0 10px 24px rgba(56, 42, 29, 0.08);
                    filter: blur(0);
                    opacity: 1;
                    pointer-events: auto;
                    z-index: 3;
                  }}
                  .node-card.is-near {{
                    opacity: 0.56;
                    filter: blur(2.8px);
                    pointer-events: auto;
                    z-index: 1;
                  }}
                  .node-card.is-far {{
                    opacity: 0.18;
                    filter: blur(7px);
                    z-index: 0;
                  }}
                  .node-card.is-hidden {{
                    opacity: 0;
                    filter: blur(10px);
                  }}
                  .card-meta {{
                    display: flex;
                    justify-content: space-between;
                    gap: 10px;
                    align-items: center;
                  }}
                  .card-kind {{
                    padding: 5px 8px;
                    border-radius: 0;
                    background: var(--accent-soft);
                    color: var(--accent);
                    font-size: 0.66rem;
                    text-transform: uppercase;
                    letter-spacing: 0.08em;
                    font-family: "IBM Plex Mono", monospace;
                  }}
                  .card-title {{
                    margin: 14px 0 10px;
                    font-size: 2rem;
                    line-height: 0.94;
                  }}
                  .card-copy {{
                    font-size: 0.9rem;
                    min-height: 88px;
                  }}
                  .card-body {{
                    display: grid;
                    gap: 12px;
                  }}
                  .atlas-guides {{
                    display: none;
                  }}
                  .card-strip {{
                    margin-top: 14px;
                    display: grid;
                    gap: 10px;
                  }}
                  .strip-item {{
                    padding-top: 10px;
                    border-top: 1px solid var(--line);
                  }}
                  .strip-item p:last-child {{
                    margin: 4px 0 0;
                    color: var(--ink-soft);
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.72rem;
                    line-height: 1.45;
                  }}
                  .sheet {{
                    position: fixed;
                    left: 50%;
                    bottom: 0;
                    z-index: 30;
                    width: min(86vw, 348px);
                    min-height: 33vh;
                    max-height: 33vh;
                    transform: translateX(-50%);
                    margin: 0 auto calc(8px + env(safe-area-inset-bottom));
                    padding: 16px 16px 18px;
                    border: 1px solid var(--line-strong);
                    background:
                      linear-gradient(180deg, rgba(255,255,255,0.9), rgba(247,240,228,0.78)),
                      repeating-linear-gradient(0deg, rgba(74, 58, 43, 0.028) 0 1px, transparent 1px 6px),
                      repeating-linear-gradient(90deg, rgba(74, 58, 43, 0.016) 0 1px, transparent 1px 10px);
                    box-shadow: 0 12px 28px rgba(56, 42, 29, 0.10);
                    overflow: hidden;
                    transition:
                      transform 420ms cubic-bezier(0.16, 1, 0.3, 1),
                      max-height 420ms cubic-bezier(0.16, 1, 0.3, 1),
                      min-height 420ms cubic-bezier(0.16, 1, 0.3, 1),
                      box-shadow 260ms ease;
                  }}
                  .sheet.is-expanded {{
                    min-height: 90vh;
                    max-height: 90vh;
                    transform: translateX(-50%) translateY(-10px) scale(1.01);
                    box-shadow: 0 20px 44px rgba(56, 42, 29, 0.18);
                  }}
                  .sheet.is-transitioning .sheet-title,
                  .sheet.is-transitioning .sheet-copy,
                  .sheet.is-transitioning .sheet-item p:last-child {{
                    opacity: 0;
                    transform: translateY(8px);
                  }}
                  .sheet-title {{
                    margin-top: 8px;
                    font-size: 2.05rem;
                    line-height: 0.96;
                    transition: opacity 180ms ease, transform 240ms ease;
                  }}
                  .sheet-copy {{
                    margin: 8px 0 0;
                    line-height: 1.56;
                    font-size: 0.9rem;
                    transition: opacity 180ms ease 20ms, transform 240ms ease 20ms;
                  }}
                  .preview-handle {{
                    width: 54px;
                    height: 2px;
                    background: rgba(32, 24, 18, 0.16);
                    margin: 0 auto 12px;
                  }}
                  .sheet-grid {{
                    display: grid;
                    gap: 8px;
                    grid-template-columns: repeat(3, minmax(0, 1fr));
                    margin-top: 12px;
                  }}
                  .sheet-item {{
                    padding-top: 8px;
                    border-top: 1px solid var(--line);
                  }}
                  .sheet-item p:last-child {{
                    margin: 4px 0 0;
                    font-size: 0.72rem;
                    color: var(--ink);
                    line-height: 1.4;
                    transition: opacity 180ms ease 40ms, transform 240ms ease 40ms;
                  }}
                </style>
              </head>
              <body>
                <main class="mobile-page">
                  <section class="deck-shell" aria-live="polite">
                    <section id="atlas-viewport" class="atlas-viewport" aria-live="polite">
                      <div id="card-field" class="card-field"></div>
                    </section>
                  </section>

                  <aside class="sheet" aria-live="polite">
                    <p class="sheet-label">Active card</p>
                    <h2 id="sheet-title" class="sheet-title"></h2>
                    <p id="sheet-copy" class="sheet-copy"></p>
                    <div class="sheet-grid">
                      <div class="sheet-item">
                        <p class="sheet-label">Thread</p>
                        <p id="sheet-thread"></p>
                      </div>
                      <div class="sheet-item">
                        <p class="sheet-label">Status</p>
                        <p id="sheet-status"></p>
                      </div>
                      <div class="sheet-item">
                        <p class="sheet-label">Coupling</p>
                        <p id="sheet-coupling"></p>
                      </div>
                    </div>
                  </aside>
                </main>

                <script>
                  const specimen = {payload};
                  const tabRail = document.getElementById('tab-rail');
                  const viewport = document.getElementById('atlas-viewport');
                  const cardField = document.getElementById('card-field');
                  const sharedThreadsCount = document.getElementById('shared-threads-count');
                  const bucketCount = document.getElementById('bucket-count');
                  const sheet = document.querySelector('.sheet');
                  const sheetTitle = document.getElementById('sheet-title');
                  const sheetCopy = document.getElementById('sheet-copy');
                  const sheetThread = document.getElementById('sheet-thread');
                  const sheetStatus = document.getElementById('sheet-status');
                  const sheetCoupling = document.getElementById('sheet-coupling');
                  const bandLayouts = new Map();
                  const CARD_STEP_X = 190;
                  const CARD_STEP_Y = 228;
                  const MAX_DISTANCE = 2;
                  let activeTab = null;
                  let currentBandIndex = 0;
                  let activeNodeId = specimen.bands[0].nodes[0].id;
                  let gesture = null;
                  let sheetGesture = null;
                  let isAnimating = false;
                  let previewExpanded = false;
                  let sheetClickSuppressed = false;

                  function setTab(tab) {{
                    if (activeTab) activeTab.classList.remove('is-active');
                    activeTab = tab;
                    if (activeTab) activeTab.classList.add('is-active');
                    activeTab?.scrollIntoView({{ behavior: 'smooth', inline: 'center', block: 'nearest' }});
                  }}

                  function setActive(node) {{
                    sheet.classList.add('is-transitioning');
                    window.setTimeout(() => {{
                      sheetTitle.textContent = node.title;
                      sheetCopy.textContent = node.summary;
                      sheetThread.textContent = node.thread;
                      sheetStatus.textContent = node.status;
                      sheetCoupling.textContent = node.coupling;
                      sheet.classList.remove('is-transitioning');
                    }}, 130);
                  }}

                  function setPreviewExpanded(expanded) {{
                    previewExpanded = expanded;
                    sheet.classList.toggle('is-expanded', expanded);
                  }}

                  function activeBand() {{
                    return specimen.bands[currentBandIndex];
                  }}

                  function buildLayout(band) {{
                    const cols = Math.max(2, Math.ceil(Math.sqrt(band.nodes.length)));
                    return band.nodes.map((node, index) => ({{
                      ...node,
                      x: index % cols,
                      y: Math.floor(index / cols),
                    }}));
                  }}

                  function bandLayout(band) {{
                    if (!bandLayouts.has(band.id)) {{
                      bandLayouts.set(band.id, buildLayout(band));
                    }}
                    return bandLayouts.get(band.id);
                  }}

                  function activeLayout() {{
                    return bandLayout(activeBand());
                  }}

                  function activeNode() {{
                    return activeLayout().find((node) => node.id === activeNodeId) || activeLayout()[0];
                  }}

                  function classifyNode(dx, dy) {{
                    const distance = Math.abs(dx) + Math.abs(dy);
                    if (distance === 0) return 'is-active';
                    if (distance <= 1) return 'is-near';
                    if (distance <= MAX_DISTANCE) return 'is-far';
                    return 'is-hidden';
                  }}

                  function renderBand(index) {{
                    currentBandIndex = index;
                    const firstNode = activeLayout()[0];
                    activeNodeId = firstNode.id;
                    renderGrid();
                    setActive(firstNode);
                  }}

                  function renderGrid() {{
                    const layout = activeLayout();
                    const centerNode = activeNode();
                    cardField.innerHTML = '';
                    layout.forEach((node) => {{
                      const dx = node.x - centerNode.x;
                      const dy = node.y - centerNode.y;
                      const stateClass = classifyNode(dx, dy);
                      const button = document.createElement('button');
                      const rotation = Math.max(-6, Math.min(6, dx * 2.25));
                      const scale = stateClass === 'is-active' ? 1 : stateClass === 'is-near' ? 0.92 : 0.84;
                      const opacity = stateClass === 'is-active' ? 1 : stateClass === 'is-near' ? 0.56 : stateClass === 'is-far' ? 0.18 : 0;
                      button.type = 'button';
                      button.className = 'node-card ' + stateClass;
                      button.style.transform =
                        `translate3d(calc(-50% + ${{dx * CARD_STEP_X}}px), calc(-50% + ${{dy * CARD_STEP_Y}}px), 0) scale(${{scale}}) rotate(${{rotation}}deg)`;
                      button.style.opacity = opacity;
                      button.innerHTML = `
                        <div class="card-meta">
                          <span>${{node.id}}</span>
                          <span class="card-kind">${{node.kind}}</span>
                        </div>
                        <h3 class="card-title">${{node.title}}</h3>
                        <div class="card-body">
                          <p class="card-copy">${{node.summary}}</p>
                          <div class="card-strip">
                            <div class="strip-item">
                              <p class="tray-label">Folder</p>
                              <p>${{activeBand().title}}</p>
                            </div>
                            <div class="strip-item">
                              <p class="tray-label">Thread</p>
                              <p>${{node.thread}}</p>
                            </div>
                            <div class="strip-item">
                              <p class="tray-label">Coupling</p>
                              <p>${{node.coupling}}</p>
                            </div>
                          </div>
                        </div>
                      `;
                      button.addEventListener('click', () => {{
                        if (node.id === activeNodeId || stateClass === 'is-hidden') {{
                          return;
                        }}
                        activeNodeId = node.id;
                        renderGrid();
                        setActive(node);
                      }});
                      cardField.appendChild(button);
                    }});
                  }}

                  function findNodeAt(x, y) {{
                    return activeLayout().find((node) => node.x === x && node.y === y);
                  }}

                  function bounce(axis, distance) {{
                    const frames = axis === 'x'
                      ? [{{ transform: 'translateX(0px)' }}, {{ transform: `translateX(${{distance}}px)` }}, {{ transform: 'translateX(0px)' }}]
                      : [{{ transform: 'translateY(0px)' }}, {{ transform: `translateY(${{distance}}px)` }}, {{ transform: 'translateY(0px)' }}];
                    viewport.animate(frames, {{ duration: 240, easing: 'cubic-bezier(0.22, 1, 0.36, 1)' }});
                  }}

                  function nudge(direction) {{
                    if (isAnimating) {{
                      return;
                    }}
                    const current = activeNode();
                    const delta =
                      direction === 'left' ? [-1, 0] :
                      direction === 'right' ? [1, 0] :
                      direction === 'up' ? [0, -1] :
                      [0, 1];
                    const next = findNodeAt(current.x + delta[0], current.y + delta[1]);
                    if (!next) {{
                      if (direction === 'left') bounce('x', 9);
                      if (direction === 'right') bounce('x', -9);
                      if (direction === 'up') bounce('y', 9);
                      if (direction === 'down') bounce('y', -9);
                      return;
                    }}
                    isAnimating = true;
                    activeNodeId = next.id;
                    renderGrid();
                    setActive(next);
                    window.setTimeout(() => {{
                      isAnimating = false;
                    }}, 320);
                  }}

                  function bindGestures() {{
                    viewport.addEventListener('pointerdown', (event) => {{
                      if (previewExpanded) {{
                        return;
                      }}
                      gesture = {{
                        id: event.pointerId,
                        x: event.clientX,
                        y: event.clientY,
                        time: performance.now(),
                      }};
                      viewport.setPointerCapture(event.pointerId);
                    }});

                    viewport.addEventListener('pointerup', (event) => {{
                      if (!gesture || gesture.id !== event.pointerId) {{
                        return;
                      }}
                      const dx = event.clientX - gesture.x;
                      const dy = event.clientY - gesture.y;
                      const elapsed = Math.max(1, performance.now() - gesture.time);
                      gesture = null;
                      const absX = Math.abs(dx);
                      const absY = Math.abs(dy);
                      const velocity = Math.max(absX, absY) / elapsed;
                      if (Math.max(absX, absY) < 28 && velocity < 0.2) {{
                        return;
                      }}
                      if (absX > absY) {{
                        nudge(dx < 0 ? 'right' : 'left');
                      }} else {{
                        nudge(dy < 0 ? 'down' : 'up');
                      }}
                    }});

                    viewport.addEventListener('pointercancel', () => {{
                      gesture = null;
                    }});

                    sheet.addEventListener('click', () => {{
                      if (sheetClickSuppressed) {{
                        sheetClickSuppressed = false;
                        return;
                      }}
                      setPreviewExpanded(!previewExpanded);
                    }});

                    sheet.addEventListener('pointerdown', (event) => {{
                      if (!previewExpanded) {{
                        return;
                      }}
                      sheetGesture = {{
                        id: event.pointerId,
                        x: event.clientX,
                        y: event.clientY,
                      }};
                      sheet.setPointerCapture(event.pointerId);
                    }});

                    sheet.addEventListener('pointerup', (event) => {{
                      if (!previewExpanded || !sheetGesture || sheetGesture.id !== event.pointerId) {{
                        return;
                      }}
                      const dx = event.clientX - sheetGesture.x;
                      const dy = event.clientY - sheetGesture.y;
                      sheetGesture = null;
                      if (Math.abs(dx) < 18 && Math.abs(dy) < 18) {{
                        sheetClickSuppressed = true;
                        setPreviewExpanded(false);
                        return;
                      }}
                      if (Math.abs(dy) > Math.abs(dx) && dy > 48) {{
                        sheetClickSuppressed = true;
                        setPreviewExpanded(false);
                      }}
                    }});

                    sheet.addEventListener('pointercancel', () => {{
                      sheetGesture = null;
                    }});

                    window.addEventListener('keydown', (event) => {{
                      if (event.key === 'Escape' && previewExpanded) {{
                        setPreviewExpanded(false);
                      }}
                      if (event.key === 'ArrowLeft') nudge('left');
                      if (event.key === 'ArrowRight') nudge('right');
                      if (event.key === 'ArrowUp') nudge('up');
                      if (event.key === 'ArrowDown') nudge('down');
                    }});
                  }}

                  if (false && tabRail) {{
                    specimen.bands.forEach((band, bandIndex) => {{
                      const tab = document.createElement('button');
                      tab.type = 'button';
                      tab.className = 'deck-tab';
                      tab.innerHTML = `
                        <p class="tab-range">${{band.range}}</p>
                        <p class="tab-title">${{band.title}}</p>
                        <p class="tab-summary">${{band.summary}}</p>
                      `;
                      tab.addEventListener('click', () => {{
                        setTab(tab);
                        renderBand(bandIndex);
                      }});
                      tabRail.appendChild(tab);
                      if (bandIndex === 0) {{
                        setTab(tab);
                      }}
                    }});
                  }}

                  renderBand(0);
                  bindGestures();
                </script>
              </body>
            </html>
            """
        ).strip()
        + "\n"
    )


def _conversation_atlas_mockup_html() -> str:
    payload = json.dumps(_conversation_atlas_specimen())
    return (
        dedent(
            f"""
            <!doctype html>
            <html lang="en">
              <head>
                <meta charset="utf-8" />
                <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
                <title>Conversation Atlas</title>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin />
                <link
                  href="https://fonts.googleapis.com/css2?family=Instrument+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&family=Cormorant+Garamond:wght@500;600;700&display=swap"
                  rel="stylesheet"
                />
                <style>
                  :root {{
                    --paper: #f8f5ee;
                    --ink: #1b1815;
                    --ink-soft: #60574d;
                    --ink-faint: #8d8478;
                    --line: rgba(33, 28, 24, 0.24);
                    --line-soft: rgba(33, 28, 24, 0.14);
                    --accent: #111111;
                  }}

                  * {{ box-sizing: border-box; }}
                  html, body {{
                    margin: 0;
                    min-height: 100%;
                    background: var(--paper);
                    color: var(--ink);
                    font-family: "IBM Plex Mono", monospace;
                  }}
                  body {{
                    -webkit-font-smoothing: antialiased;
                  }}
                  button {{ font: inherit; color: inherit; }}
                  button {{ cursor: pointer; }}
                  .atlas-shell {{
                    width: min(100%, 1600px);
                    margin: 0 auto;
                    padding: 0;
                  }}
                  .atlas-frame {{
                    min-height: 100vh;
                    background: var(--paper);
                  }}
                  .atlas-index {{
                    position: sticky;
                    top: 0;
                    z-index: 2;
                    display: grid;
                    grid-template-columns: 74px 300px 1fr 290px;
                    gap: 18px;
                    padding: 10px 18px 8px;
                    border-bottom: 1px solid var(--line-soft);
                    background: rgba(248, 245, 238, 0.96);
                    backdrop-filter: blur(10px);
                  }}
                  .index-note,
                  .band-range,
                  .band-page,
                  .node-meta,
                  .system-label {{
                    margin: 0;
                    color: var(--ink-faint);
                    font-size: 0.72rem;
                    letter-spacing: 0.08em;
                  }}
                  .band {{
                    position: relative;
                    display: grid;
                    grid-template-columns: 74px 300px minmax(0, 1fr) 290px;
                    gap: 18px;
                    align-items: start;
                    min-height: 224px;
                    padding: 14px 18px 26px;
                    border-top: 1px solid var(--line);
                  }}
                  .band:first-child {{
                    border-top: 0;
                  }}
                  .band-summary {{
                    padding-top: 24px;
                  }}
                  .band-title {{
                    margin: 12px 0 0;
                    font-family: "Cormorant Garamond", serif;
                    font-size: clamp(2rem, 2.6vw, 3.25rem);
                    line-height: 0.88;
                    letter-spacing: -0.03em;
                    max-width: 260px;
                  }}
                  .band-copy {{
                    margin: 14px 0 0;
                    color: var(--ink-soft);
                    line-height: 1.5;
                    font-size: 0.82rem;
                    max-width: 248px;
                  }}
                  .band-graph {{
                    position: relative;
                    min-height: 180px;
                    padding-top: 14px;
                  }}
                  .band-graph::before {{
                    content: "";
                    position: absolute;
                    left: -18px;
                    top: 26px;
                    width: 18px;
                    height: 1px;
                    background: var(--line);
                  }}
                  .branch-list {{
                    position: relative;
                    display: grid;
                    gap: 8px;
                    padding-left: 18px;
                    padding-top: 4px;
                  }}
                  .branch-list::before {{
                    content: "";
                    position: absolute;
                    left: 0;
                    top: 16px;
                    bottom: 20px;
                    width: 1px;
                    background: var(--line);
                  }}
                  .node {{
                    position: relative;
                    width: min(100%, 520px);
                    padding: 2px 6px 2px 8px;
                    border: 0;
                    background: transparent;
                    text-align: left;
                    transition: transform 140ms ease, opacity 140ms ease;
                  }}
                  .node::before {{
                    content: "";
                    position: absolute;
                    left: -18px;
                    top: 12px;
                    width: 18px;
                    height: 1px;
                    background: var(--line);
                  }}
                  .node:hover,
                  .node.is-active {{
                    transform: translateX(3px);
                  }}
                  .node-role {{
                    display: none;
                  }}
                  .node-title {{
                    display: inline;
                    margin: 0;
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.82rem;
                    line-height: 1.2;
                    letter-spacing: 0;
                    font-weight: 500;
                  }}
                  .node-copy {{
                    display: none;
                  }}
                  .node-tail {{
                    margin-top: 2px;
                    display: flex;
                    gap: 10px;
                    flex-wrap: wrap;
                  }}
                  .node-thread,
                  .node-coupling {{
                    color: var(--ink-faint);
                    font-size: 0.66rem;
                    line-height: 1.4;
                  }}
                  .system-panel {{
                    padding-top: 18px;
                    display: grid;
                    gap: 12px;
                  }}
                  .system-title {{
                    margin: 0;
                    font-family: "IBM Plex Mono", monospace;
                    font-size: 0.82rem;
                    line-height: 1.2;
                    font-weight: 500;
                  }}
                  .system-copy {{
                    margin: 6px 0 0;
                    color: var(--ink-soft);
                    line-height: 1.45;
                    font-size: 0.76rem;
                  }}
                  .system-grid {{
                    display: grid;
                    gap: 10px;
                  }}
                  .system-item {{
                    padding-top: 8px;
                    border-top: 1px solid var(--line-soft);
                  }}
                  .system-item p:last-child {{
                    margin: 4px 0 0;
                    color: var(--ink);
                    line-height: 1.4;
                    font-size: 0.74rem;
                  }}
                  .translation-list {{
                    margin: 6px 0 0;
                    padding-left: 16px;
                    color: var(--ink-soft);
                    line-height: 1.45;
                    font-size: 0.74rem;
                  }}
                  .translation-list li + li {{
                    margin-top: 6px;
                  }}
                  .system-footer {{
                    padding-top: 10px;
                    border-top: 1px solid var(--line-soft);
                    color: var(--ink-faint);
                    font-size: 0.7rem;
                    line-height: 1.45;
                  }}
                  @media (max-width: 1180px) {{
                    .atlas-index,
                    .band {{
                      grid-template-columns: 60px 240px minmax(0, 1fr);
                    }}
                    .system-panel {{
                      display: none;
                    }}
                  }}
                  @media (max-width: 840px) {{
                    .atlas-index {{
                      display: none;
                    }}
                    .band {{
                      grid-template-columns: 50px 1fr;
                      gap: 12px;
                      min-height: 0;
                      padding: 18px 14px 22px;
                    }}
                    .band-summary {{
                      grid-column: 2;
                    }}
                    .band-graph {{
                      grid-column: 2;
                    }}
                    .band-graph::before {{
                      left: -12px;
                      width: 12px;
                    }}
                    .band-title {{
                      font-size: 1.8rem;
                    }}
                    .branch-list {{
                      padding-left: 12px;
                    }}
                    .node::before {{
                      left: -12px;
                      width: 12px;
                    }}
                  }}
                </style>
              </head>
              <body>
                <main class="atlas-shell">
                  <section class="atlas-frame">
                    <section class="atlas-index" aria-hidden="true">
                      <p class="index-note">Axis</p>
                      <p class="index-note">Conversation orders</p>
                      <p class="index-note">Branch structures</p>
                      <p class="index-note">System</p>
                    </section>

                    <section id="tree-plane" class="tree-plane" aria-live="polite"></section>
                  </section>
                </main>

                <script>
                  const specimen = {payload};
                  const treePlane = document.getElementById('tree-plane');
                  let activeNodeButton = null;

                  function setSystem(node, button) {{
                    if (activeNodeButton) activeNodeButton.classList.remove('is-active');
                    activeNodeButton = button;
                    if (activeNodeButton) activeNodeButton.classList.add('is-active');
                  }}

                  specimen.bands.forEach((band, bandIndex) => {{
                    const section = document.createElement('section');
                    section.className = 'band';
                    section.innerHTML = `
                      <div class="band-axis">
                        <p class="band-page">${{band.range}}</p>
                      </div>
                      <div class="band-summary">
                        <div>
                          <p class="band-range">${{band.range}}</p>
                          <h2 class="band-title">${{band.title}}</h2>
                          <p class="band-copy">${{band.summary}}</p>
                        </div>
                      </div>
                      <div class="band-graph">
                        <div class="branch-list" aria-label="${{band.title}} branch list"></div>
                      </div>
                      <aside class="system-panel">
                        <div>
                          <p class="system-label">Active branch</p>
                          <h3 class="system-title">${{band.nodes[0]?.title || ""}}</h3>
                          <p class="system-copy">${{band.nodes[0]?.summary || ""}}</p>
                        </div>
                        <div class="system-grid">
                          <div class="system-item">
                            <p class="system-label">Thread</p>
                            <p>${{band.nodes[0]?.thread || ""}}</p>
                          </div>
                          <div class="system-item">
                            <p class="system-label">Status</p>
                            <p>${{band.nodes[0]?.status || ""}}</p>
                          </div>
                          <div class="system-item">
                            <p class="system-label">Coupling</p>
                            <p>${{band.nodes[0]?.coupling || ""}}</p>
                          </div>
                        </div>
                      </aside>
                    `;
                    const branchList = section.querySelector('.branch-list');
                    const bandSystemTitle = section.querySelector('.system-title');
                    const bandSystemCopy = section.querySelector('.system-copy');
                    const bandSystemThread = section.querySelectorAll('.system-item p:last-child')[0];
                    const bandSystemStatus = section.querySelectorAll('.system-item p:last-child')[1];
                    const bandSystemCoupling = section.querySelectorAll('.system-item p:last-child')[2];

                    band.nodes.forEach((node, nodeIndex) => {{
                      const button = document.createElement('button');
                      button.type = 'button';
                      button.className = 'node';
                      button.innerHTML = `
                        <p class="node-meta">${{node.id}} / ${{node.kind}}</p>
                        <span class="node-role">${{node.role}}</span>
                        <h3 class="node-title">${{node.title}}</h3>
                        <div class="node-tail">
                          <span class="node-thread">${{node.thread}}</span>
                        </div>
                      `;
                      button.addEventListener('click', () => {{
                        setSystem(node, button);
                        bandSystemTitle.textContent = node.title;
                        bandSystemCopy.textContent = node.summary;
                        bandSystemThread.textContent = node.thread;
                        bandSystemStatus.textContent = node.status;
                        bandSystemCoupling.textContent = node.coupling;
                      }});
                      branchList.appendChild(button);

                      if (bandIndex === 0 && nodeIndex === 0) {{
                        setSystem(node, button);
                      }}
                    }});

                    treePlane.appendChild(section);
                  }});
                </script>
              </body>
            </html>
            """
        ).strip()
        + "\n"
    )


def build_miniapp_ui_enhancement_assets() -> dict[str, str]:
    return {
        _FEED_UI_ENHANCEMENT_CSS: """
.timeline-shell {
  width: min(100vw - 28px, 1260px);
}

.feed {
  gap: 18px;
}

.feed-post {
  width: min(100%, 920px);
  border-radius: 28px;
  background:
    linear-gradient(180deg, rgba(17, 17, 21, 0.96), rgba(10, 10, 14, 0.98)),
    rgba(8, 8, 10, 0.96);
  border: 1px solid rgba(255, 255, 255, 0.09);
}

.feed-post.is-active {
  max-width: 1160px;
  background:
    linear-gradient(180deg, rgba(18, 18, 22, 0.99), rgba(7, 7, 10, 1)),
    rgba(8, 8, 10, 1);
}

.feed-preview {
  display: grid;
  grid-template-columns: 54px minmax(0, 1fr);
  gap: 16px;
  padding: 22px 24px;
}

.feed-preview-main {
  min-width: 0;
  display: grid;
  gap: 12px;
}

.feed-preview-top,
.feed-preview-bottom {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  align-items: flex-start;
  flex-wrap: wrap;
}

.feed-post-title {
  margin: 0;
  font-size: 1.16rem;
  line-height: 1.28;
}

.feed-preview-lead {
  margin: 0;
  color: #f5f5f7;
  font-size: 1rem;
  line-height: 1.56;
}

.feed-preview-copy {
  margin: 0;
  color: var(--muted);
  font-size: 0.95rem;
  line-height: 1.58;
}

.feed-chip-row,
.feed-meta-row,
.feed-action-row,
.context-chip-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  align-items: center;
}

.feed-chip,
.feed-meta-pill,
.feed-cta-pill,
.context-chip,
.taste-rule-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 30px;
  padding: 0 12px;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.1);
  background: rgba(255, 255, 255, 0.04);
  color: #e8e8ee;
  font-size: 0.78rem;
  letter-spacing: 0;
}

.feed-chip strong,
.feed-meta-pill strong,
.feed-cta-pill strong,
.context-chip strong {
  font-weight: 600;
}

.feed-chip--format {
  background: rgba(126, 171, 255, 0.12);
  border-color: rgba(126, 171, 255, 0.24);
}

.feed-chip--evidence {
  background: rgba(113, 203, 152, 0.12);
  border-color: rgba(113, 203, 152, 0.22);
}

.feed-chip--active {
  background: rgba(255, 210, 126, 0.12);
  border-color: rgba(255, 210, 126, 0.22);
}

.feed-cta-pill {
  background: rgba(255, 255, 255, 0.06);
}

.feed-unfold {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(320px, 0.92fr);
  gap: 18px;
  padding: 0 24px 24px;
}

.feed-unfold-main,
.feed-unfold-side {
  min-width: 0;
  display: grid;
  gap: 16px;
}

.expand-shell,
.context-shell,
.taste-shell,
.feedback-shell,
.deep-read-shell {
  padding: 20px 22px;
  border: 1px solid rgba(255, 255, 255, 0.08);
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.03);
}

.expand-shell {
  display: grid;
  gap: 16px;
}

.expand-kicker,
.context-kicker,
.taste-kicker {
  display: inline-block;
  color: var(--muted);
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.expand-title {
  margin: 0;
  font-size: 1.42rem;
  line-height: 1.12;
}

.expand-subtitle,
.expand-opening {
  margin: 0;
  line-height: 1.65;
}

.expand-opening {
  font-size: 1rem;
  color: #f3f3f5;
}

.expand-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.expand-cell {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.expand-cell p,
.context-list p,
.taste-list p {
  margin: 0;
  color: #d7d7de;
  line-height: 1.58;
}

.expand-cell strong,
.context-list strong,
.taste-list strong {
  font-size: 0.8rem;
  color: #fbfbfd;
}

.context-shell,
.taste-shell,
.feedback-shell {
  display: grid;
  gap: 14px;
}

.context-summary {
  margin: 0;
  color: #ececf2;
  line-height: 1.6;
}

.context-list,
.taste-list {
  display: grid;
  gap: 10px;
}

.context-item,
.taste-item {
  display: grid;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.025);
  border: 1px solid rgba(255, 255, 255, 0.05);
}

.source-fragment {
  display: grid;
  gap: 8px;
  padding: 14px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.06);
}

.source-fragment p,
.source-fragment strong,
.source-fragment span {
  margin: 0;
}

.source-fragment p {
  color: #d4d4dd;
  font-size: 0.9rem;
  line-height: 1.55;
}

.source-fragment span {
  color: var(--muted);
  font-family: "Geist Mono", monospace;
  font-size: 0.72rem;
}

.feedback-shell .diagnostics-actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.deep-read-shell summary {
  cursor: pointer;
  list-style: none;
  font-weight: 600;
}

.deep-read-shell summary::-webkit-details-marker {
  display: none;
}

.deep-read-shell[open] .article-text {
  margin-top: 18px;
}

.feed-empty-note {
  color: var(--muted);
  margin: 0;
}

@media (max-width: 980px) {
  .feed-post,
  .feed-post.is-active {
    width: 100%;
    max-width: none;
  }

  .feed-unfold {
    grid-template-columns: 1fr;
  }

  .expand-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .feed-preview,
  .feed-unfold {
    padding-left: 16px;
    padding-right: 16px;
  }

  .feed-preview {
    grid-template-columns: 42px minmax(0, 1fr);
  }

  .feed-preview-top,
  .feed-preview-bottom {
    flex-direction: column;
    align-items: flex-start;
  }

  .expand-shell,
  .context-shell,
  .taste-shell,
  .feedback-shell,
  .deep-read-shell {
    padding: 16px;
  }
}
""".strip()
        + "\n",
        _FEED_UI_ENHANCEMENT_JS: """
(function () {
  if (window.__INNER_WORLD_FEED_UI_ENHANCED__) {
    return;
  }
  window.__INNER_WORLD_FEED_UI_ENHANCED__ = true;

  function safeValue(value, fallback) {
    return value === undefined || value === null || value === "" ? fallback : value;
  }

  function formatLabel(value) {
    return String(safeValue(value, "")).replace(/_/g, " ");
  }

  function previewPayload(thought) {
    return thought.preview_payload || {};
  }

  function expandPayload(thought) {
    return thought.expand_payload || {};
  }

  function postContext(thought) {
    return thought.post_context || {};
  }

  function tasteDiagnostics(thought) {
    return thought.taste_diagnostics || {};
  }

  function metricChip(label, value, className) {
    return '<span class="' + className + '"><strong>' + escapeHtml(String(value)) + '</strong><span>' + escapeHtml(label) + '</span></span>';
  }

  function renderListSection(title, items, emptyCopy) {
    if (!items.length) {
      return '<div class="context-item"><strong>' + escapeHtml(title) + '</strong><p class="feed-empty-note">' + escapeHtml(emptyCopy) + '</p></div>';
    }
    return items
      .map(function (item) {
        return '<div class="context-item"><strong>' + escapeHtml(title) + '</strong><p>' + escapeHtml(item) + '</p></div>';
      })
      .join('');
  }

  renderFeedStatus = window.renderFeedStatus = function () {
    var active = state.activeThoughtId ? '1 expanded' : 'all collapsed';
    var evidenceFirst = state.feed.filter(function (thought) {
      return previewPayload(thought).lead_mode === 'evidence';
    }).length;
    var prompts = state.feed.filter(function (thought) {
      return thought.post_format === 'discussion_prompt';
    }).length;
    feedStatusEl.innerHTML = [
      metricPill('timeline', state.feed.length + ' posts'),
      metricPill('evidence', evidenceFirst + ' evidence-led'),
      metricPill('prompts', prompts),
      metricPill('mode', active)
    ].join('');
  };

  renderDiagnostics = window.renderDiagnostics = function (thought, detail) {
    var feedPost = (detail && detail.feed_post) || thought;
    var context = postContext(feedPost);
    var taste = tasteDiagnostics(feedPost);
    var sourceSnippets = context.source_snippets || [];
    var tensions = context.tensions || [];
    var contradictions = context.contradictions || [];
    var questions = context.unresolved_questions || [];
    var supportingMeta = context.supporting_meta || [];
    return [
      '<aside class="feed-unfold-side">',
      '  <section class="context-shell">',
      '    <div>',
      '      <span class="context-kicker">scoped context</span>',
      '      <p class="context-summary">' + escapeHtml(safeValue(context.context_summary, 'No scoped context summary attached yet.')) + '</p>',
      '    </div>',
      '    <div class="context-chip-row">',
             metricChip('reach', safeValue(feedPost.reach_mode, 'strict'), 'context-chip'),
             context.primary_bubble_label ? metricChip('bubble', context.primary_bubble_label, 'context-chip') : '',
             metricChip('sources', sourceSnippets.length, 'context-chip'),
             metricChip('meta', supportingMeta.length, 'context-chip'),
      '    </div>',
      '    <div class="context-list">',
             renderListSection('tension', tensions.slice(0, 2), 'No tension attached.'),
             renderListSection('contradiction', contradictions.slice(0, 1), 'No contradiction attached.'),
             renderListSection('question', questions.slice(0, 2), 'No unresolved question attached.'),
      '    </div>',
      sourceSnippets.length ? '    <div class="context-list">' + sourceSnippets.slice(0, 3).map(function (snippet) {
        return '<div class="source-fragment"><strong>' + escapeHtml(snippet.title) + '</strong><p>' + escapeHtml(snippet.excerpt) + '</p><span>' + escapeHtml(sourceFamilyFromRef(snippet.source_ref)) + ' • ' + escapeHtml(shortPath(snippet.source_ref)) + '</span></div>';
      }).join('') + '</div>' : '',
      '  </section>',
      '  <section class="taste-shell">',
      '    <span class="taste-kicker">taste diagnostics</span>',
      '    <div class="feed-meta-row">',
             metricChip('lead rule', safeValue(taste.lead_rule, 'n/a'), 'taste-rule-pill'),
             metricChip('interaction', safeValue(taste.interaction_rule, 'n/a'), 'taste-rule-pill'),
             metricChip('compactness', safeValue(taste.compactness_rule, 'n/a'), 'taste-rule-pill'),
      '    </div>',
      '    <div class="taste-list">',
      '      <div class="taste-item"><strong>format alignment</strong><p>' + escapeHtml(taste.format_preference_match ? 'Matched the current preferred format.' : 'Did not match the current preferred format.') + '</p></div>',
      '      <div class="taste-item"><strong>raw signals</strong><p>' + escapeHtml('detail ' + safeValue((taste.signal_counts || {}).detail_open, 0) + ' • chat ' + safeValue((taste.signal_counts || {}).thought_chat, 0) + ' • saved ' + safeValue((taste.signal_counts || {}).thread_saved, 0) + ' • feedback ' + safeValue((taste.signal_counts || {}).explicit_feedback, 0)) + '</p></div>',
      '    </div>',
      '  </section>',
      '  <section class="feedback-shell">',
      '    <span class="taste-kicker">feedback loop</span>',
      '    <div class="diagnostics-actions">',
      '      <button class="feedback-button" type="button" data-feedback="relevant">Relevant</button>',
      '      <button class="feedback-button" type="button" data-feedback="revisit_later">Revisit</button>',
      '      <button class="feedback-button feedback-button--danger" type="button" data-feedback="dismiss">Dismiss</button>',
      '    </div>',
      '  </section>',
      '</aside>'
    ].join('');
  };

  renderExpanded = window.renderExpanded = function (thought) {
    var isLoading = state.loadingThoughtId === thought.thought_id;
    var error = state.detailErrors[thought.thought_id];
    var detail = state.thoughtDetails[thought.thought_id];
    var feedPost = (detail && detail.feed_post) || thought;
    var expand = expandPayload(feedPost);
    var context = postContext(feedPost);

    if (error) {
      return '<div class="feed-unfold"><section class="expand-shell"><p>Unable to load the full article for this post.</p><p class="feed-empty-note">' + escapeHtml(error) + '</p></section></div>';
    }

    if (isLoading && !detail) {
      return '<div class="feed-unfold"><section class="expand-shell"><div class="skeleton skeleton--title"></div><div class="skeleton"></div><div class="skeleton"></div><div class="skeleton skeleton--wide"></div></section><aside class="context-shell"><div class="skeleton skeleton--title"></div><div class="skeleton"></div><div class="skeleton"></div></aside></div>';
    }

    if (!detail) {
      return '';
    }

    var articleMarkdown = detail.thought && detail.thought.article_markdown ? detail.thought.article_markdown : '';
    return [
      '<div class="feed-unfold">',
      '  <section class="feed-unfold-main">',
      '    <section class="expand-shell">',
      '      <div class="feed-meta-row">',
               metricChip('opening', safeValue(expand.opening_focus, 'synthesis'), 'feed-meta-pill'),
               metricChip('suggested', safeValue(expand.recommended_interaction, 'deep_read'), 'feed-meta-pill'),
               metricChip('format', formatLabel(feedPost.post_format || 'post'), 'feed-meta-pill'),
      '      </div>',
      '      <div>',
      '        <span class="expand-kicker">expand</span>',
      '        <h3 class="expand-title">' + escapeHtml(safeValue(expand.title, thought.title)) + '</h3>',
      '        <p class="expand-subtitle">' + escapeHtml(safeValue(expand.subtitle, thought.short_text)) + '</p>',
      '      </div>',
      '      <p class="expand-opening">' + escapeHtml(safeValue(expand.opening_text, previewPayload(thought).lead_text || thought.short_text)) + '</p>',
      '      <div class="expand-grid">',
      '        <div class="expand-cell"><strong>what changed</strong><p>' + escapeHtml(safeValue(expand.what_changed, 'No surfacing explanation attached.')) + '</p></div>',
      '        <div class="expand-cell"><strong>why now</strong><p>' + escapeHtml(safeValue(expand.why_it_matters_now, 'No urgency note attached.')) + '</p></div>',
      '        <div class="expand-cell"><strong>next move</strong><p>' + escapeHtml(safeValue(expand.next_action, 'No next move recorded.')) + '</p></div>',
      '      </div>',
      context.supporting_meta && context.supporting_meta.length ? '      <div class="context-chip-row">' + context.supporting_meta.slice(0, 3).map(function (item) { return metricChip(item.kind || 'meta', item.label || item.summary || 'support', 'context-chip'); }).join('') + '</div>' : '',
      '    </section>',
      '    <details class="deep-read-shell">',
      '      <summary>Open deep read</summary>',
      '      <div class="article-text">' + renderMarkdown(articleMarkdown) + '</div>',
      '    </details>',
      '  </section>',
         renderDiagnostics(thought, detail),
      '</div>'
    ].join('');
  };

  renderPost = window.renderPost = function (thought) {
    var preview = previewPayload(thought);
    var context = postContext(thought);
    var isActive = thought.thought_id === state.activeThoughtId;
    var activeClass = isActive ? ' is-active' : '';
    return [
      '<article class="post feed-post' + activeClass + '" data-thought-id="' + escapeHtml(thought.thought_id) + '">',
      '  <div class="post-summary feed-preview" data-action="toggle-post" tabindex="0" role="button" aria-expanded="' + (isActive ? 'true' : 'false') + '">',
      '    <div class="post-avatar">' + escapeHtml(monogram(thought)) + '</div>',
      '    <div class="feed-preview-main">',
      '      <div class="feed-preview-top">',
      '        <div>',
      '          <div class="post-author-row"><span class="post-author">Inner World</span><span class="post-handle">@substrate</span></div>',
      '          <h2 class="feed-post-title">' + escapeHtml(safeValue(preview.title, thought.title)) + '</h2>',
      '        </div>',
      '        <div class="feed-chip-row">',
                 metricChip('format', formatLabel(thought.post_format || 'post'), 'feed-chip feed-chip--format'),
                 metricChip('evidence', safeValue(thought.evidence_status, 'unknown'), 'feed-chip feed-chip--evidence'),
                 isActive ? metricChip('state', 'expanded', 'feed-chip feed-chip--active') : '',
      '        </div>',
      '      </div>',
      '      <p class="feed-preview-lead">' + escapeHtml(safeValue(preview.lead_text, thought.short_text)) + '</p>',
      '      <p class="feed-preview-copy">' + escapeHtml(safeValue(preview.short_text, thought.short_text)) + '</p>',
      '      <div class="feed-preview-bottom">',
      '        <div class="feed-action-row">',
                 metricChip('next', safeValue(preview.cta_label, 'Expand thought'), 'feed-cta-pill'),
                 context.primary_bubble_label ? metricChip('bubble', context.primary_bubble_label, 'feed-meta-pill') : '',
      '        </div>',
      '        <div class="feed-meta-row">',
                 metricChip('sources', safeValue((context.source_snippets || []).length, 0), 'feed-meta-pill'),
                 metricChip('threads', safeValue(thought.thread_count, 0), 'feed-meta-pill'),
                 metricChip('saved', safeValue(thought.saved_thread_count, 0), 'feed-meta-pill'),
      '        </div>',
      '      </div>',
      '    </div>',
      '  </div>',
         isActive ? renderExpanded(thought) : '',
      '</article>'
    ].join('');
  };

  renderFeed = window.renderFeed = function () {
    if (!state.feed.length) {
      feedEl.innerHTML = '<div class="empty-feed">No thoughts are available yet.</div>';
      return;
    }
    feedEl.innerHTML = state.feed.map(function (thought) {
      return renderPost(thought);
    }).join('');
  };

  if (typeof renderApp === 'function') {
    renderApp();
  }
})();
""".strip()
        + "\n",
    }


def inject_miniapp_ui_enhancement(index_html: str) -> str:
    css_tag = f'<link rel="stylesheet" href="./{_FEED_UI_ENHANCEMENT_CSS}" />'
    js_tag = f'<script src="./{_FEED_UI_ENHANCEMENT_JS}" defer></script>'
    html = index_html
    if _FEED_UI_ENHANCEMENT_CSS not in html:
        if "</head>" in html:
            html = html.replace("</head>", f"    {css_tag}\n  </head>", 1)
        else:
            html = css_tag + "\n" + html
    if _FEED_UI_ENHANCEMENT_JS not in html:
        if "</body>" in html:
            html = html.replace("</body>", f"    {js_tag}\n  </body>", 1)
        else:
            html = html + "\n" + js_tag
    return html


def make_miniapp_handler(
    root: Path,
    static_dir: Path,
    domain_overlays: List[str],
    limit: int,
    api_prefixes: List[str],
):
    class InnerWorldMiniappHandler(BaseHTTPRequestHandler):
        def _send_security_headers(self) -> None:
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Strict-Transport-Security", "max-age=31536000")
            if self._is_capture_root_request():
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'self'; base-uri 'none'; frame-ancestors 'none'; "
                    "form-action 'self'; object-src 'none'; script-src 'self'; "
                    "style-src 'self' 'unsafe-inline'; img-src 'self' data:; "
                    "font-src 'self'; connect-src 'self'; manifest-src 'self'; worker-src 'self'",
                )

        def _send_json(
            self,
            payload: dict,
            status: int = HTTPStatus.OK,
            headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self._send_security_headers()
            if headers:
                for header_name, header_value in headers.items():
                    self.send_header(header_name, header_value)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, content: str, content_type: str, status: int = HTTPStatus.OK) -> None:
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self._send_security_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_file(self, path: Path, status: int = HTTPStatus.OK) -> None:
            content = path.read_bytes()
            mime_type, _ = mimetypes.guess_type(path.name)
            self.send_response(status)
            self.send_header("Content-Type", f"{mime_type or 'application/octet-stream'}; charset=utf-8")
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self._send_security_headers()
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def _not_found(self) -> None:
            self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def _mobile_session_cookie_value(self) -> str | None:
            cookie_header = self.headers.get("Cookie")
            if not cookie_header:
                return None
            cookies = SimpleCookie()
            try:
                cookies.load(cookie_header)
            except Exception:
                return None
            morsel = cookies.get(_MOBILE_SESSION_COOKIE_NAME)
            return morsel.value if morsel else None

        def _mobile_session_authenticated(self) -> bool:
            password = os.environ.get("INNER_WORLD_MOBILE_PASSWORD")
            if not password or self._is_capture_root_request():
                return True
            return _verify_mobile_session(self._mobile_session_cookie_value(), password)

        def _capture_basic_authenticated(self, expected_password: str) -> bool:
            authorization = (self.headers.get("Authorization") or "").strip()
            scheme, separator, encoded = authorization.partition(" ")
            if not separator or scheme.lower() != "basic" or not encoded:
                return False
            try:
                decoded = base64.b64decode(encoded, validate=True).decode("utf-8")
            except (binascii.Error, UnicodeDecodeError, ValueError):
                return False
            username, separator, supplied_password = decoded.partition(":")
            if not separator:
                return False
            return hmac.compare_digest(username, _configured_capture_username()) and hmac.compare_digest(
                supplied_password,
                expected_password,
            )

        def _require_capture_auth(self) -> bool:
            if not self._is_capture_root_request():
                return True
            expected_password = os.environ.get("INNER_WORLD_CAPTURE_PASSWORD") or ""
            if not expected_password:
                self._send_json(
                    {"error": "capture_auth_not_configured"},
                    status=HTTPStatus.SERVICE_UNAVAILABLE,
                )
                return False
            if self._capture_basic_authenticated(expected_password):
                return True
            self._send_json(
                {"error": "auth_required"},
                status=HTTPStatus.UNAUTHORIZED,
                headers={"WWW-Authenticate": 'Basic realm="Thought Capture", charset="UTF-8"'},
            )
            return False

        def _require_mobile_session(self) -> bool:
            if self._mobile_session_authenticated():
                return True
            self._send_json({"error": "auth_required"}, status=HTTPStatus.UNAUTHORIZED)
            return False

        def _is_mobile_root_request(self) -> bool:
            configured_host = _configured_mobile_hostname()
            if not configured_host:
                return False
            return _normalize_host_header(self.headers.get("Host")) == configured_host

        def _is_capture_root_request(self) -> bool:
            configured_host = _configured_capture_hostname()
            if not configured_host:
                return False
            return _normalize_host_header(self.headers.get("Host")) == configured_host

        def _serve_static_dir_asset(self, base_dir: Path, relative: str) -> bool:
            candidate = _resolve_static_asset(base_dir, relative)
            if candidate is None:
                return False
            if candidate.suffix == ".html":
                self._send_text(candidate.read_text(encoding="utf-8"), "text/html")
            else:
                self._send_file(candidate)
            return True

        def _serve_mobile_surface_asset(self, relative: str) -> bool:
            return self._serve_static_dir_asset(_mobile_surface_dir(root), relative)

        def _serve_mobile_surface_request(self, path: str) -> bool:
            relative = path.strip("/") or "index.html"
            return self._serve_mobile_surface_asset(relative)

        def _serve_thought_capture_pwa_request(self, path: str) -> bool:
            base_dir = _thought_capture_pwa_dir(root)
            relative = path.strip("/") or "index.html"
            if self._serve_static_dir_asset(base_dir, relative):
                return True
            if "." not in Path(relative).name:
                return self._serve_static_dir_asset(base_dir, "index.html")
            return False

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            api_path = _canonical_api_path(path, api_prefixes)

            if not self._require_capture_auth():
                return

            if self._is_capture_root_request() and path == "/meta":
                self._send_text(
                    _self_improvement_console_html(
                        api_base="/api",
                        capture_href="/capture",
                        meta_href="/meta",
                    ),
                    "text/html",
                )
                return

            if api_path == "/self-improvement/console":
                self._send_text(
                    _self_improvement_console_html(
                        api_base="/api",
                        capture_href="/capture" if self._is_capture_root_request() else "",
                        meta_href="/meta" if self._is_capture_root_request() else "",
                    ),
                    "text/html",
                )
                return

            if self._is_capture_root_request() and not api_path:
                if self._serve_thought_capture_pwa_request(path):
                    return

            if self._is_mobile_root_request() and not api_path:
                if self._serve_mobile_surface_request(path):
                    return

            if (path == "/mobile" or path.startswith("/mobile/")) and not self._require_mobile_session():
                return

            if api_path and api_path.startswith("/mobile/") and api_path not in {
                "/mobile/session",
                "/mobile/session/logout",
                "/mobile/capture/session",
            }:
                if not self._require_mobile_session():
                    return

            if api_path == "/archive":
                archive = build_thought_archive(root, domain_overlays=domain_overlays)
                self._send_json(archive)
                return
            if api_path == "/feed":
                feed = build_thought_feed(root, limit=limit, domain_overlays=domain_overlays)
                self._send_json(feed)
                return
            if api_path in {"/state", "/runtime-overview"}:
                state = get_runtime_overview(root)
                self._send_json(state)
                return
            if api_path == "/workspace-os/dashboard":
                self._send_json(workspace_os_dashboard_payload(root))
                return
            if api_path == "/workspace-os/live/health":
                self._send_json(workspace_os_live_health())
                return
            if api_path == "/workspace-os/live/catalog":
                self._send_json(workspace_os_live_catalog())
                return
            if api_path and api_path.startswith("/workspace-os/live/context/"):
                workspace_id = api_path.removeprefix("/workspace-os/live/context/").strip("/")
                self._send_json(workspace_os_live_context(workspace_id))
                return
            if api_path and api_path.startswith("/workspace-os/live/gate/"):
                workspace_id = api_path.removeprefix("/workspace-os/live/gate/").strip("/")
                self._send_json(workspace_os_live_gate(workspace_id))
                return
            if api_path == "/world-studio/worlds":
                self._send_json(worldstudio_list_worlds(root))
                return
            if api_path == "/world-studio/guide":
                self._send_json(worldstudio_get_guide(root))
                return
            if api_path == "/world-studio/executions":
                query = parse_qs(parsed.query)
                self._send_json(
                    worldstudio_list_execution_runs(
                        root,
                        packet_id=(query.get("packet_id") or [""])[0],
                        world_id=(query.get("world_id") or [""])[0],
                    )
                )
                return
            if api_path and api_path.startswith("/world-studio/execution/"):
                execution_id = api_path.removeprefix("/world-studio/execution/").strip("/")
                try:
                    self._send_json(worldstudio_get_execution_run(root, execution_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/next-question"):
                world_id = api_path[len("/world-studio/world/") : -len("/next-question")].strip("/")
                try:
                    self._send_json(worldstudio_next_question(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/evidence"):
                world_id = api_path[len("/world-studio/world/") : -len("/evidence")].strip("/")
                try:
                    self._send_json(worldstudio_inspect_world_evidence(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/graph"):
                world_id = api_path[len("/world-studio/world/") : -len("/graph")].strip("/")
                try:
                    self._send_json(worldstudio_project_graph(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/knowledge"):
                world_id = api_path[len("/world-studio/world/") : -len("/knowledge")].strip("/")
                try:
                    self._send_json(worldstudio_inspect_world_knowledge(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/visual"):
                world_id = api_path[len("/world-studio/world/") : -len("/visual")].strip("/")
                try:
                    self._send_json(worldstudio_inspect_visual_world(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/motion"):
                world_id = api_path[len("/world-studio/world/") : -len("/motion")].strip("/")
                try:
                    self._send_json(worldstudio_inspect_motion_system(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/") and api_path.endswith("/characters"):
                world_id = api_path[len("/world-studio/world/") : -len("/characters")].strip("/")
                try:
                    self._send_json(worldstudio_inspect_character_system(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/world/"):
                world_id = api_path.removeprefix("/world-studio/world/").strip("/")
                try:
                    self._send_json(worldstudio_get_world(root, world_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path and api_path.startswith("/world-studio/population/session/"):
                session_id = api_path.removeprefix("/world-studio/population/session/").strip("/")
                try:
                    self._send_json(worldstudio_get_population_session(root, session_id))
                except FileNotFoundError:
                    self._not_found()
                return
            if api_path == "/linking-overview":
                query_params = parse_qs(parsed.query)
                query = (query_params.get("query", [""])[0] or "").strip()
                limit_value = (query_params.get("limit", ["12"])[0] or "12").strip()
                neighbor_limit_value = (query_params.get("neighbor_limit", ["6"])[0] or "6").strip()
                try:
                    limit_int = max(1, min(50, int(limit_value)))
                    neighbor_limit_int = max(1, min(20, int(neighbor_limit_value)))
                except ValueError:
                    self._send_json({"error": "invalid_limit"}, status=HTTPStatus.BAD_REQUEST)
                    return
                payload = get_linking_overview(
                    root,
                    query=query,
                    limit=limit_int,
                    neighbor_limit=neighbor_limit_int,
                    domain_overlays=domain_overlays,
                )
                self._send_json(payload)
                return
            if api_path == "/retrieval-bundle":
                query_params = parse_qs(parsed.query)
                query = (query_params.get("query", [""])[0] or "").strip()
                if not query:
                    self._send_json({"error": "query_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                limit_value = (query_params.get("limit", ["10"])[0] or "10").strip()
                neighbor_limit_value = (query_params.get("neighbor_limit", ["6"])[0] or "6").strip()
                include_cross_pond_value = (query_params.get("include_cross_pond", [""])[0] or "").strip().lower()
                include_cross_pond = include_cross_pond_value in {"true", "1", "yes"}
                try:
                    limit_int = max(1, min(50, int(limit_value)))
                    neighbor_limit_int = max(1, min(20, int(neighbor_limit_value)))
                except ValueError:
                    self._send_json({"error": "invalid_limit"}, status=HTTPStatus.BAD_REQUEST)
                    return
                payload = get_retrieval_bundle(
                    root,
                    query=query,
                    limit=limit_int,
                    neighbor_limit=neighbor_limit_int,
                    include_cross_pond=include_cross_pond,
                    domain_overlays=domain_overlays,
                )
                self._send_json(payload)
                return
            if api_path == "/dimension-search":
                query_params = parse_qs(parsed.query)
                query = (query_params.get("query", [""])[0] or "").strip()
                limit_value = (query_params.get("limit", ["20"])[0] or "20").strip()
                statuses = [value.strip() for value in query_params.get("status", []) if value.strip()]
                dimensions = [value.strip() for value in query_params.get("dimension", []) if value.strip()]
                primary_pond = (query_params.get("primary_pond", [""])[0] or "").strip() or None
                source_ref = (query_params.get("source_ref", [""])[0] or "").strip() or None
                include_in_runtime_value = (query_params.get("include_in_runtime", [""])[0] or "").strip().lower()
                include_cross_pond_value = (query_params.get("include_cross_pond", [""])[0] or "").strip().lower()
                if include_in_runtime_value in {"true", "1", "yes"}:
                    include_in_runtime = True
                elif include_in_runtime_value in {"false", "0", "no"}:
                    include_in_runtime = False
                else:
                    include_in_runtime = None
                include_cross_pond = include_cross_pond_value in {"true", "1", "yes"}
                try:
                    limit_int = max(1, min(100, int(limit_value)))
                except ValueError:
                    self._send_json({"error": "invalid_limit"}, status=HTTPStatus.BAD_REQUEST)
                    return
                dimension_filters: dict[str, list[str]] = {}
                dimension_weights: dict[str, float] = {}
                for key, values in query_params.items():
                    if key.startswith("dimension_filter."):
                        dimension_id = key.split(".", 1)[1].strip()
                        normalized_values = [value.strip() for value in values if value.strip()]
                        if dimension_id and normalized_values:
                            dimension_filters[dimension_id] = normalized_values
                    if key.startswith("dimension_weight."):
                        dimension_id = key.split(".", 1)[1].strip()
                        if not dimension_id:
                            continue
                        try:
                            dimension_weights[dimension_id] = float(values[0])
                        except (TypeError, ValueError, IndexError):
                            self._send_json({"error": "invalid_dimension_weight"}, status=HTTPStatus.BAD_REQUEST)
                            return
                payload = search_library_dimensions(
                    root,
                    query=query,
                    dimensions=dimensions or None,
                    dimension_filters=dimension_filters or None,
                    dimension_weights=dimension_weights or None,
                    primary_pond=primary_pond,
                    include_cross_pond=include_cross_pond,
                    statuses=statuses or None,
                    source_ref=source_ref,
                    include_in_runtime=include_in_runtime,
                    limit=limit_int,
                )
                self._send_json(payload)
                return
            if api_path == "/dimension-model-roles":
                payload = get_dimension_model_role_status(root)
                self._send_json(payload)
                return
            if api_path == "/link-governance-state":
                payload = get_link_governance_state(root)
                self._send_json(payload)
                return
            if api_path and api_path.startswith("/chunk/") and api_path.endswith("/pond-routing"):
                chunk_id = api_path[len("/chunk/") : -len("/pond-routing")].strip("/")
                try:
                    payload = get_chunk_pond_detail(root, chunk_id, domain_overlays)
                except ValueError:
                    self._not_found()
                    return
                self._send_json(payload)
                return
            if api_path == "/openclaw/model-control/state":
                try:
                    state = get_openclaw_model_control_state(root)
                except FileNotFoundError:
                    self._send_json({"error": "openclaw_config_not_found"}, status=HTTPStatus.NOT_FOUND)
                    return
                self._send_json(state)
                return
            if api_path == "/mobile/feed":
                feed = build_mobile_feed(root, limit=limit, domain_overlays=domain_overlays)
                self._send_json(feed)
                return
            if path == "/self-improvement":
                self._send_text(_self_improvement_console_html(api_base="/api"), "text/html")
                return
            if api_path == "/mobile/library":
                library = build_mobile_library(root)
                self._send_json(library)
                return
            if api_path and api_path.startswith("/source/"):
                source_item_id = api_path.removeprefix("/source/").strip("/")
                try:
                    detail = get_source_item_detail(root, source_item_id, domain_overlays)
                except KeyError:
                    self._not_found()
                    return
                self._send_json(detail)
                return
            if api_path and api_path.startswith("/thought/"):
                thought_id = api_path.removeprefix("/thought/").strip("/")
                try:
                    detail = get_thought_detail(root, thought_id, domain_overlays)
                except KeyError:
                    self._not_found()
                    return
                self._send_json(detail)
                return
            if api_path and api_path.startswith("/thread/"):
                thread_id = api_path.removeprefix("/thread/").strip("/")
                try:
                    detail = get_thread_detail(root, thread_id)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(detail)
                return

            if path == "/manifest.webmanifest":
                mobile_manifest = _mobile_surface_dir(root) / "manifest.webmanifest"
                if self._mobile_session_authenticated() and mobile_manifest.exists():
                    self._send_file(mobile_manifest)
                    return

            if path == "/mobile" or path.startswith("/mobile/"):
                mobile_assets_dir = _mobile_surface_dir(root)
                relative = path.removeprefix("/mobile").lstrip("/") or "index.html"
                candidate = mobile_assets_dir / relative
                if candidate.exists() and candidate.is_file():
                    if candidate.suffix == ".html":
                        self._send_text(candidate.read_text(encoding="utf-8"), "text/html")
                    else:
                        self._send_file(candidate)
                    return
                self._not_found()
                return

            if path in {_CONVERSATION_ATLAS_ROUTE, _CONVERSATION_ATLAS_ROUTE.removesuffix(".html")}:
                self._send_text(_conversation_atlas_mockup_html(), "text/html")
                return
            if path in {_CONVERSATION_ATLAS_MOBILE_ROUTE, _CONVERSATION_ATLAS_MOBILE_ROUTE.removesuffix(".html")}:
                self._send_text(_conversation_atlas_mobile_mockup_html(), "text/html")
                return

            relative = path.strip("/") or "index.html"
            enhancement_assets = build_miniapp_ui_enhancement_assets()
            if relative in enhancement_assets:
                content_type = "text/css" if relative.endswith(".css") else "application/javascript"
                self._send_text(enhancement_assets[relative], content_type)
                return
            candidate = static_dir / relative
            if candidate.exists() and candidate.is_file():
                if candidate.name == "index.html":
                    self._send_text(inject_miniapp_ui_enhancement(candidate.read_text(encoding="utf-8")), "text/html")
                else:
                    self._send_file(candidate)
                return
            self._send_text(
                inject_miniapp_ui_enhancement((static_dir / "index.html").read_text(encoding="utf-8")),
                "text/html",
            )

        def do_POST(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            api_path = _canonical_api_path(path, api_prefixes)

            if not self._require_capture_auth():
                return

            if api_path and api_path.startswith("/mobile/") and api_path not in {
                "/mobile/session",
                "/mobile/session/logout",
                "/mobile/capture/session",
            }:
                if not self._require_mobile_session():
                    return

            if api_path == "/mobile/session/logout":
                self._send_json(
                    {"authenticated": False},
                    headers={
                        "Set-Cookie": (
                            f"{_MOBILE_SESSION_COOKIE_NAME}=; Path=/; Max-Age=0; "
                            "HttpOnly; SameSite=Lax"
                        )
                    },
                )
                return

            if api_path == "/mobile/session":
                try:
                    payload = _read_json_body(self)
                except json.JSONDecodeError:
                    self._send_json({"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
                    return
                password = (payload.get("password") or "").strip()
                expected_password = os.environ.get("INNER_WORLD_MOBILE_PASSWORD") or ""
                if not expected_password or password != expected_password:
                    self._send_json({"error": "invalid_password"}, status=HTTPStatus.UNAUTHORIZED)
                    return
                self._send_json(
                    {"authenticated": True},
                    headers={
                        "Set-Cookie": (
                            f"{_MOBILE_SESSION_COOKIE_NAME}={_sign_mobile_session(expected_password)}; "
                            "Path=/; HttpOnly; SameSite=Lax"
                        )
                    },
                )
                return

            try:
                payload = _read_json_body(self)
            except json.JSONDecodeError:
                self._send_json({"error": "invalid_json"}, status=HTTPStatus.BAD_REQUEST)
                return

            if api_path == "/mobile/capture/session":
                session_id = (payload.get("session_id") or "").strip() or None
                manifest = ensure_mobile_capture_session(root, session_id=session_id)
                self._send_json({"session_id": manifest["session_id"]})
                return

            if api_path == "/self-improvement/interpret":
                raw_text = str(payload.get("text") or "").strip()
                if not raw_text:
                    self._send_json({"error": "text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                interpretation = interpret_self_improvement_turn(
                    raw_text,
                    requested_mode=str(payload.get("surface_mode") or ""),
                    requested_meta_state=str(payload.get("meta_state") or ""),
                )
                self._send_json(interpretation)
                return

            if api_path == "/self-improvement/chat":
                raw_text = str(payload.get("text") or "").strip()
                session_id = str(payload.get("session_id") or "").strip()
                turn_id = str(payload.get("turn_id") or "").strip()
                if not raw_text:
                    self._send_json({"error": "text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                response = build_self_improvement_chat_response(
                    raw_text,
                    requested_mode=str(payload.get("surface_mode") or ""),
                    requested_meta_state=str(payload.get("meta_state") or ""),
                    builder_state=payload.get("builder_state"),
                    workspace_context=payload.get("workspace_context"),
                )
                if response["interpretation"]["should_create_packet"]:
                    if not session_id or not turn_id:
                        self._send_json(
                            {"error": "session_id_and_turn_id_required_for_operate_mode"},
                            status=HTTPStatus.BAD_REQUEST,
                        )
                        return
                    packet_input = str(payload.get("packet_input") or "").strip() or compose_builder_packet_input(
                        raw_text,
                        response.get("builder_state", {}) or {},
                        response.get("builder_scope", {}) or {},
                    )
                    response["packet"] = draft_self_improvement_packet(
                        packet_input,
                        session_id,
                        turn_id,
                        use_agent=bool(payload.get("use_agent", False)),
                    )
                self._send_json(response)
                return

            if api_path == "/self-improvement/packet":
                raw_text = str(payload.get("text") or "").strip()
                session_id = str(payload.get("session_id") or "").strip()
                turn_id = str(payload.get("turn_id") or "").strip()
                if not raw_text or not session_id or not turn_id:
                    self._send_json(
                        {"error": "text_session_id_and_turn_id_required"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                packet = draft_self_improvement_packet(
                    raw_text,
                    session_id,
                    turn_id,
                    use_agent=bool(payload.get("use_agent", False)),
                )
                self._send_json(packet)
                return

            if api_path == "/self-improvement/release/candidate":
                release_id = str(payload.get("release_id") or "").strip() or None
                manifest = build_release_manifest(root, release_id=release_id)
                self._send_json(manifest)
                return

            if api_path == "/self-improvement/release/rollback-plan":
                current_release_id = str(payload.get("current_release_id") or "").strip()
                previous_release_id = str(payload.get("previous_release_id") or "").strip()
                if not current_release_id or not previous_release_id:
                    self._send_json(
                        {"error": "current_release_id_and_previous_release_id_required"},
                        status=HTTPStatus.BAD_REQUEST,
                    )
                    return
                plan = build_rollback_plan(current_release_id, previous_release_id)
                self._send_json(plan)
                return

            if api_path == "/mobile/capture":
                try:
                    result = append_mobile_capture(
                        root,
                        content=payload.get("content", ""),
                        session_id=payload.get("session_id")
                        or (payload.get("provenance") or {}).get("session_id"),
                        provenance=payload.get("provenance") or None,
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/mobile/compose":
                deposit = dict(payload.get("deposit") or {})
                deposit_body = str(deposit.get("body", "") or payload.get("content", "")).strip()
                local_deposit_id = str(deposit.get("local_deposit_id", "") or "").strip()
                session_id = str(payload.get("session_id") or "").strip()
                intent = str(payload.get("intent", "nudge") or "nudge").strip().lower()
                composition_phase = str(payload.get("composition_phase", "") or "").strip().lower()
                if not deposit_body:
                    self._send_json({"error": "deposit_body_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if not local_deposit_id:
                    self._send_json({"error": "local_deposit_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if not session_id:
                    self._send_json({"error": "session_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if intent not in {"nudge", "shape"}:
                    self._send_json({"error": "invalid_intent"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if composition_phase and composition_phase not in {"capture", "develop"}:
                    self._send_json({"error": "invalid_composition_phase"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = compose_mobile_capture_insertion(
                        root,
                        deposit_body=deposit_body,
                        local_deposit_id=local_deposit_id,
                        session_id=session_id,
                        provenance=payload.get("provenance") or None,
                        capture_mode_state=payload.get("capture_mode_state") or None,
                        intent=intent,  # type: ignore[arg-type]
                        composition_phase=composition_phase or None,  # type: ignore[arg-type]
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path and api_path.startswith("/mobile/conversations/") and api_path.endswith("/reply"):
                session_id = api_path[len("/mobile/conversations/") : -len("/reply")].strip("/")
                try:
                    result = reply_in_mobile_session(
                        root,
                        session_id=session_id,
                        user_message=payload.get("message", ""),
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/mobile/feedback":
                insight_id = payload.get("insight_id")
                feedback_state = payload.get("feedback_state")
                if not insight_id or not feedback_state:
                    self._send_json({"error": "insight_id_and_feedback_state_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                if feedback_state == "saved":
                    result = save_mobile_feed_item(root, insight_id=insight_id)
                else:
                    result = record_feedback(root, insight_id, feedback_state)
                self._send_json(result)
                return

            if api_path == "/world-studio/world":
                name = (payload.get("name") or "").strip()
                if not name:
                    self._send_json({"error": "name_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                result = worldstudio_create_world(
                    root,
                    name=name,
                    summary=payload.get("summary") or "",
                    primitives=payload.get("primitives") or [],
                    world_rules=payload.get("world_rules") or [],
                    taste_profile=payload.get("taste_profile") or None,
                    bridge_objects=payload.get("bridge_objects") or None,
                    visual_lens_rules=payload.get("visual_lens_rules") or None,
                    cut_grammar=payload.get("cut_grammar") or None,
                    constraints=payload.get("constraints") or None,
                    provenance_refs=payload.get("provenance_refs") or [],
                )
                self._send_json(result)
                return

            if api_path == "/world-studio/population/start":
                world_id = (payload.get("world_id") or "").strip()
                if not world_id:
                    name = (payload.get("name") or "").strip()
                    if not name:
                        self._send_json({"error": "world_id_or_name_required"}, status=HTTPStatus.BAD_REQUEST)
                        return
                    created = worldstudio_create_world(
                        root,
                        name=name,
                        summary=payload.get("summary") or "",
                    )
                    world_id = created["world_id"]
                try:
                    result = worldstudio_start_population_session(root, world_id)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/population/answer":
                session_id = (payload.get("session_id") or "").strip()
                answer = (payload.get("answer") or "").strip()
                if not session_id or not answer:
                    self._send_json({"error": "session_id_and_answer_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_answer_population_question(root, session_id, answer)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/ingest-evidence":
                world_id = (payload.get("world_id") or "").strip()
                if not world_id:
                    self._send_json({"error": "world_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_ingest_evidence(
                        root,
                        world_id,
                        source_text=payload.get("source_text") or "",
                        source_path=payload.get("source_path") or "",
                        source_url=payload.get("source_url") or "",
                        source_label=payload.get("source_label") or "",
                        note=payload.get("note") or "",
                        annotations=payload.get("annotations") or {},
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/ingest-visual-reference":
                world_id = (payload.get("world_id") or "").strip()
                if not world_id:
                    self._send_json({"error": "world_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_ingest_visual_reference(
                        root,
                        world_id,
                        source_path=payload.get("source_path") or "",
                        source_url=payload.get("source_url") or "",
                        source_label=payload.get("source_label") or "",
                        note=payload.get("note") or "",
                        categories=payload.get("categories") or [],
                        liked_aspects=payload.get("liked_aspects") or [],
                        negative_constraints=payload.get("negative_constraints") or [],
                        scope=payload.get("scope") or "global",
                        target_entity=payload.get("target_entity") or "",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/generate-canon":
                world_id = (payload.get("world_id") or "").strip()
                if not world_id:
                    self._send_json({"error": "world_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_generate_canon(
                        root,
                        world_id,
                        asset_types=payload.get("asset_types") or [],
                        style_note=payload.get("style_note") or "",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/motion-object":
                world_id = (payload.get("world_id") or "").strip()
                label = (payload.get("label") or "").strip()
                scope = (payload.get("scope") or "").strip()
                if not world_id or not label or not scope:
                    self._send_json({"error": "world_id_label_scope_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_create_motion_object(
                        root,
                        world_id,
                        label=label,
                        scope=scope,
                        intent=payload.get("intent") or "",
                        primary_action=payload.get("primary_action") or "",
                        body_mechanics=payload.get("body_mechanics") or [],
                        secondary_motion=payload.get("secondary_motion") or [],
                        constraints=payload.get("constraints") or [],
                        negative_constraints=payload.get("negative_constraints") or [],
                        compatible_states=payload.get("compatible_states") or [],
                        speed=payload.get("speed") or "",
                        intensity=payload.get("intensity") or "",
                        best_clip_duration=int(payload.get("best_clip_duration") or 4),
                        prompt_template=payload.get("prompt_template") or "",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/character-profile":
                world_id = (payload.get("world_id") or "").strip()
                name = (payload.get("name") or "").strip()
                if not world_id or not name:
                    self._send_json({"error": "world_id_and_name_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_create_character_profile(
                        root,
                        world_id,
                        name=name,
                        summary=payload.get("summary") or "",
                        role=payload.get("role") or "",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/update-character-profile":
                world_id = (payload.get("world_id") or "").strip()
                character_id = (payload.get("character_id") or "").strip()
                section = (payload.get("section") or "").strip()
                value = payload.get("value")
                if not world_id or not character_id or not section:
                    self._send_json({"error": "world_id_character_id_section_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_update_character_profile_section(
                        root,
                        world_id,
                        character_id,
                        section=section,
                        value=value,
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/update-character-feature":
                world_id = (payload.get("world_id") or "").strip()
                feature_id = (payload.get("feature_id") or "").strip()
                if not world_id or not feature_id:
                    self._send_json({"error": "world_id_and_feature_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_update_character_feature_object(
                        root,
                        world_id,
                        feature_id,
                        summary=payload.get("summary") or "",
                        trait_values=payload.get("trait_values"),
                        state_scope=payload.get("state_scope") or "",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/motion-binding":
                world_id = (payload.get("world_id") or "").strip()
                motion_id = (payload.get("motion_id") or "").strip()
                target_kind = (payload.get("target_kind") or "").strip()
                if not world_id or not motion_id or not target_kind:
                    self._send_json({"error": "world_id_motion_id_target_kind_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_bind_motion_object(
                        root,
                        world_id,
                        motion_id=motion_id,
                        target_kind=target_kind,
                        target_id=payload.get("target_id") or "default",
                        when_tags=payload.get("when_tags") or [],
                        exclude_tags=payload.get("exclude_tags") or [],
                        priority=int(payload.get("priority") or 1),
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/compile-motion-plan":
                world_id = (payload.get("world_id") or "").strip()
                scene_text = (payload.get("scene_text") or "").strip()
                if not world_id or not scene_text:
                    self._send_json({"error": "world_id_and_scene_text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_compile_motion_plan(
                        root,
                        world_id,
                        scene_text=scene_text,
                        duration_seconds=int(payload.get("duration_seconds") or 4),
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/compile-visual-context":
                world_id = (payload.get("world_id") or "").strip()
                query_text = (payload.get("query_text") or "").strip()
                if not world_id or not query_text:
                    self._send_json({"error": "world_id_and_query_text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_compile_visual_context(root, world_id, query_text=query_text)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/compile-scene":
                world_id = (payload.get("world_id") or "").strip()
                scene_text = (payload.get("scene_text") or "").strip()
                if not world_id or not scene_text:
                    self._send_json({"error": "world_id_and_scene_text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_compile_scene(
                        root,
                        world_id,
                        scene_text,
                        duration_seconds=int(payload.get("duration_seconds") or 12),
                        aspect_ratio=payload.get("aspect_ratio") or "16:9",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/compile-scene-from-canon":
                world_id = (payload.get("world_id") or "").strip()
                scene_text = (payload.get("scene_text") or "").strip()
                if not world_id or not scene_text:
                    self._send_json({"error": "world_id_and_scene_text_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_compile_scene_from_canon(
                        root,
                        world_id,
                        scene_text,
                        duration_seconds=int(payload.get("duration_seconds") or 12),
                        aspect_ratio=payload.get("aspect_ratio") or "16:9",
                    )
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/execute-packet":
                packet_id = (payload.get("packet_id") or "").strip()
                if not packet_id:
                    self._send_json({"error": "packet_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = worldstudio_execute_higgsfield_packet(root, packet_id, mode=(payload.get("mode") or "auto"))
                except FileNotFoundError:
                    self._not_found()
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/world-studio/demo":
                result = worldstudio_run_demo(
                    root,
                    scene_text=(payload.get("scene_text") or "").strip() or None,
                    duration_seconds=int(payload.get("duration_seconds") or 12),
                    aspect_ratio=payload.get("aspect_ratio") or "16:9",
                )
                self._send_json(result)
                return

            if api_path and api_path.startswith("/thought/") and api_path.endswith("/chat"):
                thought_id = api_path[len("/thought/") : -len("/chat")].strip("/")
                message = (payload.get("message") or "").strip()
                if not message:
                    self._send_json({"error": "message_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = chat_with_thought(
                        root,
                        thought_id,
                        message,
                        payload.get("thread_id"),
                        domain_overlays,
                    )
                except (FileNotFoundError, KeyError):
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path and api_path.startswith("/thread/") and api_path.endswith("/save"):
                thread_id = api_path[len("/thread/") : -len("/save")].strip("/")
                try:
                    result = save_thread(root, thread_id, domain_overlays)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path and api_path.startswith("/thread/") and api_path.endswith("/delete"):
                thread_id = api_path[len("/thread/") : -len("/delete")].strip("/")
                try:
                    result = delete_thread(root, thread_id)
                except FileNotFoundError:
                    self._not_found()
                    return
                self._send_json(result)
                return

            if api_path == "/feedback":
                insight_id = payload.get("insight_id")
                feedback_state = payload.get("feedback_state")
                if not insight_id or not feedback_state:
                    self._send_json({"error": "insight_id_and_feedback_state_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                result = record_feedback(root, insight_id, feedback_state)
                generate_daily_batch(root, limit=max(limit, 5), domain_overlays=domain_overlays, write_feed=True)
                self._send_json(result)
                return

            if api_path == "/openclaw/model-control/assign":
                agent_id = (payload.get("agent_id") or "").strip()
                model_id = (payload.get("model_id") or "").strip()
                if not agent_id or not model_id:
                    self._send_json({"error": "agent_id_and_model_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = stage_openclaw_agent_model(root, agent_id, model_id)
                except FileNotFoundError:
                    self._send_json({"error": "openclaw_config_not_found"}, status=HTTPStatus.NOT_FOUND)
                    return
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/link-governance/link":
                link_id = (payload.get("link_id") or "").strip()
                governance_status = (payload.get("governance_status") or "").strip()
                if not link_id or not governance_status:
                    self._send_json({"error": "link_id_and_governance_status_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = update_link_governance(
                        root,
                        link_id=link_id,
                        governance_status=governance_status,
                        confidence_override=payload.get("confidence_override"),
                        confidence_delta=payload.get("confidence_delta"),
                        notes=payload.get("notes"),
                        domain_overlays=domain_overlays,
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/link-governance/alias":
                alias_text = (payload.get("alias_text") or "").strip()
                ref_type = (payload.get("ref_type") or "").strip()
                ref_id = (payload.get("ref_id") or "").strip()
                if not alias_text or not ref_type or not ref_id:
                    self._send_json({"error": "alias_text_ref_type_and_ref_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = create_link_alias_resolution(
                        root,
                        alias_text=alias_text,
                        ref_type=ref_type,
                        ref_id=ref_id,
                        status=(payload.get("status") or "active").strip() or "active",
                        notes=payload.get("notes"),
                        domain_overlays=domain_overlays,
                    )
                except ValueError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path == "/dimension-model-roles/update":
                role_id = (payload.get("role_id") or "").strip()
                if not role_id:
                    self._send_json({"error": "role_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = update_dimension_model_role_binding(
                        root,
                        role_id=role_id,
                        backend=payload.get("backend"),
                        model_id=payload.get("model_id"),
                        enabled=payload.get("enabled"),
                        fallback_role_id=payload.get("fallback_role_id"),
                        endpoint=payload.get("endpoint"),
                        attributes=payload.get("attributes"),
                    )
                except (TypeError, ValueError) as exc:
                    self._send_json({"error": str(exc) or "invalid_model_role_payload"}, status=HTTPStatus.BAD_REQUEST)
                    return
                self._send_json(result)
                return

            if api_path and api_path.startswith("/chunk/") and api_path.endswith("/pond-routing"):
                chunk_id = api_path[len("/chunk/") : -len("/pond-routing")].strip("/")
                if not chunk_id:
                    self._send_json({"error": "chunk_id_required"}, status=HTTPStatus.BAD_REQUEST)
                    return
                pond_layers = payload.get("pond_layers")
                if pond_layers is not None and not isinstance(pond_layers, list):
                    self._send_json({"error": "pond_layers_must_be_a_list"}, status=HTTPStatus.BAD_REQUEST)
                    return
                try:
                    result = update_chunk_pond_detail(
                        root,
                        chunk_id,
                        primary_pond=payload.get("primary_pond"),
                        pond_layers=pond_layers,
                        clear_override=bool(payload.get("clear_override", False)),
                        notes=payload.get("notes"),
                        domain_overlays=domain_overlays,
                    )
                except ValueError as exc:
                    message = str(exc)
                    status = HTTPStatus.NOT_FOUND if message.startswith("Unknown chunk_id:") else HTTPStatus.BAD_REQUEST
                    self._send_json({"error": message}, status=status)
                    return
                self._send_json(result)
                return

            if api_path == "/openclaw/model-control/apply":
                try:
                    result = apply_openclaw_model_control(root)
                except FileNotFoundError:
                    self._send_json({"error": "openclaw_config_not_found"}, status=HTTPStatus.NOT_FOUND)
                    return
                except RuntimeError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.CONFLICT)
                    return
                self._send_json(result)
                return

            if api_path == "/openclaw/model-control/rollback":
                try:
                    result = rollback_openclaw_model_control(root)
                except FileNotFoundError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.NOT_FOUND)
                    return
                except RuntimeError as exc:
                    self._send_json({"error": str(exc)}, status=HTTPStatus.CONFLICT)
                    return
                self._send_json(result)
                return

            self._not_found()

    return InnerWorldMiniappHandler


def serve_miniapp(
    root: Path,
    host: str = "127.0.0.1",
    port: int = 8421,
    domain_overlays: List[str] | None = None,
    limit: int = 12,
    api_prefixes: List[str] | None = None,
    static_dir: Path | None = None,
    refresh_on_start: bool = True,
) -> None:
    domains = domain_overlays or []
    if refresh_on_start:
        derive_graph(root, domains)
        generate_daily_batch(root, limit=max(limit, 5), domain_overlays=domains, write_feed=True)
    assets_dir = static_dir or root / "product" / "inner_world_v1" / "miniapp"
    prefixes = api_prefixes or ["/api"]
    handler = make_miniapp_handler(root, assets_dir, domains, limit, prefixes)
    server = ThreadingHTTPServer((host, port), handler)
    try:
        server.serve_forever()
    finally:
        server.server_close()
