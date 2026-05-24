const state = {
  activeTab: "capture",
  authenticated: false,
  captureSessionId: null,
  threadMessages: [],
  feed: [],
  library: null,
};

function resolveApiBase() {
  const value = window.INNER_WORLD_MOBILE_CONFIG?.apiBase || "/api/mobile";
  const trimmed = String(value).trim() || "/api/mobile";
  return trimmed.endsWith("/") ? trimmed.slice(0, -1) : trimmed;
}

const API_BASE = resolveApiBase();

function apiUrl(path) {
  return `${API_BASE}${path.startsWith("/") ? path : `/${path}`}`;
}

const authViewEl = document.querySelector("#auth-view");
const appViewEl = document.querySelector("#app-view");
const authErrorEl = document.querySelector("#auth-error");
const globalStatusEl = document.querySelector("#global-status");
const loginFormEl = document.querySelector("#login-form");
const passwordInputEl = document.querySelector("#password-input");
const logoutButtonEl = document.querySelector("#logout-button");
const tabButtonEls = Array.from(document.querySelectorAll(".tab-button"));
const tabPanelEls = Array.from(document.querySelectorAll(".tab-panel"));
const captureFormEl = document.querySelector("#capture-form");
const captureInputEl = document.querySelector("#capture-input");
const continueButtonEl = document.querySelector("#continue-button");
const threadViewEl = document.querySelector("#thread-view");
const replyFormEl = document.querySelector("#reply-form");
const replyInputEl = document.querySelector("#reply-input");
const refreshFeedButtonEl = document.querySelector("#refresh-feed");
const refreshLibraryButtonEl = document.querySelector("#refresh-library");
const feedListEl = document.querySelector("#feed-list");
const librarySectionsEl = document.querySelector("#library-sections");

async function fetchJSON(path, options = {}) {
  const response = await fetch(apiUrl(path), {
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (response.status === 401) {
    state.authenticated = false;
    renderAuthGate("");
    throw new Error("auth_required");
  }

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || `request_failed_${response.status}`);
  }

  return response.json();
}

function escapeHtml(value) {
  return String(value || "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setStatus(message, tone = "") {
  globalStatusEl.textContent = message || "";
  globalStatusEl.dataset.tone = tone || "";
}

function renderAuthGate(message) {
  authViewEl.classList.remove("hidden");
  appViewEl.classList.add("hidden");
  authErrorEl.textContent = message || "";
}

function renderAppShell() {
  authViewEl.classList.add("hidden");
  appViewEl.classList.remove("hidden");
}

function setActiveTab(tab) {
  state.activeTab = tab;
  for (const button of tabButtonEls) {
    const active = button.dataset.tab === tab;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", active ? "true" : "false");
  }
  for (const panel of tabPanelEls) {
    panel.classList.toggle("hidden", panel.dataset.panel !== tab);
  }
}

function renderThread() {
  if (!state.threadMessages.length) {
    threadViewEl.innerHTML =
      '<p class="empty-copy">No conversation thread yet. Save a capture, then continue the thread if you want the assistant to help shape it.</p>';
    replyFormEl.classList.add("hidden");
    continueButtonEl.classList.add("hidden");
    return;
  }

  threadViewEl.innerHTML = state.threadMessages
    .map((message) => {
      const role = message.actor || message.role || "assistant";
      const roleLabel = role === "user" ? "You" : "Inner World";
      return `
        <article class="thread-bubble thread-bubble--${escapeHtml(role)}">
          <p class="thread-role">${escapeHtml(roleLabel)}</p>
          <p class="thread-copy">${escapeHtml(message.content)}</p>
        </article>
      `;
    })
    .join("");
  replyFormEl.classList.remove("hidden");
  continueButtonEl.classList.remove("hidden");
}

function feedbackLabel(value) {
  if (value === "saved") {
    return "Saved";
  }
  if (value === "revisit_later") {
    return "Revisit";
  }
  if (value === "relevant") {
    return "Relevant";
  }
  return "Pending";
}

function renderFeed() {
  if (!state.feed.length) {
    feedListEl.innerHTML = '<p class="empty-copy">No mobile feed items are available yet.</p>';
    return;
  }

  feedListEl.innerHTML = state.feed
    .map(
      (item) => `
        <article class="feed-card">
          <div class="feed-meta">
            <span class="meta-pill">${escapeHtml(item.post_format || "signal")}</span>
            <span class="meta-pill">${escapeHtml(feedbackLabel(item.feedback_state))}</span>
            <span class="meta-pill">${escapeHtml(String(item.thread_count || 0))} thread</span>
          </div>
          <h3>${escapeHtml(item.title || "Untitled item")}</h3>
          <p>${escapeHtml(item.summary || "")}</p>
          <div class="source-row">
            ${(item.source_refs || []).slice(0, 2).map((ref) => `<span class="source-chip">${escapeHtml(ref)}</span>`).join("")}
          </div>
          <div class="action-row">
            <button class="mini-button" type="button" data-feedback="relevant" data-insight-id="${escapeHtml(item.insight_id)}">Relevant</button>
            <button class="mini-button" type="button" data-feedback="saved" data-insight-id="${escapeHtml(item.insight_id)}">Save</button>
            <button class="mini-button" type="button" data-feedback="revisit_later" data-insight-id="${escapeHtml(item.insight_id)}">Revisit</button>
          </div>
        </article>
      `
    )
    .join("");
}

function renderLibrarySection(title, items, renderItem) {
  return `
    <section class="library-group">
      <div class="library-head">
        <h3>${escapeHtml(title)}</h3>
        <span class="meta-pill">${escapeHtml(String(items.length))}</span>
      </div>
      <div class="list-stack">
        ${items.length ? items.map(renderItem).join("") : '<p class="empty-copy">Nothing here yet.</p>'}
      </div>
    </section>
  `;
}

function renderLibrary() {
  if (!state.library) {
    librarySectionsEl.innerHTML = '<p class="empty-copy">Library sections will appear here.</p>';
    return;
  }

  librarySectionsEl.innerHTML = [
    renderLibrarySection("Captures", state.library.captures || [], (item) => {
      return `
        <article class="library-card">
          <p class="library-title">${escapeHtml(item.content || "Untitled capture")}</p>
          <p class="library-meta">${escapeHtml(item.created_at || "")}</p>
        </article>
      `;
    }),
    renderLibrarySection("Conversations", state.library.conversations || [], (item) => {
      return `
        <article class="library-card">
          <p class="library-title">${escapeHtml(item.title || "Conversation")}</p>
          <p class="library-meta">${escapeHtml(item.preview || "")}</p>
          <p class="library-meta">${escapeHtml(item.conversation_type || "")} · ${escapeHtml(String(item.message_count || 0))} messages</p>
        </article>
      `;
    }),
    renderLibrarySection("Saved Items", state.library.saved_items || [], (item) => {
      return `
        <article class="library-card">
          <p class="library-title">${escapeHtml(item.title || "Saved item")}</p>
          <p class="library-meta">${escapeHtml(item.summary || "")}</p>
          <p class="library-meta">${escapeHtml(feedbackLabel(item.feedback_state))}</p>
        </article>
      `;
    }),
  ].join("");
}

async function loadFeed() {
  const payload = await fetchJSON("/feed");
  state.feed = payload.items || [];
  renderFeed();
}

async function loadLibrary() {
  state.library = await fetchJSON("/library");
  renderLibrary();
}

async function submitFeedback(insightId, feedbackState) {
  await fetchJSON("/feedback", {
    method: "POST",
    body: JSON.stringify({ insight_id: insightId, feedback_state: feedbackState }),
  });
  state.feed = state.feed.map((item) =>
    item.insight_id === insightId ? { ...item, feedback_state: feedbackState } : item
  );
  renderFeed();
  setStatus(`Marked item as ${feedbackLabel(feedbackState).toLowerCase()}.`, "success");
}

async function submitCapture(event) {
  event.preventDefault();
  const content = captureInputEl.value.trim();
  if (!content) {
    setStatus("Capture text is required.", "error");
    return;
  }

  const payload = await fetchJSON("/capture", {
    method: "POST",
    body: JSON.stringify({
      content,
      session_id: state.captureSessionId,
    }),
  });

  state.captureSessionId = payload.session_id;
  state.threadMessages.push({ actor: "user", content });
  renderThread();
  continueButtonEl.classList.remove("hidden");
  captureInputEl.value = "";
  setStatus("Capture saved.", "success");
  loadLibrary().catch(() => {});
}

async function submitReply(event) {
  event.preventDefault();
  const message = replyInputEl.value.trim();
  if (!message || !state.captureSessionId) {
    setStatus("Start from a saved capture before continuing the thread.", "error");
    return;
  }

  state.threadMessages.push({ actor: "user", content: message });
  renderThread();
  replyInputEl.value = "";

  const payload = await fetchJSON(`/conversations/${state.captureSessionId}/reply`, {
    method: "POST",
    body: JSON.stringify({ message }),
  });

  state.threadMessages.push({
    actor: payload.assistant_message?.actor || "assistant",
    content: payload.assistant_message?.content || "",
  });
  renderThread();
  setStatus("Thread continued.", "success");
  loadLibrary().catch(() => {});
}

async function logIn(password) {
  const response = await fetch(apiUrl("/session"), {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.error || "invalid_password");
  }

  state.authenticated = true;
  renderAppShell();
  setStatus("Mobile surface unlocked.", "success");
  await Promise.all([loadFeed(), loadLibrary()]);
}

async function logOut() {
  await fetchJSON("/session/logout", {
    method: "POST",
    body: JSON.stringify({}),
  });
  state.authenticated = false;
  state.captureSessionId = null;
  state.threadMessages = [];
  renderThread();
  renderAuthGate("");
}

async function bootstrap() {
  try {
    state.authenticated = true;
    renderAppShell();
    renderThread();
    await Promise.all([loadFeed(), loadLibrary()]);
  } catch (error) {
    if (error.message !== "auth_required") {
      setStatus("The mobile surface could not load its initial data.", "error");
    }
  }

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => {
      navigator.serviceWorker.register("./service-worker.js").catch(() => {});
    });
  }
}

loginFormEl.addEventListener("submit", async (event) => {
  event.preventDefault();
  authErrorEl.textContent = "";
  try {
    await logIn(passwordInputEl.value);
    passwordInputEl.value = "";
  } catch (error) {
    authErrorEl.textContent = error.message === "invalid_password" ? "Password rejected." : "Login failed.";
  }
});

logoutButtonEl.addEventListener("click", () => {
  logOut().catch(() => {
    setStatus("Logout failed.", "error");
  });
});

for (const button of tabButtonEls) {
  button.addEventListener("click", () => {
    setActiveTab(button.dataset.tab);
  });
}

captureFormEl.addEventListener("submit", (event) => {
  submitCapture(event).catch((error) => {
    setStatus(error.message === "auth_required" ? "" : "Capture failed.", "error");
  });
});

continueButtonEl.addEventListener("click", () => {
  replyFormEl.classList.remove("hidden");
  replyInputEl.focus();
});

replyFormEl.addEventListener("submit", (event) => {
  submitReply(event).catch((error) => {
    if (error.message !== "auth_required") {
      setStatus("Reply failed.", "error");
    }
  });
});

refreshFeedButtonEl.addEventListener("click", () => {
  loadFeed()
    .then(() => setStatus("Feed refreshed.", "success"))
    .catch((error) => {
      if (error.message !== "auth_required") {
        setStatus("Feed refresh failed.", "error");
      }
    });
});

refreshLibraryButtonEl.addEventListener("click", () => {
  loadLibrary()
    .then(() => setStatus("Library refreshed.", "success"))
    .catch((error) => {
      if (error.message !== "auth_required") {
        setStatus("Library refresh failed.", "error");
      }
    });
});

feedListEl.addEventListener("click", (event) => {
  const button = event.target.closest("[data-feedback]");
  if (!button) {
    return;
  }
  submitFeedback(button.dataset.insightId, button.dataset.feedback).catch((error) => {
    if (error.message !== "auth_required") {
      setStatus("Feedback update failed.", "error");
    }
  });
});

setActiveTab("capture");
renderThread();
bootstrap();
