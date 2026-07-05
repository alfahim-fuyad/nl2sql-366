/* nl2sql — main application logic */

const dropZone      = document.getElementById("drop-zone");
const fileInput     = document.getElementById("file-input");
const uploadInfo    = document.getElementById("upload-info");
const uploadFilename = document.getElementById("upload-filename");
const uploadMeta    = document.getElementById("upload-meta");
const changeBtn     = document.getElementById("change-file-btn");
const querySection  = document.getElementById("query-section");
const questionInput = document.getElementById("question-input");
const askBtn        = document.getElementById("ask-btn");
const sqlBlock      = document.getElementById("sql-block");
const sqlOutput     = document.getElementById("sql-output");
const intentLabel   = document.getElementById("intent-label");
const errorBox      = document.getElementById("error-box");
const resultsBlock  = document.getElementById("results-block");
const resultsMeta   = document.getElementById("results-meta");
const resultsThead  = document.getElementById("results-thead");
const resultsTbody  = document.getElementById("results-tbody");

// ── File upload ──────────────────────────────────────────────────────────────

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", e => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", e => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

changeBtn.addEventListener("click", e => {
  e.stopPropagation();
  fileInput.click();
});

function uploadFile(file) {
  document.getElementById("global-error").style.display = "none";

  if (!file.name.toLowerCase().endsWith(".csv")) {
    showGlobalError("Only CSV files are supported.");
    return;
  }

  dropZone.style.display = "none";
  uploadInfo.style.display = "flex";
  uploadFilename.innerHTML = `<strong>${escHtml(file.name)}</strong>`;
  uploadMeta.textContent = "Uploading…";
  querySection.style.display = "none";
  clearResults();

  const form = new FormData();
  form.append("file", file);

  fetch("/upload", { method: "POST", body: form })
    .then(r => r.json())
    .then(data => {
      if (data.error) {
        resetUpload();
        showGlobalError(data.error);
        return;
      }
      uploadMeta.textContent = `${data.rows.toLocaleString()} rows · ${data.columns.length} columns`;
      renderPreview(data.columns, data.preview, data.rows);
      document.getElementById("preview-section").style.display = "block";
      querySection.style.display = "block";
      questionInput.focus();
    })
    .catch(() => {
      resetUpload();
      showGlobalError("Upload failed. Please try again.");
    });
}

function resetUpload() {
  dropZone.style.display = "";
  uploadInfo.style.display = "none";
  fileInput.value = "";
  document.getElementById("preview-section").style.display = "none";
  document.getElementById("preview-thead").innerHTML = "";
  document.getElementById("preview-tbody").innerHTML = "";
}

function renderPreview(columns, rows, totalRows) {
  document.getElementById("preview-meta").innerHTML =
    `Showing first <strong>${rows.length}</strong> of <strong>${totalRows.toLocaleString()}</strong> rows`;

  document.getElementById("preview-thead").innerHTML =
    "<tr>" + columns.map(c => `<th>${escHtml(String(c))}</th>`).join("") + "</tr>";

  document.getElementById("preview-tbody").innerHTML = rows.map(row =>
    "<tr>" + row.map(cell =>
      `<td>${escHtml(cell === null || cell === undefined ? "" : String(cell))}</td>`
    ).join("") + "</tr>"
  ).join("");
}

// ── Query ────────────────────────────────────────────────────────────────────

askBtn.addEventListener("click", runQuery);
questionInput.addEventListener("keydown", e => { if (e.key === "Enter") runQuery(); });

function runQuery() {
  const question = questionInput.value.trim();
  if (!question) { questionInput.focus(); return; }

  askBtn.disabled = true;
  askBtn.innerHTML = '<span class="spinner"></span>Running…';
  clearResults();

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  })
    .then(r => r.json())
    .then(data => {
      askBtn.disabled = false;
      askBtn.textContent = "Ask";

      if (data.sql) {
        sqlOutput.textContent = data.sql;
        intentLabel.textContent = "Intent: " + (data.intent || "—");
        sqlBlock.style.display = "block";
      }

      if (data.error) {
        showError(data.error);
        return;
      }

      if (data.columns && data.columns.length > 0) {
        renderTable(data.columns, data.rows, data.count);
      } else {
        resultsBlock.style.display = "block";
        resultsMeta.innerHTML = "<strong>0</strong> rows returned.";
        resultsTbody.innerHTML =
          `<tr><td colspan="99" class="no-results">No results found.</td></tr>`;
      }
    })
    .catch(() => {
      askBtn.disabled = false;
      askBtn.textContent = "Ask";
      showError("Request failed. Please try again.");
    });
}

function renderTable(columns, rows, count) {
  resultsBlock.style.display = "block";
  resultsMeta.innerHTML =
    `<strong>${count.toLocaleString()}</strong> row${count !== 1 ? "s" : ""} returned.`;

  resultsThead.innerHTML =
    "<tr>" + columns.map(c => `<th>${escHtml(String(c))}</th>`).join("") + "</tr>";

  if (rows.length === 0) {
    resultsTbody.innerHTML =
      `<tr><td colspan="${columns.length}" class="no-results">No results found.</td></tr>`;
  } else {
    resultsTbody.innerHTML = rows.map(row =>
      "<tr>" + row.map(cell =>
        `<td>${escHtml(cell === null ? "NULL" : String(cell))}</td>`
      ).join("") + "</tr>"
    ).join("");
  }
}

// ── Utilities ────────────────────────────────────────────────────────────────

function showGlobalError(msg) {
  const g = document.getElementById("global-error");
  g.textContent = msg;
  g.style.display = "block";
}

function showError(msg) {
  errorBox.textContent = msg;
  errorBox.style.display = "block";
}

function clearResults() {
  sqlBlock.style.display = "none";
  errorBox.style.display = "none";
  resultsBlock.style.display = "none";
  sqlOutput.textContent = "";
  intentLabel.textContent = "";
  resultsThead.innerHTML = "";
  resultsTbody.innerHTML = "";
  resultsMeta.textContent = "";
}

function escHtml(str) {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Logo — click to reload ────────────────────────────────────────────────────
document.getElementById("logo-btn").addEventListener("click", () => window.location.reload());

// ── Hamburger menu (mobile) ───────────────────────────────────────────────────
const navbar      = document.getElementById("navbar");
const hamburger   = document.getElementById("nav-hamburger");

function closeNav() {
  navbar.classList.remove("nav-open");
  hamburger.setAttribute("aria-expanded", "false");
}

hamburger.addEventListener("click", e => {
  e.stopPropagation();
  const isOpen = navbar.classList.toggle("nav-open");
  hamburger.setAttribute("aria-expanded", String(isOpen));
});

// Close when a nav-link button is clicked on mobile
document.getElementById("nav-links").querySelectorAll("button").forEach(btn => {
  btn.addEventListener("click", () => {
    if (window.innerWidth <= 640) closeNav();
  });
});

// Close on outside click
document.addEventListener("click", e => {
  if (!navbar.contains(e.target)) closeNav();
});

// ── Modals ───────────────────────────────────────────────────────────────────

function openModal(id) {
  document.getElementById(id).classList.add("open");
}

function closeModal(id) {
  document.getElementById(id).classList.remove("open");
}

document.getElementById("about-btn").addEventListener("click", () => openModal("about-modal"));
document.getElementById("help-btn").addEventListener("click", () => openModal("help-modal"));

document.querySelectorAll(".modal-close").forEach(btn => {
  btn.addEventListener("click", () => closeModal(btn.dataset.close));
});

document.querySelectorAll(".modal-overlay").forEach(overlay => {
  overlay.addEventListener("click", e => {
    if (e.target === overlay) closeModal(overlay.id);
  });
});

document.addEventListener("keydown", e => {
  if (e.key === "Escape") {
    closeNav();
    document.querySelectorAll(".modal-overlay.open").forEach(o => closeModal(o.id));
  }
});
