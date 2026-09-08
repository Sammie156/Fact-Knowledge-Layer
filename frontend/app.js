/**
 * Fact Knowledge Layer - Frontend Application Logic
 * Communicates with FastAPI REST API endpoints.
 */

const API_BASE = window.location.port === "8000" ? "/api" : "http://localhost:8000/api";

const state = {
  activeTab: "relationships",
  relationshipFilter: "all",
  documents: [],
  relationships: [],
  facts: [],
  showcase: null,
  activeUploadId: null,
  pollingTimer: null,
};

// ============================================================================
// Initialization & Lifecycle
// ============================================================================

document.addEventListener("DOMContentLoaded", () => {
  initTabs();
  initUpload();
  initFilters();
  initSearch();
  initActions();

  // Initial Data Fetch
  checkApiHealth();
  refreshAll();

  // Polling health every 30s
  setInterval(checkApiHealth, 30000);
});

async function refreshAll() {
  await Promise.all([
    fetchStats(),
    fetchDocuments(),
    fetchRelationships(),
    fetchShowcase(),
    fetchFacts(),
  ]);
}

// ============================================================================
// API Health & Stats
// ============================================================================

async function checkApiHealth() {
  const badge = document.getElementById("api-status-badge");
  const text = document.getElementById("api-status-text");

  try {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error("API returned non-200");
    const data = await res.json();

    if (data.status === "healthy") {
      badge.classList.remove("offline");
      text.textContent = "API & DB Connected";
    } else {
      badge.classList.add("offline");
      text.textContent = "Database Degraded";
    }
  } catch (err) {
    badge.classList.add("offline");
    text.textContent = "API Offline";
  }
}

async function fetchStats() {
  try {
    const res = await fetch(`${API_BASE}/stats`);
    if (!res.ok) return;
    const stats = await res.json();

    document.getElementById("stat-docs").textContent = stats.total_documents || 0;
    document.getElementById("stat-facts").textContent = stats.total_facts || 0;

    const relTypes = stats.relationships_by_type || {};
    document.getElementById("stat-corrob").textContent = relTypes.corroborates || 0;
    document.getElementById("stat-contradict").textContent = relTypes.contradicts || 0;
    document.getElementById("stat-context").textContent = relTypes.context_explained || 0;
  } catch (err) {
    console.error("Failed to load stats", err);
  }
}

// ============================================================================
// Navigation Tabs
// ============================================================================

function initTabs() {
  const tabButtons = document.querySelectorAll(".tab-btn");
  tabButtons.forEach(btn => {
    btn.addEventListener("click", () => {
      const targetTab = btn.getAttribute("data-tab");
      switchTab(targetTab);
    });
  });
}

function switchTab(tabId) {
  state.activeTab = tabId;

  document.querySelectorAll(".tab-btn").forEach(btn => {
    btn.classList.toggle("active", btn.getAttribute("data-tab") === tabId);
  });

  document.querySelectorAll(".tab-pane").forEach(pane => {
    pane.classList.toggle("active", pane.id === `pane-${tabId}`);
  });

  if (tabId === "relationships") fetchRelationships();
  if (tabId === "showcase") fetchShowcase();
  if (tabId === "facts") fetchFacts();
  if (tabId === "upload") fetchDocuments();
}

// ============================================================================
// Relationships Dashboard
// ============================================================================

function initFilters() {
  const chips = document.querySelectorAll(".filter-chips .chip");
  chips.forEach(chip => {
    chip.addEventListener("click", () => {
      chips.forEach(c => c.classList.remove("active"));
      chip.classList.add("active");
      state.relationshipFilter = chip.getAttribute("data-filter");
      fetchRelationships();
    });
  });
}

async function fetchRelationships() {
  const container = document.getElementById("relationships-list");
  container.innerHTML = `
    <div class="loading-spinner-state">
      <div class="spinner"></div>
      <p>Loading cross-document reasoning relationships...</p>
    </div>
  `;

  try {
    let url = `${API_BASE}/relationships?limit=100`;
    if (state.relationshipFilter && state.relationshipFilter !== "all") {
      url += `&relationship_type=${encodeURIComponent(state.relationshipFilter)}`;
    }

    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load relationships");
    const data = await res.json();
    state.relationships = data;

    document.getElementById("tab-count-relationships").textContent = data.length;

    renderRelationships(data);
  } catch (err) {
    container.innerHTML = `
      <div class="loading-spinner-state">
        <p style="color: var(--color-contradict);">Error loading relationships: ${err.message}</p>
      </div>
    `;
  }
}

function renderRelationships(list) {
  const container = document.getElementById("relationships-list");
  if (!list || list.length === 0) {
    container.innerHTML = `
      <div class="loading-spinner-state">
        <p>No relationships found for this filter. Upload multiple PDFs to trigger cross-document reasoning!</p>
      </div>
    `;
    return;
  }

  container.innerHTML = list.map(rel => {
    const typeLabel = rel.relationship_type.replace("_", " ");
    const confPct = rel.confidence ? Math.round(rel.confidence * 100) : 90;

    return `
      <article class="relationship-card">
        <div class="rel-header">
          <span class="rel-type-pill ${rel.relationship_type}">
            ${typeLabel}
          </span>
          <span class="rel-confidence">Confidence: ${confPct}%</span>
        </div>

        <div class="comparison-grid">
          <!-- Fact A -->
          <div class="fact-box">
            <div class="fact-doc-tag">
              <span class="doc-name" title="${escapeHtml(rel.fact_a.document_filename || 'Doc A')}">
                ${escapeHtml(rel.fact_a.document_filename || 'Doc A')}
              </span>
              <span class="page-pill">p. ${rel.fact_a.page_number}</span>
            </div>
            <div class="fact-main-line">
              <span class="fact-entity">${escapeHtml(rel.fact_a.entity)}</span>
              <span class="fact-attribute">&bull; ${escapeHtml(rel.fact_a.attribute)}</span>
            </div>
            <div class="fact-value-badge">
              ${escapeHtml(rel.fact_a.value)} ${escapeHtml(rel.fact_a.unit || '')}
            </div>
            <div class="fact-meta-tags">
              ${rel.fact_a.time_scope ? `<span class="meta-chip">${escapeHtml(rel.fact_a.time_scope)}</span>` : ''}
            </div>
            <div class="evidence-quote">
              &ldquo;${escapeHtml(rel.fact_a.raw_text)}&rdquo;
            </div>
          </div>

          <!-- Fact B -->
          <div class="fact-box">
            <div class="fact-doc-tag">
              <span class="doc-name" title="${escapeHtml(rel.fact_b.document_filename || 'Doc B')}">
                ${escapeHtml(rel.fact_b.document_filename || 'Doc B')}
              </span>
              <span class="page-pill">p. ${rel.fact_b.page_number}</span>
            </div>
            <div class="fact-main-line">
              <span class="fact-entity">${escapeHtml(rel.fact_b.entity)}</span>
              <span class="fact-attribute">&bull; ${escapeHtml(rel.fact_b.attribute)}</span>
            </div>
            <div class="fact-value-badge">
              ${escapeHtml(rel.fact_b.value)} ${escapeHtml(rel.fact_b.unit || '')}
            </div>
            <div class="fact-meta-tags">
              ${rel.fact_b.time_scope ? `<span class="meta-chip">${escapeHtml(rel.fact_b.time_scope)}</span>` : ''}
            </div>
            <div class="evidence-quote">
              &ldquo;${escapeHtml(rel.fact_b.raw_text)}&rdquo;
            </div>
          </div>
        </div>

        <div class="reasoning-box">
          <strong>System Reasoning:</strong> ${escapeHtml(rel.explanation || 'No explanation provided.')}
        </div>
      </article>
    `;
  }).join("");
}

// ============================================================================
// The Four Required Cases (Showcase)
// ============================================================================

async function fetchShowcase() {
  const container = document.getElementById("showcase-cards-container");
  try {
    const res = await fetch(`${API_BASE}/showcase`);
    if (!res.ok) throw new Error("Failed to load showcase");
    const data = await res.json();
    state.showcase = data;

    renderShowcase(data.cases);
  } catch (err) {
    container.innerHTML = `<div class="loading-spinner-state"><p>Failed to load showcase: ${err.message}</p></div>`;
  }
}

function renderShowcase(cases) {
  const container = document.getElementById("showcase-cards-container");
  if (!cases) return;

  container.innerHTML = cases.map(c => {
    let caseBody = "";

    if (c.relationship) {
      const rel = c.relationship;
      caseBody = `
        <div class="comparison-grid">
          <div class="fact-box">
            <div class="fact-doc-tag">
              <span class="doc-name">${escapeHtml(rel.fact_a.document_filename || '')}</span>
              <span class="page-pill">p. ${rel.fact_a.page_number}</span>
            </div>
            <div class="fact-main-line">
              <span class="fact-entity">${escapeHtml(rel.fact_a.entity)}</span>
              <span class="fact-attribute">&bull; ${escapeHtml(rel.fact_a.attribute)}</span>
            </div>
            <div class="fact-value-badge">${escapeHtml(rel.fact_a.value)} ${escapeHtml(rel.fact_a.unit || '')}</div>
            <div class="evidence-quote">&ldquo;${escapeHtml(rel.fact_a.raw_text)}&rdquo;</div>
          </div>

          <div class="fact-box">
            <div class="fact-doc-tag">
              <span class="doc-name">${escapeHtml(rel.fact_b.document_filename || '')}</span>
              <span class="page-pill">p. ${rel.fact_b.page_number}</span>
            </div>
            <div class="fact-main-line">
              <span class="fact-entity">${escapeHtml(rel.fact_b.entity)}</span>
              <span class="fact-attribute">&bull; ${escapeHtml(rel.fact_b.attribute)}</span>
            </div>
            <div class="fact-value-badge">${escapeHtml(rel.fact_b.value)} ${escapeHtml(rel.fact_b.unit || '')}</div>
            <div class="evidence-quote">&ldquo;${escapeHtml(rel.fact_b.raw_text)}&rdquo;</div>
          </div>
        </div>
        <div class="reasoning-box">
          <strong>System Reasoning:</strong> ${escapeHtml(rel.explanation || '')}
        </div>
      `;
    } else if (c.details && c.details.canonical_example) {
      const canon = c.details.canonical_example;
      caseBody = `
        <div class="failure-diagnostic">
          <div class="diagnostic-item">
            <strong>Subject:</strong>
            <span>${escapeHtml(canon.subject || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Evidence Document 1:</strong>
            <span class="evidence-quote" style="display:block; margin-top:4px;">&ldquo;${escapeHtml(canon.doc_1_evidence || canon.doc_1_value || '')}&rdquo;</span>
          </div>
          <div class="diagnostic-item">
            <strong>Evidence Document 2:</strong>
            <span class="evidence-quote" style="display:block; margin-top:4px;">&ldquo;${escapeHtml(canon.doc_2_evidence || canon.doc_2_value || '')}&rdquo;</span>
          </div>
          <div class="diagnostic-item" style="border-top:1px solid var(--border-subtle); padding-top:8px;">
            <strong>System Reasoning:</strong>
            <span>${escapeHtml(canon.system_reasoning || '')}</span>
          </div>
        </div>
      `;
    } else if (c.case_number === 4 && c.details) {
      caseBody = `
        <div class="failure-diagnostic">
          <div class="diagnostic-item">
            <strong>Failure Discovered:</strong>
            <span>${escapeHtml(c.details.failure_discovered || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Root Cause:</strong>
            <span>${escapeHtml(c.details.root_cause || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>How We Handled It:</strong>
            <span style="white-space: pre-line;">${escapeHtml(c.details.how_handled || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Proposed Architectural Improvements:</strong>
            <span>${escapeHtml(c.details.proposed_improvements || '')}</span>
          </div>
        </div>
      `;
    }

    return `
      <div class="showcase-card">
        <div class="case-num-pill">Case #${c.case_number}</div>
        <h3>${escapeHtml(c.title)}</h3>
        <p class="case-desc">${escapeHtml(c.requirement)}</p>
        ${caseBody}
      </div>
    `;
  }).join("");
}

// ============================================================================
// Grounded Facts Explorer
// ============================================================================

function initSearch() {
  const searchInput = document.getElementById("facts-search-input");
  let debounceTimeout;

  searchInput.addEventListener("input", () => {
    clearTimeout(debounceTimeout);
    debounceTimeout = setTimeout(() => {
      fetchFacts();
    }, 300);
  });

  document.getElementById("facts-doc-filter").addEventListener("change", () => {
    fetchFacts();
  });
}

async function fetchFacts() {
  const container = document.getElementById("facts-container");
  const search = document.getElementById("facts-search-input").value.trim();
  const docId = document.getElementById("facts-doc-filter").value;

  let url = `${API_BASE}/facts?limit=60`;
  if (search) url += `&search=${encodeURIComponent(search)}`;
  if (docId) url += `&document_id=${encodeURIComponent(docId)}`;

  try {
    const res = await fetch(url);
    if (!res.ok) throw new Error("Failed to load facts");
    const data = await res.json();
    state.facts = data;

    document.getElementById("tab-count-facts").textContent = data.length;

    renderFacts(data);
  } catch (err) {
    container.innerHTML = `<div class="loading-spinner-state"><p>Error: ${err.message}</p></div>`;
  }
}

function renderFacts(facts) {
  const container = document.getElementById("facts-container");
  if (!facts || facts.length === 0) {
    container.innerHTML = `<div class="loading-spinner-state"><p>No facts found.</p></div>`;
    return;
  }

  container.innerHTML = facts.map(f => `
    <div class="fact-item-card">
      <div>
        <div class="fact-doc-tag">
          <span class="doc-name">${escapeHtml(f.document_filename || '')}</span>
          <span class="page-pill">p. ${f.page_number}</span>
        </div>
        <div class="fact-main-line">
          <span class="fact-entity">${escapeHtml(f.entity)}</span>
          <span class="fact-attribute">&bull; ${escapeHtml(f.attribute)}</span>
        </div>
        <div class="fact-value-badge">${escapeHtml(f.value)} ${escapeHtml(f.unit || '')}</div>
        ${f.time_scope ? `<div class="fact-meta-tags"><span class="meta-chip">${escapeHtml(f.time_scope)}</span></div>` : ''}
      </div>
      <div class="evidence-quote">&ldquo;${escapeHtml(f.raw_text)}&rdquo;</div>
    </div>
  `).join("");
}

// ============================================================================
// PDF Upload & Document Management
// ============================================================================

function initUpload() {
  const dropzone = document.getElementById("pdf-dropzone");
  const fileInput = document.getElementById("file-input");

  dropzone.addEventListener("click", () => fileInput.click());

  dropzone.addEventListener("dragover", (e) => {
    e.preventDefault();
    dropzone.classList.add("drag-over");
  });

  dropzone.addEventListener("dragleave", () => {
    dropzone.classList.remove("drag-over");
  });

  dropzone.addEventListener("drop", (e) => {
    e.preventDefault();
    dropzone.classList.remove("drag-over");
    if (e.dataTransfer.files.length > 0) {
      handleFileSelected(e.dataTransfer.files[0]);
    }
  });

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileSelected(fileInput.files[0]);
    }
  });
}

async function handleFileSelected(file) {
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    showToast("Please select a valid PDF file.", "error");
    return;
  }

  const progressCard = document.getElementById("upload-progress-card");
  const filenameEl = document.getElementById("active-upload-filename");
  const statusEl = document.getElementById("active-upload-status");
  const msgEl = document.getElementById("active-upload-msg");

  filenameEl.textContent = file.name;
  statusEl.textContent = "Uploading...";
  statusEl.className = "status-chip chip-processing";
  msgEl.textContent = "Uploading document to Fact Knowledge Layer API...";
  progressCard.classList.remove("hidden");

  const formData = new FormData();
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/documents/upload?background=true&replace=true`, {
      method: "POST",
      body: formData,
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Upload failed");
    }

    const data = await res.json();
    state.activeUploadId = data.document_id;
    showToast(`Upload accepted: ${file.name}`, "info");

    startPollingDocument(data.document_id);
  } catch (err) {
    statusEl.textContent = "Failed";
    statusEl.className = "status-chip chip-failed";
    msgEl.textContent = `Error: ${err.message}`;
    showToast(`Upload failed: ${err.message}`, "error");
  }
}

function startPollingDocument(docId) {
  if (state.pollingTimer) clearInterval(state.pollingTimer);

  const statusEl = document.getElementById("active-upload-status");
  const msgEl = document.getElementById("active-upload-msg");
  const stepExtract = document.getElementById("step-extract");
  const stepCompare = document.getElementById("step-compare");

  state.pollingTimer = setInterval(async () => {
    try {
      const res = await fetch(`${API_BASE}/documents/${docId}`);
      if (!res.ok) return;
      const doc = await res.json();

      statusEl.textContent = doc.status;

      if (doc.status === "extracting_facts") {
        stepExtract.classList.add("active");
        msgEl.textContent = "Batching chunks & extracting structured facts with Gemini...";
      } else if (doc.status === "comparing_facts") {
        stepExtract.classList.add("active");
        stepCompare.classList.add("active");
        msgEl.textContent = "Retrieving candidate facts via pgvector & reasoning over relationships...";
      } else if (doc.status === "done") {
        clearInterval(state.pollingTimer);
        statusEl.className = "status-chip chip-done";
        statusEl.textContent = "Completed";
        msgEl.textContent = `Pipeline finished! Extracted ${doc.fact_count} facts across ${doc.page_count} pages.`;
        showToast(`Document ${doc.filename} fully processed!`, "success");
        refreshAll();
      } else if (doc.status === "failed") {
        clearInterval(state.pollingTimer);
        statusEl.className = "status-chip chip-failed";
        msgEl.textContent = "Processing failed. Check backend server logs.";
        showToast("Processing failed", "error");
      }
    } catch (err) {
      console.error("Polling error", err);
    }
  }, 2500);
}

async function fetchDocuments() {
  const container = document.getElementById("documents-container");
  const dropdown = document.getElementById("facts-doc-filter");

  try {
    const res = await fetch(`${API_BASE}/documents`);
    if (!res.ok) throw new Error("Failed to load documents");
    const docs = await res.json();
    state.documents = docs;

    document.getElementById("tab-count-docs").textContent = docs.length;

    // Populate dropdown in Facts tab
    dropdown.innerHTML = `<option value="">All Documents (${docs.length})</option>` +
      docs.map(d => `<option value="${d.id}">${escapeHtml(d.filename)}</option>`).join("");

    if (!docs || docs.length === 0) {
      container.innerHTML = `<div class="loading-spinner-state"><p>No documents uploaded yet.</p></div>`;
      return;
    }

    container.innerHTML = docs.map(d => `
      <div class="doc-item-row">
        <div class="doc-info">
          <h4>${escapeHtml(d.filename)}</h4>
          <div class="doc-submeta">
            <span>${d.page_count || 0} pages</span>
            <span>&bull;</span>
            <span>${d.fact_count || 0} facts</span>
            <span>&bull;</span>
            <span>${d.relationship_count || 0} links</span>
            <span>&bull;</span>
            <span class="status-chip chip-${d.status === 'done' ? 'done' : d.status === 'failed' ? 'failed' : 'processing'}">${d.status}</span>
          </div>
        </div>
        <div class="doc-actions">
          <button class="btn-icon" onclick="deleteDocument('${d.id}')" title="Delete document">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="3 6 5 6 21 6"></polyline>
              <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
            </svg>
          </button>
        </div>
      </div>
    `).join("");
  } catch (err) {
    container.innerHTML = `<div class="loading-spinner-state"><p>Error loading documents: ${err.message}</p></div>`;
  }
}

async function deleteDocument(docId) {
  if (!confirm("Are you sure you want to delete this document and its associated facts?")) return;

  try {
    const res = await fetch(`${API_BASE}/documents/${docId}`, { method: "DELETE" });
    if (!res.ok) throw new Error("Delete failed");
    showToast("Document deleted.", "info");
    refreshAll();
  } catch (err) {
    showToast(`Error: ${err.message}`, "error");
  }
}

// ============================================================================
// General Actions & Helpers
// ============================================================================

function initActions() {
  document.getElementById("btn-refresh-relationships").addEventListener("click", () => {
    fetchRelationships();
    fetchStats();
  });

  document.getElementById("btn-refresh-docs").addEventListener("click", () => {
    fetchDocuments();
  });

  document.getElementById("btn-recompare").addEventListener("click", async () => {
    try {
      const res = await fetch(`${API_BASE}/relationships/compare`, { method: "POST" });
      if (!res.ok) throw new Error("Re-comparison trigger failed");
      showToast("Cross-document comparison initiated in background.", "info");
      setTimeout(() => {
        fetchRelationships();
        fetchStats();
      }, 3000);
    } catch (err) {
      showToast(err.message, "error");
    }
  });
}

function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 3500);
}

function escapeHtml(str) {
  if (!str) return "";
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
