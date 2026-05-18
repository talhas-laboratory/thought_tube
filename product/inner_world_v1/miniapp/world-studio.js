const STORAGE_WORLD_ID = "inner-world-studio.activeWorldId";

const GRAPH_VIEWBOX = {
  width: 1040,
  height: 840,
  xOffset: 520,
  yOffset: 420,
};

const state = {
  guide: null,
  worlds: [],
  graph: null,
  activeWorldId: "",
  selectedNodeId: "",
  composeChoice: "",
  composeText: "",
  sceneText: "",
  compileResult: null,
  guideOpen: false,
  error: "",
};

function resolveApiBase() {
  const params = new URLSearchParams(window.location.search);
  const fromQuery = params.get("apiBase");
  const fromConfig = window.INNER_WORLD_CONFIG?.apiBaseUrl;
  const value = (fromQuery || fromConfig || "/api").trim();
  return value.endsWith("/") ? value.slice(0, -1) : value;
}

const API_BASE = resolveApiBase();

function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

function escapeHtml(value) {
  return String(value ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function shortText(value, max = 160) {
  const text = String(value || "").trim();
  if (text.length <= max) {
    return text;
  }
  return `${text.slice(0, max - 3).trimEnd()}...`;
}

function metricToken(label, value, accent = false) {
  return `<span class="status-token${accent ? " status-token--accent" : ""}">${escapeHtml(label)} ${escapeHtml(value)}</span>`;
}

function toPercentX(x) {
  return `${((Number(x || 0) + GRAPH_VIEWBOX.xOffset) / GRAPH_VIEWBOX.width) * 100}%`;
}

function toPercentY(y) {
  return `${((Number(y || 0) + GRAPH_VIEWBOX.yOffset) / GRAPH_VIEWBOX.height) * 100}%`;
}

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

function persistSelection() {
  try {
    if (state.activeWorldId) {
      window.localStorage.setItem(STORAGE_WORLD_ID, state.activeWorldId);
    } else {
      window.localStorage.removeItem(STORAGE_WORLD_ID);
    }
  } catch (_error) {
    // Ignore unavailable storage.
  }
}

function restoreSelection() {
  try {
    state.activeWorldId = window.localStorage.getItem(STORAGE_WORLD_ID) || "";
  } catch (_error) {
    state.activeWorldId = "";
  }
}

function currentWorld() {
  return state.worlds.find((world) => world.world_id === state.activeWorldId) || null;
}

function currentQuestionNode() {
  return state.graph?.nodes?.find((node) => node.node_type === "question") || null;
}

function currentQuestionTargetId() {
  return state.graph?.edges?.find((edge) => edge.edge_type === "asks_for")?.target_id || "";
}

function selectedNode() {
  if (!state.graph?.nodes?.length) {
    return null;
  }
  return state.graph.nodes.find((node) => node.node_id === state.selectedNodeId) || null;
}

function nodeEdges(nodeId) {
  if (!state.graph?.edges?.length) {
    return [];
  }
  return state.graph.edges.filter((edge) => edge.source_id === nodeId || edge.target_id === nodeId);
}

function nodeById(nodeId) {
  return state.graph?.nodes?.find((node) => node.node_id === nodeId) || null;
}

function graphStats() {
  const graph = state.graph;
  if (!graph) {
    return {
      clusterCount: 0,
      filledLayerCount: 0,
      fragmentCount: 0,
      inferredLinkCount: 0,
      packetCount: 0,
    };
  }
  const clusterCount = graph.nodes.filter((node) => node.node_type === "cluster").length;
  const filledLayerCount = Object.values(graph.coverage_by_layer || {}).filter((count) => Number(count || 0) > 0).length;
  const fragmentCount = graph.nodes.filter((node) => node.node_type === "fragment").length;
  const inferredLinkCount = graph.edges.filter((edge) => edge.edge_type === "inferred_world_link").length;
  return {
    clusterCount,
    filledLayerCount,
    fragmentCount,
    inferredLinkCount,
    packetCount: Number(graph.packet_count || 0),
  };
}

function stageModeLabel() {
  const stats = graphStats();
  if (currentQuestionNode()) {
    return "world in conversation";
  }
  if (state.graph?.ready_for_generation) {
    return "world ready";
  }
  if (!stats.fragmentCount) {
    return "world seed";
  }
  return "world in progress";
}

function nodeSummary(node, questionTargetId = "") {
  if (!node) {
    return "";
  }
  if (node.node_type === "world") {
    const stats = graphStats();
    if (!stats.fragmentCount) {
      return "Seeded frame. Waiting for the first fragments.";
    }
    return `${stats.fragmentCount} fragments across ${stats.filledLayerCount}/${stats.clusterCount} layers`;
  }
  if (node.node_type === "cluster") {
    const count = Number(node.metadata?.count || 0);
    if (node.node_id === questionTargetId) {
      return count ? `${count} fragments, active now` : "Current question lands here";
    }
    return count ? `${count} fragment${count === 1 ? "" : "s"}` : "Open space";
  }
  if (node.node_type === "question") {
    return shortText(node.summary || "", 120);
  }
  return shortText(node.summary || "", 88);
}

function displayNodeLayer(node) {
  if (!node) {
    return "";
  }
  if (node.node_type === "question") {
    if (node.layer === "meta") {
      return "entry prompt";
    }
    return `${String(node.layer || "question").replaceAll("_", " ")} prompt`;
  }
  if (node.node_type === "world") {
    return "world";
  }
  return String(node.layer || node.node_type).replaceAll("_", " ");
}

function nodeMetaLabel(node) {
  if (!node) {
    return "";
  }
  if (node.node_type === "question") {
    return "current prompt";
  }
  return displayNodeLayer(node);
}

function recommendedActionLabel(action) {
  const labels = {
    continue_population: "Continue interview",
    populate_world: "Start interview",
    compile_scene: "Compile scene",
    inspect_node_graph: "Inspect graph",
    inspect_packets: "Inspect packets",
  };
  return labels[action] || action.replaceAll("_", " ");
}

async function loadGuide() {
  state.guide = await fetchJSON(apiUrl("/world-studio/guide"));
}

async function loadWorlds() {
  const payload = await fetchJSON(apiUrl("/world-studio/worlds"));
  state.worlds = payload.worlds || [];
}

async function loadGraph(worldId) {
  if (!worldId) {
    state.graph = null;
    state.selectedNodeId = "";
    return;
  }
  state.graph = await fetchJSON(apiUrl(`/world-studio/world/${encodeURIComponent(worldId)}/graph`));
  state.activeWorldId = worldId;
  state.selectedNodeId = state.selectedNodeId && nodeById(state.selectedNodeId) ? state.selectedNodeId : state.graph.focus_node_id;
  persistSelection();
}

async function refreshAll() {
  state.error = "";
  state.compileResult = null;
  await Promise.all([loadGuide(), loadWorlds()]);
  if (state.activeWorldId) {
    await loadGraph(state.activeWorldId);
  }
  render();
}

async function startPopulation(payload) {
  state.error = "";
  const response = await fetchJSON(apiUrl("/world-studio/population/start"), {
    method: "POST",
    body: JSON.stringify(payload),
  });
  state.activeWorldId = response.world_id;
  state.composeChoice = "";
  state.composeText = "";
  state.compileResult = null;
  await loadWorlds();
  await loadGraph(response.world_id);
  render();
}

function buildAnswerPayload(questionNode) {
  const metadata = questionNode?.metadata || {};
  const note = state.composeText.trim();
  if (metadata.selection_mode === "free_text") {
    return note;
  }
  if (state.composeChoice && note && metadata.allow_free_text) {
    return `${state.composeChoice}|${note}`;
  }
  if (state.composeChoice) {
    return state.composeChoice;
  }
  if (note && metadata.allow_free_text) {
    return note;
  }
  return "";
}

async function answerPopulationQuestion() {
  const questionNode = currentQuestionNode();
  if (!questionNode) {
    return;
  }
  const payload = buildAnswerPayload(questionNode);
  if (!payload) {
    state.error = "Answer required before continuing.";
    render();
    return;
  }
  state.error = "";
  const response = await fetchJSON(apiUrl("/world-studio/population/answer"), {
    method: "POST",
    body: JSON.stringify({
      session_id: questionNode.metadata.session_id,
      answer: payload,
    }),
  });
  state.composeChoice = "";
  state.composeText = "";
  state.compileResult = null;
  if (response.world_id) {
    await loadWorlds();
    await loadGraph(response.world_id);
  }
  render();
}

async function compileScene() {
  if (!state.activeWorldId || !state.sceneText.trim()) {
    state.error = "Select a world and provide a scene before compiling.";
    render();
    return;
  }
  state.error = "";
  state.compileResult = await fetchJSON(apiUrl("/world-studio/compile-scene"), {
    method: "POST",
    body: JSON.stringify({
      world_id: state.activeWorldId,
      scene_text: state.sceneText.trim(),
      duration_seconds: 12,
      aspect_ratio: "16:9",
    }),
  });
  await loadWorlds();
  await loadGraph(state.activeWorldId);
  render();
}

function selectNode(nodeId) {
  state.selectedNodeId = nodeId;
  renderInspector();
  renderCanvas();
}

function renderWorldList() {
  const worldCountEl = document.querySelector("#world-count");
  const worldListEl = document.querySelector("#world-list");
  worldCountEl.textContent = `${state.worlds.length || 0} total`;
  if (!state.worlds.length) {
    worldListEl.innerHTML = `<p class="rail-caption">No worlds yet.</p>`;
    return;
  }
  worldListEl.innerHTML = state.worlds
    .map((world) => {
      const isActive = world.world_id === state.activeWorldId;
      return `
        <article class="world-row${isActive ? " is-active" : ""}">
          <div class="world-row-head">
            <div>
              <h3 class="world-row-title">${escapeHtml(world.name)}</h3>
              <p class="world-row-summary">${escapeHtml(shortText(world.summary || "No summary yet.", 110))}</p>
            </div>
            ${metricToken("packets", world.packet_count || 0)}
          </div>
          <div class="world-row-actions">
            <button class="secondary-button" data-world-action="open" data-world-id="${escapeHtml(world.world_id)}" type="button">Open</button>
            <button class="secondary-button" data-world-action="continue" data-world-id="${escapeHtml(world.world_id)}" type="button">Continue</button>
          </div>
        </article>
      `;
    })
    .join("");
}

function renderStageHead() {
  const stageWorldEl = document.querySelector("#stage-world");
  const stageStatusEl = document.querySelector("#stage-status");
  const world = currentWorld();
  if (!world || !state.graph) {
    stageWorldEl.innerHTML = `
      <div>
        <p class="canvas-label">workspace</p>
        <h2 class="stage-title">Build a world from the center outward.</h2>
        <p class="stage-summary">Answer one question, let it land on the table, then keep going from the most meaningful fragment.</p>
      </div>
    `;
    stageStatusEl.innerHTML = "";
    return;
  }
  const stats = graphStats();
  const guidance = currentQuestionNode()
    ? "Answer the prompt below and the graph will update in place."
    : stats.fragmentCount
      ? "Select a node or continue the interview to deepen the world."
      : "Begin the interview to turn the frame into reusable people, places, objects, rules, and pressure.";
  stageWorldEl.innerHTML = `
    <div>
      <p class="canvas-label">${escapeHtml(stageModeLabel())}</p>
      <h2 class="stage-title">${escapeHtml(world.name)}</h2>
      <p class="stage-summary">${escapeHtml(world.summary || "No summary yet.")}</p>
      <p class="stage-note">${escapeHtml(guidance)}</p>
    </div>
  `;
  stageStatusEl.innerHTML = [
    metricToken("layers", `${stats.filledLayerCount}/${stats.clusterCount}`),
    metricToken("fragments", stats.fragmentCount),
    metricToken("links", stats.inferredLinkCount),
    metricToken("packets", stats.packetCount),
    state.graph.ready_for_generation ? metricToken("state", "ready", true) : "",
  ].join("");
}

function renderCanvas() {
  const graphCanvasEl = document.querySelector("#graph-canvas");
  const emptyEl = document.querySelector("#canvas-empty");
  const edgesEl = document.querySelector("#graph-edges");
  const nodesEl = document.querySelector("#graph-nodes");
  if (!state.graph?.nodes?.length) {
    emptyEl.hidden = false;
    emptyEl.innerHTML = `
      <div>
        <p class="canvas-label">empty table</p>
        <p class="stage-summary">Create a world or open one from the left. The graph will grow as fragments, rules, and tensions accumulate.</p>
      </div>
    `;
    edgesEl.innerHTML = "";
    nodesEl.innerHTML = "";
    return;
  }
  emptyEl.hidden = true;
  const questionTargetId = currentQuestionTargetId();
  edgesEl.innerHTML = state.graph.edges
    .map((edge) => {
      const source = nodeById(edge.source_id);
      const target = nodeById(edge.target_id);
      if (!source || !target) {
        return "";
      }
      const sourceX = Number(source.layout?.x || 0) + GRAPH_VIEWBOX.xOffset;
      const sourceY = Number(source.layout?.y || 0) + GRAPH_VIEWBOX.yOffset;
      const targetX = Number(target.layout?.x || 0) + GRAPH_VIEWBOX.xOffset;
      const targetY = Number(target.layout?.y || 0) + GRAPH_VIEWBOX.yOffset;
      const isQuestion = edge.edge_type === "asks_for";
      return `
        <line
          class="edge-line${isQuestion ? " edge-line--question" : ""}"
          x1="${sourceX}"
          y1="${sourceY}"
          x2="${targetX}"
          y2="${targetY}"
          stroke-width="${isQuestion ? 2.2 : Math.max(1.2, Number(edge.weight || 1) * 1.7)}"
        ></line>
      `;
    })
    .join("");
  nodesEl.innerHTML = state.graph.nodes
    .map((node) => {
      const classes = [
        "graph-node",
        `graph-node--${node.node_type}`,
        questionTargetId && node.node_id === questionTargetId ? "is-targeted" : "",
        state.selectedNodeId === node.node_id ? "is-selected" : "",
      ]
        .filter(Boolean)
        .join(" ");
      const titleClass = node.node_type === "world" ? "graph-node-title graph-node-title--world" : "graph-node-title";
      const summary = nodeSummary(node, questionTargetId);
      return `
        <button
          class="${classes}"
          type="button"
          data-node-id="${escapeHtml(node.node_id)}"
          style="left:${toPercentX(node.layout?.x || 0)}; top:${toPercentY(node.layout?.y || 0)};"
        >
          <p class="node-meta">${escapeHtml(nodeMetaLabel(node))}</p>
          <h3 class="${titleClass}">${escapeHtml(shortText(node.label || "", node.node_type === "question" ? 90 : 44))}</h3>
          ${summary ? `<p class="graph-node-copy graph-node-copy--${escapeHtml(node.node_type)}">${escapeHtml(summary)}</p>` : ""}
        </button>
      `;
    })
    .join("");
  graphCanvasEl.setAttribute("data-has-graph", "true");
}

function renderQuestionDock() {
  const dockEl = document.querySelector("#question-dock");
  const questionNode = currentQuestionNode();
  const world = currentWorld();
  if (!world) {
    dockEl.innerHTML = `
      <div class="dock-shell">
        ${state.error ? `<div class="error-banner">${escapeHtml(state.error)}</div>` : ""}
        <div class="dock-empty">
          Start a world on the left, or open an existing one to continue building.
        </div>
      </div>
    `;
    return;
  }
  if (questionNode) {
    const metadata = questionNode.metadata || {};
    const options = metadata.response_options || [];
    const showComposeInput = metadata.selection_mode === "free_text" || metadata.allow_free_text;
    const questionCount = state.graph.edges.filter((edge) => edge.edge_type === "asks_for").length ? "Current question" : "Next question";
    dockEl.innerHTML = `
      <div class="dock-shell">
        ${state.error ? `<div class="error-banner">${escapeHtml(state.error)}</div>` : ""}
        <div class="dock-header">
          <div>
            <p class="dock-label">${escapeHtml(questionCount)}</p>
            <h2 class="dock-title">${escapeHtml(questionNode.label)}</h2>
            <p class="dock-copy">${escapeHtml(questionNode.summary || "")}</p>
          </div>
          <div class="stage-actions">
            ${(state.graph.recommended_actions || [])
              .slice(0, 2)
              .map((action) => `<span class="mini-tag">${escapeHtml(recommendedActionLabel(action))}</span>`)
              .join("")}
          </div>
        </div>
        ${
          options.length
            ? `<div class="choice-grid">
                ${options
                  .map(
                    (option) => `
                      <button
                        class="chip-button${state.composeChoice === option.id ? " is-active" : ""}"
                        type="button"
                        data-choice-id="${escapeHtml(option.id)}"
                      >
                        ${escapeHtml(option.label)}
                      </button>
                    `
                  )
                  .join("")}
              </div>`
            : ""
        }
        <div class="dock-compose">
          ${
            showComposeInput
              ? `
                <textarea
                  id="compose-input"
                  class="compose-input"
                  placeholder="${escapeHtml(metadata.selection_mode === "free_text" ? "Write one or two sentences." : "Optional note or your own phrasing.")}"
                >${escapeHtml(state.composeText)}</textarea>
              `
              : `<p class="muted-note">Choose one option to let the system ask the next useful question.</p>`
          }
          <div class="dock-actions">
            <button id="submit-answer" class="primary-button" type="button">Add to world</button>
          </div>
        </div>
      </div>
    `;
    return;
  }
  const stats = graphStats();
  dockEl.innerHTML = `
    <div class="dock-shell">
      ${state.error ? `<div class="error-banner">${escapeHtml(state.error)}</div>` : ""}
      <div class="dock-header">
        <div>
          <p class="dock-label">${escapeHtml(state.graph?.ready_for_generation ? "world ready" : "next move")}</p>
          <h2 class="dock-title">${escapeHtml(state.graph?.ready_for_generation ? "This world can now carry scenes." : stats.fragmentCount ? "Let the studio ask for the next missing piece." : "Let the studio ask the first real question.")}</h2>
          <p class="dock-copy">${escapeHtml(state.graph?.ready_for_generation ? "Move into scene generation, or inspect the graph before you do." : stats.fragmentCount ? "The interview will look at what is missing and ask into the most useful layer next." : "The world has its frame, but not its inner texture yet. Start with one easy answer and let the graph grow around it.")}</p>
        </div>
        <div class="stage-actions">
          ${(state.graph?.recommended_actions || [])
            .map((action) => `<span class="mini-tag">${escapeHtml(recommendedActionLabel(action))}</span>`)
            .join("")}
        </div>
      </div>
      <div class="dock-actions">
        <button id="resume-interview" class="primary-button" type="button">${escapeHtml(stats.fragmentCount ? "Ask next question" : "Start world interview")}</button>
      </div>
    </div>
  `;
}

function renderSceneDock() {
  const sceneDockEl = document.querySelector("#scene-dock");
  if (!state.graph?.ready_for_generation && !state.compileResult) {
    sceneDockEl.hidden = true;
    sceneDockEl.innerHTML = "";
    return;
  }
  sceneDockEl.hidden = false;
  sceneDockEl.innerHTML = `
    <div class="scene-shell">
      <div class="dock-header">
        <div>
          <p class="dock-label">scene generation</p>
          <h2 class="dock-title">Turn the world into a scene packet.</h2>
          <p class="dock-copy">Write one scene beat. The system will compile it against the world graph and packet constraints.</p>
        </div>
      </div>
      <textarea id="scene-input" class="scene-input" placeholder="Iris unlocks the tide archive and realizes the city has been editing her memories.">${escapeHtml(state.sceneText)}</textarea>
      <div class="dock-actions">
        <button id="compile-scene" class="primary-button" type="button">Compile scene</button>
      </div>
      ${
        state.compileResult
          ? `<div class="compile-result">Packet compiled: <code>${escapeHtml(state.compileResult.packet_id)}</code></div>`
          : ""
      }
    </div>
  `;
}

function renderInspector() {
  const inspectorEl = document.querySelector("#inspector");
  const node = selectedNode();
  if (!node) {
    inspectorEl.innerHTML = `
      <div>
        <p class="inspector-label">selection</p>
        <h2 class="inspector-title">Choose a fragment.</h2>
        <p class="inspector-empty">Click any node to inspect what it means, what it connects to, and what role it plays in the world.</p>
      </div>
    `;
    return;
  }
  const questionTargetId = currentQuestionTargetId();
  const edges = nodeEdges(node.node_id);
  const related = edges
    .map((edge) => nodeById(edge.source_id === node.node_id ? edge.target_id : edge.source_id))
    .filter(Boolean)
    .slice(0, 6);
  const tags = node.tags || node.shared_tags || [];
  const stats = graphStats();
  const inspectorCopy =
    node.node_type === "cluster"
      ? Number(node.metadata?.count || 0) > 0
        ? `${node.metadata.count} fragment${Number(node.metadata.count) === 1 ? "" : "s"} are already carrying this layer.`
        : node.node_id === questionTargetId
          ? "Nothing has landed here yet. The current question is trying to give this layer its first fragment."
          : "Nothing has landed here yet. The interview will return here when this layer becomes useful."
      : node.node_type === "world"
        ? worldSummaryForInspector(stats)
        : node.summary || "No additional detail yet.";
  const relatedMarkup =
    node.node_type === "world"
      ? clusterCoverageMarkup()
      : related.length
        ? `
          <div class="inspector-section">
            <p class="inspector-label">touches</p>
            <div class="inspector-related-list">
              ${related
                .map(
                  (item) => `
                    <button class="inspector-related-item" type="button" data-node-id="${escapeHtml(item.node_id)}">
                      <span class="inspector-related-title">${escapeHtml(item.label)}</span>
                      <span class="inspector-related-copy">${escapeHtml(nodeSummary(item, questionTargetId))}</span>
                    </button>
                  `
                )
                .join("")}
            </div>
          </div>
        `
        : "";
  inspectorEl.innerHTML = `
    <div>
      <p class="inspector-label">${escapeHtml(node.node_type === "question" ? "question" : node.node_type)}</p>
      <h2 class="inspector-title">${escapeHtml(node.label)}</h2>
      <p class="inspector-copy">${escapeHtml(inspectorCopy)}</p>
    </div>
    <div class="inspector-section">
      <p class="inspector-label">role</p>
      <div class="inspector-tags">
        <span class="node-tag">${escapeHtml(displayNodeLayer(node))}</span>
        <span class="node-tag">${escapeHtml(`${edges.length} linked`)}</span>
      </div>
    </div>
    ${
      tags.length
        ? `
          <div class="inspector-section">
            <p class="inspector-label">tags</p>
            <div class="inspector-tags">
              ${tags.map((tag) => `<span class="node-tag">${escapeHtml(tag)}</span>`).join("")}
            </div>
          </div>
        `
        : ""
    }
    ${relatedMarkup}
  `;
}

function worldSummaryForInspector(stats) {
  if (!stats.fragmentCount) {
    return "This world has its outer frame, but none of the reusable inner fragments have been populated yet.";
  }
  return `This world currently holds ${stats.fragmentCount} fragments across ${stats.filledLayerCount} layers, with ${stats.inferredLinkCount} inferred link${stats.inferredLinkCount === 1 ? "" : "s"} and ${stats.packetCount} compiled packet${stats.packetCount === 1 ? "" : "s"}.`;
}

function clusterCoverageMarkup() {
  const clusters = (state.graph?.nodes || []).filter((node) => node.node_type === "cluster");
  if (!clusters.length) {
    return "";
  }
  return `
    <div class="inspector-section">
      <p class="inspector-label">current shape</p>
      <div class="inspector-related-list">
        ${clusters
          .map(
            (cluster) => `
              <button class="inspector-related-item" type="button" data-node-id="${escapeHtml(cluster.node_id)}">
                <span class="inspector-related-title">${escapeHtml(cluster.label)}</span>
                <span class="inspector-related-copy">${escapeHtml(nodeSummary(cluster, currentQuestionTargetId()))}</span>
              </button>
            `
          )
          .join("")}
      </div>
    </div>
  `;
}

function renderGuideSheet() {
  const guideEl = document.querySelector("#guide-sheet");
  const toggleButton = document.querySelector("#toggle-guide");
  toggleButton.classList.toggle("is-active", state.guideOpen);
  if (!state.guideOpen) {
    guideEl.hidden = true;
    guideEl.innerHTML = "";
    return;
  }
  guideEl.hidden = false;
  guideEl.innerHTML = `
    <div class="guide-sheet-head">
      <div>
        <p class="guide-label">workflow</p>
        <h2 class="guide-title">${escapeHtml(state.guide?.title || "Worldbuilding Studio")}</h2>
      </div>
      <button id="close-guide" class="studio-text-button" type="button">Close</button>
    </div>
    <p class="guide-copy">${escapeHtml(state.guide?.summary || "")}</p>
    <ol class="guide-list">
      ${(state.guide?.recommended_workflow || []).map((step) => `<li>${escapeHtml(step)}</li>`).join("")}
    </ol>
    <ul class="guide-command-list">
      ${(state.guide?.cli_commands || []).slice(0, 4).map((command) => `<li><code>${escapeHtml(command)}</code></li>`).join("")}
    </ul>
  `;
}

function render() {
  renderWorldList();
  renderStageHead();
  renderCanvas();
  renderQuestionDock();
  renderSceneDock();
  renderInspector();
  renderGuideSheet();
}

function showError(error) {
  state.error = error instanceof Error ? error.message : String(error);
  render();
}

function wireHeaderEvents() {
  document.querySelector("#refresh-world-studio").addEventListener("click", () => refreshAll().catch(showError));
  document.querySelector("#toggle-guide").addEventListener("click", () => {
    state.guideOpen = !state.guideOpen;
    renderGuideSheet();
  });
}

function wireFormEvents() {
  document.querySelector("#new-world-form").addEventListener("submit", (event) => {
    event.preventDefault();
    const name = document.querySelector("#world-name").value.trim();
    const summary = document.querySelector("#world-summary").value.trim();
    if (!name) {
      state.error = "World name required.";
      render();
      return;
    }
    startPopulation({ name, summary }).catch(showError);
  });
}

function wireDelegatedEvents() {
  document.body.addEventListener("click", (event) => {
    const worldButton = event.target.closest("[data-world-action]");
    if (worldButton) {
      const worldId = worldButton.getAttribute("data-world-id");
      const action = worldButton.getAttribute("data-world-action");
      if (!worldId) {
        return;
      }
      if (action === "open") {
        state.activeWorldId = worldId;
        state.composeChoice = "";
        state.composeText = "";
        state.compileResult = null;
        loadGraph(worldId).then(render).catch(showError);
        return;
      }
      if (action === "continue") {
        startPopulation({ world_id: worldId }).catch(showError);
      }
      return;
    }

    const nodeButton = event.target.closest("[data-node-id]");
    if (nodeButton) {
      selectNode(nodeButton.getAttribute("data-node-id") || "");
      return;
    }

    const choiceButton = event.target.closest("[data-choice-id]");
    if (choiceButton) {
      state.composeChoice = choiceButton.getAttribute("data-choice-id") || "";
      renderQuestionDock();
      return;
    }

    if (event.target.closest("#submit-answer")) {
      answerPopulationQuestion().catch(showError);
      return;
    }

    if (event.target.closest("#resume-interview")) {
      if (state.activeWorldId) {
        startPopulation({ world_id: state.activeWorldId }).catch(showError);
      }
      return;
    }

    if (event.target.closest("#continue-world")) {
      if (state.activeWorldId) {
        loadGraph(state.activeWorldId).then(render).catch(showError);
      }
      return;
    }

    if (event.target.closest("#compile-scene")) {
      compileScene().catch(showError);
      return;
    }

    if (event.target.closest("#close-guide")) {
      state.guideOpen = false;
      renderGuideSheet();
    }
  });

  document.body.addEventListener("input", (event) => {
    if (event.target.id === "compose-input") {
      state.composeText = event.target.value;
      return;
    }
    if (event.target.id === "scene-input") {
      state.sceneText = event.target.value;
    }
  });
}

async function initialize() {
  restoreSelection();
  wireHeaderEvents();
  wireFormEvents();
  wireDelegatedEvents();
  await Promise.all([loadGuide(), loadWorlds()]);
  if (!state.activeWorldId && state.worlds.length) {
    state.activeWorldId = state.worlds[0].world_id;
  }
  if (state.activeWorldId) {
    try {
      await loadGraph(state.activeWorldId);
    } catch (_error) {
      state.activeWorldId = state.worlds[0]?.world_id || "";
      if (state.activeWorldId) {
        await loadGraph(state.activeWorldId);
      } else {
        state.graph = null;
      }
    }
  }
  render();
}

initialize().catch(showError);
