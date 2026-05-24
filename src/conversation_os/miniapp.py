from __future__ import annotations

import hashlib
import hmac
import json
import mimetypes
import os
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List
from urllib.parse import parse_qs, urlparse

from .chat_backends import (
    apply_openclaw_model_control,
    get_openclaw_model_control_state,
    rollback_openclaw_model_control,
    stage_openclaw_agent_model,
)
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
            if not password:
                return False
            return _verify_mobile_session(self._mobile_session_cookie_value(), password)

        def _require_mobile_session(self) -> bool:
            if self._mobile_session_authenticated():
                return True
            self._send_json({"error": "auth_required"}, status=HTTPStatus.UNAUTHORIZED)
            return False

        def log_message(self, format: str, *args) -> None:  # noqa: A003
            return

        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            path = parsed.path
            api_path = _canonical_api_path(path, api_prefixes)

            if (path == "/mobile" or path.startswith("/mobile/")) and not self._require_mobile_session():
                return

            if api_path and api_path.startswith("/mobile/") and api_path not in {"/mobile/session", "/mobile/session/logout"}:
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

            if api_path and api_path.startswith("/mobile/") and api_path not in {"/mobile/session", "/mobile/session/logout"}:
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

            if api_path == "/mobile/capture":
                try:
                    result = append_mobile_capture(
                        root,
                        content=payload.get("content", ""),
                        session_id=payload.get("session_id"),
                    )
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
