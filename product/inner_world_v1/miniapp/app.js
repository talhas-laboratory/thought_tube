const state = {
  feed: [],
  runtime: null,
  linkingOverview: null,
  linkingQuery: "",
  linkingError: null,
  selectedOceanNodeRef: null,
  selectedOceanEdgeId: null,
  governanceBusy: false,
  activeThoughtId: null,
  thoughtDetails: {},
  loadingThoughtId: null,
  detailErrors: {},
};

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("apiBase");
  const fromConfig = window.INNER_WORLD_CONFIG?.apiBaseUrl;
  const value = (fromQuery || fromConfig || "/api").trim();
  if (!value) {
    return "/api";
  }
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

const API_BASE = resolveApiBase();

function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

const refreshButtonEl = document.querySelector("#refresh-feed");
const runtimeBadgesEl = document.querySelector("#runtime-badges");
const systemSnapshotEl = document.querySelector("#system-snapshot");
const feedStatusEl = document.querySelector("#feed-status");
const feedEl = document.querySelector("#feed");

async function fetchJSON(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  if (!response.ok) {
    const errorPayload = await response.json().catch(() => ({}));
    throw new Error(errorPayload.error || `Request failed: ${response.status}`);
  }
  return response.json();
}

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function formatInline(text) {
  return escapeHtml(text)
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>");
}

function renderMarkdown(markdown) {
  const lines = String(markdown || "").split("\n");
  let html = "";
  let inList = false;

  const closeList = () => {
    if (inList) {
      html += "</ul>";
      inList = false;
    }
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();
    if (!line) {
      closeList();
      continue;
    }
    if (line.startsWith("# ")) {
      closeList();
      html += `<h1>${formatInline(line.slice(2))}</h1>`;
      continue;
    }
    if (line.startsWith("## ")) {
      closeList();
      html += `<h2>${formatInline(line.slice(3))}</h2>`;
      continue;
    }
    if (line.startsWith("### ")) {
      closeList();
      html += `<h3>${formatInline(line.slice(4))}</h3>`;
      continue;
    }
    if (line.startsWith("- ")) {
      if (!inList) {
        html += "<ul>";
        inList = true;
      }
      html += `<li>${formatInline(line.slice(2))}</li>`;
      continue;
    }
    closeList();
    html += `<p>${formatInline(line)}</p>`;
  }

  closeList();
  return html;
}

function shortPath(value) {
  const segments = String(value || "").split("/").filter(Boolean);
  return segments.slice(-2).join("/") || value || "";
}

function sourceFamilyFromRef(ref) {
  const text = String(ref || "");
  if (text.includes("/chat_converter/") || text.includes("/apps/chat_converter/")) {
    return "chat converter";
  }
  if (text.includes("/thought-tube/") || text.includes("/.thought-tube/")) {
    return "thought tube";
  }
  if (text.includes("/.openclaw/")) {
    return "openclaw";
  }
  return "vault";
}

function titleCaseLabel(value) {
  return String(value || "")
    .replaceAll("_", " ")
    .replaceAll("-", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function metricPill(label, value) {
  return `
    <span class="metric-pill">
      <span>${escapeHtml(label)}</span>
      <strong>${escapeHtml(value)}</strong>
    </span>
  `;
}

function statusChip(label, tone = "") {
  return `<span class="status-chip${tone ? ` status-chip--${tone}` : ""}">${escapeHtml(label)}</span>`;
}

function formatNumber(value) {
  return Number(value || 0).toLocaleString();
}

function formatConfidence(value) {
  return Number(value || 0).toFixed(2);
}

function capsuleTone(kind) {
  if (kind === "concept") {
    return "var(--grounded)";
  }
  if (kind === "bubble") {
    return "var(--current)";
  }
  if (kind === "thread_abstraction") {
    return "var(--signal)";
  }
  return "var(--muted-strong)";
}

function capsuleLabel(kind) {
  return titleCaseLabel(kind || "capsule");
}

function pipelineTone(status) {
  if (status === "completed" || status === "succeeded") {
    return "grounded";
  }
  if (status === "running" || status === "resume") {
    return "live";
  }
  if (status === "failed") {
    return "danger";
  }
  return "speculative";
}

function pipelineSummaryCopy(summary) {
  if (!summary) {
    return "No runtime pipeline run has been recorded yet.";
  }
  if (summary.run_status === "running") {
    return `Rebuild is currently running at ${titleCaseLabel(summary.active_stage || "unknown stage")}.`;
  }
  if (summary.run_status === "failed") {
    return `The last runtime rebuild failed after ${titleCaseLabel(summary.last_completed_stage || "startup")}.`;
  }
  if (summary.run_status === "completed" && summary.last_completed_stage === "connections") {
    return "The latest runtime rebuild completed fully, including the bounded connections surface.";
  }
  if (summary.last_completed_stage) {
    return `The latest runtime rebuild completed through ${titleCaseLabel(summary.last_completed_stage)}.`;
  }
  return "Runtime pipeline state is available but no completed stage is recorded yet.";
}

function renderPipelineStageRail(pipeline) {
  const summary = pipeline?.summary;
  const stages = (pipeline?.stages || []).filter((stage) => stage.status !== "not_selected");
  if (!summary && !stages.length) {
    return `
      <section class="overview-card overview-card--full">
        <span class="section-kicker">runtime pipeline</span>
        <p class="overview-empty">No pipeline snapshot has been written yet.</p>
      </section>
    `;
  }

  const counts = summary?.counts || {};
  return `
    <section class="overview-card overview-card--full">
      <div class="overview-head">
        <div>
          <span class="section-kicker">runtime pipeline</span>
          <h3>Rebuild state</h3>
        </div>
        <div class="chip-row">
          ${statusChip(summary?.run_status || "unknown", pipelineTone(summary?.run_status || "unknown"))}
          ${metricPill("completed", formatNumber(counts.completed || 0))}
          ${metricPill("skipped", formatNumber(counts.skipped_completed || 0))}
          ${metricPill("failed", formatNumber(counts.failed || 0))}
        </div>
      </div>
      <p class="overview-copy">${escapeHtml(pipelineSummaryCopy(summary))}</p>
      <div class="stage-rail">
        ${stages.length
          ? stages
              .map(
                (stage) => `
                  <div class="stage-pill stage-pill--${escapeHtml(stage.status || "unknown")}">
                    <strong>${escapeHtml(stage.label)}</strong>
                    <span>${escapeHtml(stage.status || "unknown")}</span>
                    <em>${escapeHtml(stage.duration_seconds != null ? `${stage.duration_seconds}s` : "pending")}</em>
                  </div>
                `
              )
              .join("")
          : `<p class="overview-empty">No stage-level runtime details are available yet.</p>`}
      </div>
    </section>
  `;
}

function renderConceptShelf(concepts) {
  return `
    <section class="overview-card">
      <div class="overview-head">
        <div>
          <span class="section-kicker">concept graph</span>
          <h3>Top concepts</h3>
        </div>
      </div>
      <div class="knowledge-grid">
        ${concepts.length
          ? concepts
              .map(
                (concept) => `
                  <article class="knowledge-card">
                    <div class="knowledge-card__head">
                      <strong>${escapeHtml(concept.label)}</strong>
                      ${statusChip(concept.status || "provisional", concept.status === "active" ? "grounded" : "speculative")}
                    </div>
                    <p>${escapeHtml(concept.transfer_shape || concept.abstract_pattern || "No transfer shape attached yet.")}</p>
                    <div class="knowledge-card__meta">
                      ${metricPill("confidence", formatConfidence(concept.confidence))}
                      ${metricPill("sources", formatNumber(concept.source_ref_count))}
                      ${metricPill("aliases", formatNumber(concept.alias_count))}
                    </div>
                  </article>
                `
              )
              .join("")
          : `<p class="overview-empty">No concept nodes have been materialized yet.</p>`}
      </div>
    </section>
  `;
}

function renderBubbleShelf(bubbles, pipelineSummary) {
  const waitingOnBubbles =
    !bubbles.length &&
    pipelineSummary &&
    pipelineSummary.last_completed_stage &&
    pipelineSummary.last_completed_stage !== "context_bubbles" &&
    pipelineSummary.last_completed_stage !== "knowledge_layer" &&
    pipelineSummary.last_completed_stage !== "connections";

  return `
    <section class="overview-card">
      <div class="overview-head">
        <div>
          <span class="section-kicker">context bubbles</span>
          <h3>Top bubbles</h3>
        </div>
      </div>
      <div class="knowledge-grid">
        ${bubbles.length
          ? bubbles
              .map(
                (bubble) => `
                  <article class="knowledge-card">
                    <div class="knowledge-card__head">
                      <strong>${escapeHtml(bubble.label)}</strong>
                      ${statusChip(bubble.status || "active", bubble.status === "active" ? "grounded" : "speculative")}
                    </div>
                    <div class="knowledge-card__meta">
                      ${metricPill("confidence", formatConfidence(bubble.confidence))}
                      ${metricPill("support", formatNumber(bubble.support_count))}
                      ${metricPill("concepts", formatNumber(bubble.concept_count))}
                    </div>
                    <div class="chip-row">
                      ${(bubble.dominant_primitives || [])
                        .map((label) => `<span class="module-chip">${escapeHtml(label)}</span>`)
                        .join("")}
                    </div>
                    <p>${escapeHtml(
                      `${formatNumber(bubble.active_tension_count)} tensions, ${formatNumber(
                        bubble.open_question_count
                      )} open questions, ${formatNumber(bubble.source_ref_count)} source refs.`
                    )}</p>
                  </article>
                `
              )
              .join("")
          : `<p class="overview-empty">${
              waitingOnBubbles
                ? "Context bubbles have not been materialized yet. The runtime rebuild has not reached that stage."
                : "No context bubbles are available yet."
            }</p>`}
      </div>
    </section>
  `;
}

function renderConnectionShelf(connections, summary) {
  const totalCount = summary?.total_connection_count || 0;
  const includedCount = summary?.included_connection_count || 0;
  const truncated = Boolean(summary?.truncated);
  return `
    <section class="overview-card">
      <div class="overview-head">
        <div>
          <span class="section-kicker">connections</span>
          <h3>Top connections</h3>
        </div>
      </div>
      <div class="knowledge-grid">
        ${connections.length
          ? connections
              .map(
                (connection) => `
                  <article class="knowledge-card">
                    <div class="knowledge-card__head">
                      <strong>${escapeHtml(titleCaseLabel(connection.kind || "relates_to"))}</strong>
                      ${statusChip(formatConfidence(connection.strength || 0), "live")}
                    </div>
                    <p>${escapeHtml(`${shortPath(connection.left_source_ref)} ↔ ${shortPath(connection.right_source_ref)}`)}</p>
                    <div class="chip-row">
                      ${(connection.shared_concepts || [])
                        .map((label) => `<span class="module-chip">${escapeHtml(label)}</span>`)
                        .join("")}
                    </div>
                  </article>
                `
              )
              .join("")
          : `<p class="overview-empty">No connection summary has been materialized yet.</p>`}
      </div>
      <p class="overview-copy">${escapeHtml(
        truncated
          ? `${formatNumber(includedCount)} of ${formatNumber(totalCount)} connections are shown in the bounded surface.`
          : `${formatNumber(totalCount)} connections are available in the current surface.`
      )}</p>
    </section>
  `;
}

function layoutOceanMap(map) {
  const width = 960;
  const height = 360;
  const laneOrder = ["concept", "bubble", "thread_abstraction", "meta"];
  const laneY = {
    concept: 74,
    bubble: 152,
    thread_abstraction: 236,
    meta: 314,
  };
  const groups = new Map();
  for (const kind of laneOrder) {
    groups.set(kind, []);
  }

  for (const node of map.nodes || []) {
    const kind = groups.has(node.kind) ? node.kind : "meta";
    groups.get(kind).push(node);
  }

  for (const rows of groups.values()) {
    rows.sort((left, right) => {
      if ((left.role || "") !== (right.role || "")) {
        return left.role === "seed" ? -1 : 1;
      }
      return Number(right.confidence || 0) - Number(left.confidence || 0);
    });
  }

  const positionedNodes = [];
  for (const kind of laneOrder) {
    const rows = groups.get(kind) || [];
    if (!rows.length) {
      continue;
    }
    const span = Math.max(1, rows.length - 1);
    rows.forEach((node, index) => {
      const x = rows.length === 1 ? width / 2 : 82 + (index * (width - 164)) / span;
      positionedNodes.push({
        ...node,
        x,
        y: laneY[kind] || laneY.meta,
        radius: node.role === "seed" ? 15 : 11,
      });
    });
  }

  const positions = new Map(positionedNodes.map((node) => [node.ref_key, node]));
  const positionedEdges = (map.edges || [])
    .map((edge) => {
      const from = positions.get(edge.from_ref);
      const to = positions.get(edge.to_ref);
      if (!from || !to) {
        return null;
      }
      return { ...edge, from, to };
    })
    .filter(Boolean);

  return { width, height, nodes: positionedNodes, edges: positionedEdges };
}

function oceanNodeDetail(linkingOverview, refKey) {
  if (!linkingOverview || !refKey) {
    return null;
  }
  const bundle = linkingOverview.retrieval_bundle || {};
  const rows = [...(bundle.seed_capsules || []), ...(bundle.related_capsules || [])];
  return rows.find((row) => `${row.ref_type}:${row.ref_id}` === refKey) || null;
}

function oceanEdgeDetail(linkingOverview, edgeId) {
  if (!linkingOverview || !edgeId) {
    return null;
  }
  const bundle = linkingOverview.retrieval_bundle || {};
  return (bundle.included_links || []).find((row) => row.link_id === edgeId) || null;
}

function renderOceanMapGraph(map) {
  const laidOut = layoutOceanMap(map);
  const laneRules = [
    { label: "concepts", y: 74 },
    { label: "bubbles", y: 152 },
    { label: "abstractions", y: 236 },
    { label: "evidence", y: 314 },
  ];

  return `
    <svg class="ocean-map-svg" viewBox="0 0 ${laidOut.width} ${laidOut.height}" role="img" aria-label="Knowledge ocean map">
      <defs>
        <linearGradient id="oceanCurrent" x1="0%" y1="0%" x2="100%" y2="0%">
          <stop offset="0%" stop-color="rgba(91, 176, 255, 0.08)" />
          <stop offset="50%" stop-color="rgba(91, 176, 255, 0.32)" />
          <stop offset="100%" stop-color="rgba(91, 176, 255, 0.08)" />
        </linearGradient>
      </defs>
      ${laneRules
        .map(
          (lane) => `
            <g class="ocean-lane">
              <line x1="36" y1="${lane.y}" x2="${laidOut.width - 36}" y2="${lane.y}" stroke="rgba(255,255,255,0.08)" stroke-dasharray="4 8" />
              <text x="36" y="${lane.y - 14}" fill="rgba(255,255,255,0.52)" font-size="11" font-family="'Geist Mono', monospace" letter-spacing="0.16em">${escapeHtml(
                lane.label.toUpperCase()
              )}</text>
            </g>
          `
        )
        .join("")}
      ${laidOut.edges
        .map((edge) => {
          const tone =
            edge.status === "rejected"
              ? "rgba(255,100,103,0.55)"
              : edge.layer === "semantic"
                ? "rgba(91,176,255,0.42)"
                : "rgba(255,255,255,0.18)";
          const width = edge.status === "promoted" ? 2.8 : 1.5;
          return `
            <line
              class="ocean-edge${state.selectedOceanEdgeId === edge.edge_id ? " is-selected" : ""}"
              data-edge-id="${escapeHtml(edge.edge_id)}"
              x1="${edge.from.x}"
              y1="${edge.from.y}"
              x2="${edge.to.x}"
              y2="${edge.to.y}"
              stroke="${tone}"
              stroke-width="${width}"
              stroke-linecap="round"
              opacity="${edge.status === "rejected" ? "0.35" : "1"}"
            />
          `;
        })
        .join("")}
      ${laidOut.nodes
        .map((node) => {
          const fill = capsuleTone(node.kind);
          const stroke = node.role === "seed" ? "rgba(255,255,255,0.72)" : "rgba(255,255,255,0.22)";
          const labelY = node.y + node.radius + 18;
          return `
            <g class="ocean-node ocean-node--${escapeHtml(node.kind || "meta")}${state.selectedOceanNodeRef === node.ref_key ? " is-selected" : ""}" data-node-ref="${escapeHtml(node.ref_key)}">
              <circle cx="${node.x}" cy="${node.y}" r="${node.radius + 9}" fill="${fill}" opacity="0.08" />
              <circle cx="${node.x}" cy="${node.y}" r="${node.radius}" fill="${fill}" stroke="${stroke}" stroke-width="1.5" />
              <text x="${node.x}" y="${labelY}" text-anchor="middle" fill="rgba(255,255,255,0.92)" font-size="12" font-weight="600">${escapeHtml(
                String(node.label || "").slice(0, 24)
              )}</text>
              <text x="${node.x}" y="${labelY + 16}" text-anchor="middle" fill="rgba(255,255,255,0.48)" font-size="10" font-family="'Geist Mono', monospace">${escapeHtml(
                capsuleLabel(node.kind)
              )}</text>
            </g>
          `;
        })
        .join("")}
    </svg>
  `;
}

function renderOceanMapPanel(linkingOverview) {
  if (!linkingOverview) {
    return `
      <section class="overview-card overview-card--full ocean-map-card">
        <div class="ocean-map-empty">Knowledge ocean map is not available yet.</div>
      </section>
    `;
  }

  const map = linkingOverview.ocean_map || { nodes: [], edges: [], alias_hits: [] };
  const query = state.linkingQuery || "";
  const focusLabel = map.mode === "focused" ? "focused current" : "ambient current";
  const topNodes = (map.nodes || []).slice(0, 5);
  const strongestEdges = (map.edges || []).slice(0, 4);
  const selectedNode = oceanNodeDetail(linkingOverview, state.selectedOceanNodeRef);
  const selectedEdge = oceanEdgeDetail(linkingOverview, state.selectedOceanEdgeId);

  const inspector = selectedEdge
    ? `
      <section class="ocean-map-section ocean-map-section--inspector">
        <span class="section-kicker">selected current</span>
        <div class="ocean-map-inspector">
          <strong>${escapeHtml(titleCaseLabel(selectedEdge.kind || "link"))}</strong>
          <p>${escapeHtml(`${selectedEdge.from_ref_type}:${selectedEdge.from_ref_id} → ${selectedEdge.to_ref_type}:${selectedEdge.to_ref_id}`)}</p>
          <div class="chip-row">
            ${statusChip(selectedEdge.status || "provisional", selectedEdge.status === "promoted" ? "grounded" : selectedEdge.status === "rejected" ? "danger" : "live")}
            ${metricPill("confidence", formatConfidence(selectedEdge.confidence))}
            ${metricPill("evidence", formatNumber((selectedEdge.evidence_refs || []).length))}
          </div>
          <div class="chip-row ocean-map-actions">
            <button class="feedback-button" type="button" data-action="govern-edge" data-edge-id="${escapeHtml(selectedEdge.link_id)}" data-status="promoted"${
              state.governanceBusy ? " disabled" : ""
            }>Promote</button>
            <button class="feedback-button" type="button" data-action="govern-edge" data-edge-id="${escapeHtml(selectedEdge.link_id)}" data-status="downweighted"${
              state.governanceBusy ? " disabled" : ""
            }>Downweight</button>
            <button class="feedback-button feedback-button--danger" type="button" data-action="govern-edge" data-edge-id="${escapeHtml(selectedEdge.link_id)}" data-status="rejected"${
              state.governanceBusy ? " disabled" : ""
            }>Reject</button>
          </div>
          <div class="source-ref-list">
            ${(selectedEdge.evidence_refs || []).slice(0, 6).map((ref) => `<code>${escapeHtml(shortPath(ref))}</code>`).join("")}
          </div>
        </div>
      </section>
    `
    : selectedNode
      ? `
        <section class="ocean-map-section ocean-map-section--inspector">
          <span class="section-kicker">selected island</span>
          <div class="ocean-map-inspector">
            <strong>${escapeHtml(selectedNode.label || "semantic capsule")}</strong>
            <p>${escapeHtml(selectedNode.summary || "No summary attached yet.")}</p>
            <div class="chip-row">
              ${statusChip(selectedNode.status || "provisional", selectedNode.status === "active" ? "grounded" : "speculative")}
              ${metricPill("confidence", formatConfidence(selectedNode.confidence))}
              ${metricPill("sources", formatNumber((selectedNode.source_refs || []).length))}
              ${metricPill("linked", formatNumber((selectedNode.linked_ref_ids || []).length))}
            </div>
            <div class="chip-row ocean-map-actions">
              <button class="feedback-button" type="button" data-action="alias-node" data-ref-type="${escapeHtml(selectedNode.ref_type)}" data-ref-id="${escapeHtml(selectedNode.ref_id)}"${
                state.governanceBusy ? " disabled" : ""
              }>Add alias</button>
              <button class="feedback-button" type="button" data-action="focus-node" data-node-label="${escapeHtml(selectedNode.label || "")}">Focus this region</button>
            </div>
            <div class="source-ref-list">
              ${(selectedNode.source_refs || []).slice(0, 6).map((ref) => `<code>${escapeHtml(shortPath(ref))}</code>`).join("")}
            </div>
          </div>
        </section>
      `
      : `
        <section class="ocean-map-section ocean-map-section--inspector">
          <span class="section-kicker">inspection</span>
          <div class="ocean-map-inspector ocean-map-inspector--empty">
            <p>Click an island or a current to inspect it and steer the field directly from the map.</p>
          </div>
        </section>
      `;

  return `
    <section class="overview-card overview-card--full ocean-map-card">
      <div class="overview-head ocean-map-head">
        <div>
          <span class="section-kicker">knowledge ocean</span>
          <h3>Live ocean map</h3>
          <p class="overview-copy">A lightweight view of the strongest semantic islands and currents. Use it to see where the system is currently clustering meaning.</p>
        </div>
        <div class="chip-row">
          ${statusChip(focusLabel, map.mode === "focused" ? "live" : "speculative")}
          ${metricPill("nodes", formatNumber(map.node_count || 0))}
          ${metricPill("currents", formatNumber(map.edge_count || 0))}
          ${metricPill("sources", formatNumber(map.source_ref_count || 0))}
        </div>
      </div>
      <form class="ocean-map-form" data-action="linking-query">
        <input
          class="ocean-map-input"
          type="text"
          name="linking-query"
          value="${escapeHtml(query)}"
          placeholder="Focus the ocean: signal membrane, context routing, ambiguity before structure..."
        />
        <button class="refresh-button" type="submit">Focus</button>
        <button class="refresh-button refresh-button--ghost" type="button" data-action="clear-linking-query">Clear</button>
      </form>
      ${
        state.linkingError
          ? `<p class="overview-empty ocean-map-error">${escapeHtml(state.linkingError)}</p>`
          : ""
      }
      <div class="ocean-map-shell">
        <div class="ocean-map-canvas">
          ${renderOceanMapGraph(map)}
        </div>
        <aside class="ocean-map-sidebar">
          <section class="ocean-map-section">
            <span class="section-kicker">main pull</span>
            <div class="ocean-map-list">
              ${
                topNodes.length
                  ? topNodes
                      .map(
                        (node) => `
                          <div class="ocean-map-item">
                            <strong>${escapeHtml(node.label)}</strong>
                            <span>${escapeHtml(capsuleLabel(node.kind))} • ${escapeHtml(node.role || "related")}</span>
                          </div>
                        `
                      )
                      .join("")
                  : `<p class="overview-empty">No capsule nodes are available in this view.</p>`
              }
            </div>
          </section>
          <section class="ocean-map-section">
            <span class="section-kicker">strongest currents</span>
            <div class="ocean-map-list">
              ${
                strongestEdges.length
                  ? strongestEdges
                      .map(
                        (edge) => `
                          <div class="ocean-map-item">
                            <strong>${escapeHtml(titleCaseLabel(edge.kind || "link"))}</strong>
                            <span>${escapeHtml(`${edge.from_ref.split(":").slice(1).join(":")} → ${edge.to_ref.split(":").slice(1).join(":")}`)}</span>
                          </div>
                        `
                      )
                      .join("")
                  : `<p class="overview-empty">No currents are visible yet.</p>`
              }
            </div>
          </section>
          ${
            (map.alias_hits || []).length
              ? `
                <section class="ocean-map-section">
                  <span class="section-kicker">alias hits</span>
                  <div class="chip-row">
                    ${map.alias_hits.map((item) => `<span class="module-chip">${escapeHtml(item.alias_text)}</span>`).join("")}
                  </div>
                </section>
              `
              : ""
          }
          ${inspector}
        </aside>
      </div>
    </section>
  `;
}

function monogram(thought) {
  const text = thought.reasoning_primitive || thought.title || "IW";
  return text
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0])
    .join("")
    .toUpperCase();
}

function thoughtById(thoughtId) {
  return state.feed.find((thought) => thought.thought_id === thoughtId) || null;
}

function renderRuntimeSnapshot() {
  if (!state.runtime) {
    runtimeBadgesEl.innerHTML = metricPill("status", "runtime offline");
    systemSnapshotEl.innerHTML = `
      <div class="snapshot-strip snapshot-strip--offline">
        <p class="snapshot-copy">Runtime state is unavailable. The feed can still render if the API responds.</p>
      </div>
    `;
    return;
  }

  const counts = state.runtime.counts || {};
  const sourceFamilies = state.runtime.source_families || [];
  const metaLayer = state.runtime.meta_layer || [];
  const pipeline = state.runtime.pipeline || {};
  const topConcepts = state.runtime.top_concepts || [];
  const topBubbles = state.runtime.top_bubbles || [];
  const topConnections = state.runtime.top_connections || [];
  const connectionSummary = state.runtime.connection_summary || {};
  const liveThoughts = state.runtime.feed?.count || state.feed.length || 0;

  runtimeBadgesEl.innerHTML = [
    metricPill("live", `${liveThoughts} posts`),
    metricPill("chunks", formatNumber(counts.chunks || 0)),
    metricPill("concepts", formatNumber(counts.concept_nodes || 0)),
    metricPill("bubbles", formatNumber(counts.context_bubbles || 0)),
    metricPill("graph", formatNumber(counts.knowledge_edges || 0)),
    metricPill("connections", formatNumber(counts.connections || 0)),
    metricPill("review", formatNumber(counts.review_queue || 0)),
  ].join("");

  systemSnapshotEl.innerHTML = `
    <div class="snapshot-strip">
      <p class="snapshot-copy">${escapeHtml(
        `${formatNumber(counts.sources || 0)} sources, ${formatNumber(counts.analysis_units || 0)} analysis units, ${formatNumber(
          counts.conversation_threads || 0
        )} threads, ${formatNumber(counts.thread_abstractions || 0)} abstractions, ${formatNumber(
          counts.knowledge_nodes || 0
        )} knowledge nodes.`
      )}</p>
      <div class="tag-cloud">
        ${sourceFamilies
          .map((item) => `<span class="cloud-pill">${escapeHtml(titleCaseLabel(item.label))} <strong>${escapeHtml(item.count)}</strong></span>`)
          .join("")}
        ${metaLayer
          .map((item) => `<span class="cloud-pill cloud-pill--muted">${escapeHtml(titleCaseLabel(item.label))} <strong>${escapeHtml(item.count)}</strong></span>`)
          .join("")}
      </div>
    </div>
    <div class="overview-grid">
      ${renderPipelineStageRail(pipeline)}
      ${renderOceanMapPanel(state.linkingOverview)}
      ${renderConceptShelf(topConcepts)}
      ${renderBubbleShelf(topBubbles, pipeline.summary)}
      ${renderConnectionShelf(topConnections, connectionSummary)}
    </div>
  `;
}

function renderFeedStatus() {
  const groundedCount = state.feed.filter((thought) => thought.evidence_status === "grounded").length;
  const expanded = state.activeThoughtId ? "1 expanded" : "all collapsed";
  feedStatusEl.innerHTML = [
    metricPill("timeline", `${state.feed.length} posts`),
    metricPill("grounded", groundedCount),
    metricPill("mode", expanded),
  ].join("");
}

function renderDiagnostics(thought, detail) {
  const sourceSnippets = detail?.source_snippets || [];
  const threads = detail?.threads || [];
  const articleThought = detail?.thought || thought;
  const primitive = detail?.primitive || {
    label: thought.reasoning_primitive || "thought packet",
    plugin_id: thought.reasoning_primitive || "thought pipeline",
  };

  return `
    <aside class="diagnostics-card">
      <div class="diagnostics-header">
        <div>
          <p class="eyebrow">system diagnostics</p>
          <h3>Assessment surface</h3>
        </div>
        <div class="diagnostics-actions">
          <button class="feedback-button" type="button" data-feedback="relevant">Relevant</button>
          <button class="feedback-button" type="button" data-feedback="revisit_later">Revisit</button>
          <button class="feedback-button feedback-button--danger" type="button" data-feedback="dismiss">Dismiss</button>
        </div>
      </div>

      <div class="diagnostics-grid">
        ${[
          ["confidence", Number(articleThought.confidence_score || 0).toFixed(2)],
          ["relevance", Number(articleThought.relevance_score || 0).toFixed(2)],
          ["novelty", Number(articleThought.novelty_score || 0).toFixed(2)],
          ["sources", articleThought.source_refs?.length || 0],
        ]
          .map(
            ([label, value]) => `
              <div class="diagnostics-metric">
                <strong>${escapeHtml(value)}</strong>
                <span>${escapeHtml(label)}</span>
              </div>
            `
          )
          .join("")}
      </div>

      <section class="diagnostics-section">
        <span class="section-kicker">status</span>
        <div class="chip-row">
          ${statusChip(articleThought.evidence_status, articleThought.evidence_status === "grounded" ? "grounded" : "speculative")}
          ${statusChip(articleThought.feedback_state || "pending")}
          ${statusChip(articleThought.review_status || "review")}
        </div>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">why surfaced</span>
        <p>${escapeHtml(articleThought.what_changed || "No surfacing explanation attached.")}</p>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">next move</span>
        <p>${escapeHtml(articleThought.next_action || "No next move recorded.")}</p>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">generation</span>
        <div class="meta-list">
          <div><span>primitive</span><strong>${escapeHtml(primitive.label)}</strong></div>
          <div><span>pipeline</span><strong>${escapeHtml(primitive.plugin_id || articleThought.reasoning_pipeline || "thought pipeline")}</strong></div>
          <div><span>profile</span><strong>${escapeHtml(articleThought.article_profile || "default")}</strong></div>
          <div><span>threads</span><strong>${escapeHtml(threads.length)}</strong></div>
        </div>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">module order</span>
        <div class="chip-row">
          ${(articleThought.article_module_order || []).map((moduleId) => `<span class="module-chip">${escapeHtml(moduleId)}</span>`).join("")}
        </div>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">source refs</span>
        <div class="source-ref-list">
          ${(articleThought.source_refs || [])
            .map((ref) => `<code>${escapeHtml(shortPath(ref))}</code>`)
            .join("")}
        </div>
      </section>

      <section class="diagnostics-section">
        <span class="section-kicker">supporting fragments</span>
        <div class="fragment-list">
          ${
            sourceSnippets.length
              ? sourceSnippets
                  .map(
                    (snippet) => `
                      <div class="fragment-card">
                        <strong>${escapeHtml(snippet.title)}</strong>
                        <p>${escapeHtml(snippet.excerpt)}</p>
                        <span>${escapeHtml(sourceFamilyFromRef(snippet.source_ref))} • ${escapeHtml(shortPath(snippet.source_ref))}</span>
                      </div>
                    `
                  )
                  .join("")
              : `<div class="fragment-card fragment-card--empty"><p>No source excerpts attached yet.</p></div>`
          }
        </div>
      </section>
    </aside>
  `;
}

function renderExpanded(thought) {
  const isLoading = state.loadingThoughtId === thought.thought_id;
  const error = state.detailErrors[thought.thought_id];
  const detail = state.thoughtDetails[thought.thought_id];

  if (error) {
    return `
      <div class="post-expanded">
        <section class="article-card article-card--empty">
          <p>Unable to load the full article for this post.</p>
        </section>
        <aside class="diagnostics-card diagnostics-card--empty">
          <p>${escapeHtml(error)}</p>
        </aside>
      </div>
    `;
  }

  if (isLoading && !detail) {
    return `
      <div class="post-expanded">
        <section class="article-card article-card--loading">
          <div class="skeleton skeleton--title"></div>
          <div class="skeleton"></div>
          <div class="skeleton"></div>
          <div class="skeleton skeleton--wide"></div>
        </section>
        <aside class="diagnostics-card diagnostics-card--loading">
          <div class="skeleton skeleton--title"></div>
          <div class="skeleton"></div>
          <div class="skeleton"></div>
          <div class="skeleton skeleton--wide"></div>
        </aside>
      </div>
    `;
  }

  if (!detail) {
    return "";
  }

  return `
    <div class="post-expanded">
      <section class="article-card">
        <div class="article-text">${renderMarkdown(detail.thought.article_markdown)}</div>
      </section>
      ${renderDiagnostics(thought, detail)}
    </div>
  `;
}

function renderPost(thought) {
  const isActive = thought.thought_id === state.activeThoughtId;
  const activeClass = isActive ? " is-active" : "";

  return `
    <article class="post${activeClass}" data-thought-id="${escapeHtml(thought.thought_id)}">
      <div class="post-summary" data-action="toggle-post" tabindex="0" role="button" aria-expanded="${isActive ? "true" : "false"}">
        <div class="post-avatar">${escapeHtml(monogram(thought))}</div>
        <div class="post-body">
          <div class="post-headline">
            <div class="post-author-row">
              <span class="post-author">Inner World</span>
              <span class="post-handle">@substrate</span>
            </div>
          </div>
          <p class="post-copy">${escapeHtml(thought.short_text)}</p>
        </div>
      </div>
      ${isActive ? renderExpanded(thought) : ""}
    </article>
  `;
}

function renderFeed() {
  if (!state.feed.length) {
    feedEl.innerHTML = `<div class="empty-feed">No thoughts are available yet.</div>`;
    return;
  }
  feedEl.innerHTML = state.feed.map((thought) => renderPost(thought)).join("");
}

function renderApp() {
  renderRuntimeSnapshot();
  renderFeedStatus();
  renderFeed();
}

async function loadRuntimeState() {
  try {
    state.runtime = await fetchJSON(apiUrl("/runtime-overview"));
  } catch (primaryError) {
    state.runtime = await fetchJSON(apiUrl("/state"));
  }
}

async function loadLinkingOverview(query = state.linkingQuery) {
  const params = new URLSearchParams();
  params.set("limit", "10");
  params.set("neighbor_limit", "6");
  if (query) {
    params.set("query", query);
  }
  state.linkingError = null;
  state.linkingOverview = await fetchJSON(apiUrl(`/linking-overview?${params.toString()}`));
}

async function governOceanEdge(edgeId, governanceStatus) {
  state.governanceBusy = true;
  renderRuntimeSnapshot();
  try {
    await fetchJSON(apiUrl("/link-governance/link"), {
      method: "POST",
      body: JSON.stringify({
        link_id: edgeId,
        governance_status: governanceStatus,
        notes: `Governed from ocean map as ${governanceStatus}.`,
      }),
    });
    await loadLinkingOverview(state.linkingQuery);
  } catch (error) {
    state.linkingError = error.message || "Unable to govern the selected current.";
  } finally {
    state.governanceBusy = false;
    renderRuntimeSnapshot();
  }
}

async function aliasOceanNode(refType, refId) {
  const aliasText = window.prompt("Add an alias for this island");
  if (!aliasText || !aliasText.trim()) {
    return;
  }
  state.governanceBusy = true;
  renderRuntimeSnapshot();
  try {
    await fetchJSON(apiUrl("/link-governance/alias"), {
      method: "POST",
      body: JSON.stringify({
        alias_text: aliasText.trim(),
        ref_type: refType,
        ref_id: refId,
        notes: "Added from ocean map.",
      }),
    });
    await loadLinkingOverview(state.linkingQuery);
  } catch (error) {
    state.linkingError = error.message || "Unable to add alias for this island.";
  } finally {
    state.governanceBusy = false;
    renderRuntimeSnapshot();
  }
}

async function loadFeed() {
  const payload = await fetchJSON(apiUrl("/feed"));
  state.feed = payload.thoughts || [];
  if (state.activeThoughtId && !state.feed.some((thought) => thought.thought_id === state.activeThoughtId)) {
    state.activeThoughtId = null;
  }
}

async function ensureThoughtDetail(thoughtId) {
  if (state.thoughtDetails[thoughtId]) {
    return state.thoughtDetails[thoughtId];
  }
  state.loadingThoughtId = thoughtId;
  state.detailErrors[thoughtId] = null;
  renderFeed();
  try {
    const detail = await fetchJSON(apiUrl(`/thought/${encodeURIComponent(thoughtId)}`));
    state.thoughtDetails[thoughtId] = detail;
    return detail;
  } catch (error) {
    state.detailErrors[thoughtId] = error.message || "Failed to load thought detail.";
    throw error;
  } finally {
    state.loadingThoughtId = null;
  }
}

async function toggleThought(thoughtId) {
  if (state.activeThoughtId === thoughtId) {
    state.activeThoughtId = null;
    renderFeed();
    return;
  }
  state.activeThoughtId = thoughtId;
  renderFeed();
  try {
    await ensureThoughtDetail(thoughtId);
  } catch (error) {
    console.error(error);
  }
  renderFeed();
}

async function refreshCollections() {
  await Promise.all([loadRuntimeState(), loadFeed(), loadLinkingOverview(state.linkingQuery)]);
  renderApp();
  if (state.activeThoughtId) {
    delete state.thoughtDetails[state.activeThoughtId];
    await ensureThoughtDetail(state.activeThoughtId).catch((error) => console.error(error));
    renderFeed();
  }
}

async function sendFeedback(feedbackState, thoughtId) {
  const activeThought = state.thoughtDetails[thoughtId]?.thought || thoughtById(thoughtId);
  if (!activeThought?.insight_id) {
    return;
  }
  await fetchJSON(apiUrl("/feedback"), {
    method: "POST",
    body: JSON.stringify({
      insight_id: activeThought.insight_id,
      feedback_state: feedbackState,
    }),
  });
  delete state.thoughtDetails[thoughtId];
  await refreshCollections();
}

feedEl.addEventListener("click", (event) => {
  const feedbackButton = event.target.closest("[data-feedback]");
  if (feedbackButton) {
    const post = feedbackButton.closest(".post");
    if (post?.dataset.thoughtId) {
      sendFeedback(feedbackButton.dataset.feedback, post.dataset.thoughtId).catch((error) => console.error(error));
    }
    return;
  }

  const toggleTarget = event.target.closest('[data-action="toggle-post"]');
  if (toggleTarget) {
    const post = toggleTarget.closest(".post");
    if (post?.dataset.thoughtId) {
      toggleThought(post.dataset.thoughtId).catch((error) => console.error(error));
    }
  }
});

feedEl.addEventListener("keydown", (event) => {
  const toggleTarget = event.target.closest('[data-action="toggle-post"]');
  if (!toggleTarget) {
    return;
  }
  if (event.key !== "Enter" && event.key !== " ") {
    return;
  }
  event.preventDefault();
  const post = toggleTarget.closest(".post");
  if (post?.dataset.thoughtId) {
    toggleThought(post.dataset.thoughtId).catch((error) => console.error(error));
  }
});

systemSnapshotEl.addEventListener("submit", (event) => {
  const form = event.target.closest('[data-action="linking-query"]');
  if (!form) {
    return;
  }
  event.preventDefault();
  const input = form.querySelector('input[name="linking-query"]');
  state.linkingQuery = (input?.value || "").trim();
  loadLinkingOverview(state.linkingQuery)
    .then(() => renderRuntimeSnapshot())
    .catch((error) => {
      state.linkingError = error.message || "Unable to focus the ocean map.";
      renderRuntimeSnapshot();
    });
});

systemSnapshotEl.addEventListener("click", (event) => {
  const nodeTarget = event.target.closest("[data-node-ref]");
  if (nodeTarget) {
    state.selectedOceanNodeRef = nodeTarget.dataset.nodeRef || null;
    state.selectedOceanEdgeId = null;
    renderRuntimeSnapshot();
    return;
  }

  const edgeTarget = event.target.closest("[data-edge-id]");
  if (edgeTarget && edgeTarget.dataset.action !== "govern-edge") {
    state.selectedOceanEdgeId = edgeTarget.dataset.edgeId || null;
    state.selectedOceanNodeRef = null;
    renderRuntimeSnapshot();
    return;
  }

  const target = event.target.closest('[data-action="clear-linking-query"]');
  if (!target) {
    const governTarget = event.target.closest('[data-action="govern-edge"]');
    if (governTarget) {
      governOceanEdge(governTarget.dataset.edgeId, governTarget.dataset.status).catch((error) => console.error(error));
      return;
    }

    const aliasTarget = event.target.closest('[data-action="alias-node"]');
    if (aliasTarget) {
      aliasOceanNode(aliasTarget.dataset.refType, aliasTarget.dataset.refId).catch((error) => console.error(error));
      return;
    }

    const focusNodeTarget = event.target.closest('[data-action="focus-node"]');
    if (focusNodeTarget) {
      state.linkingQuery = (focusNodeTarget.dataset.nodeLabel || "").trim();
      loadLinkingOverview(state.linkingQuery)
        .then(() => renderRuntimeSnapshot())
        .catch((error) => {
          state.linkingError = error.message || "Unable to focus this region.";
          renderRuntimeSnapshot();
        });
      return;
    }
    return;
  }
  state.linkingQuery = "";
  state.selectedOceanNodeRef = null;
  state.selectedOceanEdgeId = null;
  loadLinkingOverview("")
    .then(() => renderRuntimeSnapshot())
    .catch((error) => {
      state.linkingError = error.message || "Unable to reset the ocean map.";
      renderRuntimeSnapshot();
    });
});

refreshButtonEl.addEventListener("click", () => {
  refreshCollections().catch((error) => console.error(error));
});

async function init() {
  await refreshCollections();
}

init().catch((error) => {
  console.error(error);
  runtimeBadgesEl.innerHTML = metricPill("status", "load failed");
  systemSnapshotEl.innerHTML = `<div class="snapshot-strip snapshot-strip--offline"><p class="snapshot-copy">Runtime and feed failed to load.</p></div>`;
  feedEl.innerHTML = `<div class="empty-feed">Unable to load the timeline.</div>`;
});
