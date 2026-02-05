// ── State ────────────────────────────────────────────────────────────────────
let todos = [];
let selectedId = null;
let activeCategory = "Alle";
let activeFilter = "alle"; // "alle", "done", "active", "overdue"
let sortMode = "newest";
let syncInProgress = false;

const CATEGORIES   = ["Alle", "Arbejde", "Privat", "Indkøb"];
const CAT_ICONS    = { Alle: "☰", Arbejde: "⚒", Privat: "⌂", Indkøb: "☷" };
const PRI_ORDER    = { "Høj": 0, "Medium": 1, "Lav": 2 };

// ── API helpers ──────────────────────────────────────────────────────────────

async function api(path, opts = {}) {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  return res.json();
}

async function fetchTodos()          { todos = await api("/todos"); render(); }
async function addTodo(data)         { await api("/todos", { method: "POST", body: JSON.stringify(data) }); await fetchTodos(); }
async function toggleTodo(id)        { await api(`/todos/${id}/toggle`, { method: "PATCH" }); await fetchTodos(); }
async function deleteTodo(id)        { await api(`/todos/${id}`, { method: "DELETE" }); if (selectedId === id) selectedId = null; await fetchTodos(); }
async function updateTodo(id, data)  { await api(`/todos/${id}`, { method: "PUT", body: JSON.stringify(data) }); await fetchTodos(); }

// ── Filtering & sorting ─────────────────────────────────────────────────────

function getFiltered() {
  let list = [...todos];

  if (activeCategory !== "Alle") {
    list = list.filter(t => t.category === activeCategory);
  }

  if (activeFilter === "done")    list = list.filter(t => t.done);
  if (activeFilter === "active")  list = list.filter(t => !t.done);
  if (activeFilter === "overdue") list = list.filter(t => isOverdue(t));

  const q = document.getElementById("search").value.trim().toLowerCase();
  if (q) list = list.filter(t => t.text.toLowerCase().includes(q));

  if (sortMode === "newest")      list.sort((a, b) => b.id - a.id);
  else if (sortMode === "oldest") list.sort((a, b) => a.id - b.id);
  else if (sortMode === "priority") list.sort((a, b) => (PRI_ORDER[a.priority] ?? 1) - (PRI_ORDER[b.priority] ?? 1));
  else if (sortMode === "alpha")  list.sort((a, b) => a.text.localeCompare(b.text, "da"));

  return list;
}

// ── Render ───────────────────────────────────────────────────────────────────

function render() {
  renderSidebar();
  renderList();
  renderDetail();
  renderStatusbar();
}

function renderSidebar() {
  const total  = todos.length;
  const done   = todos.filter(t => t.done).length;
  const active = total - done;

  const overdue = todos.filter(t => isOverdue(t)).length;

  document.getElementById("stat-total").textContent   = total;
  document.getElementById("stat-done").textContent    = done;
  document.getElementById("stat-active").textContent  = active;
  document.getElementById("stat-overdue").textContent = overdue;

  // Highlight active stat filter
  document.querySelectorAll(".stat-row[data-filter]").forEach(row => {
    row.classList.toggle("stat-active", row.dataset.filter === activeFilter);
  });

  document.querySelectorAll(".cat-btn").forEach(btn => {
    const cat = btn.dataset.cat;
    btn.classList.toggle("active", cat === activeCategory);

    let count = cat === "Alle" ? total : todos.filter(t => t.category === cat).length;
    const badge = btn.querySelector(".badge");
    badge.textContent = count || "";
  });
}

function renderList() {
  const container = document.getElementById("todo-list");
  const filtered = getFiltered();

  if (!filtered.length) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="icon">☐</div>
        <h3>Ingen todos fundet</h3>
        <p>Tilføj en ny todo herunder, eller skift kategori</p>
      </div>`;
    return;
  }

  container.innerHTML = filtered.map(t => {
    const priClass = t.priority === "Høj" ? "pri-high" : t.priority === "Lav" ? "pri-low" : "pri-medium";
    const priBadge = t.priority === "Høj" ? "badge-pri-high" : t.priority === "Lav" ? "badge-pri-low" : "badge-pri-medium";
    const doneClass = t.done ? "done" : "";
    const selClass  = t.id === selectedId ? "selected" : "";
    const overdueClass = isOverdue(t) ? "overdue" : "";

    let meta = "";
    if (t.priority) meta += `<span class="badge ${priBadge}">${t.priority}</span>`;
    if (t.category) meta += `<span class="badge badge-cat">${CAT_ICONS[t.category] || ""} ${t.category}</span>`;
    if (t.deadline) {
      const dlBadgeClass = isOverdue(t) ? "badge-deadline badge-overdue" : "badge-deadline";
      meta += `<span class="badge ${dlBadgeClass}">${formatDate(t.deadline)}${isOverdue(t) ? " — overskredet!" : ""}</span>`;
    }
    if (t.attachment) meta += `<span class="badge badge-attachment">📎 Fil</span>`;

    return `
      <div class="todo-card ${priClass} ${doneClass} ${selClass} ${overdueClass}" data-id="${t.id}" onclick="selectTodo(${t.id})">
        <div class="checkbox" onclick="event.stopPropagation(); toggleTodo(${t.id})">${t.done ? "✓" : ""}</div>
        <div class="todo-body">
          <div class="todo-text">${escapeHtml(t.text)}</div>
          ${meta ? `<div class="todo-meta">${meta}</div>` : ""}
        </div>
      </div>`;
  }).join("");
}

function renderDetail() {
  const panel = document.getElementById("detail-content");
  const empty = document.getElementById("detail-empty");
  const actions = document.getElementById("detail-actions");

  const todo = todos.find(t => t.id === selectedId);

  if (!todo) {
    panel.style.display = "none";
    actions.style.display = "none";
    empty.style.display = "block";
    return;
  }

  empty.style.display = "none";
  panel.style.display = "block";
  actions.style.display = "flex";

  document.getElementById("d-text").textContent     = todo.text;
  document.getElementById("d-category").textContent = todo.category || "(ingen)";

  const dPri = document.getElementById("d-priority");
  dPri.textContent = todo.priority;
  dPri.className = "detail-field-value";
  if (todo.priority === "Høj")    dPri.style.color = "#ef4444";
  else if (todo.priority === "Lav") dPri.style.color = "#22c55e";
  else dPri.style.color = "#f59e0b";

  const dDeadline = document.getElementById("d-deadline");
  if (isOverdue(todo)) {
    dDeadline.textContent = `${formatDate(todo.deadline)} — overskredet!`;
    dDeadline.style.color = "#ef4444";
  } else {
    dDeadline.textContent = todo.deadline ? formatDate(todo.deadline) : "(ingen)";
    dDeadline.style.color = "";
  }

  const dStatus = document.getElementById("d-status");
  if (isOverdue(todo)) {
    dStatus.textContent = "⚠  Overskredet";
    dStatus.style.color = "#ef4444";
  } else if (todo.done) {
    dStatus.textContent = "✓  Færdig";
    dStatus.style.color = "var(--success)";
  } else {
    dStatus.textContent = "○  Aktiv";
    dStatus.style.color = "var(--primary)";
  }

  const toggleBtn = document.getElementById("btn-toggle");
  toggleBtn.textContent = todo.done ? "↺  Genåbn" : "✓  Færdiggør";

  // Attachment
  const attachEl = document.getElementById("d-attachment");
  if (todo.attachment) {
    const isImage = /\.(jpg|jpeg|png|gif)$/i.test(todo.attachment);
    const fileName = todo.attachment.replace(/^[a-f0-9]+_/, "");
    let html = "";
    if (isImage) {
      html += `<img class="attachment-preview" src="/uploads/${encodeURIComponent(todo.attachment)}" alt="${escapeHtml(fileName)}">`;
    } else {
      html += `<div class="attachment-file">📄 ${escapeHtml(fileName)}</div>`;
    }
    html += `<div class="attachment-actions">`;
    html += `<a class="btn-attachment btn-download" href="/uploads/${encodeURIComponent(todo.attachment)}" download="${escapeHtml(fileName)}">⬇ Download</a>`;
    html += `<button class="btn-attachment btn-remove-file" onclick="handleRemoveAttachment()">✕ Fjern</button>`;
    html += `</div>`;
    attachEl.innerHTML = html;
  } else {
    attachEl.innerHTML = `
      <label class="upload-label" for="file-upload">📎 Tilføj fil</label>
      <input type="file" id="file-upload" class="file-input" accept=".jpg,.jpeg,.png,.gif,.pdf,.docx,.txt" onchange="handleUpload(this)">
    `;
  }
}

function renderStatusbar() {
  const total   = todos.length;
  const done    = todos.filter(t => t.done).length;
  const active  = total - done;
  const overdue = todos.filter(t => isOverdue(t)).length;
  let text = `≡  ${total} todos   ·   ✓ ${done} færdige   ·   ○ ${active} aktive`;
  if (overdue > 0) text += `   ·   ⚠ ${overdue} overskredet`;
  document.getElementById("statusbar").textContent = text;
}

// ── Actions ──────────────────────────────────────────────────────────────────

function selectTodo(id) {
  selectedId = id;
  render();
}

function selectCategory(cat) {
  activeCategory = cat;
  render();
}

function selectFilter(filter) {
  activeFilter = activeFilter === filter ? "alle" : filter;
  render();
}

function handleSort(value) {
  sortMode = value;
  render();
}

function handleSearch() {
  render();
}

async function handleAdd() {
  const text = document.getElementById("add-text").value.trim();
  if (!text) return;

  const category = document.getElementById("add-category").value;
  const priority = document.getElementById("add-priority").value;
  const deadline = document.getElementById("add-deadline").value.trim();

  await addTodo({ text, category, priority, deadline: deadline || "" });

  document.getElementById("add-text").value = "";
  document.getElementById("add-category").value = "";
  document.getElementById("add-priority").value = "Medium";
  document.getElementById("add-deadline").value = "";
}

async function handleToggle() {
  if (selectedId) await toggleTodo(selectedId);
}

function handleEdit() {
  const todo = todos.find(t => t.id === selectedId);
  if (!todo) return;

  document.getElementById("edit-text").value     = todo.text;
  document.getElementById("edit-category").value = todo.category || "";
  document.getElementById("edit-priority").value = todo.priority || "Medium";
  document.getElementById("edit-deadline").value = todo.deadline || "";

  document.getElementById("modal-overlay").classList.add("open");
  document.getElementById("edit-text").focus();
}

async function handleSaveEdit() {
  const text = document.getElementById("edit-text").value.trim();
  if (!text) return;

  await updateTodo(selectedId, {
    text,
    category: document.getElementById("edit-category").value,
    priority: document.getElementById("edit-priority").value,
    deadline: document.getElementById("edit-deadline").value.trim(),
  });

  closeModal();
}

function closeModal() {
  document.getElementById("modal-overlay").classList.remove("open");
}

async function handleDelete() {
  const todo = todos.find(t => t.id === selectedId);
  if (!todo) return;
  if (!confirm(`Er du sikker på du vil slette "${todo.text}"?`)) return;
  await deleteTodo(selectedId);
}

// ── File upload ──────────────────────────────────────────────────────────────

async function handleUpload(input) {
  if (!selectedId || !input.files.length) return;

  const file = input.files[0];
  if (file.size > 10 * 1024 * 1024) {
    alert("Filen er for stor (max 10 MB)");
    return;
  }

  const formData = new FormData();
  formData.append("file", file);

  const res = await fetch(`/api/todos/${selectedId}/upload`, {
    method: "POST",
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json();
    alert(err.error || "Upload fejlede");
    return;
  }

  await fetchTodos();
}

async function handleRemoveAttachment() {
  if (!selectedId) return;
  if (!confirm("Er du sikker på du vil fjerne filen?")) return;

  await fetch(`/api/todos/${selectedId}/attachment`, { method: "DELETE" });
  await fetchTodos();
}

// Theme
function toggleTheme() {
  document.documentElement.classList.toggle("dark");
  const isDark = document.documentElement.classList.contains("dark");
  localStorage.setItem("theme", isDark ? "dark" : "light");
  document.getElementById("theme-label").textContent = isDark ? "☀  Lyst tema" : "☾  Mørkt tema";
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function isOverdue(todo) {
  if (todo.done || !todo.deadline) return false;
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const dl = new Date(todo.deadline + "T00:00:00");
  return dl < today;
}

function formatDate(dateStr) {
  if (!dateStr) return "";
  const parts = dateStr.split("-");
  if (parts.length === 3 && parts[0].length === 4) {
    return `${parts[2]}-${parts[1]}-${parts[0]}`;
  }
  return dateStr;
}

function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str;
  return div.innerHTML;
}

// ── Todoist Sync ─────────────────────────────────────────────────────────────

async function handleSync() {
  if (syncInProgress) return;
  syncInProgress = true;

  const btn = document.getElementById("sync-btn");
  const icon = document.getElementById("sync-icon");
  const label = document.getElementById("sync-label");

  btn.disabled = true;
  btn.classList.remove("sync-success", "sync-error");
  icon.classList.add("spinning");
  label.textContent = "Synkroniserer...";

  try {
    const res = await fetch("/api/sync", { method: "POST" });
    const data = await res.json();

    if (!res.ok) {
      btn.classList.add("sync-error");
      label.textContent = "Sync fejlet";
      showSyncToast(data.error || "Sync fejlede", "error");
    } else {
      btn.classList.add("sync-success");
      label.textContent = "Sync OK";
      const parts = [];
      if (data.pulled > 0)    parts.push(`${data.pulled} hentet`);
      if (data.pushed > 0)    parts.push(`${data.pushed} sendt`);
      if (data.updated > 0)   parts.push(`${data.updated} opdateret`);
      if (data.completed > 0) parts.push(`${data.completed} afsluttet`);
      const msg = parts.length > 0
        ? `Sync OK: ${parts.join(", ")}`
        : "Sync OK: Alt er opdateret";
      if (data.errors && data.errors.length > 0) {
        showSyncToast(`${msg} (${data.errors.length} fejl)`, "error");
      } else {
        showSyncToast(msg, "success");
      }
      await fetchTodos();
    }
  } catch (e) {
    btn.classList.add("sync-error");
    label.textContent = "Sync fejlet";
    showSyncToast("Kunne ikke forbinde til serveren.", "error");
  }

  icon.classList.remove("spinning");
  btn.disabled = false;
  syncInProgress = false;

  setTimeout(() => {
    btn.classList.remove("sync-success", "sync-error");
    label.textContent = "Sync Todoist";
  }, 3000);
}

function showSyncToast(message, type) {
  let toast = document.querySelector(".sync-toast");
  if (!toast) {
    toast = document.createElement("div");
    toast.className = "sync-toast";
    document.body.appendChild(toast);
  }

  toast.textContent = message;
  toast.classList.remove("toast-success", "toast-error", "toast-visible");
  toast.classList.add(type === "success" ? "toast-success" : "toast-error");

  // Trigger reflow for animation reset
  void toast.offsetWidth;
  toast.classList.add("toast-visible");

  clearTimeout(toast._hideTimer);
  toast._hideTimer = setTimeout(() => {
    toast.classList.remove("toast-visible");
  }, 4000);
}

async function checkSyncStatus() {
  try {
    const res = await fetch("/api/sync/status");
    const data = await res.json();
    const btn = document.getElementById("sync-btn");
    if (!data.configured) {
      btn.title = "Konfigurer API token i config.py";
    }
  } catch (e) {
    // Ignore — server might not be running
  }
}

// ── Init ─────────────────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Restore theme
  if (localStorage.getItem("theme") === "dark") {
    document.documentElement.classList.add("dark");
    document.getElementById("theme-label").textContent = "☀  Lyst tema";
  }

  // Enter key on add input
  document.getElementById("add-text").addEventListener("keydown", e => {
    if (e.key === "Enter") handleAdd();
  });

  // Escape closes modal
  document.addEventListener("keydown", e => {
    if (e.key === "Escape") closeModal();
  });

  // Click outside modal
  document.getElementById("modal-overlay").addEventListener("click", e => {
    if (e.target === e.currentTarget) closeModal();
  });

  fetchTodos();
  checkSyncStatus();
});
