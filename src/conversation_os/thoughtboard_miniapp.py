"""Thoughtboard Miniapp Server.

This module serves embeddable web components and APIs for the Thoughtboard.
"""

from __future__ import annotations

import json
import mimetypes
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import List
from urllib.parse import urlparse

from .storage import make_id
from .product_thoughtboard import (
    build_thoughtboard_feed,
    ingest_pasted_conversation,
    save_thoughtboard_card,
    delete_thoughtboard_card,
)

MODULE_ID = "surface.thoughtboard.thoughtboard_miniapp"
CONTRACT_VERSION = "1.0"
PUBLIC_API = (
    "MODULE_ID",
    "CONTRACT_VERSION",
    "make_thoughtboard_handler",
    "serve_thoughtboard_miniapp",
)
__all__ = list(PUBLIC_API)


def _read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    if length <= 0:
        return {}
    payload = handler.rfile.read(length)
    if not payload:
        return {}
    return json.loads(payload.decode("utf-8"))


def _embed_js_payload() -> str:
    return """
class ThoughtBoardElement extends HTMLElement {
  constructor() {
    super();
    this.attachShadow({ mode: 'open' });
    this.activeLayout = 'masonry';
  }

  static get observedAttributes() {
    return ['layout', 'api-host'];
  }

  attributeChangedCallback(name, oldValue, newValue) {
    if (name === 'layout' && newValue) {
      this.activeLayout = newValue;
    }
    this.render();
  }

  connectedCallback() {
    this.render();
  }

  async fetchFeed() {
    const host = this.getAttribute('api-host') || '';
    try {
      const response = await fetch(`${host}/api/thoughtboard/feed`);
      if (!response.ok) throw new Error('Failed to load feed');
      return await response.json();
    } catch (e) {
      console.error(e);
      return null;
    }
  }

  async render() {
    const layout = this.getAttribute('layout') || this.activeLayout || 'masonry';
    const data = await this.fetchFeed();
    
    if (!data) {
      this.shadowRoot.innerHTML = `<div class="error">Failed to load Thoughtboard data.</div>`;
      return;
    }

    // Collect all unique tags for filter header
    const allTags = new Set();
    data.cards.forEach(card => {
      (card.tags || []).forEach(t => allTags.add(t));
    });

    const filterTagsHtml = Array.from(allTags).map(t => 
      `<span class="filter-tag" data-tag="${t}">#${t}</span>`
    ).join('');

    const cardsHtml = data.cards.map(card => {
      const tagsHtml = (card.tags || []).map(t => `<span class="tag">#${t}</span>`).join(' ');
      const mediaHtml = (card.media_refs || []).map(m => `<img class="media" src="${m}" alt="moodboard visual"/>`).join('');
      
      // Classify card type based on tags
      let cardClass = 'card';
      let typeLabel = '';
      if (card.tags && card.tags.includes('tension')) {
        cardClass += ' card-tension';
        typeLabel = '<span class="type-badge badge-tension">Tension</span>';
      } else if (card.tags && card.tags.includes('chatbot-discussion')) {
        cardClass += ' card-chat';
        typeLabel = '<span class="type-badge badge-chat">Chat</span>';
      } else if (card.tags && card.tags.includes('stabilized')) {
        cardClass += ' card-stable';
        typeLabel = '<span class="type-badge badge-stable">Tenet</span>';
      }
      
      const serializedTags = JSON.stringify(card.tags || []);
      
      return `
        <div class="${cardClass} card-depth" data-tags='${serializedTags}'>
          ${mediaHtml}
          <div class="card-content">
            <div class="card-header-row">
              <h3 class="card-title">${this.escapeHtml(card.title)}</h3>
              ${typeLabel}
            </div>
            <p class="card-summary">${this.escapeHtml(card.summary).replace(/\\n/g, '<br>')}</p>
            <div class="card-footer">
              <span class="date">${new Date(card.created_at).toLocaleDateString()}</span>
              <div class="tags">${tagsHtml}</div>
            </div>
          </div>
        </div>
      `;
    }).join('');

    this.shadowRoot.innerHTML = `
      <style>
        :host {
          display: block;
          font-family: system-ui, -apple-system, sans-serif;
          color: #f3f4f6;
          background: var(--host-bg, #090d16);
          padding: 2rem;
          border-radius: 1.5rem;
          transition: background 0.5s ease-in-out;
          
          /* Dynamic Internal State Variables */
          --state-opacity: 0.7;
          --state-blur: 12px;
          --state-border-radius: 0.75rem;
          --state-border-color: rgba(255, 255, 255, 0.08);
          --state-shadow-offset: 0px;
          --accent-primary: #818cf8;
          --accent-secondary: #a78bfa;
          --card-bg: rgba(30, 41, 59, var(--state-opacity));
        }
        
        .container {
          max-width: 1200px;
          margin: 0 auto;
        }

        .thoughtboard-header {
          display: flex;
          flex-direction: column;
          gap: 1rem;
          margin-bottom: 2.5rem;
          border-bottom: 1px solid rgba(255, 255, 255, 0.05);
          padding-bottom: 1.5rem;
        }

        .header-top {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 1rem;
        }

        h2 {
          font-size: 2.25rem;
          font-weight: 800;
          margin: 0;
          background: linear-gradient(to right, var(--accent-primary), var(--accent-secondary));
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          transition: background 0.3s;
        }

        /* State Simulator Panel */
        .state-controller {
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          padding: 0.75rem 1rem;
          border-radius: 0.75rem;
          display: flex;
          align-items: center;
          flex-wrap: wrap;
          gap: 0.75rem;
          font-size: 0.85rem;
        }

        .controller-title {
          font-weight: 600;
          color: #94a3b8;
        }

        .state-btn {
          background: rgba(255, 255, 255, 0.05);
          border: 1px solid rgba(255, 255, 255, 0.05);
          color: #94a3b8;
          padding: 0.3rem 0.75rem;
          border-radius: 0.5rem;
          cursor: pointer;
          font-weight: 500;
          transition: all 0.2s;
        }

        .state-btn:hover {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
        }

        .state-btn.active {
          background: var(--accent-primary);
          color: #ffffff;
          border-color: transparent;
          box-shadow: 0 0 10px rgba(129, 140, 248, 0.3);
        }

        /* Toolbar & Controls */
        .controls-row {
          display: flex;
          justify-content: space-between;
          align-items: center;
          flex-wrap: wrap;
          gap: 1rem;
        }

        .layout-selector {
          display: flex;
          background: rgba(255, 255, 255, 0.04);
          padding: 0.25rem;
          border-radius: 0.5rem;
          border: 1px solid rgba(255, 255, 255, 0.04);
        }

        .layout-btn {
          background: transparent;
          border: none;
          color: #94a3b8;
          padding: 0.4rem 0.8rem;
          font-size: 0.85rem;
          border-radius: 0.35rem;
          cursor: pointer;
          font-weight: 600;
          transition: all 0.2s;
        }

        .layout-btn.active {
          background: rgba(255, 255, 255, 0.1);
          color: #ffffff;
        }

        /* Filter tags */
        .filter-tags {
          display: flex;
          gap: 0.5rem;
          flex-wrap: wrap;
        }

        .filter-tag {
          font-size: 0.8rem;
          padding: 0.25rem 0.6rem;
          border-radius: 0.35rem;
          background: rgba(255, 255, 255, 0.03);
          border: 1px solid rgba(255, 255, 255, 0.05);
          color: #64748b;
          cursor: pointer;
          transition: all 0.2s;
          font-weight: 500;
        }

        .filter-tag:hover, .filter-tag.active {
          background: rgba(129, 140, 248, 0.1);
          border-color: var(--accent-primary);
          color: var(--accent-primary);
        }

        .error {
          color: #ef4444;
          padding: 1rem;
          border: 1px dashed #ef4444;
          border-radius: 0.5rem;
        }

        /* Masonry Layout */
        .masonry {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
          gap: var(--grid-gap, 1.5rem);
        }

        /* Feed Layout */
        .feed {
          display: flex;
          flex-direction: column;
          gap: var(--grid-gap, 1.5rem);
          max-width: 800px;
          margin: 0 auto;
        }

        /* Glassmorphic Cards */
        .card {
          background: var(--card-bg);
          backdrop-filter: blur(var(--state-blur));
          -webkit-backdrop-filter: blur(var(--state-blur));
          border: 1px solid var(--state-border-color);
          border-radius: var(--state-border-radius);
          overflow: hidden;
          transition: transform 0.3s cubic-bezier(0.16, 1, 0.3, 1), 
                      box-shadow 0.3s, 
                      border-color 0.3s,
                      border-radius 0.3s;
          position: relative;
          box-shadow: var(--state-shadow-offset) var(--state-shadow-offset) 0px rgba(239, 68, 68, 0.3);
        }

        .card:hover {
          transform: translateY(-4px);
          box-shadow: calc(var(--state-shadow-offset) + 2px) calc(var(--state-shadow-offset) + 2px) 0px rgba(239, 68, 68, 0.5), 
                      0 12px 30px rgba(0, 0, 0, 0.4);
          border-color: rgba(255, 255, 255, 0.2);
        }

        /* Distinct Card Types */
        .card-tension {
          border-left: 4px solid #ef4444;
        }

        .card-chat {
          border-left: 4px solid #3b82f6;
        }

        .card-stable {
          border-left: 4px solid #10b981;
        }

        .card-header-row {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: 0.75rem;
          gap: 0.5rem;
        }

        .type-badge {
          font-size: 0.7rem;
          padding: 0.15rem 0.4rem;
          border-radius: 0.25rem;
          font-weight: 700;
          text-transform: uppercase;
        }

        .badge-tension { background: rgba(239, 68, 68, 0.15); color: #f87171; }
        .badge-chat { background: rgba(59, 130, 246, 0.15); color: #60a5fa; }
        .badge-stable { background: rgba(16, 185, 129, 0.15); color: #34d399; }

        .media {
          width: 100%;
          height: 180px;
          object-fit: cover;
          border-bottom: 1px solid var(--state-border-color);
        }

        .card-content {
          padding: 1.25rem;
        }

        .card-title {
          margin: 0;
          font-size: 1.15rem;
          color: #ffffff;
          font-weight: 700;
          line-height: 1.4;
        }

        .card-summary {
          margin: 0.75rem 0 1.25rem 0;
          font-size: 0.95rem;
          line-height: 1.6;
          color: #cbd5e1;
        }

        .card-footer {
          display: flex;
          justify-content: space-between;
          align-items: center;
          font-size: 0.8rem;
          color: #64748b;
          border-top: 1px solid rgba(255, 255, 255, 0.05);
          padding-top: 0.75rem;
        }

        .tags {
          display: flex;
          gap: 0.4rem;
          flex-wrap: wrap;
        }

        .tag {
          color: var(--accent-primary);
          font-weight: 600;
        }
      </style>
      
      <div class="container">
        <div class="thoughtboard-header">
          <div class="header-top">
            <h2>Thoughtboard Surface</h2>
            
            <div class="state-controller">
              <span class="controller-title">🧠 State Matcher:</span>
              <button class="state-btn active" data-state="default">Standard</button>
              <button class="state-btn" data-state="fluidity">Fluidity</button>
              <button class="state-btn" data-state="tension">Tension</button>
              <button class="state-btn" data-state="permanence">Permanence</button>
            </div>
          </div>
          
          <div class="controls-row">
            <div class="filter-tags">
              <span class="filter-tag active" data-tag="all">All Thoughts</span>
              ${filterTagsHtml}
            </div>
            
            <div class="layout-selector">
              <button class="layout-btn ${layout === 'masonry' ? 'active' : ''}" data-layout="masonry">Masonry</button>
              <button class="layout-btn ${layout === 'feed' ? 'active' : ''}" data-layout="feed">Timeline</button>
            </div>
          </div>
        </div>

        <div class="${layout === 'feed' ? 'feed' : 'masonry'}">
          ${cardsHtml}
        </div>
      </div>
    `;

    this.bindEvents();
  }

  bindEvents() {
    const shadow = this.shadowRoot;
    
    // Layout filter
    shadow.querySelectorAll('.layout-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        shadow.querySelectorAll('.layout-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        this.setAttribute('layout', btn.dataset.layout);
      });
    });
    
    // Tag filter
    shadow.querySelectorAll('.filter-tag').forEach(tag => {
      tag.addEventListener('click', () => {
        const activeTag = tag.dataset.tag;
        shadow.querySelectorAll('.filter-tag').forEach(t => t.classList.remove('active'));
        tag.classList.add('active');
        
        shadow.querySelectorAll('.card').forEach(card => {
          if (activeTag === 'all') {
            card.style.display = 'block';
          } else {
            const cardTags = JSON.parse(card.dataset.tags || '[]');
            card.style.display = cardTags.includes(activeTag) ? 'block' : 'none';
          }
        });
      });
    });

    // State simulation controller
    shadow.querySelectorAll('.state-btn').forEach(btn => {
      btn.addEventListener('click', () => {
        shadow.querySelectorAll('.state-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        
        const state = btn.dataset.state;
        const host = this;
        
        if (state === 'fluidity') {
          host.style.setProperty('--state-opacity', '0.35');
          host.style.setProperty('--state-blur', '24px');
          host.style.setProperty('--state-border-radius', '2rem');
          host.style.setProperty('--state-border-color', 'rgba(96, 165, 250, 0.25)');
          host.style.setProperty('--state-shadow-offset', '0px');
          host.style.setProperty('--accent-primary', '#60a5fa');
          host.style.setProperty('--accent-secondary', '#38bdf8');
          host.style.setProperty('--host-bg', '#050b14');
        } else if (state === 'tension') {
          host.style.setProperty('--state-opacity', '0.85');
          host.style.setProperty('--state-blur', '0px');
          host.style.setProperty('--state-border-radius', '0.25rem');
          host.style.setProperty('--state-border-color', 'rgba(239, 68, 68, 0.5)');
          host.style.setProperty('--state-shadow-offset', '6px');
          host.style.setProperty('--accent-primary', '#f87171');
          host.style.setProperty('--accent-secondary', '#fb923c');
          host.style.setProperty('--host-bg', '#110606');
        } else if (state === 'permanence') {
          host.style.setProperty('--state-opacity', '0.95');
          host.style.setProperty('--state-blur', '4px');
          host.style.setProperty('--state-border-radius', '0.5rem');
          host.style.setProperty('--state-border-color', 'rgba(255, 255, 255, 0.2)');
          host.style.setProperty('--state-shadow-offset', '0px');
          host.style.setProperty('--accent-primary', '#10b981');
          host.style.setProperty('--accent-secondary', '#34d399');
          host.style.setProperty('--host-bg', '#020f08');
        } else {
          host.style.setProperty('--state-opacity', '0.7');
          host.style.setProperty('--state-blur', '12px');
          host.style.setProperty('--state-border-radius', '0.75rem');
          host.style.setProperty('--state-border-color', 'rgba(255, 255, 255, 0.08)');
          host.style.setProperty('--state-shadow-offset', '0px');
          host.style.setProperty('--accent-primary', '#818cf8');
          host.style.setProperty('--accent-secondary', '#a78bfa');
          host.style.setProperty('--host-bg', '#090d16');
        }
      });
    });
  }

  escapeHtml(str) {
    if (!str) return '';
    return str.replace(/&/g, '&amp;')
              .replace(/</g, '&lt;')
              .replace(/>/g, '&gt;')
              .replace(/"/g, '&quot;')
              .replace(/'/g, '&#039;');
  }
}

if (!customElements.get('thought-board')) {
  customElements.define('thought-board', ThoughtBoardElement);
}
"""


def make_thoughtboard_handler(root: Path):
    class ThoughtboardHandler(BaseHTTPRequestHandler):
        def _send_json(
            self,
            payload: dict,
            status: int = HTTPStatus.OK,
            headers: dict[str, str] | None = None,
        ) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.send_header("Cache-Control", "no-store, max-age=0")
            if headers:
                for name, val in headers.items():
                    self.send_header(name, val)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _send_text(self, content: str, content_type: str, status: int = HTTPStatus.OK) -> None:
            body = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", f"{content_type}; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_OPTIONS(self) -> None:
            self.send_response(HTTPStatus.OK)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS, DELETE")
            self.send_header("Access-Control-Allow-Headers", "Content-Type")
            self.end_headers()

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path == "/api/thoughtboard/feed":
                try:
                    feed = build_thoughtboard_feed(root)
                    self._send_json(feed)
                except Exception as e:
                    self._send_json({"error": "server_error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            elif path == "/thoughtboard/embed.js":
                self._send_text(_embed_js_payload(), "application/javascript")
            else:
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path == "/api/thoughtboard/card":
                try:
                    body = _read_json_body(self)
                    card = save_thoughtboard_card(root, body)
                    self._send_json(card)
                except Exception as e:
                    self._send_json({"error": "server_error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            elif path == "/api/thoughtboard/import":
                try:
                    body = _read_json_body(self)
                    title = body.get("title") or "Imported Chat"
                    transcript = body.get("transcript") or ""
                    if not transcript:
                        self._send_json({"error": "bad_request", "message": "Transcript is required"}, status=HTTPStatus.BAD_REQUEST)
                        return
                    result = ingest_pasted_conversation(root, title, transcript)
                    self._send_json(result)
                except Exception as e:
                    self._send_json({"error": "server_error", "message": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)
            else:
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

        def do_DELETE(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            
            if path.startswith("/api/thoughtboard/card/"):
                card_id = path.split("/")[-1]
                if delete_thoughtboard_card(root, card_id):
                    self._send_json({"success": True})
                else:
                    self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)
            else:
                self._send_json({"error": "not_found"}, status=HTTPStatus.NOT_FOUND)

    return ThoughtboardHandler


def serve_thoughtboard_miniapp(root: Path, host: str, port: int) -> None:
    handler = make_thoughtboard_handler(root)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Serving Thoughtboard Miniapp at http://{host}:{port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
