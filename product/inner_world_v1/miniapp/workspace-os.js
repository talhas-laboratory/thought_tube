const state = {
  snapshot: null,
  selectedId: "",
  liveContext: null,
  liveHealth: null,
  mode: "loading",
};

const LANES = ["backlog", "ready", "in-progress", "review", "blocked", "done"];
const LANE_LABELS = {
  backlog: "Backlog",
  ready: "Ready",
  "in-progress": "In progress",
  review: "Review",
  blocked: "Blocked",
  done: "Done",
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

async function fetchJSON(url) {
  const response = await fetch(url, { headers: { Accept: "application/json" } });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `Request failed: ${response.status}`);
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

const syncStatusEl = document.querySelector("#sync-status");
const repoMetaEl = document.querySelector("#repo-meta");
const treeEl = document.querySelector("#workspace-tree");
const boardEl = document.querySelector("#task-board");
const detailEl = document.querySelector("#workspace-detail");
const liveDetailEl = document.querySelector("#live-detail");
const statsEl = document.querySelector("#workspace-stats");
const kickerEl = document.querySelector("#selected-workspace-kicker");
const titleEl = document.querySelector("#selected-workspace-title");

function setSyncStatus(text, mode = "snapshot") {
  state.mode = mode;
  syncStatusEl.textContent = text;
  syncStatusEl.dataset.mode = mode;
}

function workspaceEntries() {
  return Object.values(state.snapshot?.workspaces || {});
}

function buildTree() {
  const entries = workspaceEntries();
  const byId = Object.fromEntries(entries.map((row) => [row.workspace_id, row]));
  const children = {};
  for (const link of state.snapshot?.hierarchy_links || []) {
    if (!children[link.parent]) {
      children[link.parent] = [];
    }
    children[link.parent].push(link);
  }

  const roots = entries.filter((row) => !row.parent_workspace_id);
  const renderNode = (entry, depth = 0) => {
    const done = entry.status_counts?.done || 0;
    const total = (entry.tasks || []).length;
    const button = document.createElement("button");
    button.type = "button";
    button.className = `workspace-tree-item${state.selectedId === entry.workspace_id ? " is-active" : ""}`;
    button.dataset.workspaceId = entry.workspace_id;
    button.innerHTML = `
      <span class="tree-label">${escapeHtml(entry.label || entry.workspace_id)}</span>
      <span class="tree-meta">${escapeHtml(entry.workspace_id)} · ${done}/${total} done</span>
    `;
    button.addEventListener("click", () => selectWorkspace(entry.workspace_id));

    const wrap = document.createElement("div");
    if (depth > 0) {
      wrap.className = "workspace-tree-child";
    }
    wrap.appendChild(button);

    for (const link of children[entry.workspace_id] || []) {
      const child = byId[link.child];
      if (child) {
        wrap.appendChild(renderNode(child, depth + 1));
      }
    }
    return wrap;
  };

  treeEl.innerHTML = "";
  if (!roots.length) {
    for (const entry of entries) {
      treeEl.appendChild(renderNode(entry));
    }
    return;
  }
  for (const root of roots) {
    treeEl.appendChild(renderNode(root));
  }
}

function renderBoard(entry) {
  const tasks = entry.tasks || [];
  kickerEl.textContent = entry.workspace_id;
  titleEl.textContent = entry.label || entry.workspace_id;

  const doneCount = entry.status_counts?.done || 0;
  const total = tasks.length;
  statsEl.innerHTML = `
    <span class="stat-pill stat-pill--done">${doneCount}/${total} done</span>
    <span class="stat-pill">${escapeHtml(entry.status || "active")}</span>
  `;

  boardEl.innerHTML = "";
  for (const lane of LANES) {
    const laneTasks = tasks.filter((task) => task.status === lane);
    const laneEl = document.createElement("div");
    laneEl.className = "task-lane";
    laneEl.innerHTML = `
      <div class="task-lane-head">
        <span>${LANE_LABELS[lane] || lane}</span>
        <span>${laneTasks.length}</span>
      </div>
      <div class="task-lane-body"></div>
    `;
    const body = laneEl.querySelector(".task-lane-body");
    if (!laneTasks.length) {
      body.innerHTML = `<div class="task-card"><div class="task-card-title" style="color:var(--muted)">—</div></div>`;
    } else {
      for (const task of laneTasks) {
        const card = document.createElement("div");
        card.className = "task-card";
        card.innerHTML = `
          <div class="task-card-title">${escapeHtml(task.title)}</div>
          <div class="task-card-id">${escapeHtml(task.task_id)}</div>
        `;
        body.appendChild(card);
      }
    }
    boardEl.appendChild(laneEl);
  }
}

function renderDetail(entry) {
  const release = entry.release || {};
  const continuity = entry.continuity_meta || {};
  detailEl.innerHTML = `
    <div class="detail-block">
      <h3>Goal</h3>
      <p>${escapeHtml(entry.goal || "—")}</p>
    </div>
    <div class="detail-block">
      <h3>Projection sync</h3>
      <p>${escapeHtml(entry.tasks_summary || "No live summary line in TASKS.md")}</p>
      <p>Continuity: ${escapeHtml(continuity.generated_at || continuity.canonical_revision || "—")}</p>
    </div>
    <div class="detail-block">
      <h3>G5 release</h3>
      <p>Version: ${escapeHtml(release.provider_contract_version || "—")}</p>
      <p>SHA: <code>${escapeHtml((release.release_git_revision || "—").slice(0, 12))}</code></p>
    </div>
    <div class="detail-block">
      <h3>Repo paths</h3>
      <div class="detail-links">
        ${entry.readme_path ? `<a href="../../${entry.readme_path}" target="_blank" rel="noreferrer">${escapeHtml(entry.readme_path)}</a>` : ""}
        ${entry.workboard_path ? `<a href="../../${entry.workboard_path}" target="_blank" rel="noreferrer">${escapeHtml(entry.workboard_path)}</a>` : ""}
        ${entry.continuity_path ? `<a href="../../${entry.continuity_path}" target="_blank" rel="noreferrer">${escapeHtml(entry.continuity_path)}</a>` : ""}
        ${release.path ? `<a href="../../${release.path}" target="_blank" rel="noreferrer">${escapeHtml(release.path)}</a>` : ""}
      </div>
    </div>
  `;
}

function renderLiveDetail() {
  if (!state.liveContext && !state.liveHealth) {
    liveDetailEl.innerHTML = "";
    return;
  }
  const blockers = state.liveContext?.orientation?.blockers || [];
  const openThreads = state.liveContext?.orientation?.open_threads || [];
  liveDetailEl.innerHTML = `
    <div class="detail-block">
      <h3>Live API</h3>
      <p>Health: ${escapeHtml(JSON.stringify(state.liveHealth || {}))}</p>
      <p>Open threads: ${openThreads.length}</p>
      <p>Blockers: ${blockers.length}</p>
      ${
        blockers.length
          ? `<p>${blockers.map((row) => escapeHtml(row.reason || row.blocker_id || "blocker")).join("<br/>")}</p>`
          : ""
      }
    </div>
  `;
}

async function loadLiveContext(workspaceId) {
  try {
    state.liveHealth = await fetchJSON(apiUrl("/workspace-os/live/health"));
    if (state.liveHealth?.error) {
      return;
    }
    state.liveContext = await fetchJSON(apiUrl(`/workspace-os/live/context/${encodeURIComponent(workspaceId)}`));
    if (!state.liveContext?.error) {
      setSyncStatus("Live workspace API + git snapshot", "live");
    }
  } catch (error) {
    state.liveContext = { error: String(error) };
  }
  renderLiveDetail();
}

function selectWorkspace(workspaceId) {
  state.selectedId = workspaceId;
  const entry = state.snapshot?.workspaces?.[workspaceId];
  if (!entry) {
    return;
  }
  buildTree();
  renderBoard(entry);
  renderDetail(entry);
  loadLiveContext(workspaceId);
}

async function loadDashboard() {
  setSyncStatus("Loading dashboard…", "loading");
  try {
    state.snapshot = await fetchJSON(apiUrl("/workspace-os/dashboard"));
    repoMetaEl.textContent = `rev ${(state.snapshot.repository_revision || "—").slice(0, 12)} · generated ${state.snapshot.generated_at || "—"}`;
    setSyncStatus("Git projections (TASKS.md + manifests)", "snapshot");
    buildTree();
    const preferred =
      state.selectedId ||
      "unified-framework-synthesis" ||
      workspaceEntries()[0]?.workspace_id ||
      "";
    if (preferred && state.snapshot.workspaces[preferred]) {
      selectWorkspace(preferred);
    }
  } catch (error) {
    try {
      const fallback = await fetch("./workspace-dashboard-snapshot.json");
      if (fallback.ok) {
        state.snapshot = await fallback.json();
        repoMetaEl.textContent = `static snapshot · ${state.snapshot.generated_at || ""}`;
        setSyncStatus("Static snapshot file (serve via miniapp for live refresh)", "snapshot");
        buildTree();
        selectWorkspace(state.selectedId || "metaphysical-kernel-ontology");
        return;
      }
    } catch (_ignored) {
      // fall through
    }
    setSyncStatus(`Failed to load dashboard: ${error}`, "error");
  }
}

document.querySelector("#refresh-dashboard")?.addEventListener("click", () => {
  loadDashboard();
});

loadDashboard();
