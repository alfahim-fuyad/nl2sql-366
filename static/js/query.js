// static/js/query.js

askBtn.addEventListener("click", runQuery);
questionInput.addEventListener("keydown", (e) => {
  if (e.key === "Enter") runQuery();
});

function runQuery() {
  const question = questionInput.value.trim();
  if (!question) {
    questionInput.focus();
    return;
  }

  askBtn.disabled = true;
  askBtn.innerHTML = '<span class="spinner"></span>Running…';
  clearResults();

  fetch("/ask", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  })
    .then((r) => r.json())
    .then((data) => {
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
        resultsTbody.innerHTML = `<tr><td colspan="99" class="no-results">No results found.</td></tr>`;
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
  resultsMeta.innerHTML = `<strong>${count.toLocaleString()}</strong> row${count !== 1 ? "s" : ""} returned.`;

  resultsThead.innerHTML =
    "<tr>" +
    columns.map((c) => `<th>${escHtml(String(c))}</th>`).join("") +
    "</tr>";

  if (rows.length === 0) {
    resultsTbody.innerHTML = `<tr><td colspan="${columns.length}" class="no-results">No results found.</td></tr>`;
  } else {
    resultsTbody.innerHTML = rows
      .map(
        (row) =>
          "<tr>" +
          row
            .map(
              (cell) =>
                `<td>${escHtml(cell === null ? "NULL" : String(cell))}</td>`,
            )
            .join("") +
          "</tr>",
      )
      .join("");
  }
}
