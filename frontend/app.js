/**
 * Fact Knowledge Layer - Frontend Application Logic
 * Communicates with FastAPI REST API endpoints.
 */

const API_BASE = window.location.protocol.startsWith("http")
  ? `${window.location.origin}/api`
  : "http://localhost:8000/api";

const state = {
  activeTab: "relationships",
  relationshipFilter: "all",
  documents: [],
  relationships: [],
  facts: [],
  showcase: null,
  activeUploadId: null,
  pollingTimer: null,
  settings: null,
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
  initSettingsModal();

  // Initial Data Fetch
  checkApiHealth();
  fetchSettings();
  refreshAll();

  // Polling health every 30s
  setInterval(checkApiHealth, 30000);
});

async function refreshAll() {
  await Promise.all([
    fetchStats(),
    fetchDocuments(),
    fetchRelationships(),
    fetchDiagnostics(),
    fetchFacts(),
  ]);
  if (state.activeTab === "graph") {
    initGraph();
  }
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
  if (tabId === "graph") initGraph();
  if (tabId === "facts") fetchFacts();
  if (tabId === "diagnostics" || tabId === "showcase") fetchDiagnostics();
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
// Audit & Diagnostics
// ============================================================================

async function fetchDiagnostics() {
  const container = document.getElementById("diagnostics-cards-container") || document.getElementById("showcase-cards-container");
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/showcase`);
    if (!res.ok) throw new Error("Failed to load diagnostics");
    const data = await res.json();
    state.showcase = data;

    renderDiagnostics(data.cases);
  } catch (err) {
    container.innerHTML = `<div class="loading-spinner-state"><p>Failed to load diagnostics: ${err.message}</p></div>`;
  }
}

const fetchShowcase = fetchDiagnostics;

function renderDiagnostics(cases) {
  const container = document.getElementById("diagnostics-cards-container") || document.getElementById("showcase-cards-container");
  if (!cases || !container) return;

  const categoryBadges = {
    1: `<span class="diag-type-badge corrob"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg> Verified Corroboration Profile</span>`,
    2: `<span class="diag-type-badge contradict"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg> Conflicting Claims Profile</span>`,
    3: `<span class="diag-type-badge context"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg> Context Reconciliation Profile</span>`,
    4: `<span class="diag-type-badge failure"><svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg> Extraction &amp; Table Diagnostic</span>`
  };

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
          <strong>Resolution Reasoning:</strong> ${escapeHtml(rel.explanation || '')}
        </div>
      `;
    } else if (c.details && c.details.canonical_example) {
      const canon = c.details.canonical_example;
      caseBody = `
        <div class="failure-diagnostic">
          <div class="diagnostic-item">
            <strong>Target Entity &amp; Metric:</strong>
            <span>${escapeHtml(canon.subject || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Document 1 Source Quote:</strong>
            <span class="evidence-quote" style="display:block; margin-top:4px;">&ldquo;${escapeHtml(canon.doc_1_evidence || canon.doc_1_value || '')}&rdquo;</span>
          </div>
          <div class="diagnostic-item">
            <strong>Document 2 Source Quote:</strong>
            <span class="evidence-quote" style="display:block; margin-top:4px;">&ldquo;${escapeHtml(canon.doc_2_evidence || canon.doc_2_value || '')}&rdquo;</span>
          </div>
          <div class="diagnostic-item" style="border-top:1px solid var(--border-subtle); padding-top:8px;">
            <strong>Contextual Resolution:</strong>
            <span>${escapeHtml(canon.system_reasoning || '')}</span>
          </div>
        </div>
      `;
    } else if (c.case_number === 4 && c.details) {
      caseBody = `
        <div class="failure-diagnostic">
          <div class="diagnostic-item">
            <strong>Diagnostic Anomaly Detected:</strong>
            <span>${escapeHtml(c.details.failure_discovered || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Root Cause Analysis:</strong>
            <span>${escapeHtml(c.details.root_cause || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Active Mitigation &amp; Guardrails:</strong>
            <span style="white-space: pre-line;">${escapeHtml(c.details.how_handled || '')}</span>
          </div>
          <div class="diagnostic-item">
            <strong>Architectural Recovery Roadmap:</strong>
            <span>${escapeHtml(c.details.proposed_improvements || '')}</span>
          </div>
        </div>
      `;
    }

    return `
      <div class="showcase-card">
        ${categoryBadges[c.case_number] || ''}
        <h3>${escapeHtml(c.title)}</h3>
        <p class="case-desc">${escapeHtml(c.requirement)}</p>
        ${caseBody}
      </div>
    `;
  }).join("");
}

const renderShowcase = renderDiagnostics;

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
  
  const alertBox = document.getElementById("upload-alert-box");
  if (alertBox) alertBox.classList.add("hidden");

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
        msgEl.textContent = "Batching chunks & extracting structured facts...";
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
      } else if (doc.status === "quota_exceeded" || doc.status === "failed") {
        clearInterval(state.pollingTimer);
        const isQuota = doc.status === "quota_exceeded";
        statusEl.className = `status-chip ${isQuota ? "chip-quota" : "chip-failed"}`;
        statusEl.textContent = isQuota ? "Quota Exceeded" : "Failed";

        const alertBox = document.getElementById("upload-alert-box");
        const alertTitle = document.getElementById("upload-alert-title");
        const alertDesc = document.getElementById("upload-alert-desc");

        if (alertBox) {
          alertBox.classList.remove("hidden");
          alertBox.classList.toggle("alert-quota", isQuota);
          if (alertTitle) {
            alertTitle.textContent = isQuota
              ? "⚡ Ingestion Paused: Daily Quota Limit Hit"
              : "Pipeline Processing Error";
          }
          if (alertDesc) {
            alertDesc.textContent = doc.error_message || "An error occurred during processing.";
          }
        }

        const pill = document.getElementById("llm-active-pill");
        if (pill && isQuota) {
          pill.classList.add("quota-warning");
        }

        showToast(
          isQuota ? "Daily quota exceeded! Switch to Groq in Settings (⚙️)." : `Processing failed: ${doc.error_message || "Unknown error"}`,
          "error"
        );
        refreshAll();
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

    container.innerHTML = docs.map(d => {
      const isQuota = d.status === "quota_exceeded";
      const statusClass = d.status === "done" ? "done" : (isQuota ? "quota" : (d.status === "failed" ? "failed" : "processing"));
      const statusLabel = isQuota ? "Quota Exceeded" : d.status;

      return `
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
              <span class="status-chip chip-${statusClass}">${statusLabel}</span>
            </div>
            ${d.error_message ? `<div style="font-size: 11px; color: ${isQuota ? 'var(--color-context)' : 'var(--color-contradict)'}; margin-top: 4px; line-height: 1.35;">⚠️ ${escapeHtml(d.error_message)}</div>` : ''}
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
      `;
    }).join("");
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

  const resetBtn = document.getElementById("btn-reset-system");
  if (resetBtn) {
    resetBtn.addEventListener("click", resetEntireSystem);
  }

  const openSettingsFromAlert = document.getElementById("btn-open-settings-from-alert");
  if (openSettingsFromAlert) {
    openSettingsFromAlert.addEventListener("click", () => {
      const openBtn = document.getElementById("btn-open-settings");
      if (openBtn) openBtn.click();
    });
  }
}

async function resetEntireSystem() {
  const confirmed = confirm(
    "⚠️ DANGER: Are you sure you want to completely reset the Knowledge Layer?\n\nThis will permanently delete:\n• All uploaded documents\n• All extracted chunks\n• All grounded facts & vector embeddings\n• All cross-document relationships\n\nThis action cannot be undone."
  );
  if (!confirmed) return;

  try {
    const res = await fetch(`${API_BASE}/documents/reset`, { method: "POST" });
    if (!res.ok) throw new Error("Reset request failed");
    const data = await res.json();
    showToast(data.message || "Knowledge layer reset successfully.", "info");
    await refreshAll();
  } catch (err) {
    showToast(`Reset failed: ${err.message}`, "error");
  }
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

// ============================================================================
// Settings & Multi-Provider LLM Switcher
// ============================================================================

async function fetchSettings() {
  try {
    const res = await fetch(`${API_BASE}/settings`);
    if (!res.ok) return;
    const data = await res.json();
    state.settings = data;

    const labelEl = document.getElementById("active-llm-label");
    const pillEl = document.getElementById("llm-active-pill");
    const cbText = document.getElementById("cb-status-text");

    const isGroq = data.active_provider === "groq";
    if (labelEl) {
      labelEl.textContent = isGroq ? `Groq (${data.active_model})` : `Gemini (${data.active_model})`;
    }
    if (pillEl) {
      pillEl.classList.toggle("groq", isGroq);
    }

    if (cbText) {
      cbText.textContent = data.circuit_breaker_enabled ? "active (Groq configured)" : "inactive";
      cbText.style.color = data.circuit_breaker_enabled ? "var(--color-corrob)" : "var(--color-context)";
    }
  } catch (err) {
    console.error("Failed to load settings", err);
  }
}

function initSettingsModal() {
  const modal = document.getElementById("settings-modal");
  const openBtn = document.getElementById("btn-open-settings");
  const closeBtn = document.getElementById("btn-close-settings");
  const cancelBtn = document.getElementById("btn-cancel-settings");
  const saveBtn = document.getElementById("btn-save-settings");

  if (!modal || !openBtn) return;

  const radioInputs = document.querySelectorAll('input[name="llm-provider-radio"]');
  const modelSelect = document.getElementById("settings-model-select");
  const apiKeyInput = document.getElementById("settings-api-key");
  const customModelWrap = document.getElementById("custom-model-wrap");
  const customModelInput = document.getElementById("settings-custom-model");

  function getEffectiveModel() {
    if (modelSelect.value === "__custom__") {
      return customModelInput.value.trim();
    }
    return modelSelect.value;
  }

  function openModal() {
    if (!state.settings) return;
    const cur = state.settings;

    radioInputs.forEach(r => {
      r.checked = r.value === cur.active_provider;
      const card = r.closest(".provider-card");
      if (card) card.classList.toggle("active", r.checked);
    });

    populateModels(cur.active_provider, cur.active_model);
    apiKeyInput.value = "";
    const testStatus = document.getElementById("test-connection-status");
    if (testStatus) {
      testStatus.textContent = "";
      testStatus.className = "test-status-text";
    }
    modal.classList.remove("hidden");
  }

  function closeModal() {
    modal.classList.add("hidden");
  }

  function populateModels(providerId, selectedModel) {
    if (!state.settings) return;
    const provider = state.settings.providers.find(p => p.id === providerId);
    if (!provider) return;

    const available = provider.available_models || [];
    const isCustom = selectedModel && !available.includes(selectedModel);

    let html = available
      .map(m => `<option value="${m}" ${(!isCustom && m === selectedModel) ? "selected" : ""}>${m}</option>`)
      .join("");
    html += `<option value="__custom__" ${isCustom ? "selected" : ""}>⚙️ Custom / Specify Model ID...</option>`;
    modelSelect.innerHTML = html;

    if (isCustom) {
      customModelWrap.classList.remove("hidden");
      customModelInput.value = selectedModel;
    } else {
      customModelWrap.classList.add("hidden");
      customModelInput.value = "";
    }
  }

  modelSelect.addEventListener("change", () => {
    if (modelSelect.value === "__custom__") {
      customModelWrap.classList.remove("hidden");
      customModelInput.focus();
    } else {
      customModelWrap.classList.add("hidden");
    }
  });

  async function refreshAvailableModels() {
    const checkedRadio = document.querySelector('input[name="llm-provider-radio"]:checked');
    if (!checkedRadio) return;
    const prov = checkedRadio.value;
    const key = apiKeyInput.value.trim();
    try {
      const url = `${API_BASE}/settings/models?provider=${prov}${key ? `&api_key=${encodeURIComponent(key)}` : ""}`;
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();
      if (data.models && data.models.length > 0) {
        const p = state.settings?.providers?.find(pr => pr.id === prov);
        if (p) p.available_models = data.models;
        const curModel = getEffectiveModel();
        populateModels(prov, curModel);
      }
    } catch (e) {
      console.warn("Could not dynamically refresh models", e);
    }
  }

  apiKeyInput.addEventListener("change", refreshAvailableModels);

  openBtn.addEventListener("click", openModal);
  if (closeBtn) closeBtn.addEventListener("click", closeModal);
  if (cancelBtn) cancelBtn.addEventListener("click", closeModal);

  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });

  radioInputs.forEach(r => {
    r.addEventListener("change", () => {
      document.querySelectorAll(".provider-card").forEach(c => c.classList.remove("active"));
      r.closest(".provider-card").classList.add("active");
      populateModels(r.value, null);
      refreshAvailableModels();
    });
  });

  const testBtn = document.getElementById("btn-test-connection");
  const testStatus = document.getElementById("test-connection-status");

  if (testBtn) {
    testBtn.addEventListener("click", async () => {
      const checkedRadio = document.querySelector('input[name="llm-provider-radio"]:checked');
      if (!checkedRadio) return;
      const selectedProvider = checkedRadio.value;
      const selectedModel = getEffectiveModel();
      const apiKey = apiKeyInput.value.trim();

      if (!selectedModel) {
        showToast("Please select or enter a valid Model ID to test.", "warning");
        return;
      }

      if (testStatus) {
        testStatus.className = "test-status-text";
        testStatus.textContent = "Testing connection...";
      }
      testBtn.disabled = true;

      try {
        const payload = {
          provider: selectedProvider,
          model: selectedModel,
        };
        if (apiKey) payload.api_key = apiKey;

        const res = await fetch(`${API_BASE}/settings/test`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        const data = await res.json();
        if (testStatus) {
          if (data.success) {
            testStatus.className = "test-status-text success";
            testStatus.textContent = `✅ ${data.message}`;
          } else {
            testStatus.className = "test-status-text error";
            testStatus.textContent = `❌ ${data.message}`;
          }
        }
      } catch (err) {
        if (testStatus) {
          testStatus.className = "test-status-text error";
          testStatus.textContent = `❌ Test request failed: ${err.message}`;
        }
      } finally {
        testBtn.disabled = false;
      }
    });
  }

  if (saveBtn) {
    saveBtn.addEventListener("click", async () => {
      const checkedRadio = document.querySelector('input[name="llm-provider-radio"]:checked');
      if (!checkedRadio) return;
      const selectedProvider = checkedRadio.value;
      const selectedModel = getEffectiveModel();
      const apiKey = apiKeyInput.value.trim();

      if (!selectedModel) {
        showToast("Please enter a valid Model ID.", "warning");
        return;
      }

      saveBtn.textContent = "Saving...";
      saveBtn.disabled = true;

      try {
        const payload = {
          provider: selectedProvider,
          model: selectedModel,
        };
        if (apiKey) payload.api_key = apiKey;

        const res = await fetch(`${API_BASE}/settings`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(payload),
        });

        if (!res.ok) {
          const err = await res.json();
          throw new Error(err.detail || "Failed to save settings");
        }

        const updated = await res.json();
        state.settings = updated;
        await fetchSettings();
        showToast(`Active LLM switched to ${selectedProvider.toUpperCase()} (${selectedModel})`, "success");
        closeModal();
      } catch (err) {
        showToast(`Error: ${err.message}`, "error");
      } finally {
        saveBtn.textContent = "Apply Settings";
        saveBtn.disabled = false;
      }
    });
  }
}

// ============================================================================
// Obsidian-Style Force-Directed Graph View (D3.js)
// ============================================================================

let graphSimulation = null;
let graphZoom = null;
let isGraphControlsInitialized = false;
let showDocLinks = true;

async function initGraph() {
  const container = document.getElementById("graph-canvas-container");
  const svgEl = document.getElementById("graph-svg");
  if (!container || !svgEl) return;

  if (typeof d3 === "undefined") {
    container.innerHTML = `
      <div class="loading-spinner-state" style="height: 100%;">
        <p style="color: var(--color-contradict);">D3.js library could not be loaded. Please check your network connection.</p>
      </div>
    `;
    return;
  }

  initGraphControlsOnce();

  try {
    const res = await fetch(`${API_BASE}/graph?include_isolated=true&max_facts=300`);
    if (!res.ok) throw new Error(`API returned status ${res.status}`);
    const graphData = await res.json();
    renderGraphVisualization(graphData);
  } catch (err) {
    console.error("Failed to load graph data:", err);
    showToast(`Error loading graph: ${err.message}`, "error");
  }
}

function initGraphControlsOnce() {
  if (isGraphControlsInitialized) return;
  isGraphControlsInitialized = true;

  const svg = d3.select("#graph-svg");

  const btnZoomIn = document.getElementById("btn-graph-zoom-in");
  if (btnZoomIn) {
    btnZoomIn.addEventListener("click", () => {
      if (graphZoom) svg.transition().duration(250).call(graphZoom.scaleBy, 1.35);
    });
  }

  const btnZoomOut = document.getElementById("btn-graph-zoom-out");
  if (btnZoomOut) {
    btnZoomOut.addEventListener("click", () => {
      if (graphZoom) svg.transition().duration(250).call(graphZoom.scaleBy, 0.74);
    });
  }

  const btnReset = document.getElementById("btn-graph-reset");
  if (btnReset) {
    btnReset.addEventListener("click", () => {
      if (graphZoom) svg.transition().duration(350).call(graphZoom.transform, d3.zoomIdentity);
    });
  }

  const btnToggleDocs = document.getElementById("btn-toggle-doc-links");
  if (btnToggleDocs) {
    btnToggleDocs.addEventListener("click", () => {
      showDocLinks = !showDocLinks;
      btnToggleDocs.classList.toggle("active", !showDocLinks);
      btnToggleDocs.textContent = showDocLinks ? "Toggle Doc Links" : "Show Doc Links";
      d3.selectAll(".link-contains").style("display", showDocLinks ? "" : "none");
    });
  }

  const closeInspectorBtn = document.getElementById("btn-close-inspector");
  if (closeInspectorBtn) {
    closeInspectorBtn.addEventListener("click", closeNodeInspector);
  }
}

function renderGraphVisualization(data) {
  const container = document.getElementById("graph-canvas-container");
  const svg = d3.select("#graph-svg");
  svg.selectAll("*").remove();

  if (!data || !data.nodes || data.nodes.length === 0) {
    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;
    svg.attr("width", width).attr("height", height);
    svg.append("text")
      .attr("x", width / 2)
      .attr("y", height / 2)
      .attr("text-anchor", "middle")
      .attr("fill", "#64748b")
      .attr("font-size", "14px")
      .text("No documents or facts in knowledge layer. Upload PDFs to generate graph.");
    return;
  }

  const width = container.clientWidth || 1000;
  const height = container.clientHeight || 680;
  svg.attr("width", width).attr("height", height);

  if (graphSimulation) {
    graphSimulation.stop();
  }

  // Deep clone data to avoid D3 mutation issues across re-renders
  const nodes = data.nodes.map(d => ({ ...d }));
  const links = data.links.map(d => ({ ...d }));

  // Index connections for fast Obsidian hover highlights
  const linkedByIndex = {};
  links.forEach(l => {
    const s = typeof l.source === "object" ? l.source.id : l.source;
    const t = typeof l.target === "object" ? l.target.id : l.target;
    linkedByIndex[`${s},${t}`] = true;
    linkedByIndex[`${t},${s}`] = true;
  });

  function isConnected(a, b) {
    return a.id === b.id || linkedByIndex[`${a.id},${b.id}`];
  }

  // Container group for pan & zoom
  const rootG = svg.append("g").attr("class", "graph-root");

  // D3 Zoom
  graphZoom = d3.zoom()
    .scaleExtent([0.15, 4.5])
    .on("zoom", (event) => {
      rootG.attr("transform", event.transform);
    });

  svg.call(graphZoom);

  // Background click closes inspector & resets focus
  svg.on("click", (event) => {
    if (event.target.tagName === "svg" || event.target.classList.contains("graph-root")) {
      closeNodeInspector();
      rootG.selectAll(".graph-node").classed("dimmed", false).classed("highlighted", false);
      rootG.selectAll(".graph-link").classed("dimmed", false).classed("highlighted", false);
    }
  });

  // SVG Glow Filter
  const defs = svg.append("defs");
  const filter = defs.append("filter")
    .attr("id", "neon-glow")
    .attr("x", "-50%")
    .attr("y", "-50%")
    .attr("width", "200%")
    .attr("height", "200%");
  filter.append("feGaussianBlur").attr("stdDeviation", "2.5").attr("result", "coloredBlur");
  const feMerge = filter.append("feMerge");
  feMerge.append("feMergeNode").attr("in", "coloredBlur");
  feMerge.append("feMergeNode").attr("in", "SourceGraphic");

  // Force Simulation setup
  graphSimulation = d3.forceSimulation(nodes)
    .force("link", d3.forceLink(links)
      .id(d => d.id)
      .distance(d => d.type === "contains" ? 70 : 160)
      .strength(d => d.type === "contains" ? 0.8 : 0.35)
    )
    .force("charge", d3.forceManyBody()
      .strength(d => d.type === "document" ? -550 : -110)
      .distanceMax(600)
    )
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collide", d3.forceCollide().radius(d => (d.radius || 8) + 12).iterations(2));

  // Render Links
  const linkGroup = rootG.append("g").attr("class", "graph-links");
  const linkElements = linkGroup.selectAll("line")
    .data(links)
    .join("line")
    .attr("class", d => `graph-link link-${d.type}`)
    .style("display", d => (!showDocLinks && d.type === "contains" ? "none" : null));

  // Render Nodes
  const nodeGroup = rootG.append("g").attr("class", "graph-nodes");
  const nodeElements = nodeGroup.selectAll("g")
    .data(nodes)
    .join("g")
    .attr("class", d => `graph-node node-type-${d.type}`)
    .call(d3.drag()
      .on("start", (event, d) => {
        if (!event.active) graphSimulation.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) graphSimulation.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      })
    );

  // Circles
  nodeElements.append("circle")
    .attr("r", d => d.radius || (d.type === "document" ? 18 : 8))
    .attr("class", d => d.type === "document" ? "node-doc" : "node-fact");

  // Labels
  nodeElements.append("text")
    .attr("class", d => `node-label ${d.type === "document" ? "doc-label" : ""}`)
    .attr("dy", d => (d.radius || 8) + 13)
    .text(d => {
      if (d.type === "document") {
        return d.label.length > 24 ? d.label.substring(0, 22) + "..." : d.label;
      }
      return d.label;
    });

  // Obsidian-style Hover Interaction
  nodeElements
    .on("mouseenter", (event, d) => {
      nodeElements
        .classed("dimmed", n => !isConnected(d, n))
        .classed("highlighted", n => isConnected(d, n));

      linkElements
        .classed("dimmed", l => {
          const s = l.source.id || l.source;
          const t = l.target.id || l.target;
          return s !== d.id && t !== d.id;
        })
        .classed("highlighted", l => {
          const s = l.source.id || l.source;
          const t = l.target.id || l.target;
          return s === d.id || t === d.id;
        });
    })
    .on("mouseleave", () => {
      nodeElements.classed("dimmed", false).classed("highlighted", false);
      linkElements.classed("dimmed", false).classed("highlighted", false);
    })
    .on("click", (event, d) => {
      event.stopPropagation();
      openNodeInspector(d, links);
    });

  // Simulation tick
  graphSimulation.on("tick", () => {
    linkElements
      .attr("x1", d => d.source.x)
      .attr("y1", d => d.source.y)
      .attr("x2", d => d.target.x)
      .attr("y2", d => d.target.y);

    nodeElements
      .attr("transform", d => `translate(${d.x},${d.y})`);
  });
}

function openNodeInspector(node, allLinks) {
  const inspector = document.getElementById("node-inspector");
  const badge = document.getElementById("inspector-badge");
  const body = document.getElementById("inspector-body");
  if (!inspector || !body) return;

  inspector.classList.remove("hidden");

  if (node.type === "document") {
    if (badge) {
      badge.textContent = "Document Hub";
      badge.style.background = "rgba(129, 140, 248, 0.15)";
      badge.style.color = "#818cf8";
      badge.style.borderColor = "rgba(129, 140, 248, 0.4)";
    }

    body.innerHTML = `
      <div class="inspector-main-line">
        <h3 style="color: #f8fafc; font-size: 16px; margin-bottom: 6px; word-break: break-all;">${escapeHtml(node.label)}</h3>
        <span class="inspector-attr">PDF Source File</span>
      </div>

      <div class="inspector-meta-row">
        <span class="meta-chip">Facts Extracted: <strong>${node.facts_count || 0}</strong></span>
        <span class="meta-chip">Doc ID: ${node.id.substring(0, 8)}...</span>
      </div>

      <div class="inspector-evidence" style="border-left-color: #818cf8;">
        Click any associated fact node (gray particle connected to this hub) to view its verbatim textual evidence, extracted metrics, and cross-document reasoning relationships.
      </div>
    `;
  } else {
    // Fact Node
    if (badge) {
      badge.textContent = "Grounded Fact Node";
      badge.style.background = "rgba(56, 189, 248, 0.15)";
      badge.style.color = "var(--accent-cyan)";
      badge.style.borderColor = "rgba(56, 189, 248, 0.3)";
    }

    // Find relationships involving this fact
    const factLinks = (allLinks || []).filter(l => {
      const s = l.source.id || l.source;
      const t = l.target.id || l.target;
      return (s === node.id || t === node.id) && l.type !== "contains";
    });

    let relationshipsHtml = "";
    if (factLinks.length > 0) {
      relationshipsHtml = `
        <div class="inspector-relations-section">
          <strong style="color: var(--text-primary); font-size: 12px;">Cross-Document Relationships (${factLinks.length}):</strong>
          ${factLinks.map(l => {
            const relType = l.type;
            const badgeClass = relType === "corroborates" ? "badge-corrob" : (relType === "contradicts" ? "badge-contradict" : "badge-context");
            const label = relType === "corroborates" ? "Corroborates" : (relType === "contradicts" ? "Contradicts" : "Context Explained");
            return `
              <div class="inspector-rel-item">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
                  <span class="relationship-badge ${badgeClass}">${label}</span>
                  ${l.confidence ? `<span style="font-size: 10px; color: var(--text-muted); font-family: var(--font-mono);">${Math.round(l.confidence * 100)}% conf</span>` : ""}
                </div>
                <div style="color: var(--text-secondary); font-size: 11px; line-height: 1.4;">
                  ${escapeHtml(l.explanation || "No explanation provided.")}
                </div>
              </div>
            `;
          }).join("")}
        </div>
      `;
    } else {
      relationshipsHtml = `
        <div class="inspector-relations-section">
          <div style="color: var(--text-muted); font-size: 11px; font-style: italic;">
            Standalone fact &mdash; No conflicting or corroborating statements found across other uploaded documents.
          </div>
        </div>
      `;
    }

    body.innerHTML = `
      <div class="inspector-main-line">
        <span class="inspector-entity">${escapeHtml(node.entity || "Entity")}</span>
        <span class="inspector-attr">${escapeHtml(node.attribute || "Attribute")}</span>
      </div>

      <div class="inspector-value">
        ${escapeHtml(node.value || "")} <span style="font-size: 13px; color: var(--text-muted); font-weight: normal;">${escapeHtml(node.unit || "")}</span>
      </div>

      <div class="inspector-meta-row">
        <span class="meta-chip">Source: <strong>${escapeHtml(node.document_filename || "PDF")}</strong></span>
        <span class="meta-chip">Page: <strong>${node.page_number || 1}</strong></span>
        ${node.time_scope ? `<span class="meta-chip">Time: <strong>${escapeHtml(node.time_scope)}</strong></span>` : ""}
        ${node.confidence ? `<span class="meta-chip">Conf: <strong>${Math.round(node.confidence * 100)}%</strong></span>` : ""}
      </div>

      <div>
        <div style="font-size: 11px; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.04em; margin-bottom: 4px;">Verbatim Source Grounding</div>
        <div class="inspector-evidence">
          &ldquo;${escapeHtml(node.raw_text || "No verbatim evidence available.")}&rdquo;
        </div>
      </div>

      ${relationshipsHtml}
    `;
  }
}

function closeNodeInspector() {
  const inspector = document.getElementById("node-inspector");
  if (inspector) inspector.classList.add("hidden");
}
