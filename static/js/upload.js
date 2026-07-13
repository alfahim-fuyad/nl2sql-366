// static/js/upload.js

dropZone.addEventListener("click", () => fileInput.click());

dropZone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropZone.classList.add("dragover");
});

dropZone.addEventListener("dragleave", () => {
  dropZone.classList.remove("dragover");
});

dropZone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropZone.classList.remove("dragover");
  const file = e.dataTransfer.files[0];
  if (file) uploadFile(file);
});

fileInput.addEventListener("change", () => {
  if (fileInput.files[0]) uploadFile(fileInput.files[0]);
});

changeBtn.addEventListener("click", (e) => {
  e.stopPropagation();
  fileInput.click();
});

function uploadFile(file) {
  document.getElementById("global-error").style.display = "none";
  const fileName = file.name.toLowerCase();

  if (
    !fileName.endsWith(".csv") &&
    !fileName.endsWith(".xlsx") &&
    !fileName.endsWith(".xls")
  ) {
    showGlobalError(
      "Only CSV and Excel (.csv, .xlsx, .xls) files are supported.",
    );
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
    .then((r) => r.json())
    .then((data) => {
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
    "<tr>" +
    columns.map((c) => `<th>${escHtml(String(c))}</th>`).join("") +
    "</tr>";

  document.getElementById("preview-tbody").innerHTML = rows
    .map(
      (row) =>
        "<tr>" +
        row
          .map(
            (cell) =>
              `<td>${escHtml(cell === null || cell === undefined ? "" : String(cell))}</td>`,
          )
          .join("") +
        "</tr>",
    )
    .join("");
}
